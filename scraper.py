import logging
import html
import asyncio
import re
import os
import hashlib
from typing import Optional, Set
from datetime import datetime, timedelta, timezone
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from telethon.tl.types import User, Channel, Chat
from aiogram import Bot
from aiogram.types import LinkPreviewOptions

import config
import database
import filters
from bot import get_dispatcher_report_keyboard

logger = logging.getLogger(__name__)

# Qayta ishlanmasligi uchun oxirgi xabarlar ID to'plami va dublikat nazorati
_PROCESSED_MESSAGE_KEYS: Set[str] = set()
_PROCESSED_CARGO_CACHE: dict = {}      # key: cargo_signature, value: timestamp (12 soatlik bir xil e'lon deduplikatsiyasi)
_PHONE_DESTINATIONS: dict = {}          # key: phone_filter (last9/canonical), value: set of distinct destinations (12 soatlik)
_SENDER_DESTINATIONS: dict = {}         # key: sender_id, value: set of distinct destinations (12 soatlik)
_FORWARD_LOCK = asyncio.Lock()

def create_telethon_client() -> TelegramClient:
    """Telethon sessiyasini yaratish (StringSession yoki fayl orqali, cheksiz avto-ulanish bilan)."""
    if getattr(config, "SESSION_STRING", ""):
        session = StringSession(config.SESSION_STRING)
        logger.info("Telethon sessiyasi SESSION_STRING orqali yuklanmoqda.")
    else:
        session_name = "sender_913981059" if os.path.exists("sender_913981059.session") else "logistika_userbot"
        session = session_name
        logger.info(f"Telethon sessiyasi fayldan yuklanmoqda: {session_name}.session")
    return TelegramClient(
        session,
        config.API_ID,
        config.API_HASH,
        connection_retries=None,  # Cheksiz qayta ulanish (internet uzilsa ham to'xtamaydi)
        retry_delay=3,            # 3 soniyada qayta urinish
        auto_reconnect=True,      # Avtomatik ulanish
        timeout=25
    )

def extract_source_url(msg, entity=None) -> Optional[str]:
    """Telethon xabaridan to'g'ridan-to'g'ri Telegram havolasini shakllantirish."""
    try:
        chat = getattr(msg, 'chat', None) or entity
        username = getattr(chat, 'username', None) if chat else None
        if username:
            return f"https://t.me/{username}/{msg.id}"
        peer = getattr(msg, 'peer_id', None)
        if hasattr(peer, 'channel_id') and peer.channel_id:
            return f"https://t.me/c/{peer.channel_id}/{msg.id}"
        chat_id = getattr(msg, 'chat_id', None)
        if chat_id:
            clean_id = str(abs(chat_id))
            if clean_id.startswith("100"):
                clean_id = clean_id[3:]
            return f"https://t.me/c/{clean_id}/{msg.id}"
    except Exception:
        pass
    return None

async def process_single_message(msg, bot: Bot, source_title: str = "", delay: float = 0.5) -> bool:
    """Bitta xabarni AGENTS.md qat'iy standartlari bo'yicha saralash va yuborish."""
    try:
        raw_text = msg.message or ""
        if not raw_text or len(raw_text.strip()) < 15:
            return False

        msg_key = f"{msg.chat_id}_{msg.id}"
        if msg_key in _PROCESSED_MESSAGE_KEYS:
            return False
        _PROCESSED_MESSAGE_KEYS.add(msg_key)
        if len(_PROCESSED_MESSAGE_KEYS) > 15000:
            _PROCESSED_MESSAGE_KEYS.clear()

        # 1. Forward qilinganmi (AGENTS.md: boshqa joydan uzatilgan bo'lsa - o'chiriladi)
        if bool(msg.forward):
            return False

        # 2. Jo'natuvchi ma'lumotlarini olish
        sender = getattr(msg, 'sender', None)
        if sender is None and msg.sender_id:
            try:
                sender = await asyncio.wait_for(msg.get_sender(), timeout=3.5)
            except Exception:
                try:
                    if hasattr(msg, 'client') and msg.client:
                        sender = await msg.client.get_entity(msg.sender_id)
                except Exception:
                    sender = None
        sender_id = str(msg.sender_id or "")

        first_name = ""
        last_name = ""
        username = ""

        if isinstance(sender, User):
            first_name = sender.first_name or ""
            last_name = sender.last_name or ""
            # Barcha asosiy va qo'shimcha usernamelarni yig'ish
            all_usernames = []
            if sender.username:
                all_usernames.append(sender.username)
            if hasattr(sender, 'usernames') and sender.usernames:
                for u_obj in sender.usernames:
                    u_val = getattr(u_obj, 'username', '') if hasattr(u_obj, 'username') else str(u_obj)
                    if u_val and u_val not in all_usernames:
                        all_usernames.append(u_val)
            username = " ".join(all_usernames)
        elif isinstance(sender, (Channel, Chat)):
            # Kanal yoki guruh nomidan yozilgan bo'lsa - bu zakazchi emas
            return False

        # 2.0. Telegram Premium tekshiruvi (Foydalanuvchi qoidasi: Premium akkauntlar dispetcher/reklama hisoblanadi va o'tkazilmaydi)
        has_custom_emoji = False
        if hasattr(msg, 'entities') and msg.entities:
            from telethon.tl.types import MessageEntityCustomEmoji
            has_custom_emoji = any(isinstance(e, MessageEntityCustomEmoji) for e in msg.entities)

        is_premium = bool(
            getattr(sender, 'premium', False)
            or getattr(sender, 'emoji_status', None) is not None
            or has_custom_emoji
        )
        if is_premium:
            logger.info(f"Telegram Premium akkaunt aniqlandi (chetlatildi): {sender_id} ({first_name} {last_name} | @{username})")
            if sender_id:
                await database.block_sender(sender_id, f"{first_name} {last_name}".strip(), "Telegram Premium akkaunt (dispetcher/reklama)")
            extracted_phone = filters.extract_phone(raw_text)
            if sender_id.isdigit():
                asyncio.create_task(database.add_outreach_lead(
                    user_id=int(sender_id),
                    username=username,
                    first_name=first_name,
                    last_name=last_name,
                    phone=extracted_phone,
                    reason="Telegram Premium akkaunt",
                    message_snippet=raw_text,
                    source_group=source_title
                ))
            return False

        # 2.1. Profil nomida dispetcher/logist belgisi yoki qisqartmalari (LOG65, Лог65, disp, disper va h.k.)
        disp_profile_ok, disp_profile_reason = filters.check_dispatcher_profile_name(first_name, last_name, username)
        if not disp_profile_ok:
            logger.info(f"Dispetcher/logist profili aniqlandi: {disp_profile_reason} ({first_name} {last_name} | @{username} | ID: {sender_id})")
            if sender_id:
                await database.block_sender(sender_id, f"{first_name} {last_name}".strip(), disp_profile_reason)
            extracted_phone = filters.extract_phone(raw_text)
            if extracted_phone:
                await database.block_sender(extracted_phone, f"{first_name} {last_name}".strip(), "Dispetcher raqami")
            if sender_id.isdigit():
                asyncio.create_task(database.add_outreach_lead(
                    user_id=int(sender_id),
                    username=username,
                    first_name=first_name,
                    last_name=last_name,
                    phone=extracted_phone,
                    reason=disp_profile_reason,
                    message_snippet=raw_text,
                    source_group=source_title
                ))
            return False

        # 2.2. Ayol profillar va ayol username'lar (AGENTS.md 7-band: ayol ismlari, familiyalari yoki belgilari)
        sender_prof_ok, sender_prof_reason = filters.check_sender_profile(first_name, last_name, username)
        if not sender_prof_ok:
            logger.info(f"Ayol profili yoki taqiqlangan profil aniqlandi: {sender_prof_reason} ({first_name} {last_name} | @{username} | ID: {sender_id})")
            if sender_id:
                await database.block_sender(sender_id, f"{first_name} {last_name}".strip(), sender_prof_reason)
            extracted_phone = filters.extract_phone(raw_text)
            if extracted_phone:
                await database.block_sender(extracted_phone, f"{first_name} {last_name}".strip(), "Dispetcher raqami")
            if sender_id.isdigit():
                asyncio.create_task(database.add_outreach_lead(
                    user_id=int(sender_id),
                    username=username,
                    first_name=first_name,
                    last_name=last_name,
                    phone=extracted_phone,
                    reason=sender_prof_reason,
                    message_snippet=raw_text,
                    source_group=source_title
                ))
            return False

        # 3. Jo'natuvchi bazada bloklanganmi
        if await database.is_sender_blocked(sender_id):
            return False

        # 3.1. Telefon raqami dastlabki tekshiruvda qora ro'yxatda bormi (bloklangan dispetcher)
        pre_phone = filters.extract_phone(raw_text)
        if pre_phone and await database.is_sender_blocked(pre_phone):
            logger.debug(f"Qora ro'yxatdagi dispetcher raqami chetlatildi: {pre_phone}")
            return False

        # 4. AGENTS.md filtrlardan o'tkazish
        is_valid, reason, cargo_data = filters.filter_cargo_message(
            text=raw_text,
            is_forward=False,
            first_name=first_name,
            last_name=last_name,
            username=username
        )

        clean_preview = raw_text.replace("\n", " ")[:40]
        if not is_valid:
            logger.debug(f"Filtrdan o'tmadi ({reason}): {clean_preview}")
            # Botlarni qat'iyan chetlatamiz (Cleanrobot, Spambot va h.k.)
            is_bot = (
                getattr(sender, 'bot', False) 
                or (username and (username.lower().endswith('bot') or 'robot' in username.lower()))
                or ('bot' in first_name.lower())
            )
            # Faqat haqiqiy tirik odamlar va aniq dispetcherlik stop-filtrlari
            if not is_bot and sender_id.isdigit() and isinstance(sender, User):
                disp_keywords = ("keshbek", "otkat", "termin", "telefon", "dispetcher", "spambot")
                extracted_phone = (cargo_data.get("phone") if cargo_data else None) or filters.extract_phone(raw_text)
                has_phone = bool(extracted_phone)
                # Aniq dispetcher so'zlari yoki telefon raqami bor bo'lib uzun matn/ko'p yo'nalish bo'lsa
                if any(k in reason.lower() for k in disp_keywords) or (has_phone and "ko'p yo'nalish" in reason.lower()) or has_phone:
                    asyncio.create_task(database.add_outreach_lead(
                        user_id=int(sender_id),
                        username=username,
                        first_name=first_name,
                        last_name=last_name,
                        phone=extracted_phone,
                        reason=reason,
                        message_snippet=raw_text,
                        source_group=source_title
                    ))
            return False

        phone = cargo_data.get("phone")
        if not phone:
            return False

        # 5. Telefon raqami ham bloklanganlar ro'yxatida bormi
        if await database.is_sender_blocked(phone):
            return False

        # 6. Raqam va Akkaunt mezonlari:
        # A. Ayni bir xil e'lonni (telefon + yo'nalish + matn hash'i) 12 soat ichida takror yuborish taqiqlanadi (deduplikatsiya).
        # B. Haqiqiy yukchida 2 tagacha har xil yo'nalish bo'lishi mumkin (ruxsat beriladi).
        # C. 3 va undan ortiq har xil yo'nalish bo'lsa dispetcher deb hisoblanadi va bloklanadi.
        # D. Bir xil e'lonni ko'p guruhga tashlash dispetcherlik belgisi emas (bloklanmaydi, faqat takroriy yuborish to'xtatiladi).
        dest_text = " ➡️ ".join([d.title() for d in cargo_data["destinations"]])
        dest_norm = dest_text.lower().replace(" ", "")
        canonical_phone = cargo_data.get("phone", "")
        phone_digits = re.sub(r"\D", "", str(canonical_phone))
        phone_filter = phone_digits[-9:] if len(phone_digits) >= 9 else str(canonical_phone)

        # Yuk matni hash'i (harf, raqam va asosiy mazmun bo'yicha)
        cargo_hash = hashlib.md5(raw_text.strip().lower().encode("utf-8")).hexdigest()[:8]
        cargo_signature = f"{canonical_phone}_{dest_norm}_{cargo_hash}"
        now_ts = asyncio.get_event_loop().time()

        # 1. Tezkor in-memory ayni bir xil e'lon takrorini to'xtatish (bloklanmaydi, yukchi turli guruhlarga tashlashi mumkin)
        if cargo_signature in _PROCESSED_CARGO_CACHE:
            if now_ts - _PROCESSED_CARGO_CACHE[cargo_signature] < (12 * 3600):
                logger.debug(f"12 soatlik takror e'lon cheklandi: {canonical_phone} | {dest_text}")
                return False

        # 2. In-memory yo'nalishlar sonini tekshirish (2 tagacha ruxsat, 3 va undan ortiq bo'lsa dispetcher)
        phone_dests = _PHONE_DESTINATIONS.get(phone_filter, set())
        sender_dests = _SENDER_DESTINATIONS.get(sender_id, set()) if sender_id else set()

        if dest_norm not in phone_dests and len(phone_dests) >= 2:
            logger.info(f"Dispetcher aniqlandi: telefon raqam 3-har xil yo'nalishga e'lon bermoqda ({phone_filter} -> {dest_text})")
            if sender_id:
                await database.block_sender(sender_id, f"{first_name} {last_name}".strip(), "12 soat ichida 3 xil yo'nalishga e'lon bergan dispetcher")
            return False

        if sender_id and dest_norm not in sender_dests and len(sender_dests) >= 2:
            logger.info(f"Dispetcher aniqlandi: akkaunt 3-har xil yo'nalishga e'lon bermoqda ({sender_id} -> {dest_text})")
            await database.block_sender(sender_id, f"{first_name} {last_name}".strip(), "12 soat ichida 3 xil yo'nalishga e'lon bergan dispetcher")
            return False

        # 3. Database orqali 12 soatlik qat'iy tekshiruv (Deduplikatsiya va 3-yo'nalish qoidasi)
        can_send_cargo, cargo_check_reason = await database.check_cargo_forward_eligibility(
            sender_id=sender_id,
            phone=canonical_phone,
            cargo_signature=cargo_signature,
            dest_text=dest_text,
            hours=12
        )
        if not can_send_cargo:
            logger.debug(f"12 soatlik tekshiruvdan o'tmadi ({cargo_check_reason}): {canonical_phone} | {sender_id}")
            if "dispetcher" in cargo_check_reason.lower():
                if sender_id:
                    await database.block_sender(
                        sender_id=sender_id,
                        sender_name=f"{first_name} {last_name}".strip(),
                        reason=cargo_check_reason
                    )
                if sender_id.isdigit():
                    asyncio.create_task(database.add_outreach_lead(
                        user_id=int(sender_id),
                        username=username,
                        first_name=first_name,
                        last_name=last_name,
                        phone=canonical_phone,
                        reason=cargo_check_reason,
                        message_snippet=raw_text,
                        source_group=source_title
                    ))
            return False

        # 7. AGENTS.md 5-band: Spambot / chastota tekshiruvi
        if await database.is_sender_spammer(sender_id, canonical_phone):
            if sender_id:
                await database.block_sender(
                    sender_id=sender_id,
                    sender_name=f"{first_name} {last_name}".strip(),
                    reason="Spambot chastotasi (qisqa vaqtda guruhlarga qayta-qayta tashlagan dispetcher)"
                )
            logger.info(f"Dispetcher spambot aniqlandi: {sender_id} | Tel: {canonical_phone}")
            return False

        # 8. Faollikni qayd qilish:
        primary_dest = cargo_data["destinations"][0] if cargo_data["destinations"] else "noma'lum"
        await database.log_sender_activity(sender_id, primary_dest, phone=canonical_phone, cargo_signature=cargo_signature)
        await database.log_sender_activity(canonical_phone, primary_dest, phone=canonical_phone, cargo_signature=cargo_signature)

        dest_count = await database.get_sender_distinct_destinations_today(sender_id) if sender_id else 0
        phone_dest_count = await database.get_sender_distinct_destinations_today(canonical_phone) if canonical_phone else 0
        max_dest_count = max(dest_count, phone_dest_count)
        if max_dest_count >= 3:
            if sender_id:
                await database.block_sender(
                    sender_id=sender_id,
                    sender_name=f"{first_name} {last_name}".strip(),
                    reason=f"Bir kunda {max_dest_count} ta har xil viloyatga e'lon berdi (dispetcher chastotasi)"
                )
            logger.info(f"Dispetcher bloklandi: {sender_id} | Tel: {canonical_phone} ({max_dest_count} ta viloyat)")
            return False

        dest_text = " ➡️ ".join([d.title() for d in cargo_data["destinations"]])
        cargo_text_safe = html.escape(cargo_data["original_text"])
        phone_display = filters.format_phone_display(canonical_phone)
        phone_safe = html.escape(phone_display)
        chat = getattr(msg, 'chat', None)
        if chat is None and hasattr(msg, 'get_chat'):
            try:
                chat = await asyncio.wait_for(msg.get_chat(), timeout=1.5)
            except Exception:
                chat = None
        source_url = extract_source_url(msg, entity=chat)
        details = cargo_data.get("details") or filters.extract_cargo_details(cargo_data["original_text"])

        is_truck = cargo_data.get("is_truck_offer", False)
        header_title = "🚚 <b>BO'SH MASHINA (Haydovchi)</b>" if is_truck else "🚛 <b>YANGI YUK E'LONI (Birinchi qo'l)</b>"

        post_lines = [
            f"{header_title}",
            f"📍 <b>Yo'nalish:</b> {dest_text}"
        ]
        if details.get("tonnage"):
            post_lines.append(f"⚖️ <b>Vazn:</b> {details['tonnage']}")
        if details.get("truck_type"):
            post_lines.append(f"🚛 <b>Mashina:</b> {details['truck_type']}")
        if details.get("goods"):
            post_lines.append(f"📦 <b>Mahsulot:</b> {details['goods']}")
        if details.get("price"):
            post_lines.append(f"💰 <b>Narx:</b> {details['price']}")

        post_lines.append(f"📞 <b>Aloqa uchun raqam:</b> <code>{phone_safe}</code>")
        post_lines.append("")
        post_lines.append("📝 <b>E'lon matni:</b>")
        post_lines.append(f"<i>{cargo_text_safe}</i>")

        if source_url:
            post_lines.append("")
            post_lines.append(f'🔗 <a href="{source_url}">Xabarni ko\'rish »</a>')

        post_lines.append("")
        post_lines.append("⚠️ <i>Dispetcher e'loni bo'lsa, pastdagi tugmani bosing (qora ro'yxatga kiritiladi)!</i>")

        formatted_post = "\n".join(post_lines)

        # Yopiq guruhga yuborish
        if config.PRIVATE_GROUP_ID != 0:
            async with _FORWARD_LOCK:
                now_ts = asyncio.get_event_loop().time()

                # Qulf ichida in-memory takroriy tekshiruv:
                if cargo_signature in _PROCESSED_CARGO_CACHE:
                    if now_ts - _PROCESSED_CARGO_CACHE[cargo_signature] < (12 * 3600):
                        return False

                # Qulf ichida takroriy tekshiruv (boshqa coroutine ayni vaqtda yuborgan bo'lsa)
                can_send_cargo, cargo_check_reason = await database.check_cargo_forward_eligibility(
                    sender_id=sender_id,
                    phone=canonical_phone,
                    cargo_signature=cargo_signature,
                    dest_text=dest_text,
                    hours=12
                )
                if not can_send_cargo:
                    return False

                sent = False
                for attempt in range(3):
                    try:
                        await bot.send_message(
                            chat_id=config.PRIVATE_GROUP_ID,
                            text=formatted_post,
                            reply_markup=get_dispatcher_report_keyboard(sender_id=sender_id, source_url=source_url),
                            parse_mode="HTML",
                            link_preview_options=LinkPreviewOptions(is_disabled=True)
                        )
                        sent = True
                        break
                    except Exception as send_err:
                        err_str = str(send_err)
                        if "retry after" in err_str.lower() or "flood control" in err_str.lower():
                            m = re.search(r"retry after (\d+)", err_str, re.IGNORECASE)
                            wait_sec = (int(m.group(1)) + 1) if m else 5
                            logger.warning(f"Telegram flood cheklovi: {wait_sec} soniya kutilmoqda...")
                            await asyncio.sleep(wait_sec)
                        elif attempt < 2:
                            logger.warning(f"Bot API orqali yuborishda vaqtinchalik xatolik ({send_err}), qayta urinilmoqda ({attempt+1}/3)...")
                            await asyncio.sleep(1.5)
                        else:
                            raise send_err

                if sent:
                    _PROCESSED_CARGO_CACHE[cargo_signature] = now_ts
                    _PHONE_DESTINATIONS.setdefault(phone_filter, set()).add(dest_norm)
                    if sender_id:
                        _SENDER_DESTINATIONS.setdefault(sender_id, set()).add(dest_norm)
                    if len(_PROCESSED_CARGO_CACHE) > 5000:
                        _PROCESSED_CARGO_CACHE.clear()

                    # Uzatilgan toza yukni doimiy bazaga va kunlik hisobga kiritish
                    await database.log_forwarded_cargo(
                        destinations=dest_text,
                        phone=canonical_phone,
                        source_title=source_title,
                        sender_id=sender_id,
                        cargo_signature=cargo_signature
                    )
                    logger.info(f"✅ HAQIQIY ZAKAZCHI YUBORILDI: {dest_text} | Tel: {canonical_phone} ({phone_display}) (Manba: {source_title})")
                    if delay > 0:
                        await asyncio.sleep(delay)
                    return True

        return False

    except Exception as e:
        logger.error(f"Xabarni qayta ishlashda xatolik: {e}")
        return False

async def scan_12_hours_history(client: TelegramClient, bot: Bot, resolved_entities):
    """Oxirgi 12 soat ichidagi yangi yuklarni tahlil qilib yopiq guruhga yuborish."""
    cutoff = datetime.now(timezone.utc) - timedelta(hours=12)
    logger.info(f"Oxirgi 12 soatlik xabarlarni tahlil qilish boshlandi (Chegara: {cutoff.strftime('%Y-%m-%d %H:%M UTC')})...")

    total_scanned = 0
    total_found = 0

    for ent in resolved_entities:
        title = getattr(ent, 'title', '')
        try:
            logger.info(f"12 soatlik tahlil o'tkazilmoqda: {title}...")
            async for msg in client.iter_messages(ent, limit=200):
                if not msg.date:
                    continue
                if msg.date < cutoff:
                    break
                total_scanned += 1
                sent = await process_single_message(msg, bot, title, delay=1.2)
                if sent:
                    total_found += 1
                await asyncio.sleep(0.1)
        except Exception as e:
            logger.warning(f"12 soatlik tahlilda guruhda xatolik ({title}): {e}")

    logger.info(f"12 soatlik tahlil yakunlandi! Jami tekshirildi: {total_scanned} ta, guruhga yuborildi: {total_found} ta toza yuk.")

async def start_scraper(client: TelegramClient, bot: Bot):
    """Scraperni ishga tushirish (dialoglarni uyg'otish, event listener va faol kuzatuv)."""
    logger.info("Scraper faollashtirilmoqda...")

    resolved_entities = []
    valid_chat_ids = set()

    try:
        await client.get_dialogs(limit=50)
        logger.info("Dialoglar muvaffaqiyatli uyg'otildi.")
    except Exception as e:
        logger.warning(f"Dialoglarni uyg'otishda xatolik: {e}")

    # 12 soat ichida yuborilgan e'lonlar va yo'nalishlarni keshga oldindan yuklash
    try:
        now_t = asyncio.get_event_loop().time()
        recent_cargos = await database.get_recent_forwarded_cargos_info(hours=12)
        for rc in recent_cargos:
            sig = rc.get("cargo_signature")
            if sig:
                _PROCESSED_CARGO_CACHE[sig] = now_t
            p_val = rc.get("phone") or ""
            p_dig = re.sub(r"\D", "", str(p_val))
            p_f = p_dig[-9:] if len(p_dig) >= 9 else str(p_val)
            d_val = (rc.get("destinations") or "").lower().replace(" ", "")
            s_val = str(rc.get("sender_id") or "")
            if p_f and d_val:
                _PHONE_DESTINATIONS.setdefault(p_f, set()).add(d_val)
            if s_val and d_val and s_val not in ("None", "0", ""):
                _SENDER_DESTINATIONS.setdefault(s_val, set()).add(d_val)

        logger.info(f"So'nggi 12 soatda e'lon yuborilgan {len(_PROCESSED_CARGO_CACHE)} ta e'lon va {len(_PHONE_DESTINATIONS)} ta raqam yo'nalishlari keshga yuklandi.")
    except Exception as e_cache:
        logger.warning(f"12 soatlik keshni yuklashda xatolik: {e_cache}")

    # ⚡️ VIP Manba (@yuk_markazi_gruupa) ni KUNI-TUN DOIMIY KUZATUVGA OLISH (Faqat jim kuzatish, xabar yozmasdan)
    async def start_vip_instant_monitor():
        target_username = "yuk_markazi_gruupa"
        vip_client = client

        # 1. Asosiy client (logistika_userbot) orqali tekshirish
        vip_ent = None
        try:
            vip_ent = await client.get_entity(target_username)
            # Test xabar o'qish imkoniyatini tekshirish
            async for _ in client.iter_messages(vip_ent, limit=1):
                pass
            logger.info(f"✅ @{target_username} asosiy akkaunt (logistika_userbot) orqali ulandi!")
        except Exception as e_main:
            logger.info(f"Asosiy akkauntda @{target_username} cheklovi mavjud ({e_main}). 2-akkaunt (outreach_userbot) orqali ulanmoqda...")
            vip_ent = None

        # 2. Agar asosiy akkaunt cheklangan bo'lsa, 2-akkaunt (outreach_userbot) orqali ulaymiz
        if vip_ent is None and os.path.exists("outreach_userbot.session"):
            try:
                vip_client = TelegramClient("outreach_userbot", config.API_ID, config.API_HASH)
                await vip_client.connect()
                if await vip_client.is_user_authorized():
                    vip_ent = await vip_client.get_entity(target_username)
                    logger.info(f"⚡️ @{target_username} 2-akkaunt (outreach_userbot) orqali muvaffaqiyatli ulandi!")
            except Exception as e_sec:
                logger.error(f"2-akkaunt orqali ulanishda xatolik: {e_sec}")
                vip_ent = None

        if not vip_ent:
            logger.error(f"❌ VIP manba (@{target_username}) yuklanmadi!")
            return

        real_id = getattr(vip_ent, 'id', 1234214428)
        real_title = getattr(vip_ent, 'title', '') or '🌏YUK_🎯markazi🇺🇿'

        # Guruhni ovozsiz qilish (mute)
        try:
            from telethon.tl.types import InputPeerChannel
            from telethon.tl.functions.account import UpdateNotifySettingsRequest
            from telethon.tl.types import InputPeerNotifySettings
            acc_h = getattr(vip_ent, 'access_hash', 0)
            if acc_h:
                await vip_client(UpdateNotifySettingsRequest(
                    peer=InputPeerChannel(real_id, acc_h),
                    settings=InputPeerNotifySettings(mute_until=2147483647)
                ))
        except Exception:
            pass

        if real_id:
            valid_chat_ids.add(real_id)
            valid_chat_ids.add(-real_id)
            valid_chat_ids.add(-1000000000000 - real_id if real_id > 0 else real_id)

        if vip_ent not in resolved_entities:
            resolved_entities.append(vip_ent)

        logger.info(f"⚡️ [VIP MANBA — KUZATUV] @{target_username} ({real_title} | ID: {real_id}) 24/7 TO'LIQ KUZATUVGA OLINDI!")

        # Dastlabki so'nggi 25 ta xabarni ko'rib, eng yangi ID ni qayd qilish
        last_max_id = 0
        try:
            async for msg in vip_client.iter_messages(vip_ent, limit=25):
                if msg.id > last_max_id:
                    last_max_id = msg.id
                await process_single_message(msg, bot, real_title, delay=0.1)
            logger.info(f"✅ @{target_username} manbasidan dastlabki xabarlar muvaffaqiyatli o'qildi (So'nggi ID: {last_max_id})")
        except Exception as init_err:
            logger.warning(f"VIP manba dastlabki o'qishda: {init_err}")

        # Tinimsiz 24/7 har 2.0 soniyada yangi yuklarni tekshirib yopiq guruhga uzatish
        while True:
            try:
                if vip_client.is_connected():
                    new_msgs = []
                    async for msg in vip_client.iter_messages(vip_ent, min_id=last_max_id, limit=30):
                        new_msgs.append(msg)
                        if msg.id > last_max_id:
                            last_max_id = msg.id

                    for msg in reversed(new_msgs):
                        await process_single_message(msg, bot, real_title, delay=0.1)

                await asyncio.sleep(2.0)
            except asyncio.CancelledError:
                break
            except Exception as loop_err:
                err_str = str(loop_err)
                if "flood" in err_str.lower():
                    logger.warning(f"VIP manbada flood-wait: 15 soniya kutilmoqda...")
                    await asyncio.sleep(15)
                else:
                    logger.warning(f"VIP manbani tekshirishda: {loop_err}")
                    await asyncio.sleep(4)

    asyncio.create_task(start_vip_instant_monitor())

    # 1. Akkaunt a'zo bo'lgan barcha guruhlarni to'g'ridan-to'g'ri dialoglardan olish (ResolveUsernameRequest va Flood Waitsiz!)
    try:
        dialogs = await client.get_dialogs()
        for d in dialogs:
            if d.is_channel or d.is_group:
                # O'zimizning yopiq guruhimizni (va logistika botini) scraperdan chetlatamiz
                if config.PRIVATE_GROUP_ID and d.id in (config.PRIVATE_GROUP_ID, int(str(config.PRIVATE_GROUP_ID).replace("-100", ""))):
                    continue
                if d.entity not in resolved_entities:
                    resolved_entities.append(d.entity)
        logger.info(f"Mavjud dialoglardan {len(resolved_entities)} ta guruh va kanal to'liq kuzatuvga ulandi!")
    except Exception as e:
        logger.warning(f"Dialoglardan guruhlarni olishda xatolik: {e}")

    # 2. Foydalanuvchi taqdim etgan barcha target guruhlarni yuklash (user_target_groups.txt va config.SOURCE_GROUPS)
    target_list = list(config.SOURCE_GROUPS or [])
    try:
        if os.path.exists("user_target_groups.txt"):
            with open("user_target_groups.txt", "r", encoding="utf-8") as f:
                for line in f:
                    clean_line = line.strip()
                    if clean_line and not clean_line.startswith("#"):
                        target_list.append(clean_line)
    except Exception as e_f:
        logger.debug(f"user_target_groups.txt o'qishda: {e_f}")

    resolved_ids = {e.id for e in resolved_entities if hasattr(e, 'id')}
    resolved_unames = {e.username.lower() for e in resolved_entities if getattr(e, 'username', None)}

    for g in target_list:
        clean_g = g.lstrip('@').lower()
        if clean_g in resolved_unames:
            continue
        try:
            ent = await client.get_entity(g)
            if ent.id not in resolved_ids:
                # Ochiq guruh bo'lsa a'zo bo'lishga urinish
                try:
                    from telethon.tl.functions.channels import JoinChannelRequest
                    await client(JoinChannelRequest(ent))
                    logger.info(f"✅ Yangi target guruhga muvaffaqiyatli a'zo bo'lindi: @{clean_g}")
                except Exception:
                    pass
                resolved_entities.append(ent)
                resolved_ids.add(ent.id)
                if getattr(ent, 'username', None):
                    resolved_unames.add(ent.username.lower())
                logger.info(f"Qo'shimcha guruh kuzatuvga ulandi: {g} -> ID: {ent.id}")
                # So'nggi xabarlarni darhol tahlil qilish
                try:
                    title = getattr(ent, 'title', '')
                    async for msg in client.iter_messages(ent, limit=15):
                        await process_single_message(msg, bot, title, delay=0.03)
                except Exception:
                    pass
        except Exception as e_ent:
            logger.debug(f"Target guruhni yuklashda ({g}): {e_ent}")

    if not resolved_entities:
        logger.warning("Kuzatiladigan birorta guruh topilmadi!")
        return

    from telethon import utils
    for ent in resolved_entities:
        if hasattr(ent, 'id'):
            valid_chat_ids.add(ent.id)
            try:
                valid_chat_ids.add(utils.get_peer_id(ent))
            except Exception:
                pass

    # 1. Real vaqtdagi yangi xabarlar tinglovchisi (barcha 115+ guruhlarimiz uchun uzluksiz push rejimida)
    @client.on(events.NewMessage())
    async def on_new_msg(event):
        try:
            # Shaxsiy chatlar (lichka) yoki o'zimizning yopiq guruhimiz xabarlarini o'tkazmaymiz
            if event.is_private:
                return
            if config.PRIVATE_GROUP_ID:
                clean_target = int(str(config.PRIVATE_GROUP_ID).replace("-100", ""))
                if event.chat_id in (config.PRIVATE_GROUP_ID, -config.PRIVATE_GROUP_ID, clean_target, -clean_target):
                    return

            title = getattr(event.chat, 'title', '') or ''
            await process_single_message(event.message, bot, title, delay=0.1)
        except Exception as e:
            logger.debug(f"on_new_msg xatolik: {e}")

    # 2. Tezkor aktiv dialoglar skaneri (Telegramda oxirgi xabar kelgan faol guruhlar doim ro'yxat boshida turadi)
    async def fast_recent_dialogs_loop():
        logger.info("⚡️ Tezkor aktiv dialoglar skaneri ishga tushirildi (har 4 soniyada 35 ta faol guruh).")
        while True:
            try:
                if not client.is_connected():
                    await asyncio.sleep(3)
                    continue

                recent_dialogs = await client.get_dialogs(limit=35)
                for d in recent_dialogs:
                    if not (d.is_channel or d.is_group):
                        continue
                    if config.PRIVATE_GROUP_ID and d.id in (config.PRIVATE_GROUP_ID, int(str(config.PRIVATE_GROUP_ID).replace("-100", ""))):
                        continue
                    title = d.title or ""
                    try:
                        async for msg in client.iter_messages(d.entity, limit=8):
                            await process_single_message(msg, bot, title, delay=0.03)
                    except Exception as e_msg:
                        logger.debug(f"Aktiv dialog xabarini o'qishda ({title}): {e_msg}")
                await asyncio.sleep(4.0)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.warning(f"Fast recent dialogs loop xatosi: {e}")
                await asyncio.sleep(5)

    # 3. Doimiy barcha guruhlarni to'liq aylanib chiquvchi fon skanerlash sikli
    async def active_poll_loop():
        logger.info("Doimiy to'liq guruhlar skanerlash sikli ishga tushirildi.")
        last_dialog_check = asyncio.get_event_loop().time()
        while True:
            try:
                if not client.is_connected():
                    try:
                        logger.warning("Telethon aloqasi uzilgan, qayta ulanmoqda...")
                        await client.connect()
                    except Exception as conn_err:
                        logger.debug(f"Telethon qayta ulanish kutilyapti: {conn_err}")
                        await asyncio.sleep(3)
                        continue

                # Har 60 soniyada yangi qo'shilgan guruhlarni avtomatik aniqlash va kuzatuvga olish
                now_t = asyncio.get_event_loop().time()
                if now_t - last_dialog_check > 60:
                    last_dialog_check = now_t
                    try:
                        d_list = await client.get_dialogs(limit=150)
                        added_count = 0
                        for d in d_list:
                            if (d.is_channel or d.is_group) and d.entity not in resolved_entities:
                                if config.PRIVATE_GROUP_ID and d.id in (config.PRIVATE_GROUP_ID, int(str(config.PRIVATE_GROUP_ID).replace("-100", ""))):
                                    continue
                                resolved_entities.append(d.entity)
                                if hasattr(d.entity, 'id'):
                                    valid_chat_ids.add(d.entity.id)
                                added_count += 1
                                # Yangi qo'shilgan guruhdagi yangi xabarlarni darhol saralab yuborish
                                try:
                                    async for msg in client.iter_messages(d.entity, limit=20):
                                        await process_single_message(msg, bot, d.title or "", delay=0.03)
                                except Exception:
                                    pass
                        if added_count > 0:
                            logger.info(f"🆕 Akkauntdan yangi qo'shilgan {added_count} ta guruh avtomatik kuzatuvga ulandi! (Jami: {len(resolved_entities)} ta)")
                    except Exception as diag_err:
                        logger.debug(f"Yangi dialoglarni tekshirishda xatolik: {diag_err}")

                for ent in resolved_entities:
                    try:
                        title = getattr(ent, 'title', '')
                        async for msg in client.iter_messages(ent, limit=15):
                            await process_single_message(msg, bot, title, delay=0.03)
                    except Exception as poll_err:
                        logger.debug(f"Guruhni tekshirishda xatolik ({getattr(ent, 'id', '')}): {poll_err}")
                    await asyncio.sleep(0.25)
                await asyncio.sleep(5)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Faol skanerlashda kutilmagan xatolik: {e}")
                await asyncio.sleep(5)

    # 4. 12 soatlik xabarlarni tahlil qilish (boshlanishda va har 2 soatda)
    async def periodic_12h_scan():
        while True:
            try:
                await scan_12_hours_history(client, bot, resolved_entities)
                await asyncio.sleep(2 * 3600)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"12 soatlik skanerlashda xatolik: {e}")
                await asyncio.sleep(60)

    asyncio.create_task(fast_recent_dialogs_loop())
    asyncio.create_task(active_poll_loop())
    # asyncio.create_task(periodic_12h_scan())
    logger.info("Scraper to'liq jonli (Real vaqt + Fast Dialogs 4s + Barcha guruhlar polli) rejimi bilan faol!")
