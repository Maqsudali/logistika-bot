import logging
import html
from datetime import datetime, timedelta
from typing import Optional, Tuple, Dict, Any, List

from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ReplyKeyboardMarkup,
    KeyboardButton,
    BotCommand,
    CallbackQuery,
    Message,
    ChatMemberUpdated
)
from aiogram.filters.chat_member_updated import ChatMemberUpdatedFilter, ADMINISTRATOR, IS_ADMIN
from aiogram.exceptions import TelegramBadRequest

import config
import database
from filters import analyze_reported_cargo_ad, extract_phone

logger = logging.getLogger(__name__)

# Bot.get_me() keshlanadi - har safar Telegram API ga so'rov yubormaslik uchun
_bot_me_cache = None

def save_private_group_id(chat_id: int):
    """PRIVATE_GROUP_ID ni xotirada va .env faylida saqlash."""
    config.PRIVATE_GROUP_ID = chat_id
    try:
        import re
        env_path = ".env"
        with open(env_path, "r", encoding="utf-8") as f:
            content = f.read()

        if re.search(r"PRIVATE_GROUP_ID=.*", content):
            new_content = re.sub(r"PRIVATE_GROUP_ID=.*", f"PRIVATE_GROUP_ID={chat_id}", content)
        else:
            new_content = content + f"\nPRIVATE_GROUP_ID={chat_id}\n"

        with open(env_path, "w", encoding="utf-8") as f:
            f.write(new_content)
        logger.info(f"PRIVATE_GROUP_ID = {chat_id} .env ga saqlandi.")
    except Exception as e:
        logger.error(f".env ga PRIVATE_GROUP_ID saqlashda xatolik: {e}")

# FSM Holatlari
class PaymentState(StatesGroup):
    waiting_for_receipt = State()

def get_bot_and_dp() -> tuple[Bot, Dispatcher]:
    bot = Bot(token=config.BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())
    return bot, dp

# --- KLAVIATURALAR ---

def get_about_service_text() -> str:
    return (
        "🚛 <b>«YUKLAR MARKAZI» — YOPIQ GURUH HAQIDA</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "📌 <b>Bu guruh nima vazifani bajaradi?</b>\n\n"
        "Botimiz Telegram'dagi yuzlab logistika guruhlaridagi e'lonlarni tunu-kun avtomatik saralaydi va "
        "<b>faqat haqiqiy yuk egalari (zakazchilar)ning e'lonlarini</b> ajratib, to'g'ridan-to'g'ri "
        "ushbu yopiq guruhga yetkazib beradi.\n\n"
        "💡 <b>Sizga qanday foyda keltiradi?</b>\n"
        "• Yuzlab guruhlarni titkilab, vaqt yo'qotmaysiz — barcha e'lonlar bitta joyda jamlanadi.\n"
        "• E'lon chiqqan soniyadayoq guruhga tushadi (yukni birinchilardan bo'lib olish imkoniyati).\n"
        "• O'rtadagi vositachilarsiz to'g'ridan-to'g'ri 1-qo'l yuk egasi bilan bog'lanasiz.\n\n"
        "🛑 <b>GURUH A'ZOLARIGA QAT'IY TALAB VA ASOSIY QOIDA:</b>\n"
        "Dasturimiz dispetcherlarni 95%+ aniqlikda to'xtatadi. Ammo dispetcherlar turli yangi hiylalar bilan e'lon berishi mumkin.\n\n"
        "Agar guruhda <b>dispetcher e'lonini ko'rsangiz, uni aslo e'tiborsiz qoldirmang — zudlik bilan e'lon ostidagi «🗑 Dispetcher bo'lsa, o'chirish» tugmasini bosing!</b>\n\n"
        "❓ <b>Bu nima beradi va nega bu shart?</b>\n"
        "1️⃣ E'lon darhol guruhdan o'chiriladi;\n"
        "2️⃣ Eng muhimi — o'sha dispetcher tizimimizda umrbod <b>QORA RO'YXATGA</b> kiritiladi;\n"
        "3️⃣ Keyingi gal ushbu dispetcherning birorta e'loni guruhga adashib ham tushmaydi!\n\n"
        "🎯 <i>Natijada: har safar tugmani bosganingizda dispetcherlar soni kundan-kunga kamayib boradi va guruhda faqat 100% haqiqiy yuk egalarining toza e'lonlari qoladi!</i>\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "👇 <i>Guruhga qo'shilish yoki xizmatlardan foydalanish uchun pastdagi tugmalarni bosing:</i>"
    )

def get_reply_main_keyboard(is_admin: bool = False) -> ReplyKeyboardMarkup:
    """Xabar yozish maydonida (klaviaturada) doimiy turadigan pastki menyu tugmalari."""
    buttons = [
        [
            KeyboardButton(text="🚛 Yopiq guruhga kirish"),
            KeyboardButton(text="💳 Obuna sotib olish")
        ],
        [
            KeyboardButton(text="📖 Yopiq guruh haqida"),
            KeyboardButton(text="ℹ️ Mening a'zoligim")
        ],
        [
            KeyboardButton(text="👥 Taklif qilish (Bonus)")
        ]
    ]
    if is_admin:
        buttons.append([
            KeyboardButton(text="📊 Statistika")
        ])
    return ReplyKeyboardMarkup(
        keyboard=buttons,
        resize_keyboard=True,
        is_persistent=True
    )

def get_main_keyboard(is_admin: bool = False) -> InlineKeyboardMarkup:
    buttons = [
        [
            InlineKeyboardButton(text="🚛 Yopiq guruhga kirish", callback_data="btn_vip_access"),
            InlineKeyboardButton(text="💳 Obuna sotib olish", callback_data="btn_plans")
        ],
        [
            InlineKeyboardButton(text="📖 Yopiq guruh haqida", callback_data="btn_about_service")
        ],
        [
            InlineKeyboardButton(text="ℹ️ Mening a'zoligim", callback_data="btn_my_sub"),
            InlineKeyboardButton(text="👥 Taklif qilish (Referal)", callback_data="btn_referral")
        ]
    ]
    if is_admin:
        buttons.append([
            InlineKeyboardButton(text="📊 Statistika (Faqat Admin)", callback_data="btn_admin_stats")
        ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def format_admin_stats(stats: dict) -> str:
    now_str = datetime.now().strftime("%d.%m.%Y %H:%M")
    return (
        "📊 <b>TIZIM STATISTIKASI (Faqat Administrator uchun)</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "🚛 <b>Yopiq Guruhga Uzatilgan Toza Yuklar:</b>\n"
        f"• 📅 <b>Bugun uzatildi:</b> <b>{stats.get('today_forwarded', 0)} ta</b>\n"
        f"• 📦 <b>Jami uzatilgan:</b> <b>{stats.get('total_forwarded', 0)} ta</b>\n\n"
        "👥 <b>Foydalanuvchilar:</b>\n"
        f"• Jami bot a'zolari: <b>{stats['total_users']} ta</b>\n"
        f"• Bugun yangi kirganlar: <b>{stats['today_users']} ta</b>\n"
        f"• Sinov muddatini ishlatganlar: <b>{stats['trial_users']} ta</b>\n"
        f"• Hozirda faol a'zolar (guruhda): <b>{stats['active_subscriptions']} ta</b>\n\n"
        "💰 <b>Moliya va Haridlar:</b>\n"
        f"• Obuna sotib olgan mijozlar: <b>{stats['unique_paying_users']} kishi</b>\n"
        f"• Jami tasdiqlangan haridlar: <b>{stats['total_paid_orders']} ta</b>\n"
        f"  ├ 📅 1 Haftalik obunalar: <b>{stats['week_orders']} ta</b>\n"
        f"  └ 📅 1 Oylik obunalar: <b>{stats['month_orders']} ta</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"💵 <b>Jami tushum:</b> <b>{stats['total_revenue']:,} so'm</b>\n"
        f"💳 <b>Bugungi tushum:</b> <b>{stats['today_revenue']:,} so'm</b> ({stats['today_paid_orders']} ta to'lov)\n\n"
        "🛡 <b>Xavfsizlik & Filtrlash:</b>\n"
        f"• Bloklangan dispetcherlar: <b>{stats['blocked_senders']} ta</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"🕒 <i>Yangilangan vaqt: {now_str}</i>"
    )

def get_plans_keyboard(referral_balance: int) -> InlineKeyboardMarkup:
    week_final = max(0, config.PRICE_WEEK - referral_balance)
    month_final = max(0, config.PRICE_MONTH - referral_balance)
    
    week_label = f"📅 1 Hafta — {week_final:,} so'm" if week_final > 0 else "📅 1 Hafta — BEPUL (Bonus bilan)"
    month_label = f"📅 1 Oy — {month_final:,} so'm" if month_final > 0 else "📅 1 Oy — BEPUL (Bonus bilan)"
    
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text=week_label, 
                callback_data="buy_plan:week"
            )
        ],
        [
            InlineKeyboardButton(
                text=month_label, 
                callback_data="buy_plan:month"
            )
        ],
        [
            InlineKeyboardButton(text="👥 Do'stlarni taklif qilish (+5,000 so'm)", callback_data="btn_referral")
        ],
        [
            InlineKeyboardButton(text="⬅️ Ortga", callback_data="btn_back_main")
        ]
    ])

def get_dispatcher_report_keyboard(sender_id: str, source_url: Optional[str] = None) -> InlineKeyboardMarkup:
    """Yopiq guruhga yuboriladigan e'lon ostidagi tugmalar."""
    keyboard = []
    if source_url:
        keyboard.append([
            InlineKeyboardButton(
                text="👁 Xabarni ko'rish",
                url=source_url
            )
        ])
    keyboard.append([
        InlineKeyboardButton(
            text="🗑 Dispetcher bo'lsa, o'chirish", 
            callback_data=f"disp_report:{sender_id}"
        )
    ])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

# --- ASOSIY HANDLERLAR ---

async def create_user_vip_link(bot: Bot, user_id: int, plan_type: str = "trial", duration_hours: int = 72) -> Tuple[Optional[str], Optional[Dict[str, Any]]]:
    """Foydalanuvchi uchun 1 kishilik taklif havolasini yaratish va obunasini saqlash."""
    if config.PRIVATE_GROUP_ID == 0:
        return None, None
    try:
        expire_time = datetime.now() + timedelta(hours=24)
        invite_link_obj = await bot.create_chat_invite_link(
            chat_id=config.PRIVATE_GROUP_ID,
            member_limit=1,
            expire_date=expire_time
        )
        sub = None
        if duration_hours > 0:
            sub = await database.create_subscription(user_id=user_id, plan_type=plan_type, duration_hours=duration_hours)
        return invite_link_obj.invite_link, sub
    except Exception as e:
        logger.error(f"VIP invite link yaratishda xatolik (user: {user_id}): {e}")
        return None, None

async def cmd_start(message: Message, bot: Bot):
    user_id = message.from_user.id
    username = message.from_user.username
    raw_full_name = message.from_user.full_name or "Foydalanuvchi"
    safe_name = html.escape(raw_full_name)

    # Foydalanuvchi avval ro'yxatdan o'tganmi yoki yangi kirdimi tekshiramiz
    existing_user = await database.get_user(user_id)
    is_new_user = (existing_user is None)

    # Referal parametrini tekshirish: /start ref_123456
    referrer_id = None
    args = (message.text or "").split()
    if len(args) > 1 and args[1].startswith("ref_"):
        try:
            ref_candidate = int(args[1].replace("ref_", ""))
            if ref_candidate != user_id:
                referrer_id = ref_candidate
        except ValueError:
            pass

    await database.get_or_create_user(
        user_id=user_id,
        username=username,
        full_name=raw_full_name,
        referrer_id=referrer_id
    )

    is_admin = (user_id == config.ADMIN_ID)

    # 1. Adminga zudlik bilan bildirishnoma (Start bosgan har bir kishiga e'tibor)
    if not is_admin and config.ADMIN_ID != 0:
        status_label = "🆕 YANGI FOYDALANUVCHI" if is_new_user else "🔄 QAYTA /START BOSGAN FOYDALANUVCHI"
        username_label = f"@{username}" if username else "Mavjud emas"
        admin_alert = (
            f"🔔 <b>{status_label} /START BOSDI!</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            f"👤 <b>Ismi:</b> {safe_name}\n"
            f"🆔 <b>Telegram ID:</b> <code>{user_id}</code>\n"
            f"🔗 <b>Username:</b> {username_label}\n"
            f"👥 <b>Referal:</b> {referrer_id or 'Yoʻq'}\n"
            f"🕒 <b>Vaqt:</b> {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}\n"
            "━━━━━━━━━━━━━━━━━━━━"
        )
        profile_url = f"https://t.me/{username}" if username else f"tg://user?id={user_id}"
        admin_kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="💬 Foydalanuvchiga yozish", url=profile_url)]
        ])
        try:
            await bot.send_message(chat_id=config.ADMIN_ID, text=admin_alert, reply_markup=admin_kb, parse_mode="HTML")
        except Exception as e:
            logger.debug(f"Adminga start xabarnomasini yuborishda xatolik: {e}")

    # 2. Foydalanuvchiga shaxsiy taklif havola tekshirish
    active_sub = await database.get_active_subscription(user_id)
    user_data = await database.get_user(user_id)
    has_trial = user_data.get("has_used_trial", 0) if user_data else 0

    invite_link = None
    if is_admin:
        invite_link, _ = await create_user_vip_link(bot, user_id, plan_type="vip", duration_hours=999999)
    elif active_sub:
        invite_link, _ = await create_user_vip_link(bot, user_id, plan_type=active_sub["plan_type"], duration_hours=0)
    elif not has_trial:
        invite_link, _ = await create_user_vip_link(bot, user_id, plan_type="trial", duration_hours=72)
        await database.update_trial_used(user_id)

    if invite_link:
        if not has_trial or is_new_user:
            welcome_text = (
                f"Assalomu alaykum, <b>{safe_name}</b>! «Birinchi qo'l yuklar» tizimiga xush kelibsiz.\n\n"
                "🎁 <b>Sizga yopiq VIP guruhimizga kirish uchun 3 kunlik bepul sinov obunasi berildi!</b>\n\n"
                "🛑 <b>Guruhning asosiy talabi va qoidasi:</b>\n"
                "Guruhda adashib tushgan dispetcher e'lonini ko'rsangiz, <b>qat'iyan «🗑 Dispetcher bo'lsa, o'chirish» tugmasini bosing!</b>\n"
                "Siz tugmani bossangiz, o'sha dispetcher umrbod qora ro'yxatga olinadi va keyingi safar uning xabarlari guruhga kiritilmaydi. Shunday qilib guruhimiz faqat haqiqiy yukchilar uchun tozalanib boradi!\n\n"
                f"🔗 <b>Guruhga kirish havolangiz:</b>\n{invite_link}"
            )
        elif is_admin:
            welcome_text = (
                f"Assalomu alaykum, <b>{safe_name}</b>! Admin paneliga xush kelibsiz.\n"
                "👑 Sizning VIP admin obunangiz cheksiz muddatga faol.\n"
                f"🔗 Yopiq guruhga kirish havolangiz: {invite_link}"
            )
        else:
            welcome_text = (
                f"Assalomu alaykum, <b>{safe_name}</b>! «Birinchi qo'l yuklar» tizimiga xush kelibsiz.\n\n"
                "✅ <b>Sizning VIP obunangiz faol holatda.</b>\n\n"
                "🛑 <b>Eslatma:</b> Guruhda dispetcher e'loniga ko'zingiz tushsa, qat'iyan <b>«🗑 Dispetcher bo'lsa, o'chirish»</b> tugmasini bosing. O'sha dispetcher qora ro'yxatga kiritiladi va keyingi safar uning e'loni guruhga tushmaydi!\n\n"
                f"🔗 <b>Yopiq guruhga kirish havolangiz:</b>\n{invite_link}"
            )

        main_kb_buttons = [
            [InlineKeyboardButton(text="🚛 Yopiq guruhga kirish", url=invite_link)],
            [
                InlineKeyboardButton(text="ℹ️ Mening a'zoligim", callback_data="btn_my_sub"),
                InlineKeyboardButton(text="👥 Taklif qilish (Referal)", callback_data="btn_referral")
            ]
        ]
        if is_admin:
            main_kb_buttons.append([
                InlineKeyboardButton(text="📊 Statistika (Faqat Admin)", callback_data="btn_admin_stats")
            ])
        inline_kb = InlineKeyboardMarkup(inline_keyboard=main_kb_buttons)

        await message.answer(
            welcome_text,
            reply_markup=inline_kb,
            parse_mode="HTML"
        )
    else:
        about_text = get_about_service_text()
        full_welcome = (
            f"Assalomu alaykum, <b>{safe_name}</b>!\n\n"
            f"{about_text}"
        )
        await message.answer(
            full_welcome,
            reply_markup=get_reply_main_keyboard(is_admin=is_admin),
            parse_mode="HTML"
        )
        await message.answer(
            "👇 <b>Asosiy boshqaruv menyusi:</b>",
            reply_markup=get_main_keyboard(is_admin=is_admin),
            parse_mode="HTML"
        )

async def callback_back_main(call: CallbackQuery, state: FSMContext):
    await state.clear()
    is_admin = (call.from_user.id == config.ADMIN_ID)
    await call.message.answer(
        "👇 <b>Asosiy menyu:</b>",
        reply_markup=get_main_keyboard(is_admin=is_admin),
        parse_mode="HTML"
    )
    await call.answer()

# --- 0. BOT VA YOPIQ GURUH HAQIDA ---

async def execute_about_service(target):
    text = get_about_service_text()
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🚛 Yopiq guruhga kirish", callback_data="btn_vip_access"),
            InlineKeyboardButton(text="💳 Obuna tariflari", callback_data="btn_plans")
        ],
        [
            InlineKeyboardButton(text="👥 Taklif qilish (Referal)", callback_data="btn_referral")
        ],
        [
            InlineKeyboardButton(text="⬅️ Asosiy menyu", callback_data="btn_back_main")
        ]
    ])
    await target.answer(text, reply_markup=kb, parse_mode="HTML")

async def callback_about_service(call: CallbackQuery):
    await execute_about_service(call.message)
    await call.answer()

async def cmd_about_service_message(message: Message):
    await execute_about_service(message)

# --- 1. DOIMIY VIP GURUHGA KIRISH ---

async def execute_vip_access(target, user_id: int, bot: Bot):
    """Guruhga kirish: Yangi a'zolarga 3 kunlik bepul sinov, sinovi tugaganlarga obuna menyusi."""
    user = await database.get_user(user_id)
    if not user:
        await target.answer("Foydalanuvchi topilmadi. Qaytadan /start bosing.")
        return

    # Agar yopiq guruh ID si hali ulanmagan bo'lsa
    if config.PRIVATE_GROUP_ID == 0:
        await target.answer("Hozirda yopiq guruh sozlanmoqda. Tez orada faollashadi!")
        return

    is_admin = (user_id == config.ADMIN_ID or user_id == 8258153060)

    # 1. Faol obunasi bormi tekshiramiz
    active_sub = await database.get_active_subscription(user_id)

    if is_admin:
        invite_link, _ = await create_user_vip_link(bot, user_id, plan_type="vip", duration_hours=999999)
        if invite_link:
            await target.answer(
                f"👑 <b>Administrator sifatida VIP kirish:</b>\n\n🔗 {invite_link}",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="Guruhga kirish 🚛", url=invite_link)]
                ]),
                parse_mode="HTML"
            )
        return

    if active_sub:
        invite_link, _ = await create_user_vip_link(bot, user_id, plan_type=active_sub["plan_type"], duration_hours=0)
        end_dt = active_sub["end_date"]
        plan_name = "3 kunlik bepul sinov" if active_sub["plan_type"] == "trial" else ("1 Haftalik" if active_sub["plan_type"] == "week" else "1 Oylik")
        msg = (
            f"✅ <b>Sizning obunangiz faol!</b>\n\n"
            f"▫️ <b>Tarif:</b> {plan_name}\n"
            f"▫️ <b>Tugash vaqti:</b> <code>{end_dt}</code>\n\n"
            "🛑 <b>Guruhning asosiy talabi:</b>\n"
            "Agar guruhda dispetcher e'loniga ko'zingiz tushsa, <b>qat'iyan «🗑 Dispetcher bo'lsa, o'chirish» tugmasini bosing!</b>\n"
            "Bu dispetcherni umrbod qora ro'yxatga kiritadi va keyingi safar uning xabarlari guruhga kiritilmaydi!\n\n"
            f"🔗 <b>Guruhga kirish havolasi:</b>\n{invite_link}\n\n"
            f"<i>(Ushbu havola faqat siz uchun 1 kishilik yaratildi va 24 soat amal qiladi)</i>"
        )
        await target.answer(
            msg,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="Guruhga kirish 🚛", url=invite_link)]
            ]),
            parse_mode="HTML"
        )
        return

    # 2. Sinov muddatidan foydalanganmi tekshiramiz
    if user.get("has_used_trial", 0) == 1:
        ref_balance = user.get("referral_balance", 0)
        ref_count = await database.get_referral_count(user_id)
        week_final = max(0, config.PRICE_WEEK - ref_balance)
        month_final = max(0, config.PRICE_MONTH - ref_balance)

        expired_msg = (
            "⚠️ <b>Sizning 3 kunlik bepul sinov muddatingiz yakunlangan!</b>\n\n"
            "Yopiq VIP guruhimizdagi 1-qo'l toza yuklar va haqiqiy zakazchilar kontaktlaridan "
            "foydalanishni davom ettirish uchun iltimos, o'zingizga mos tarifni tanlang:\n\n"
            f"▫️ 📅 <b>1 Haftalik obuna:</b> {config.PRICE_WEEK:,} so'm\n"
            f"▫️ 📅 <b>1 Oylik obuna:</b> {config.PRICE_MONTH:,} so'm\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "👥 <b>SIZNING REFERAL HISOBINGIZ:</b>\n"
            f"• Taklif qilgan do'stlaringiz: <b>{ref_count} kishi</b>\n"
            f"• To'plangan bonus balansingiz: <b>{ref_balance:,} so'm</b>\n\n"
            f"▫️ <b>1 Hafta to'lovi:</b> " + (f"<s>{config.PRICE_WEEK:,}</s> ➡️ <b>{week_final:,} so'm</b>" if ref_balance > 0 else f"<b>{config.PRICE_WEEK:,} so'm</b>") + "\n"
            f"▫️ <b>1 Oy to'lovi:</b> " + (f"<s>{config.PRICE_MONTH:,}</s> ➡️ <b>{month_final:,} so'm</b>" if ref_balance > 0 else f"<b>{config.PRICE_MONTH:,} so'm</b>") + "\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "<i>💡 Har bir taklif qilgan do'stingiz uchun hisobingizga +5,000 so'm qo'shiladi va obuna to'lovidan chegiriladi!</i>"
        )
        await target.answer(
            expired_msg,
            reply_markup=get_plans_keyboard(ref_balance),
            parse_mode="HTML"
        )
        return

    # 3. Yangi foydalanuvchi -> 3 KUNLIK (72 soat) BEPUL SINOV BERISH
    invite_link, sub = await create_user_vip_link(bot, user_id, plan_type="trial", duration_hours=72)
    await database.update_trial_used(user_id)

    end_str = sub["end_date"] if sub else "3 kun"

    welcome_trial_msg = (
        f"Assalomu alaykum, <b>{safe_name}</b>! «Birinchi qo'l yuklar» markaziga xush kelibsiz.\n\n"
        "🎁 <b>Sizga yopiq VIP guruhimizga kirish uchun 3 kunlik bepul sinov obunasi berildi!</b>\n\n"
        "🛑 <b>GURUHNING QAT'IY QOIDASI:</b>\n"
        "Guruhda dispetcher e'lonini ko'rgan zahotingiz <b>qat'iyan «🗑 Dispetcher bo'lsa, o'chirish» tugmasini bosing!</b>\n"
        "Sababi: siz tugmani bossangiz, o'sha dispetcher qora ro'yxatga olinadi va keyingi safar uning e'lonlari guruhga adashib tushmaydi. Shundagina dispetcherlar kamayib, faqat haqiqiy yukchilar qoladi!\n\n"
        f"🔗 <b>Guruhga kirish havolasi:</b>\n{invite_link}"
    )

    await target.answer(
        welcome_trial_msg,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Guruhga kirish 🚛", url=invite_link)]
        ]),
        parse_mode="HTML"
    )

async def callback_vip_access(call: CallbackQuery, bot: Bot):
    await execute_vip_access(call.message, call.from_user.id, bot)
    await call.answer()

async def cmd_vip_message(message: Message, bot: Bot):
    await execute_vip_access(message, message.from_user.id, bot)

# --- 2. TARIFLAR VA TO'LOV TIZIMI ---

async def execute_plans(target, user_id: int):
    """Tariflar ro'yxatini chatga yangi xabar qilib chiqarish."""
    user = await database.get_user(user_id)
    ref_balance = user["referral_balance"] if user else 0
    ref_count = await database.get_referral_count(user_id)

    week_final = max(0, config.PRICE_WEEK - ref_balance)
    month_final = max(0, config.PRICE_MONTH - ref_balance)

    text = (
        "💳 <b>Yopiq VIP guruh obuna tariflari:</b>\n\n"
        f"1️⃣ 📅 <b>1 Hafta (7 kun):</b> {config.PRICE_WEEK:,} so'm\n"
        f"2️⃣ 📅 <b>1 Oy (30 kun):</b> {config.PRICE_MONTH:,} so'm\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "👥 <b>REFERALDAN KELGAN DO'STLAR VA BALANS:</b>\n"
        f"• Taklif qilgan do'stlaringiz: <b>{ref_count} kishi</b>\n"
        f"• To'plangan referal balansingiz: <b>{ref_balance:,} so'm</b>\n\n"
        f"▫️ <b>1 Hafta to'lovi:</b> " + (f"<s>{config.PRICE_WEEK:,}</s> ➡️ <b>{week_final:,} so'm</b>" if ref_balance > 0 else f"<b>{config.PRICE_WEEK:,} so'm</b>") + "\n"
        f"▫️ <b>1 Oy to'lovi:</b> " + (f"<s>{config.PRICE_MONTH:,}</s> ➡️ <b>{month_final:,} so'm</b>" if ref_balance > 0 else f"<b>{config.PRICE_MONTH:,} so'm</b>") + "\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "<i>(Referal hisobingizdagi mablag' to'lov paytida avtomatik chegirib beriladi!)</i>\n\n"
        "O'zingizga mos tarifni tanlang:"
    )
    await target.answer(
        text,
        reply_markup=get_plans_keyboard(ref_balance),
        parse_mode="HTML"
    )

async def callback_plans(call: CallbackQuery):
    await execute_plans(call.message, call.from_user.id)
    await call.answer()

async def cmd_plans_message(message: Message):
    await execute_plans(message, message.from_user.id)

async def callback_buy_plan(call: CallbackQuery):
    user_id = call.from_user.id
    plan = call.data.split(":")[1]  # 'week' yoki 'month'

    user = await database.get_user(user_id)
    ref_balance = user["referral_balance"] if user else 0
    ref_count = await database.get_referral_count(user_id)

    base_price = config.PRICE_WEEK if plan == "week" else config.PRICE_MONTH
    plan_name = "1 Hafta (7 kun)" if plan == "week" else "1 Oy (30 kun)"

    discount = min(base_price, ref_balance)
    final_amount = max(0, base_price - discount)

    pay_text = (
        f"🛒 <b>Tanlangan tarif:</b> {plan_name}\n"
        f"💵 <b>Asl narxi:</b> {base_price:,} so'm\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "👥 <b>Do'stlar va Chegirma hisobi:</b>\n"
        f"• Taklif qilgan do'stlaringiz: <b>{ref_count} kishi</b>\n"
        f"• Referal hisobingiz: <b>{ref_balance:,} so'm</b>\n"
        f"• Bonusdan chegirma: <b>-{discount:,} so'm</b>\n"
        f"👉 <b>To'lanishi kerak:</b> <u><b>{final_amount:,} so'm</b></u>\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
    )

    if final_amount > 0:
        pay_text += (
            f"💳 <b>To'lov uchun karta:</b> <code>{config.PAYMENT_CARD}</code>\n"
            f"👤 <b>Karta egasi:</b> {config.PAYMENT_CARD_HOLDER}\n\n"
            "To'lovni amalga oshirganingizdan so'ng pastdagi <b>«📸 To'lov chekini yuborish»</b> yoki <b>«✅ To'lov qildim»</b> tugmasini bosing. "
            "Administrator 1-10 daqiqa ichida tekshirib, guruhga kirish havolasini beradi."
        )
        kb = [
            [InlineKeyboardButton(text="📸 To'lov chekini yuborish", callback_data=f"btn_send_receipt:{plan}:{final_amount}:{discount}")],
            [InlineKeyboardButton(text="✅ To'lov qildim (Cheksiz)", callback_data=f"btn_paid_done:{plan}:{final_amount}:{discount}")],
            [InlineKeyboardButton(text="👥 Do'stlarni taklif qilish (+5,000 so'm)", callback_data="btn_referral")],
            [InlineKeyboardButton(text="⬅️ Bekor qilish", callback_data="btn_back_main")]
        ]
    else:
        pay_text += (
            "🎉 <b>Tabriklaymiz! Referal balansingiz to'liq qopladi!</b>\n\n"
            "Sizdan qo'shimcha to'lov talab qilinmaydi. Pastdagi tugmani bosing va 0 so'm bilan guruhga ulaning:"
        )
        kb = [
            [InlineKeyboardButton(text="🎁 Bonus hisobidan guruhga ulanish (0 so'm)", callback_data=f"btn_paid_done:{plan}:0:{discount}")],
            [InlineKeyboardButton(text="⬅️ Bekor qilish", callback_data="btn_back_main")]
        ]

    # Chatga yangi xabar qilib chiqarish
    await call.message.answer(
        pay_text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=kb),
        parse_mode="HTML"
    )
    await call.answer()

async def callback_send_receipt(call: CallbackQuery, state: FSMContext):
    """Foydalanuvchiga to'lov chekini rasm shaklida yuborishni so'rash."""
    parts = call.data.split(":")
    plan = parts[1]
    final_amount = int(parts[2])
    discount = int(parts[3])

    await state.set_state(PaymentState.waiting_for_receipt)
    await state.update_data(plan=plan, final_amount=final_amount, discount=discount)

    await call.message.answer(
        "📸 <b>Iltimos, to'lov chekining rasmini (skrinshotini) yuboring:</b>\n\n"
        "To'lov kvitansiyasini rasm shaklida shu yerga jo'nating. "
        "Administrator chekni tekshirib tasdiqlagach, yopiq guruhga kirish huquqingiz beriladi yoki guruh a'zoligingiz uzaytiriladi.\n\n"
        "<i>Bekor qilish uchun pastdagi tugmani bosing:</i>",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Bekor qilish", callback_data="btn_back_main")]
        ]),
        parse_mode="HTML"
    )
    await call.answer()

async def handle_receipt_photo(message: Message, state: FSMContext, bot: Bot):
    """Foydalanuvchi to'lov chekini rasm shaklida yuborganida ishlaydi."""
    user_id = message.from_user.id
    state_data = await state.get_data()
    plan = state_data.get("plan", "week")
    final_amount = state_data.get("final_amount", config.PRICE_WEEK)
    discount = state_data.get("discount", 0)

    photo_file_id = message.photo[-1].file_id
    receipt_caption = message.caption or "To'lov cheki (rasm)"

    payment_id = await database.create_payment(
        user_id=user_id,
        plan_type=plan,
        amount=final_amount,
        discount=discount,
        receipt_file_id=photo_file_id,
        receipt_text=receipt_caption
    )

    await state.clear()

    await message.answer(
        "⏳ <b>To'lov chekingiz muvaffaqiyatli qabul qilindi!</b>\n\n"
        "Administrator chekni tekshirib tasdiqlaganidan so'nggina yopiq guruhga kirish havolasi yuboriladi yoki "
        "guruhdagi a'zoligingiz uzaytiriladi. Iltimos, kuting...",
        parse_mode="HTML"
    )

    # Adminga chek rasmi bilan yuborish
    if config.ADMIN_ID != 0:
        admin_markup = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Tasdiqlash", callback_data=f"admin_approve:{payment_id}"),
                InlineKeyboardButton(text="❌ Rad etish", callback_data=f"admin_reject:{payment_id}")
            ]
        ])
        user_name_safe = html.escape(message.from_user.full_name or "Foydalanuvchi")
        username_safe = html.escape(message.from_user.username or "yo'q")
        plan_title = "1 Hafta (7 kun)" if plan == "week" else "1 Oy (30 kun)"

        caption = (
            f"🧾 <b>Yangi to'lov cheki keldi! (ID: #{payment_id})</b>\n\n"
            f"👤 <b>Foydalanuvchi:</b> {user_name_safe} (@{username_safe})\n"
            f"🆔 <b>User ID:</b> <code>{user_id}</code>\n"
            f"📦 <b>Tarif:</b> {plan_title}\n"
            f"💰 <b>Summa:</b> <b>{final_amount:,} so'm</b> (Chegirma: {discount:,} so'm)\n"
            f"💳 <b>Karta:</b> <code>{config.PAYMENT_CARD}</code>\n\n"
            "⚡️ <i>Chekni tekshirib, quyidagi tugmalar orqali tasdiqlang yoki rad eting:</i>"
        )
        try:
            await bot.send_photo(
                chat_id=config.ADMIN_ID,
                photo=photo_file_id,
                caption=caption,
                reply_markup=admin_markup,
                parse_mode="HTML"
            )
        except Exception as e:
            logger.error(f"Adminga chek rasmini yuborishda xatolik: {e}")

async def callback_paid_done(call: CallbackQuery, bot: Bot):
    """Foydalanuvchi to'lov qildim tugmasini bosganida ishlaydi."""
    user_id = call.from_user.id
    parts = call.data.split(":")
    plan = parts[1]
    final_amount = int(parts[2])
    discount = int(parts[3])

    # Bazaga to'lov arizasini kiritish
    payment_id = await database.create_payment(
        user_id=user_id,
        plan_type=plan,
        amount=final_amount,
        discount=discount,
        receipt_file_id=None,
        receipt_text="Foydalanuvchi to'lov qildim tugmasini bosdi"
    )

    await call.message.answer(
        "⏳ <b>Arizangiz qabul qilindi!</b>\n\n"
        "Administrator to'lovingizni tekshirib tasdiqlagach, sizga yopiq guruhga kirish havolasini yuboradi "
        "yoki guruhdagi a'zoligingizni uzaytiradi. Iltimos, kuting...",
        parse_mode="HTML"
    )
    await call.answer()

    # Adminga xabar yuborish
    if config.ADMIN_ID != 0:
        admin_markup = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Tasdiqlash", callback_data=f"admin_approve:{payment_id}"),
                InlineKeyboardButton(text="❌ Rad etish", callback_data=f"admin_reject:{payment_id}")
            ]
        ])

        user_name_safe = html.escape(call.from_user.full_name or "Foydalanuvchi")
        username_safe = html.escape(call.from_user.username or "yo'q")
        plan_title = "1 Hafta (7 kun)" if plan == "week" else "1 Oy (30 kun)"

        admin_caption = (
            f"🔔 <b>Yangi to'lov arizasi! (ID: #{payment_id})</b>\n\n"
            f"👤 <b>Foydalanuvchi:</b> {user_name_safe} (@{username_safe})\n"
            f"🆔 <b>User ID:</b> <code>{user_id}</code>\n"
            f"📦 <b>Tarif:</b> {plan_title}\n"
            f"💰 <b>To'langan summa:</b> <b>{final_amount:,} so'm</b> (Chegirma: {discount:,} so'm)\n"
            f"💳 <b>Karta:</b> <code>{config.PAYMENT_CARD}</code>\n\n"
            "⚡️ <i>Foydalanuvchi to'lovni amalga oshirganini bildirdi. Bank ilovangizni tekshirib, ruxsat bering:</i>"
        )

        try:
            await bot.send_message(
                chat_id=config.ADMIN_ID,
                text=admin_caption,
                reply_markup=admin_markup,
                parse_mode="HTML"
            )
        except Exception as e:
            logger.error(f"Adminga to'lov xabarini yuborishda xatolik: {e}")

# --- 3. ADMIN TASDIQLASH / RAD ETISH HANDLERLARI ---

async def callback_admin_approve(call: CallbackQuery, bot: Bot):
    payment_id = int(call.data.split(":")[1])
    payment = await database.get_payment(payment_id)

    if not payment or payment["status"] != "pending":
        await call.answer("Bu to'lov allaqachon ko'rib chiqilgan!", show_alert=True)
        return

    user_id = payment["user_id"]
    plan = payment["plan_type"]
    duration_hours = 7 * 24 if plan == "week" else 30 * 24

    # 1. Foydalanuvchi hozirda guruhda bormi tekshirish
    in_group = False
    if config.PRIVATE_GROUP_ID != 0:
        try:
            m = await bot.get_chat_member(chat_id=config.PRIVATE_GROUP_ID, user_id=user_id)
            if m.status in ("member", "restricted", "administrator", "creator"):
                in_group = True
        except Exception:
            in_group = False

    # 2. Yangi 1 kishilik va 1 soatlik link yaratish (agar guruhda bo'lmasa)
    invite_link = None
    if config.PRIVATE_GROUP_ID != 0:
        try:
            # Agar foydalanuvchi muddati tugab bloklangan bo'lsa, blokdan chiqaramiz
            try:
                await bot.unban_chat_member(chat_id=config.PRIVATE_GROUP_ID, user_id=user_id, only_if_banned=True)
            except Exception:
                pass
            expire_time = datetime.now() + timedelta(hours=1)
            invite_link_obj = await bot.create_chat_invite_link(
                chat_id=config.PRIVATE_GROUP_ID,
                member_limit=1,
                expire_date=expire_time
            )
            invite_link = invite_link_obj.invite_link
        except Exception as e:
            logger.error(f"Admin approve invite link xatosi: {e}")

    # 3. To'lovni tasdiqlash va obunani faollashtirish
    await database.update_payment_status(payment_id, "approved")
    if payment["discount"] > 0:
        await database.deduct_referral_balance(user_id, payment["discount"])

    sub = await database.create_subscription(user_id, plan, duration_hours)

    # 4. Foydalanuvchiga tarifiga qarab xabar yuborish
    plan_title = "1 Haftalik" if plan == "week" else "1 Oylik"
    try:
        if in_group:
            user_msg = (
                "✅ <b>To'lovingiz muvaffaqiyatli tasdiqlandi!</b>\n\n"
                f"Siz hozirda yopiq guruhdasiz. <b>{plan_title}</b> obuna muddatingiz "
                f"<b>{sub['end_date']}</b> gacha muvaffaqiyatli uzaytirildi! 🚛📦\n\n"
                "1-qo'l toza yuklardan uzluksiz foydalanishda davom eting!"
            )
            reply_kb = None
        else:
            user_msg = (
                "✅ <b>To'lovingiz muvaffaqiyatli tasdiqlandi!</b>\n\n"
                f"📅 <b>{plan_title} obuna muddati:</b> <b>{sub['end_date']}</b> gacha faollashtirildi.\n\n"
                "🔗 <b>Yopiq guruhga kirish uchun shaxsiy havolangiz:</b>\n"
                f"{invite_link}\n\n"
                "⚠️ Havola faqat 1 kishilik va 1 soat davomida amal qiladi. Hoziroq bosing va guruhga qo'shiling!"
            )
            reply_kb = None
            if invite_link and invite_link.startswith("http"):
                reply_kb = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="Guruhga kirish 🚛", url=invite_link)]
                ])

        await bot.send_message(
            chat_id=user_id,
            text=user_msg,
            reply_markup=reply_kb,
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"Foydalanuvchiga tasdiq xabarini yuborishda xatolik: {e}")

    await call.message.edit_reply_markup(reply_markup=None)
    if call.message.caption:
        await call.message.edit_caption(
            caption=f"{call.message.caption}\n\n✅ <b>ADMIN TOMONIDAN TASDIQLANDI</b>",
            parse_mode="HTML"
        )
    else:
        await call.message.edit_text(
            text=f"{call.message.text}\n\n✅ <b>ADMIN TOMONIDAN TASDIQLANDI</b>",
            parse_mode="HTML"
        )
    await call.answer("To'lov tasdiqlandi va foydalanuvchiga xabar yuborildi.")

async def callback_admin_reject(call: CallbackQuery, bot: Bot):
    payment_id = int(call.data.split(":")[1])
    payment = await database.get_payment(payment_id)

    if not payment or payment["status"] != "pending":
        await call.answer("Bu to'lov allaqachon ko'rib chiqilgan!", show_alert=True)
        return

    await database.update_payment_status(payment_id, "rejected")

    try:
        await bot.send_message(
            chat_id=payment["user_id"],
            text=(
                "❌ <b>To'lovingiz administrator tomonidan rad etildi.</b>\n\n"
                "To'lov kvitansiyasida xatolik bo'lishi mumkin. "
                "Iltimos, qaytadan urinib ko'ring yoki adminga murojaat qiling."
            ),
            parse_mode="HTML"
        )
    except Exception:
        pass

    await call.message.edit_reply_markup(reply_markup=None)
    if call.message.caption:
        await call.message.edit_caption(
            caption=f"{call.message.caption}\n\n❌ <b>RAD ETILDI</b>",
            parse_mode="HTML"
        )
    else:
        await call.message.edit_text(
            text=f"{call.message.text}\n\n❌ <b>RAD ETILDI</b>",
            parse_mode="HTML"
        )
    await call.answer("To'lov rad etildi.")

# --- 4. REFERAL TIZIMI ---

async def execute_referral(target, user_id: int, bot: Bot):
    global _bot_me_cache
    user = await database.get_user(user_id)
    ref_balance = user["referral_balance"] if user else 0
    ref_count = await database.get_referral_count(user_id)

    if _bot_me_cache is None:
        _bot_me_cache = await bot.get_me()
    ref_link = f"https://t.me/{_bot_me_cache.username}?start=ref_{user_id}"

    text = (
        "👥 <b>Referal (Do'stlarni taklif qilish) tizimi</b>\n\n"
        f"🔗 <b>Sizning shaxsiy taklif havolangiz:</b>\n<code>{ref_link}</code>\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"👤 <b>Siz taklif qilgan do'stlar:</b> <b>{ref_count} kishi</b>\n"
        f"💵 <b>To'plangan bonus balansingiz:</b> <b>{ref_balance:,} so'm</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        f"💰 <b>Bonus sharti:</b> Siz taklif qilgan har bir do'stingiz botga kirganda "
        f"hisobingizga <b>{config.REFERRAL_BONUS:,} so'm</b> naqd chegirma beriladi.\n\n"
        "🎁 <b>Bepul obuna imkoniyati:</b>\n"
        f"• <b>5 ta do'st</b> taklif qilsangiz = <b>25,000 so'm</b> (1 Haftalik obuna BEPUL!)\n"
        f"• <b>16 ta do'st</b> taklif qilsangiz = <b>80,000 so'm</b> (1 Oylik obuna BEPUL!)\n\n"
        "Ushbu balansdan yopiq VIP guruh obunasini sotib olishda avtomatik chegirma sifatida foydalanasiz!"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💳 Obuna tariflarini ko'rish", callback_data="btn_plans")],
        [InlineKeyboardButton(text="⬅️ Bosh menyu", callback_data="btn_back_main")]
    ])
    await target.answer(text, reply_markup=kb, parse_mode="HTML")

async def callback_referral(call: CallbackQuery, bot: Bot):
    await execute_referral(call.message, call.from_user.id, bot)
    await call.answer()

async def cmd_referral_message(message: Message, bot: Bot):
    await execute_referral(message, message.from_user.id, bot)

# --- 5. MENING OBUNAM ---

async def execute_my_sub(target, user_id: int):
    sub = await database.get_active_subscription(user_id)
    if sub:
        plan_titles = {
            "vip": "Doimiy VIP a'zo", 
            "trial": "3 kunlik bepul sinov muddati", 
            "week": "1 Hafta (7 kun)", 
            "month": "1 Oy (30 kun)"
        }
        title = plan_titles.get(sub["plan_type"], "Faol a'zo")
        end_date_str = sub["end_date"]

        if sub["plan_type"] == "vip":
            duration_str = "Cheksiz (Doimiy)"
            time_left_str = "Cheklovlarsiz"
        else:
            try:
                end_dt = datetime.strptime(end_date_str, "%Y-%m-%d %H:%M:%S")
                duration_str = end_dt.strftime("%d.%m.%Y soat %H:%M")
                now = datetime.now()
                if end_dt > now:
                    diff = end_dt - now
                    hours = int(diff.total_seconds() // 3600)
                    mins = int((diff.total_seconds() % 3600) // 60)
                    if hours >= 24:
                        days = hours // 24
                        rem_hours = hours % 24
                        time_left_str = f"{days} kun {rem_hours} soat"
                    else:
                        time_left_str = f"{hours} soat {mins} daqiqa"
                else:
                    time_left_str = "Tugagan"
            except Exception:
                duration_str = end_date_str
                time_left_str = "—"

        text = (
            "ℹ️ <b>Sizning a'zolik holatingiz:</b>\n\n"
            f"💎 <b>Maqom:</b> {title}\n"
            f"⏳ <b>Amal qilish muddati:</b> {duration_str}\n"
            f"⏱ <b>Qolgan vaqt:</b> {time_left_str}\n"
            "✅ <b>Holati:</b> Faol"
        )
        await target.answer(text, parse_mode="HTML")
    else:
        user = await database.get_user(user_id)
        has_trial = user["has_used_trial"] if user else 0
        if not has_trial:
            text = (
                "ℹ️ <b>Siz hali yopiq guruhga a'zo emassiz.</b>\n\n"
                "Sizda <b>3 kunlik bepul sinov muddati</b> mavjud! Guruhga kirish uchun pastdagi tugmani bosing:"
            )
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🚛 3 kunlik sinov bilan kirish", callback_data="btn_vip_access")]
            ])
        else:
            text = (
                "ℹ️ <b>Sizning 3 kunlik bepul sinov muddatingiz yakunlangan.</b>\n\n"
                "Yopiq guruhga kirish va saralangan 1-qo'l yuklarni ko'rish uchun obuna sotib olishingiz mumkin:"
            )
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="💳 Obuna tariflari", callback_data="btn_plans")]
            ])
        await target.answer(text, reply_markup=kb, parse_mode="HTML")

async def callback_my_sub(call: CallbackQuery):
    await execute_my_sub(call.message, call.from_user.id)
    await call.answer()

async def cmd_my_sub_message(message: Message):
    await execute_my_sub(message, message.from_user.id)

# --- 6. GURUHDAGI 'BU DISPETCHER' TUGMASI ---

async def callback_report_dispatcher(call: CallbackQuery, bot: Bot):
    """
    Guruhdagi '🗑 Dispetcher bo'lsa, o'chirish' tugmasi bosilganda:
    Barcha a'zolar uchun xatosiz ishlaydi. E'lonni guruhdan o'chirib,
    dispetcherni (ham akkaunt, ham telefon raqamini) qora ro'yxatga kiritadi.
    Kelgusida bu raqamdan birorta e'lon guruhga aslo o'tmaydi.
    """
    import re
    import html

    if not call.message:
        try:
            await call.answer("Ushbu e'lon allaqachon o'chirilgan!", show_alert=True)
        except Exception:
            pass
        return

    data_parts = (call.data or "").split(":")
    sender_id = data_parts[1] if len(data_parts) > 1 else ""
    message_text = call.message.text or call.message.caption or ""

    # E'lon matni, yo'nalishi va telefon raqamini ajratish
    phone_match = re.search(r"Aloqa uchun raqam:\s*([+\d\s\(\)-]+)", message_text)
    raw_phone = phone_match.group(1).strip() if phone_match else ""
    extracted_phone = extract_phone(raw_phone) or extract_phone(message_text) or raw_phone

    dest_match = re.search(r"Yo'nalish:\s*([^\n]+)", message_text)
    dest_text = dest_match.group(1).strip() if dest_match else ""

    ad_match = re.search(r"E'lon(?:\s*matni)?:\s*\n?(.*?)(?=\n🔗|\n\Z|\Z)", message_text, re.DOTALL | re.IGNORECASE)
    ad_text = ad_match.group(1).strip() if ad_match else message_text

    # Xabarni guruhdan o'chirish
    already_deleted = False
    try:
        await bot.delete_message(chat_id=call.message.chat.id, message_id=call.message.message_id)
    except Exception as e:
        err_str = str(e).lower()
        if "message to delete not found" in err_str or "message can't be deleted" in err_str:
            already_deleted = True
        else:
            logger.error(f"Xabarni o'chirishda xatolik: {e}")

    if already_deleted:
        try:
            await call.answer("Ushbu e'lon allaqachon o'chirilgan!", show_alert=True)
        except Exception:
            pass
        return

    # Qora ro'yxatga kiritish: Faqat ushbu o'chirilgan dispetcher akkaunti (sender_id) bloklanadi.
    # Boshqa akkauntlarga nisbatan xabarlar asossiz bloklanmaydi (haqiqiy yuk egalari to'silmasligi uchun).
    user_name = call.from_user.full_name or "Guruh a'zosi"
    reason_str = f"Guruh a'zosi ({user_name}) tomonidan dispetcher deb o'chirildi"

    if sender_id and sender_id not in ("None", "0", ""):
        await database.block_sender(
            sender_id=sender_id,
            sender_name="Dispetcher akkaunti",
            reason=reason_str
        )

    # Guruhdan o'chirilgan yuk yozuvini tozalash (haqiqiy yuk egasiga keyinchalik xalaqit bermasligi uchun)
    if extracted_phone:
        await database.delete_forwarded_cargo_by_phone(extracted_phone)
        clean_norm_phone = extract_phone(extracted_phone)
        if clean_norm_phone and clean_norm_phone != extracted_phone:
            await database.delete_forwarded_cargo_by_phone(clean_norm_phone)

    logger.info(f"🚨 DISPETCHER GURUHDAN O'CHIRILDI VA FAQAT USHBU AKKAUNT BLOKLANDI: ID {sender_id} (Tel: {extracted_phone}) | O'chirgan: {user_name} ({call.from_user.id})")

    # Outreach taklif bazasiga kiritish (dispetcherga taklif yuborish uchun)
    try:
        uid = int(sender_id) if (sender_id and sender_id.isdigit()) else 0
        await database.add_outreach_lead(
            user_id=uid,
            username=None,
            first_name="Dispetcher",
            last_name="",
            phone=extracted_phone,
            reason=f"Guruhdan o'chirildi ({reason_str[:80]})",
            message_snippet=ad_text[:180],
            source_group="Yopiq Guruh"
        )
    except Exception as err:
        logger.debug(f"Outreach lead qo'shishda xatolik: {err}")

    # Tugmani bosgan a'zoga bildirishnoma (Telegram 200 belgilik qat'iy chekloviga mos holda)
    alert_msg = "✅ Katta rahmat!\n\n🗑 Dispetcher e'loni o'chirildi va uning akkaunti QORA RO'YXATGA olindi.\n\n🛡 Endi uning xabarlari guruhga aslo tushmaydi!"

    try:
        await call.answer(alert_msg, show_alert=True)
    except Exception as ans_err:
        logger.warning(f"call.answer da xatolik: {ans_err}")
        try:
            await call.answer("E'lon o'chirildi va qora ro'yxatga olindi.", show_alert=False)
        except Exception:
            pass

    # E'lonni chuqur tahlil qilish (Adminga hisobot uchun)
    phone_history = []
    if extracted_phone:
        phone_history = await database.get_phone_forward_history(extracted_phone, hours=24)
    analysis = analyze_reported_cargo_ad(
        text=ad_text,
        phone=extracted_phone,
        sender_id=sender_id,
        destinations_text=dest_text,
        phone_history=phone_history,
        is_blocked=True
    )

    # Adminga to'liq tahlil hisoboti yuborish
    if config.ADMIN_ID:
        original_source_title = phone_history[0].get("source_title", "Noma'lum") if phone_history else "Noma'lum"
        admin_msg = (
            "🚨 <b>DISPETCHER E'LONI GURUHDAN O'CHIRILDI!</b>\n\n"
            f"👤 <b>O'chirgan a'zo:</b> {html.escape(user_name)} (ID: <code>{call.from_user.id}</code>)\n"
            f"🏛 <b>Manba:</b> {html.escape(original_source_title)}\n"
            f"📞 <b>Qora ro'yxatdagi raqam:</b> <code>{html.escape(extracted_phone or 'Mavjud emas')}</code>\n"
            f"🆔 <b>Sender ID:</b> <code>{html.escape(sender_id or 'Mavjud emas')}</code>\n"
            f"📍 <b>Yo'nalish:</b> {html.escape(dest_text)}\n\n"
            f"📝 <b>E'lon matni:</b>\n<i>{html.escape(ad_text)}</i>\n\n"
            f"🔬 <b>AI Tahlil xulosasi:</b> {analysis.get('verdict_text', 'Dispetcher')} (Disp: {analysis.get('disp_score', 0)}, Yukchi: {analysis.get('shipper_score', 0)})\n"
            "🗑 <i>Xabar o'chirildi va raqam barcha formatlari bilan qora ro'yxatga kiritildi (keyingi e'lonlari kiritilmaydi).</i>"
        )
        try:
            await bot.send_message(chat_id=config.ADMIN_ID, text=admin_msg, parse_mode="HTML")
        except Exception as e:
            logger.error(f"Adminga xabarnoma yuborishda xatolik: {e}")

# --- 7. GURUHGA QO'SHILISH VA SOZLASH ---

async def on_my_chat_member(event: ChatMemberUpdated, bot: Bot):
    """Bot guruhga admin qilib qo'shilganda guruh ID sini avtomatik aniqlash."""
    if event.new_chat_member.status in ("administrator", "creator"):
        chat_id = event.chat.id
        chat_title = event.chat.title or "Yopiq Guruh"
        save_private_group_id(chat_id)
        logger.info(f"Bot yopiq guruhga admin bo'ldi: {chat_title} (ID: {chat_id})")

        if config.ADMIN_ID:
            try:
                await bot.send_message(
                    chat_id=config.ADMIN_ID,
                    text=(
                        f"✅ <b>Yopiq guruh muvaffaqiyatli ulandi!</b>\n\n"
                        f"📌 Nomi: <b>{html.escape(chat_title)}</b>\n"
                        f"🆔 Guruh ID: <code>{chat_id}</code>\n\n"
                        "Endi bot ushbu guruh uchun 1 kishilik va 1 soatlik taklif havolalarini avtomatik taqdim etadi!"
                    ),
                    parse_mode="HTML"
                )
            except Exception as e:
                logger.error(f"Adminga xabar yuborishda xatolik: {e}")

async def cmd_set_group(message: Message, bot: Bot):
    """Guruh ichida /setgroup buyrug'i yozilganda shu guruhni asosiy yopiq guruh qilib belgilash."""
    if message.chat.type in ("group", "supergroup"):
        chat_id = message.chat.id
        chat_title = message.chat.title or "Yopiq Guruh"
        save_private_group_id(chat_id)
        await message.answer(
            f"✅ <b>Ushbu guruh muvaffaqiyatli biriktirildi!</b>\n\n"
            f"📌 Guruh nomi: <b>{html.escape(chat_title)}</b>\n"
            f"🆔 Guruh ID: <code>{chat_id}</code>\n\n"
            "Endi obuna yoki 3 kunlik sinov muddati olganlarga aynan shu guruhga havola beriladi.",
            parse_mode="HTML"
        )

async def cmd_reset_trial(message: Message):
    """Admin uchun o'zining sinov muddatini test qilish maqsadida 0 ga tushirish."""
    if message.from_user.id == config.ADMIN_ID:
        import aiosqlite
        async with aiosqlite.connect(config.DB_PATH) as db:
            await db.execute("UPDATE users SET has_used_trial = 0 WHERE user_id = ?", (message.from_user.id,))
            await db.commit()
        await message.answer(
            "🔄 <b>Sinov muddati holati qayta tiklandi (0 qilindi)!</b>\n"
            "Endi botda '🎁 3 kunlik sinov muddati' tugmasini qayta bosib tekshirishingiz mumkin.",
            parse_mode="HTML"
        )

async def cmd_stats(message: Message):
    """Admin uchun /stat buyrug'i."""
    if message.from_user.id != config.ADMIN_ID:
        return
    stats = await database.get_admin_stats()
    text = format_admin_stats(stats)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📋 Bugungi uzatilgan yuklar", callback_data="btn_today_cargos")],
        [InlineKeyboardButton(text="🔄 Yangilash", callback_data="btn_admin_stats")],
        [InlineKeyboardButton(text="⬅️ Asosiy menyu", callback_data="btn_back_main")]
    ])
    await message.answer(text, reply_markup=kb, parse_mode="HTML")

async def callback_admin_stats(call: CallbackQuery):
    """Admin statistika tugmasini bosganda yoki yangilaganda."""
    if call.from_user.id != config.ADMIN_ID:
        await call.answer("Bu statistika faqat administrator uchun!", show_alert=True)
        return
    stats = await database.get_admin_stats()
    text = format_admin_stats(stats)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📋 Bugungi uzatilgan yuklar", callback_data="btn_today_cargos")],
        [InlineKeyboardButton(text="🔄 Yangilash", callback_data="btn_admin_stats")],
        [InlineKeyboardButton(text="⬅️ Asosiy menyu", callback_data="btn_back_main")]
    ])
    try:
        await call.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    except Exception:
        pass
    await call.answer("Statistika yangilandi.")

async def cmd_today_cargos(message: Message):
    """Admin uchun bugun guruhga uzatilgan barcha yuklarni monitoring qilish."""
    if message.from_user.id != config.ADMIN_ID:
        return
    cargos = await database.get_today_forwarded_cargos_list(limit=25)
    stats = await database.get_forwarded_cargos_stats()

    if not cargos:
        await message.answer(
            f"📊 <b>BUGUNGI YUKLAR MONITORINGI</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            f"📅 Bugun guruhga hali yangi toza yuk e'lonlari uzatilmadi.\n"
            f"📦 Jami uzatilgan: <b>{stats['total_forwarded']} ta</b>",
            parse_mode="HTML"
        )
        return

    lines = [
        f"📊 <b>BUGUN GURUHGA UZATILGAN YUKLAR NAZORATI</b>\n"
        f"📅 Bugun uzatildi: <b>{stats['today_forwarded']} ta</b> | Jami: <b>{stats['total_forwarded']} ta</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "<i>So'nggi uzatilgan yuklar:</i>\n"
    ]
    for idx, c in enumerate(cargos, start=1):
        time_part = str(c['created_at']).split(" ")[1][:5] if " " in str(c['created_at']) else ""
        lines.append(
            f"<b>{idx}.</b> ⏰ <b>{time_part}</b> | 📍 <b>{html.escape(c['destinations'])}</b>\n"
            f"   📞 <code>{html.escape(c['phone'])}</code> | Guruh: <i>{html.escape(c['source_title'])}</i>\n"
        )

    await message.answer("\n".join(lines), parse_mode="HTML")

async def callback_today_cargos(call: CallbackQuery):
    """Admin statistika menyusidan bugungi yuklar tugmasini bosganda."""
    if call.from_user.id != config.ADMIN_ID:
        await call.answer("Faqat administrator uchun!", show_alert=True)
        return
    cargos = await database.get_today_forwarded_cargos_list(limit=25)
    stats = await database.get_forwarded_cargos_stats()

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Yangilash", callback_data="btn_today_cargos")],
        [InlineKeyboardButton(text="⬅️ Statistikaga qaytish", callback_data="btn_admin_stats")]
    ])

    if not cargos:
        text = (
            f"📊 <b>BUGUNGI YUKLAR MONITORINGI</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            f"📅 Bugun guruhga hali yangi toza yuk e'lonlari uzatilmadi.\n"
            f"📦 Jami uzatilgan: <b>{stats['total_forwarded']} ta</b>"
        )
    else:
        lines = [
            f"📊 <b>BUGUN GURUHGA UZATILGAN YUKLAR NAZORATI</b>\n"
            f"📅 Bugun uzatildi: <b>{stats['today_forwarded']} ta</b> | Jami: <b>{stats['total_forwarded']} ta</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "<i>So'nggi uzatilgan yuklar:</i>\n"
        ]
        for idx, c in enumerate(cargos, start=1):
            time_part = str(c['created_at']).split(" ")[1][:5] if " " in str(c['created_at']) else ""
            lines.append(
                f"<b>{idx}.</b> ⏰ <b>{time_part}</b> | 📍 <b>{html.escape(c['destinations'])}</b>\n"
                f"   📞 <code>{html.escape(c['phone'])}</code> | Guruh: <i>{html.escape(c['source_title'])}</i>\n"
            )
        text = "\n".join(lines)

    try:
        await call.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    except Exception:
        pass
    await call.answer()

async def handle_user_message(message: Message, bot: Bot):
    """Foydalanuvchi botga ixtiyoriy matn, savol yoki murojaat yozganda adminga yetkazish va e'tibor qaratish."""
    if not message.text:
        return
    user_id = message.from_user.id
    if user_id == config.ADMIN_ID:
        return

    safe_name = html.escape(message.from_user.full_name or "Foydalanuvchi")
    username = message.from_user.username
    user_text = html.escape(message.text)

    # 1. Adminga darhol xabar yetkazish
    if config.ADMIN_ID != 0:
        username_str = f"@{username}" if username else "Mavjud emas"
        admin_alert = (
            "📩 <b>BOT FOYDALANUVCHISIDAN MUROJAAT / XABAR:</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            f"👤 <b>Kimdan:</b> {safe_name}\n"
            f"🆔 <b>Telegram ID:</b> <code>{user_id}</code>\n"
            f"🔗 <b>Username:</b> {username_str}\n"
            f"🕒 <b>Vaqt:</b> {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}\n"
            f"💬 <b>Murojaat matni:</b>\n<i>{user_text}</i>\n"
            "━━━━━━━━━━━━━━━━━━━━"
        )
        profile_url = f"https://t.me/{username}" if username else f"tg://user?id={user_id}"
        admin_kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="💬 Foydalanuvchiga yozish", url=profile_url)]
        ])
        try:
            await bot.send_message(chat_id=config.ADMIN_ID, text=admin_alert, reply_markup=admin_kb, parse_mode="HTML")
        except Exception as e:
            logger.debug(f"Adminga murojaat yetkazishda xatolik: {e}")

    # 2. Foydalanuvchiga muloyim javob va VIP guruh tugmasi
    reply_text = (
        f"Assalomu alaykum, <b>{safe_name}</b>!\n\n"
        "Xabaringiz ma'muriyatga yetkazildi. Tez orada siz bilan bog'lanamiz.\n\n"
        "Agar siz <b>yopiq VIP guruhga</b> kirmoqchi bo'lsangiz, quyidagi tugmani bosing:"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🚛 Yopiq guruhga kirish (VIP)", callback_data="btn_vip_access")],
        [InlineKeyboardButton(text="ℹ️ Mening a'zoligim", callback_data="btn_my_sub")]
    ])
    await message.answer(reply_text, reply_markup=kb, parse_mode="HTML")

# --- HANDLERLARNI RO'YXATDAN O'TKAZISH ---

async def setup_bot_commands(bot: Bot):
    """Telegramning chap pastki burchagidagi ko'k 'Menu' tugmasiga buyruqlarni o'rnatish."""
    commands = [
        BotCommand(command="start", description="🚀 Boshlash / Asosiy menyu"),
        BotCommand(command="vip", description="🚛 Yopiq guruhga kirish (VIP)"),
        BotCommand(command="about", description="📖 Yopiq guruh haqida"),
        BotCommand(command="sub", description="ℹ️ Mening a'zoligim"),
        BotCommand(command="ref", description="👥 Do'stlarni taklif qilish"),
        BotCommand(command="stat", description="📊 Statistika (Admin)")
    ]
    try:
        await bot.set_my_commands(commands)
    except Exception as e:
        logger.error(f"Bot buyruqlarini sozlashda xatolik: {e}")

def register_handlers(dp: Dispatcher):
    dp.my_chat_member.register(on_my_chat_member)
    dp.message.register(cmd_set_group, Command("setgroup", "id"))
    dp.message.register(cmd_reset_trial, Command("reset_trial"))
    dp.message.register(cmd_stats, Command("stat", "stats", "statistika", "admin"))
    dp.message.register(cmd_today_cargos, Command("today", "yuklar", "bugun"))
    dp.message.register(cmd_start, CommandStart())

    # Komandalar
    dp.message.register(cmd_about_service_message, Command("about", "haqida", "info"))
    dp.message.register(cmd_vip_message, Command("vip", "trial", "kirish"))
    dp.message.register(cmd_plans_message, Command("plans", "tariflar"))
    dp.message.register(cmd_my_sub_message, Command("sub", "obunam"))
    dp.message.register(cmd_referral_message, Command("ref", "referal"))

    # Pastki (Reply) klaviatura tugmalari bosilganda
    dp.message.register(cmd_start, F.text.in_(["🚀 Boshlash /start", "🚀 Boshlash", "Asosiy menyu"]))
    dp.message.register(cmd_about_service_message, F.text.in_([
        "📖 Yopiq guruh haqida",
        "📖 Bot va Guruh nima uchun?",
        "📖 Bot va Guruh haqida",
        "📖 Bu qanday ishlaydi?"
    ]))
    dp.message.register(cmd_vip_message, F.text.in_([
        "🚛 Yopiq guruhga kirish",
        "🚛 Yopiq guruhga kirish (VIP)",
        "🚛 Yopiq guruhga kirish (Doimiy VIP)",
        "🎁 3 kunlik sinov muddati"
    ]))
    dp.message.register(cmd_plans_message, F.text.in_([
        "💳 Obuna sotib olish",
        "💳 Obuna (Tariflar)",
        "💳 Tariflar"
    ]))
    dp.message.register(cmd_my_sub_message, F.text.in_(["ℹ️ Mening a'zoligim", "ℹ️ Mening obunam"]))
    dp.message.register(cmd_referral_message, F.text.in_(["👥 Taklif qilish (Bonus)", "👥 Taklif qilish"]))
    dp.message.register(cmd_stats, F.text == "📊 Statistika")

    # Inline callback query'lar
    dp.callback_query.register(callback_about_service, F.data == "btn_about_service")
    dp.callback_query.register(callback_admin_stats, F.data == "btn_admin_stats")
    dp.callback_query.register(callback_today_cargos, F.data == "btn_today_cargos")
    dp.callback_query.register(callback_back_main, F.data == "btn_back_main")
    dp.callback_query.register(callback_vip_access, F.data.in_(["btn_vip_access", "btn_trial"]))
    dp.callback_query.register(callback_plans, F.data == "btn_plans")
    dp.callback_query.register(callback_buy_plan, F.data.startswith("buy_plan:"))
    dp.callback_query.register(callback_send_receipt, F.data.startswith("btn_send_receipt:"))
    dp.callback_query.register(callback_paid_done, F.data.startswith("btn_paid_done:"))
    dp.callback_query.register(callback_admin_approve, F.data.startswith("admin_approve:"))
    dp.callback_query.register(callback_admin_reject, F.data.startswith("admin_reject:"))
    dp.callback_query.register(callback_referral, F.data == "btn_referral")
    dp.callback_query.register(callback_my_sub, F.data == "btn_my_sub")
    dp.callback_query.register(callback_report_dispatcher, F.data.startswith("disp_report:"))

    # To'lov cheki rasmini qabul qilish handler'i
    dp.message.register(handle_receipt_photo, F.photo)

    # Har qanday erkin matnli murojaat va savollar uchun fallback
    dp.message.register(handle_user_message, F.text)


