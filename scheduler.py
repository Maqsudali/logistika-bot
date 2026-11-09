import asyncio
import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import PRIVATE_GROUP_ID
import database

logger = logging.getLogger(__name__)

def get_group_request_message(name: str = "") -> str:
    name_str = f", <b>{name}</b>" if name and name.lower() not in ("user", "admin", "none", "") else ""
    return (
        f"🤝 <b>QADRLI HAYDOVCHILAR VA YUK ISHTIROKCHILARI{name_str}!</b>\n\n"
        "Bizning asosiy maqsadimiz — sizga Telegramdagi minglab behuda e'lonlar, vositachilar va keshbekchilarsiz, "
        "<b>faqat 1-qo'l haqiqiy zakazchilarning toza yuklarini</b> saralab yetkazishdir.\n\n"
        "💡 <b>Sizdan kichik bir samimiy iltimosimiz bor:</b>\n"
        "Agar siz turli xil Telegram yuk guruhlarida (dispetcherlar va yuk egalari aralash yozadigan ochiq guruhlarda) a'zo bo'lsangiz, "
        "ushbu guruhlarning <b>havolalarini (linklarini)</b> bizga yuborishingizni so'raymiz!\n\n"
        "<b>Bu sizga qanday foyda beradi?</b>\n"
        "✅ Siz yuborgan guruhlardagi yuzlab aralash e'lonlarni maxsus tizimimiz soniya ichida tahlil qiladi;\n"
        "✅ Barcha keshbekchilar, vositachilar va spamerlar filtrlanib, <b>faqat 1-qo'l toza yuklar</b> ajratib olinadi;\n"
        "✅ Va ushbu toza yuklar darhol bizning <b>yopiq guruhimizga</b> uzatib boriladi!\n\n"
        "<i>Natijada o'zingiz ham, boshqa haydovchilar ham bir joyda har kuni yanada ko'proq toza yuklarni topish imkoniga ega bo'lasiz.</i>\n\n"
        "👇 <b>O'zingiz bilgan guruh havolalarini pastdagi tugma orqali adminga yuboring:</b>"
    )

def get_group_request_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🔗 Adminga guruh havolasini yuborish",
                    url="https://t.me/maqsudali_o6"
                )
            ]
        ]
    )

async def check_expiring_trials_1hour(bot: Bot):
    """Sinov muddati tugashiga 1 soat (60 daqiqa) qolganida foydalanuvchilarga ogohlantirish yuborish."""
    try:
        expiring_subs = await database.get_expiring_trial_subscriptions(within_minutes=60)
        if not expiring_subs:
            return

        from config import PRICE_WEEK, PRICE_MONTH, ADMIN_ID

        for sub in expiring_subs:
            sub_id = sub["id"]
            uid = sub["user_id"]
            if uid == ADMIN_ID or uid == 8258153060:
                continue

            try:
                alert_text = (
                    "🚨 <b>DIQQAT! BEPUL SINOV MUDDATINGIZ TUGASHIGA 1 SOAT QOLDI!</b> ⏳\n"
                    "━━━━━━━━━━━━━━━━━━━━\n"
                    "👋 <b>Hurmatli hamkor!</b>\n\n"
                    "Sizning <b>FEMMORA LOGISTIKA</b> yopiq guruhimizdan bepul foydalanish sinov muddatingiz "
                    "<b>1 soatdan so'ng</b> to'liq yakunlanadi!\n\n"
                    "Guruh tizimi 1 soatdan keyin obunani yangilamagan a'zolarni avtomatik chetlatishni boshlaydi.\n\n"
                    "━━━━━━━━━━━━━━━━━━━━\n"
                    "🚛 <b>Toza va 1-qo'l yuklar oqimidan uzilib qolmaslik uchun obunani hoziroq uzaytiring:</b>\n\n"
                    f"▫️ 📅 <b>1 Haftalik to'liq obuna:</b> <code>{PRICE_WEEK:,}</code> so'm\n"
                    f"▫️ 📅 <b>1 Oylik to'liq obuna:</b> <code>{PRICE_MONTH:,}</code> so'm\n\n"
                    "👉 Hoziroq pastdagi <b>«💳 Obuna sotib olish»</b> tugmasini bosing va o'z joyingizni saqlab qoling! 👇"
                )
                kb = InlineKeyboardMarkup(inline_keyboard=[
                    [
                        InlineKeyboardButton(text="💳 Obuna sotib olish", callback_data="btn_plans")
                    ],
                    [
                        InlineKeyboardButton(text="👨‍💻 Aloqa / Adminga yozish", url="https://t.me/maqsudali_o6")
                    ]
                ])

                await bot.send_message(chat_id=uid, text=alert_text, reply_markup=kb, parse_mode="HTML")
                await database.mark_subscription_warning_sent(sub_id)
                logger.info(f"⏳ 1 SOATLIK OGOHLANTIRISH YUBORILDI -> User ID: {uid} (Sub ID: {sub_id})")
                await asyncio.sleep(0.5)
            except Exception as send_err:
                logger.warning(f"1 soatlik ogohlantirish yuborishda xatolik ({uid}): {send_err}")
                await database.mark_subscription_warning_sent(sub_id)
    except Exception as e:
        logger.error(f"check_expiring_trials_1hour umumiy xatoligi: {e}")

async def check_expired_subscriptions(bot: Bot):
    """Muddati tugagan obunalarni faolsizlantirish va guruhdan chetlatish."""
    try:
        # Avval 1 soat qolganlarni ogohlantiramiz
        await check_expiring_trials_1hour(bot)

        # So'ng to'liq muddati tugaganlarni ko'ramiz
        expired_subs = await database.get_expired_active_subscriptions()
        if not expired_subs:
            return

        from config import PRIVATE_GROUP_ID, ADMIN_ID

        for sub in expired_subs:
            sub_id = sub["id"]
            uid = sub["user_id"]
            if uid == ADMIN_ID or uid == 8258153060:
                continue

            await database.deactivate_subscription(sub_id)
            logger.info(f"🚫 Obuna muddati tugadi: User ID: {uid} (Sub ID: {sub_id})")

            # Guruhdan chiqarish
            if PRIVATE_GROUP_ID != 0:
                try:
                    await bot.ban_chat_member(chat_id=PRIVATE_GROUP_ID, user_id=uid)
                    logger.info(f"Guruhdan chetlatildi va bloklandi: {uid}")
                except Exception as kick_err:
                    logger.debug(f"Guruhdan chiqarishda xatolik ({uid}): {kick_err}")

            # Foydalanuvchiga xabar berish
            try:
                exp_text = (
                    "⚠️ <b>Sizning bepul sinov muddatingiz to'liq yakunlandi!</b>\n\n"
                    "Yopiq guruhimizdagi 1-qo'l toza yuklar va haqiqiy zakazchilar raqamlaridan foydalanishni "
                    "davom ettirish uchun iltimos, obuna tariflaridan birini tanlang va faollashtiring.\n\n"
                    "Pastdagi tugmani bosing 👇"
                )
                kb = InlineKeyboardMarkup(inline_keyboard=[
                    [
                        InlineKeyboardButton(text="💳 Obuna sotib olish", callback_data="btn_plans")
                    ],
                    [
                        InlineKeyboardButton(text="👨‍💻 Adminga yozish", url="https://t.me/maqsudali_o6")
                    ]
                ])
                await bot.send_message(chat_id=uid, text=exp_text, reply_markup=kb, parse_mode="HTML")
            except Exception as notify_err:
                logger.debug(f"Tugaganlik xabarini yuborishda xatolik ({uid}): {notify_err}")

            await asyncio.sleep(0.5)
    except Exception as e:
        logger.error(f"check_expired_subscriptions xatoligi: {e}")

async def check_and_send_group_requests(bot: Bot):
    """
    Yangi foydalanuvchilarga botga qo'shilganidan 2 kun (48 soat) o'tgach,
    guruh havolalarini so'rash xabarini avtomatik yuborish vazifasi.
    """
    try:
        pending_users = await database.get_users_pending_group_request(min_days=2)
        if not pending_users:
            return

        for user in pending_users:
            uid = user["user_id"]
            name = (user.get("full_name") or "").strip() or "Haydovchi"
            try:
                msg = get_group_request_message(name)
                kb = get_group_request_keyboard()
                await bot.send_message(chat_id=uid, text=msg, parse_mode="HTML", reply_markup=kb)
                await database.mark_user_group_request_sent(uid)
                logger.info(f"Guruh havolasi so'rovi yangi a'zoga yuborildi: {uid} ({name})")
                await asyncio.sleep(0.3)
            except Exception as e:
                logger.warning(f"Guruh so'rovi yuborilmadi ({uid}): {e}")
                err_str = str(e).lower()
                if "blocked" in err_str or "deactivated" in err_str or "chat not found" in err_str:
                    await database.mark_user_group_request_sent(uid)
    except Exception as e:
        logger.error(f"check_and_send_group_requests xatoligi: {e}")

async def scheduled_outreach_job():
    """Har 10 daqiqada 1 ta dispetcherga taklif yuborish."""
    try:
        import outreach_sender
        logger.info("⏰ [OUTREACH] Har 10 daqiqalik navbat: 1 ta dispetcherga xabar yuborilmoqda...")
        sent = await outreach_sender.send_outreach_batch(max_messages=1)
        if sent > 0:
            logger.info("✅ [OUTREACH] 1 ta dispetcherga xabar muvaffaqiyatli yetkazildi.")
    except Exception as e:
        logger.error(f"[OUTREACH] 10 daqiqalik yuborish xatoligi: {e}")

async def scheduled_morning_offers_job(bot: Bot):
    """Har kuni ertalab soat 06:00 da (Toshkent vaqti) muddati tugagan obunachilarga qayta taklif yuborish."""
    try:
        from send_morning_expired_offers import send_morning_offers
        logger.info("🌅 [MORNING_OFFERS] Ertalabki soat 06:00 obuna taklifi yuborish boshlanmoqda...")
        res = await send_morning_offers(bot=bot)
        logger.info(f"✅ [MORNING_OFFERS] Ertalabki takliflar yakunlandi: {res}")
    except Exception as e:
        logger.error(f"[MORNING_OFFERS] Ertalabki taklif yuborishda xatolik: {e}")

_LAST_DAILY_REMINDER_DATE = ""

async def scheduled_daily_user_reminder(bot: Bot):
    """
    Foydalanuvchi talabi: Har kuni ertalab soat 07:00 da (Toshkent vaqti)
    barcha bot foydalanuvchilariga yangi 1-qo'l toza yuklar haqida eslatma
    va yopiq guruhga kirish/obuna tugmalari bilan xabar yuborish.
    """
    global _LAST_DAILY_REMINDER_DATE
    from datetime import datetime
    today_str = datetime.now().strftime("%Y-%m-%d")
    if _LAST_DAILY_REMINDER_DATE == today_str:
        logger.info(f"Bugun ({today_str}) uchun kundalik xabarnoma allaqachon yuborilgan.")
        return
    _LAST_DAILY_REMINDER_DATE = today_str

    logger.info("🌅 [DAILY_REMINDER] Ertalabki soat 07:00 barcha bot a'zolariga xabar yuborish boshlandi...")
    try:
        users = await database.get_all_registered_users()
        if not users:
            logger.info("[DAILY_REMINDER] Foydalanuvchilar topilmadi.")
            return

        msg_text = (
            "🌅 <b>XAYRLI TONG, HURMATLI HAMKOR!</b> 🚛\n\n"
            "Bugungi yangi ish kuningiz barakali, unumli va yo'lingiz bexatar bo'lsin!\n\n"
            "<b>FEMMORA LOGISTIKA</b> yopiq guruhimizda 240+ dan ortiq saralangan manbalardan "
            "barcha vositachilar va spamerlar chetlatilib, <b>faqat 1-qo'l haqiqiy zakazchilarning toza yuklari</b> "
            "va aloqa raqamlari muntazam uzatilmoqda.\n\n"
            "Bugungi eng qulay yuklarni o'tkazib yubormaslik uchun guruhga kiring yoki obunangizni yangilang! 👇"
        )

        kb = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="🚛 Yopiq guruhga kirish", callback_data="btn_vip_access"),
                InlineKeyboardButton(text="💳 Obuna tariflari", callback_data="btn_plans")
            ],
            [
                InlineKeyboardButton(text="👥 Do'stlarni taklif qilish (Bonus)", callback_data="btn_referral")
            ]
        ])

        success_count = 0
        blocked_count = 0

        for u in users:
            uid = u.get("user_id")
            if not uid or uid <= 0:
                continue

            try:
                await bot.send_message(
                    chat_id=uid,
                    text=msg_text,
                    parse_mode="HTML",
                    reply_markup=kb
                )
                success_count += 1
                await asyncio.sleep(0.05)
            except Exception as e:
                err_str = str(e).lower()
                if "blocked" in err_str or "deactivated" in err_str or "chat not found" in err_str:
                    blocked_count += 1
                else:
                    logger.debug(f"[DAILY_REMINDER] Yuborishda xatolik ({uid}): {e}")

        logger.info(f"✅ [DAILY_REMINDER] Ertalabki xabarnoma yakunlandi: {success_count} taga yetkazildi, {blocked_count} ta bloklangan/o'chirilgan.")
    except Exception as e:
        logger.error(f"[DAILY_REMINDER] Umumiy xatolik: {e}")

def setup_scheduler(bot: Bot) -> AsyncIOScheduler:
    """APScheduler ni sozlash va ishga tushirish."""
    scheduler = AsyncIOScheduler()
    # Har 3 daqiqada tekshiradi (1 soat qolganini va tugaganini aniq ushlash uchun)
    scheduler.add_job(
        check_expired_subscriptions,
        "interval",
        minutes=3,
        args=[bot],
        id="check_subscriptions_job",
        replace_existing=True
    )
    # Har 30 daqiqada yangi a'zolarga 2 kunlik muddatni tekshirib xabar yuboradi
    scheduler.add_job(
        check_and_send_group_requests,
        "interval",
        minutes=30,
        args=[bot],
        id="group_requests_job",
        replace_existing=True
    )
    # Kuniga 4 mahal (00:00, 06:00, 12:00, 19:00 Toshkent vaqti) 20 tadan dispetcherga xabar yuborish
    try:
        from zoneinfo import ZoneInfo
        tashkent_tz = ZoneInfo("Asia/Tashkent")
    except Exception:
        tashkent_tz = None

    # Har kuni ertalab soat 07:00 da (Toshkent vaqti) barcha bot foydalanuvchilariga xabarnoma yuborish
    scheduler.add_job(
        scheduled_daily_user_reminder,
        "cron",
        hour=7,
        minute=0,
        timezone=tashkent_tz,
        args=[bot],
        id="scheduled_daily_user_reminder_job",
        replace_existing=True
    )

    # Har 10 daqiqada 1 ta dispetcherga xabar yuborish (kunduzi 08:00 dan 22:00 gacha)
    scheduler.add_job(
        scheduled_outreach_job,
        "cron",
        hour="8-22",
        minute="*/10",
        timezone=tashkent_tz,
        id="scheduled_outreach_job",
        replace_existing=True
    )

    # Har kuni ertalab soat 06:00 da (Toshkent vaqti) muddati tugaganlarga obuna taklifini yuborish
    scheduler.add_job(
        scheduled_morning_offers_job,
        "cron",
        hour=6,
        minute=0,
        timezone=tashkent_tz,
        args=[bot],
        id="scheduled_morning_offers_job",
        replace_existing=True
    )

    # Har kuni soat 17:00 da (Toshkent vaqti) sinov muddati tugaganlarni yopiq guruhdan chiqarish
    scheduler.add_job(
        scheduled_kick_expired_trial_job,
        "cron",
        hour=17,
        minute=0,
        timezone=tashkent_tz,
        args=[bot],
        id="scheduled_kick_expired_trial_job",
        replace_existing=True
    )
    return scheduler

async def scheduled_kick_expired_trial_job(bot: Bot):
    """Har kuni soat 17:00 da (Toshkent vaqti) sinov muddati tugagan a'zolarni yopiq guruhdan chiqarish."""
    try:
        from kick_expired_members import kick_expired_members
        logger.info("🚪 [KICK_EXPIRED] Soat 17:00 bo'ldi! Sinov muddati tugaganlarni guruhdan chiqarish boshlanmoqda...")
        await kick_expired_members(dry_run=False)
        logger.info("✅ [KICK_EXPIRED] Soat 17:00 tozalash muvaffaqiyatli yakunlandi.")
    except Exception as e:
        logger.error(f"[KICK_EXPIRED] Soat 17:00 chiqarishda xatolik: {e}")



