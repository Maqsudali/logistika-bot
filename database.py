import aiosqlite
import logging
import re
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Tuple
from config import DB_PATH

logger = logging.getLogger(__name__)

# Persistent connection (connection pool) - har safar yangi ulanish ochmaslik uchun
_db_connection: Optional[aiosqlite.Connection] = None

async def _get_db() -> aiosqlite.Connection:
    """Yagona persistent DB ulanishini qaytarish (connection reuse)."""
    global _db_connection
    if _db_connection is None:
        _db_connection = await aiosqlite.connect(DB_PATH, timeout=60.0)
        _db_connection.row_factory = aiosqlite.Row
        # SQLite optimizatsiya pragmalari (qulflanishni oldini olish)
        await _db_connection.execute("PRAGMA busy_timeout = 60000")
        await _db_connection.execute("PRAGMA journal_mode=WAL")
        await _db_connection.execute("PRAGMA synchronous=NORMAL")
        await _db_connection.execute("PRAGMA cache_size=-8000")  # 8MB cache
        await _db_connection.execute("PRAGMA mmap_size=67108864")  # 64MB mmap
        await _db_connection.execute("PRAGMA temp_store=MEMORY")
    return _db_connection

async def close_db():
    """DB ulanishini yopish (graceful shutdown uchun)."""
    global _db_connection
    if _db_connection:
        await _db_connection.close()
        _db_connection = None

async def init_db():
    """Ma'lumotlar bazasini va barcha jadvallarni initsializatsiya qilish."""
    db = await _get_db()

    await db.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            full_name TEXT,
            has_used_trial INTEGER DEFAULT 0,
            referral_balance INTEGER DEFAULT 0,
            referrer_id INTEGER,
            joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            group_request_sent INTEGER DEFAULT 0
        )
    """)

    try:
        await db.execute("ALTER TABLE users ADD COLUMN group_request_sent INTEGER DEFAULT 0")
        await db.commit()
    except Exception:
        pass

    await db.execute("""
        CREATE TABLE IF NOT EXISTS subscriptions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            plan_type TEXT NOT NULL,
            start_date TIMESTAMP NOT NULL,
            end_date TIMESTAMP NOT NULL,
            is_active INTEGER DEFAULT 1,
            warning_sent INTEGER DEFAULT 0,
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        )
    """)

    try:
        await db.execute("ALTER TABLE subscriptions ADD COLUMN warning_sent INTEGER DEFAULT 0")
        await db.commit()
    except Exception:
        pass

    await db.execute("""
        CREATE TABLE IF NOT EXISTS payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            plan_type TEXT NOT NULL,
            amount INTEGER NOT NULL,
            discount INTEGER DEFAULT 0,
            receipt_file_id TEXT,
            receipt_text TEXT,
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        )
    """)

    await db.execute("""
        CREATE TABLE IF NOT EXISTS blocked_senders (
            sender_id TEXT PRIMARY KEY,
            sender_name TEXT,
            reason TEXT,
            blocked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    await db.execute("""
        CREATE TABLE IF NOT EXISTS sender_activity (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sender_id TEXT NOT NULL,
            destination TEXT,
            phone TEXT,
            cargo_signature TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    await db.execute("""
        CREATE TABLE IF NOT EXISTS forwarded_cargos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            destinations TEXT,
            phone TEXT,
            source_title TEXT,
            sender_id TEXT,
            cargo_signature TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    await db.execute("""
        CREATE TABLE IF NOT EXISTS outreach_leads (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            last_name TEXT,
            phone TEXT,
            reason TEXT,
            message_snippet TEXT,
            source_group TEXT,
            status TEXT DEFAULT 'pending',
            error_message TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            sent_at TIMESTAMP
        )
    """)

    # Ustunlar migratsiyasi (agar avval ochilgan jadvallarda bo'lmasa)
    try:
        await db.execute("ALTER TABLE forwarded_cargos ADD COLUMN sender_id TEXT")
        await db.commit()
    except Exception:
        pass
    try:
        await db.execute("ALTER TABLE forwarded_cargos ADD COLUMN cargo_signature TEXT")
        await db.commit()
    except Exception:
        pass
    try:
        await db.execute("ALTER TABLE sender_activity ADD COLUMN phone TEXT")
        await db.commit()
    except Exception:
        pass
    try:
        await db.execute("ALTER TABLE sender_activity ADD COLUMN cargo_signature TEXT")
        await db.commit()
    except Exception:
        pass
    try:
        await db.execute("ALTER TABLE outreach_leads ADD COLUMN whatsapp_status TEXT DEFAULT 'pending'")
        await db.commit()
    except Exception:
        pass
    try:
        await db.execute("ALTER TABLE outreach_leads ADD COLUMN whatsapp_sent_at TIMESTAMP")
        await db.commit()
    except Exception:
        pass

    # --- TEZLIK UCHUN INDEXLAR ---
    await db.execute("CREATE INDEX IF NOT EXISTS idx_subscriptions_user_active ON subscriptions(user_id, is_active, end_date)")
    await db.execute("CREATE INDEX IF NOT EXISTS idx_payments_status ON payments(status)")
    await db.execute("CREATE INDEX IF NOT EXISTS idx_payments_user ON payments(user_id, status)")
    await db.execute("CREATE INDEX IF NOT EXISTS idx_payments_created ON payments(created_at)")
    await db.execute("CREATE INDEX IF NOT EXISTS idx_sender_activity_sender ON sender_activity(sender_id, created_at)")
    await db.execute("CREATE INDEX IF NOT EXISTS idx_sender_activity_phone ON sender_activity(phone, created_at)")
    await db.execute("CREATE INDEX IF NOT EXISTS idx_users_joined ON users(joined_at)")
    await db.execute("CREATE INDEX IF NOT EXISTS idx_forwarded_cargos_created ON forwarded_cargos(created_at)")
    await db.execute("CREATE INDEX IF NOT EXISTS idx_forwarded_cargos_sender ON forwarded_cargos(sender_id, created_at)")
    await db.execute("CREATE INDEX IF NOT EXISTS idx_forwarded_cargos_phone ON forwarded_cargos(phone, created_at)")
    await db.execute("CREATE INDEX IF NOT EXISTS idx_outreach_leads_status ON outreach_leads(status, created_at)")
    await db.execute("CREATE INDEX IF NOT EXISTS idx_outreach_leads_wa_status ON outreach_leads(whatsapp_status, created_at)")
    await db.execute("CREATE INDEX IF NOT EXISTS idx_blocked_senders_sid ON blocked_senders(sender_id)")

    # Mavjud qora ro'yxatdagi telefon raqamlarini barcha formatlar (last9, +998...) bilan to'ldirish
    try:
        async with db.execute("SELECT sender_id, sender_name, reason FROM blocked_senders WHERE sender_id LIKE '%9%' OR sender_id LIKE '%+%' OR sender_id LIKE '%8%'") as cursor:
            b_rows = await cursor.fetchall()
            for r in b_rows:
                b_sid, b_name, b_reason = r[0], r[1], r[2]
                b_digits = re.sub(r"\D", "", str(b_sid))
                if len(b_digits) >= 9:
                    b_last9 = b_digits[-9:]
                    await db.execute("INSERT OR IGNORE INTO blocked_senders (sender_id, sender_name, reason) VALUES (?, ?, ?)", (b_last9, b_name, b_reason))
                    await db.execute("INSERT OR IGNORE INTO blocked_senders (sender_id, sender_name, reason) VALUES (?, ?, ?)", (f"+998{b_last9}", b_name, b_reason))
                    await db.execute("INSERT OR IGNORE INTO blocked_senders (sender_id, sender_name, reason) VALUES (?, ?, ?)", (f"998{b_last9}", b_name, b_reason))
    except Exception:
        pass

    await db.commit()

async def get_or_create_user(
    user_id: int, 
    username: Optional[str], 
    full_name: Optional[str], 
    referrer_id: Optional[int] = None
) -> Dict[str, Any]:
    """Foydalanuvchini olish yoki yangi foydalanuvchi sifatida yaratish."""
    db = await _get_db()
    async with db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)) as cursor:
        user = await cursor.fetchone()
        if user:
            return dict(user)

    # Yangi foydalanuvchi yaratish
    await db.execute("""
        INSERT INTO users (user_id, username, full_name, referrer_id)
        VALUES (?, ?, ?, ?)
    """, (user_id, username, full_name, referrer_id))
    await db.commit()

    # Agar taklif qilgan odam bo'lsa, unga bonus berish
    if referrer_id and referrer_id != user_id:
        # Referrer bazada borligini tekshiramiz
        async with db.execute("SELECT user_id FROM users WHERE user_id = ?", (referrer_id,)) as ref_cursor:
            if await ref_cursor.fetchone():
                from config import REFERRAL_BONUS
                await db.execute("""
                    UPDATE users 
                    SET referral_balance = referral_balance + ? 
                    WHERE user_id = ?
                """, (REFERRAL_BONUS, referrer_id))
                await db.commit()

    async with db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)) as cursor:
        new_user = await cursor.fetchone()
        return dict(new_user)

async def get_user(user_id: int) -> Optional[Dict[str, Any]]:
    """Foydalanuvchini olish."""
    db = await _get_db()
    async with db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)) as cursor:
        user = await cursor.fetchone()
        return dict(user) if user else None

async def update_trial_used(user_id: int):
    """Sinov muddatidan foydalangan deb belgilash."""
    db = await _get_db()
    await db.execute("UPDATE users SET has_used_trial = 1 WHERE user_id = ?", (user_id,))
    await db.commit()

async def deduct_referral_balance(user_id: int, amount: int):
    """Foydalanuvchining referal balansidan chegirib tashlash."""
    db = await _get_db()
    await db.execute("""
        UPDATE users 
        SET referral_balance = MAX(0, referral_balance - ?) 
        WHERE user_id = ?
    """, (amount, user_id))
    await db.commit()

async def get_referral_count(user_id: int) -> int:
    """Foydalanuvchi taklif qilgan do'stlar (referallar) sonini hisoblash."""
    db = await _get_db()
    async with db.execute("SELECT COUNT(*) FROM users WHERE referrer_id = ?", (user_id,)) as cursor:
        row = await cursor.fetchone()
        return row[0] if row else 0

async def create_subscription(user_id: int, plan_type: str, duration_hours: int) -> Dict[str, Any]:
    """Yangi obunani yaratish yoki mavjud faol obunani uzaytirish."""
    now = datetime.now()
    db = await _get_db()
    # Mavjud faol obuna bormi tekshiramiz
    async with db.execute("""
        SELECT * FROM subscriptions 
        WHERE user_id = ? AND is_active = 1 AND end_date > ?
        ORDER BY end_date DESC LIMIT 1
    """, (user_id, now.strftime("%Y-%m-%d %H:%M:%S"))) as cursor:
        existing = await cursor.fetchone()

    if plan_type == "vip":
        end_date_str = "2099-12-31 23:59:59"
        if existing:
            await db.execute("""
                UPDATE subscriptions SET plan_type = 'vip', end_date = ? WHERE id = ?
            """, (end_date_str, existing["id"]))
            await db.commit()
            return {
                "id": existing["id"],
                "user_id": user_id,
                "plan_type": "vip",
                "start_date": existing["start_date"],
                "end_date": end_date_str,
                "is_active": 1
            }
        else:
            start_str = now.strftime("%Y-%m-%d %H:%M:%S")
            cursor = await db.execute("""
                INSERT INTO subscriptions (user_id, plan_type, start_date, end_date, is_active)
                VALUES (?, 'vip', ?, ?, 1)
            """, (user_id, start_str, end_date_str))
            await db.commit()
            return {
                "id": cursor.lastrowid,
                "user_id": user_id,
                "plan_type": "vip",
                "start_date": start_str,
                "end_date": end_date_str,
                "is_active": 1
            }

    if existing:
        # Agar mavjud obuna bo'lsa, uning tugash vaqtiga qo'shamiz
        current_end = datetime.strptime(existing["end_date"], "%Y-%m-%d %H:%M:%S")
        new_end = current_end + timedelta(hours=duration_hours)
        await db.execute("""
            UPDATE subscriptions SET end_date = ? WHERE id = ?
        """, (new_end.strftime("%Y-%m-%d %H:%M:%S"), existing["id"]))
        await db.commit()
        return {
            "id": existing["id"],
            "user_id": user_id,
            "plan_type": plan_type,
            "start_date": existing["start_date"],
            "end_date": new_end.strftime("%Y-%m-%d %H:%M:%S"),
            "is_active": 1
        }
    else:
        # Yangi obuna
        start_str = now.strftime("%Y-%m-%d %H:%M:%S")
        end_str = (now + timedelta(hours=duration_hours)).strftime("%Y-%m-%d %H:%M:%S")
        cursor = await db.execute("""
            INSERT INTO subscriptions (user_id, plan_type, start_date, end_date, is_active)
            VALUES (?, ?, ?, ?, 1)
        """, (user_id, plan_type, start_str, end_str))
        await db.commit()
        return {
            "id": cursor.lastrowid,
            "user_id": user_id,
            "plan_type": plan_type,
            "start_date": start_str,
            "end_date": end_str,
            "is_active": 1
        }

async def get_active_subscription(user_id: int) -> Optional[Dict[str, Any]]:
    """Foydalanuvchining faol obunasi mavjudligini tekshirish."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    db = await _get_db()
    async with db.execute("""
        SELECT * FROM subscriptions 
        WHERE user_id = ? AND is_active = 1 AND end_date > ?
        ORDER BY end_date DESC LIMIT 1
    """, (user_id, now)) as cursor:
        sub = await cursor.fetchone()
        return dict(sub) if sub else None

async def get_expired_active_subscriptions() -> List[Dict[str, Any]]:
    """Muddati tugagan, lekin hali o'chirilmagan (is_active=1) obunalar ro'yxatini olish."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    db = await _get_db()
    async with db.execute("""
        SELECT * FROM subscriptions 
        WHERE is_active = 1 AND end_date <= ?
    """, (now,)) as cursor:
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]

async def deactivate_subscription(sub_id: int):
    """Obunani faolsizlantirish."""
    db = await _get_db()
    await db.execute("UPDATE subscriptions SET is_active = 0 WHERE id = ?", (sub_id,))
    await db.commit()

async def get_expiring_trial_subscriptions(within_minutes: int = 60) -> List[Dict[str, Any]]:
    """Tugashiga belgilangan daqiqa (1 soat) qolgan va hali ogohlantirish yuborilmagan obunalarni olish."""
    now = datetime.now()
    threshold = (now + timedelta(minutes=within_minutes)).strftime("%Y-%m-%d %H:%M:%S")
    now_str = now.strftime("%Y-%m-%d %H:%M:%S")
    db = await _get_db()
    async with db.execute("""
        SELECT * FROM subscriptions 
        WHERE is_active = 1 
          AND (warning_sent = 0 OR warning_sent IS NULL)
          AND end_date > ? 
          AND end_date <= ?
    """, (now_str, threshold)) as cursor:
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]

async def mark_subscription_warning_sent(sub_id: int):
    """Obunaga ogohlantirish yuborilgan deb belgilash."""
    db = await _get_db()
    await db.execute("UPDATE subscriptions SET warning_sent = 1 WHERE id = ?", (sub_id,))
    await db.commit()

async def create_payment(
    user_id: int,
    plan_type: str,
    amount: int,
    discount: int,
    receipt_file_id: Optional[str] = None,
    receipt_text: Optional[str] = None
) -> int:
    """Yangi to'lov arizasini kiritish."""
    db = await _get_db()
    cursor = await db.execute("""
        INSERT INTO payments (user_id, plan_type, amount, discount, receipt_file_id, receipt_text, status)
        VALUES (?, ?, ?, ?, ?, ?, 'pending')
    """, (user_id, plan_type, amount, discount, receipt_file_id, receipt_text))
    await db.commit()
    return cursor.lastrowid

async def get_payment(payment_id: int) -> Optional[Dict[str, Any]]:
    """To'lov ma'lumotlarini olish."""
    db = await _get_db()
    async with db.execute("SELECT * FROM payments WHERE id = ?", (payment_id,)) as cursor:
        row = await cursor.fetchone()
        return dict(row) if row else None

async def update_payment_status(payment_id: int, status: str):
    """To'lov holatini yangilash (approved, rejected)."""
    db = await _get_db()
    await db.execute("UPDATE payments SET status = ? WHERE id = ?", (status, payment_id))
    await db.commit()

# --- DISPETCHERLAR VA SENDERLARNI BLOKLASH LOGIKASI ---

async def is_sender_blocked(sender_id: str) -> bool:
    """Jo'natuvchi bloklanganligini tekshirish (ID yoki Telefon raqami bo'yicha)."""
    if not sender_id:
        return False
    db = await _get_db()
    sid = str(sender_id).strip()
    if not sid:
        return False

    # 1. To'g'ridan-to'g'ri tekshirish
    async with db.execute("SELECT 1 FROM blocked_senders WHERE sender_id = ?", (sid,)) as cursor:
        if await cursor.fetchone():
            return True

    # 2. Telefon raqami bo'lsa (faqat aniq telefon formatida: + bilan boshlansa yoki 12 xonali 998 bo'lsa)
    digits = re.sub(r"\D", "", sid)
    if sid.startswith("+") or (len(digits) == 12 and digits.startswith("998")):
        last9 = digits[-9:]
        async with db.execute("""
            SELECT 1 FROM blocked_senders 
            WHERE sender_id = ? 
               OR sender_id = ? 
               OR sender_id = ? 
               OR sender_id = ?
        """, (last9, f"+998{last9}", f"998{last9}", digits)) as cursor:
            if await cursor.fetchone():
                return True

    return False

async def block_sender(sender_id: str, sender_name: Optional[str] = None, reason: str = "Dispetcher deb topildi"):
    """Jo'natuvchini bazada bloklash (Faqat berilgan akkaunt/identifikator bloklanadi)."""
    sid = str(sender_id or "").strip()
    if not sid:
        return

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    db = await _get_db()

    # Asosiy sender_id ni kiritish
    await db.execute("""
        INSERT OR REPLACE INTO blocked_senders (sender_id, sender_name, reason, blocked_at)
        VALUES (?, ?, ?, ?)
    """, (sid, sender_name, reason, now_str))

    # Faqat aniq telefon raqami bo'lsa barcha formatlarini ham kiritish
    digits = re.sub(r"\D", "", sid)
    if sid.startswith("+") or (len(digits) == 12 and digits.startswith("998")):
        last9 = digits[-9:]
        variants = [
            last9,             # 901234567
            f"+998{last9}",    # +998901234567
            f"998{last9}",     # 998901234567
            digits             # to'liq raqamlar
        ]
        for v in variants:
            if v and v != sid:
                await db.execute("""
                    INSERT OR REPLACE INTO blocked_senders (sender_id, sender_name, reason, blocked_at)
                    VALUES (?, ?, ?, ?)
                """, (v, sender_name, reason, now_str))

    await db.commit()

async def log_sender_activity(sender_id: str, destination: str, phone: Optional[str] = None, cargo_signature: Optional[str] = None):
    """Jo'natuvchining yo'nalish faolligini qayd qilish."""
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    db = await _get_db()
    await db.execute("""
        INSERT INTO sender_activity (sender_id, destination, phone, cargo_signature, created_at)
        VALUES (?, ?, ?, ?, ?)
    """, (str(sender_id), destination.lower(), str(phone or ""), str(cargo_signature or ""), now_str))
    await db.commit()

async def get_sender_distinct_destinations_today(sender_id: str) -> int:
    """Jo'natuvchining bugungi har xil viloyat/yo'nalishlar sonini hisoblash."""
    today_start = datetime.now().strftime("%Y-%m-%d 00:00:00")
    db = await _get_db()
    sid = str(sender_id)
    digits = re.sub(r"\D", "", sid)
    last9 = digits[-9:] if len(digits) >= 9 else sid
    async with db.execute("""
        SELECT COUNT(DISTINCT destination) FROM sender_activity
        WHERE (sender_id = ? OR sender_id LIKE '%' || ?) AND created_at >= ?
    """, (sid, last9, today_start)) as cursor:
        row = await cursor.fetchone()
        return row[0] if row else 0

async def is_sender_spammer(sender_id: str, phone: Optional[str] = None) -> bool:
    """AGENTS.md: Akkaunt qisqa vaqtda guruhlarga spambot orqali qayta-qayta tashlayotgan bo'lsa."""
    db = await _get_db()
    ten_mins_ago = (datetime.now() - timedelta(minutes=10)).strftime("%Y-%m-%d %H:%M:%S")
    # Turli xil e'lonlar / yuklar (cargo_signature) soni 3 va undan ortiq bo'lsa dispetcher spambot hisoblanadi
    query = """
        SELECT COUNT(DISTINCT cargo_signature) FROM sender_activity 
        WHERE (sender_id = ? OR (phone != '' AND phone = ?)) AND created_at >= ?
    """
    async with db.execute(query, (str(sender_id), str(phone or ""), ten_mins_ago)) as cursor:
        row = await cursor.fetchone()
        distinct_cargos = row[0] if row else 0
        return distinct_cargos >= 3

async def is_phone_already_forwarded(phone: str, hours: int = 12) -> bool:
    """Ushbu telefon raqamidan so'nggi 12 soat ichida e'lon yuborilganmi."""
    db = await _get_db()
    time_limit = (datetime.now() - timedelta(hours=hours)).strftime("%Y-%m-%d %H:%M:%S")
    phone_digits = re.sub(r"\D", "", str(phone))
    phone_filter = phone_digits[-9:] if len(phone_digits) >= 9 else str(phone)
    async with db.execute("""
        SELECT COUNT(*) FROM forwarded_cargos 
        WHERE (phone = ? OR phone LIKE '%' || ?) AND created_at >= ?
    """, (str(phone), phone_filter, time_limit)) as cursor:
        row = await cursor.fetchone()
        return (row[0] if row else 0) >= 1

async def check_cargo_forward_eligibility(
    sender_id: str,
    phone: str,
    cargo_signature: str = "",
    dest_text: str = "",
    hours: int = 12
) -> Tuple[bool, str]:
    """
    Foydalanuvchining yangilangan qat'iy mezonlari:
    1. Ayni bir xil e'lonni (telefon + yo'nalish + yuk hash'i) 12 soat ichida takror yuborish taqiqlanadi (faqat 1 marta uzatiladi).
       Biroq, bir xil e'lonni ko'p guruhga tashlash dispetcherlik belgisi EMAS, shunchaki takrorlash to'xtatiladi (bloklanmaydi).
    2. Haqiqiy yukchida 2 tagacha har xil yo'nalish/yuk bo'lishi mumkin (2 tagacha ruxsat beriladi).
    3. Faqat 3 va undan ortiq har xil yo'nalish bo'lganidagina (3-yo'nalishdan boshlab) dispetcher deb topiladi va bloklanadi.
    """
    db = await _get_db()
    time_limit = (datetime.now() - timedelta(hours=hours)).strftime("%Y-%m-%d %H:%M:%S")
    phone_digits = re.sub(r"\D", "", str(phone or ""))
    phone_filter = phone_digits[-9:] if len(phone_digits) >= 9 else str(phone)
    sid = str(sender_id or "").strip()

    # 1. Ayni bir xil e'lon so'nggi 12 soat ichida yopiq guruhga allaqachon uzatilganmi? (Deduplikatsiya)
    if cargo_signature:
        async with db.execute("""
            SELECT COUNT(*) FROM forwarded_cargos 
            WHERE cargo_signature = ? AND created_at >= ?
        """, (cargo_signature, time_limit)) as cursor:
            row = await cursor.fetchone()
            if (row[0] if row else 0) >= 1:
                return False, f"Ushbu e'lon so'nggi {hours} soat ichida yopiq guruhga allaqachon yuborilgan (takror)"

    # 2. Har xil yo'nalishlar tekshiruvi:
    # So'nggi 12 soat ichida ushbu raqam yoki akkauntdan guruhga nechta HAR XIL yo'nalish uzatilgan?
    dest_norm = dest_text.strip().lower()
    async with db.execute("""
        SELECT DISTINCT destinations FROM forwarded_cargos 
        WHERE (phone = ? OR phone LIKE '%' || ? OR (sender_id != '' AND sender_id = ?)) 
          AND created_at >= ?
    """, (str(phone), phone_filter, sid, time_limit)) as cursor:
        rows = await cursor.fetchall()
        forwarded_dests = set(r[0].strip().lower() for r in rows if r[0])

    # Agar ushbu yo'nalish avval uzatilganlar orasida bo'lmasa, bu yangi yo'nalish hisoblanadi
    if dest_norm and dest_norm not in forwarded_dests:
        if len(forwarded_dests) >= 2:
            # Allaqachon 2 ta har xil yo'nalish yuborilgan, bu 3-yo'nalish!
            return False, f"Ushbu jo'natuvchi so'nggi {hours} soat ichida 3-har xil yo'nalishga e'lon bermoqda (dispetcher)"

    # Faollik bazasidan ham tekshirish (faqat 3 va undan ortiq xil viloyat bo'lsa dispetcher):
    async with db.execute("""
        SELECT COUNT(DISTINCT destination) FROM sender_activity
        WHERE (sender_id = ? OR phone = ? OR phone LIKE '%' || ?) AND created_at >= ?
    """, (sid, str(phone), phone_filter, time_limit)) as cursor:
        row = await cursor.fetchone()
        distinct_dests = row[0] if row else 0
        if distinct_dests >= 3:
            return False, f"Ushbu jo'natuvchidan so'nggi {hours} soat ichida {distinct_dests} xil viloyatga e'lon berilgan (dispetcher)"

    return True, "OK"

async def block_dispatcher_and_all_clones(
    sender_id: str,
    phone: str,
    reason: str = "Dispetcher deb topildi",
    username: Optional[str] = None,
    reported_by: str = ""
) -> List[str]:
    """
    Foydalanuvchi talabi: Agar dispetcher o'chirilsa, uning 'momosi' (barcha klon akkauntlari,
    ushbu telefon raqamiga bog'langan barcha boshqa Telegram akkauntlari, username va raqamlari)
    aniqlanib, barchasi qora ro'yxatga kiritiladi.
    """
    db = await _get_db()
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    blocked_items = []

    sid = str(sender_id or "").strip()
    phone_str = str(phone or "").strip()
    phone_digits = re.sub(r"\D", "", phone_str)
    last9 = phone_digits[-9:] if len(phone_digits) >= 9 else phone_str

    # 1. Asosiy telefon raqamining barcha formatlarini bloklash
    if phone_digits:
        canonical_p = f"998{last9}" if len(last9) == 9 else phone_digits
        variants = [
            canonical_p,
            last9,
            f"+998{last9}" if len(last9) == 9 else f"+{phone_digits}",
            phone_str
        ]
        for v in variants:
            if v:
                await db.execute("""
                    INSERT OR REPLACE INTO blocked_senders (sender_id, sender_name, reason, blocked_at)
                    VALUES (?, ?, ?, ?)
                """, (v, "Dispetcher raqami", reason, now_str))
                blocked_items.append(v)

    # 2. Asosiy sender_id ni bloklash
    if sid and sid not in ("None", "0", ""):
        await db.execute("""
            INSERT OR REPLACE INTO blocked_senders (sender_id, sender_name, reason, blocked_at)
            VALUES (?, ?, ?, ?)
        """, (sid, "Dispetcher akkaunti", reason, now_str))
        blocked_items.append(sid)

    # 3. Usernameni ham bloklash (agar mavjud bo'lsa)
    if username and str(username).strip():
        un = str(username).strip().lstrip("@")
        await db.execute("""
            INSERT OR REPLACE INTO blocked_senders (sender_id, sender_name, reason, blocked_at)
            VALUES (?, ?, ?, ?)
        """, (f"@{un}", "Dispetcher usernamesi", reason, now_str))
        await db.execute("""
            INSERT OR REPLACE INTO blocked_senders (sender_id, sender_name, reason, blocked_at)
            VALUES (?, ?, ?, ?)
        """, (un, "Dispetcher usernamesi", reason, now_str))
        blocked_items.append(f"@{un}")

    # 4. MOMOSINI TOPISH: Ushbu telefon raqami bilan avval e'lon bergan BARCHA boshqa akkauntlarni (klonlarni) topish va bloklash
    if last9:
        try:
            async with db.execute("""
                SELECT DISTINCT sender_id FROM sender_activity 
                WHERE (phone = ? OR phone LIKE '%' || ? OR sender_id = ? OR sender_id LIKE '%' || ?) 
                  AND sender_id != '' AND sender_id != 'None' AND sender_id != '0' AND sender_id != ?
                UNION
                SELECT DISTINCT sender_id FROM forwarded_cargos 
                WHERE (phone = ? OR phone LIKE '%' || ? OR sender_id = ? OR sender_id LIKE '%' || ?) 
                  AND sender_id != '' AND sender_id != 'None' AND sender_id != '0' AND sender_id != ?
                UNION
                SELECT DISTINCT CAST(user_id AS TEXT) FROM outreach_leads
                WHERE (phone = ? OR phone LIKE '%' || ?)
                  AND user_id != 0 AND user_id IS NOT NULL AND CAST(user_id AS TEXT) != ?
            """, (phone_str, last9, phone_str, last9, sid, phone_str, last9, phone_str, last9, sid, phone_str, last9, sid)) as cursor:
                rows = await cursor.fetchall()
                clone_senders = [r[0] for r in rows if r[0]]
                for c_sid in clone_senders:
                    clone_reason = f"Dispetcher kloni / momosi ({phone_str} raqamiga ulangan)"
                    await db.execute("""
                        INSERT OR REPLACE INTO blocked_senders (sender_id, sender_name, reason, blocked_at)
                        VALUES (?, ?, ?, ?)
                    """, (str(c_sid), "Dispetcher klon akkaunti", clone_reason, now_str))
                    blocked_items.append(f"klon_{c_sid}")

            # Klonlarning username'larini ham qidirib bloklash
            async with db.execute("""
                SELECT DISTINCT username FROM outreach_leads
                WHERE (phone = ? OR phone LIKE '%' || ?) AND username IS NOT NULL AND username != ''
            """, (phone_str, last9)) as u_cur:
                u_rows = await u_cur.fetchall()
                for ur in u_rows:
                    u_name = ur[0].strip().lstrip("@")
                    if u_name:
                        await db.execute("""
                            INSERT OR REPLACE INTO blocked_senders (sender_id, sender_name, reason, blocked_at)
                            VALUES (?, ?, ?, ?)
                        """, (f"@{u_name}", "Dispetcher usernamesi (klon)", f"Dispetcher kloni (@{u_name})", now_str))
                        await db.execute("""
                            INSERT OR REPLACE INTO blocked_senders (sender_id, sender_name, reason, blocked_at)
                            VALUES (?, ?, ?, ?)
                        """, (u_name, "Dispetcher usernamesi (klon)", f"Dispetcher kloni (@{u_name})", now_str))
                        blocked_items.append(f"@{u_name}")
        except Exception as e:
            logger.error(f"Klonlarni topishda xatolik: {e}")

    await db.commit()
    return blocked_items

async def check_phone_forward_eligibility(phone: str, current_dest: str = "", hours: int = 12) -> Tuple[bool, str]:
    """Eski chaqiruvchilar uchun moslik funksiyasi."""
    return await check_cargo_forward_eligibility(
        sender_id="",
        phone=phone,
        cargo_signature="",
        dest_text=current_dest,
        hours=hours
    )

async def get_recent_forwarded_phones(hours: int = 12) -> List[str]:
    """So'nggi N soat ichida yopiq guruhga yuborilgan barcha telefon raqamlar ro'yxati."""
    db = await _get_db()
    time_limit = (datetime.now() - timedelta(hours=hours)).strftime("%Y-%m-%d %H:%M:%S")
    async with db.execute("SELECT DISTINCT phone FROM forwarded_cargos WHERE created_at >= ?", (time_limit,)) as cursor:
        rows = await cursor.fetchall()
        return [r[0] for r in rows if r[0]]

async def get_recent_forwarded_senders(hours: int = 12) -> List[str]:
    """So'nggi N soat ichida yopiq guruhga yuborilgan barcha akkauntlar (sender_id) ro'yxati."""
    db = await _get_db()
    time_limit = (datetime.now() - timedelta(hours=hours)).strftime("%Y-%m-%d %H:%M:%S")
    async with db.execute("SELECT DISTINCT sender_id FROM forwarded_cargos WHERE created_at >= ? AND sender_id IS NOT NULL AND sender_id != ''", (time_limit,)) as cursor:
        rows = await cursor.fetchall()
        return [r[0] for r in rows if r[0]]

async def get_recent_forwarded_cargos_info(hours: int = 12) -> List[Dict[str, Any]]:
    """So'nggi N soat ichida yopiq guruhga yuborilgan barcha e'lonlar tafsilotlari (keshni to'ldirish uchun)."""
    db = await _get_db()
    time_limit = (datetime.now() - timedelta(hours=hours)).strftime("%Y-%m-%d %H:%M:%S")
    async with db.execute("""
        SELECT destinations, phone, sender_id, cargo_signature, created_at 
        FROM forwarded_cargos 
        WHERE created_at >= ?
    """, (time_limit,)) as cursor:
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]

# --- GURUHGA UZATILGAN YUKLAR NAZORATI VA STATISTIKASI ---

async def log_forwarded_cargo(destinations: str, phone: str, source_title: str, sender_id: str = "", cargo_signature: str = ""):
    """Guruhga uzatilgan toza yuk e'lonini doimiy bazaga kiritish."""
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    db = await _get_db()
    await db.execute("""
        INSERT INTO forwarded_cargos (destinations, phone, source_title, sender_id, cargo_signature, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (destinations, phone, source_title, str(sender_id), str(cargo_signature), now_str))
    await db.commit()

async def get_phone_forward_history(phone: str, hours: int = 24) -> List[Dict[str, Any]]:
    """Ushbu telefon raqamidan so'nggi vaqtda yuborilgan e'lonlar ro'yxati."""
    db = await _get_db()
    time_limit = (datetime.now() - timedelta(hours=hours)).strftime("%Y-%m-%d %H:%M:%S")
    async with db.execute("""
        SELECT destinations, source_title, created_at
        FROM forwarded_cargos
        WHERE phone = ? AND created_at >= ?
        ORDER BY created_at DESC
    """, (str(phone), time_limit)) as cursor:
        rows = await cursor.fetchall()
        return [
            {"destinations": r[0], "source_title": r[1], "created_at": r[2]}
            for r in rows
        ]

async def delete_forwarded_cargo_by_phone(phone: str) -> int:
    """Dispetcher deb topilganda ushbu telefon raqamiga oid yuklarni qaydlaridan tozalash."""
    db = await _get_db()
    sid = str(phone or "").strip()
    if not sid:
        return 0
    digits = re.sub(r"\D", "", sid)
    last9 = digits[-9:] if len(digits) >= 9 else sid
    cursor = await db.execute("""
        DELETE FROM forwarded_cargos 
        WHERE phone = ? OR phone = ? OR phone = ? OR phone LIKE '%' || ?
    """, (sid, f"+998{last9}", last9, last9))
    await db.commit()
    return cursor.rowcount

async def get_forwarded_cargos_stats() -> Dict[str, int]:
    """Bugungi va umumiy uzatilgan yuklar sonini qaytarish."""
    db = await _get_db()
    today_start = datetime.now().strftime("%Y-%m-%d 00:00:00")
    async with db.execute("""
        SELECT 
            COUNT(*) as total,
            SUM(CASE WHEN created_at >= ? THEN 1 ELSE 0 END) as today
        FROM forwarded_cargos
    """, (today_start,)) as cur:
        row = await cur.fetchone()
        return {
            "total_forwarded": (row[0] or 0) if row else 0,
            "today_forwarded": (row[1] or 0) if row else 0
        }

async def get_today_forwarded_cargos_list(limit: int = 15) -> List[Dict[str, Any]]:
    """Bugun guruhga uzatilgan so'nggi yuklar ro'yxatini olish."""
    db = await _get_db()
    today_start = datetime.now().strftime("%Y-%m-%d 00:00:00")
    async with db.execute("""
        SELECT destinations, phone, source_title, created_at
        FROM forwarded_cargos
        WHERE created_at >= ?
        ORDER BY id DESC
        LIMIT ?
    """, (today_start, limit)) as cur:
        rows = await cur.fetchall()
        return [
            {
                "destinations": r[0],
                "phone": r[1],
                "source_title": r[2],
                "created_at": r[3]
            }
            for r in rows
        ]

# --- ADMIN STATISTIKA FUNKSIYASI ---

async def get_admin_stats() -> Dict[str, Any]:
    """Admin uchun barcha statistik ko'rsatkichlarni hisoblash (optimallashtirilgan)."""
    now = datetime.now()
    now_str = now.strftime("%Y-%m-%d %H:%M:%S")
    today_start = now.strftime("%Y-%m-%d 00:00:00")

    db = await _get_db()

    # Bitta so'rovda ko'p natija olish (tezroq)
    async with db.execute("""
        SELECT 
            COUNT(*) as total,
            SUM(CASE WHEN joined_at >= ? THEN 1 ELSE 0 END) as today,
            SUM(CASE WHEN has_used_trial = 1 THEN 1 ELSE 0 END) as trial
        FROM users
    """, (today_start,)) as cur:
        row = await cur.fetchone()
        total_users = row[0]
        today_users = row[1]
        trial_users = row[2]

    # Faol obunalar
    async with db.execute("SELECT COUNT(*) FROM subscriptions WHERE is_active = 1 AND end_date > ?", (now_str,)) as cur:
        active_subscriptions = (await cur.fetchone())[0]

    # To'lovlar statistikasi bitta so'rovda
    async with db.execute("""
        SELECT 
            COUNT(*) as total_paid,
            COALESCE(SUM(amount), 0) as total_rev,
            COUNT(DISTINCT user_id) as unique_payers,
            SUM(CASE WHEN created_at >= ? THEN 1 ELSE 0 END) as today_paid,
            COALESCE(SUM(CASE WHEN created_at >= ? THEN amount ELSE 0 END), 0) as today_rev,
            SUM(CASE WHEN plan_type = 'week' THEN 1 ELSE 0 END) as week_cnt,
            SUM(CASE WHEN plan_type = 'month' THEN 1 ELSE 0 END) as month_cnt
        FROM payments WHERE status = 'approved'
    """, (today_start, today_start)) as cur:
        pay_row = await cur.fetchone()
        total_paid_orders = pay_row[0]
        total_revenue = pay_row[1]
        unique_paying_users = pay_row[2]
        today_paid_orders = pay_row[3]
        today_revenue = pay_row[4]
        week_orders = pay_row[5]
        month_orders = pay_row[6]

    # Bloklangan dispetcherlar
    async with db.execute("SELECT COUNT(*) FROM blocked_senders") as cur:
        blocked_senders = (await cur.fetchone())[0]

    # Guruhga uzatilgan toza yuklar (bugun va jami)
    async with db.execute("""
        SELECT 
            COUNT(*) as total_fwd,
            SUM(CASE WHEN created_at >= ? THEN 1 ELSE 0 END) as today_fwd
        FROM forwarded_cargos
    """, (today_start,)) as cur:
        fwd_row = await cur.fetchone()
        total_forwarded = (fwd_row[0] or 0) if fwd_row else 0
        today_forwarded = (fwd_row[1] or 0) if fwd_row else 0

    return {
        "total_users": total_users,
        "today_users": today_users,
        "trial_users": trial_users,
        "active_subscriptions": active_subscriptions,
        "total_paid_orders": total_paid_orders,
        "unique_paying_users": unique_paying_users,
        "total_revenue": total_revenue,
        "today_paid_orders": today_paid_orders,
        "today_revenue": today_revenue,
        "week_orders": week_orders,
        "month_orders": month_orders,
        "blocked_senders": blocked_senders,
        "total_forwarded": total_forwarded,
        "today_forwarded": today_forwarded,
    }

# ==========================================
# OUTREACH (DISPETCHERLARNI JALB QILISH) BAZASI
# ==========================================

async def add_outreach_lead(
    user_id: int,
    username: Optional[str],
    first_name: str,
    last_name: str,
    phone: Optional[str],
    reason: str,
    message_snippet: str,
    source_group: str
) -> bool:
    """Potensial dispetcherni taklif bazasiga qo'shish (agar avval qo'shilmagan bo'lsa yoki telefon qo'shish)."""
    db = await _get_db()
    try:
        await db.execute("""
            INSERT INTO outreach_leads 
            (user_id, username, first_name, last_name, phone, reason, message_snippet, source_group, status, whatsapp_status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'pending', 'pending')
            ON CONFLICT(user_id) DO UPDATE SET
                phone = COALESCE(excluded.phone, outreach_leads.phone),
                username = COALESCE(excluded.username, outreach_leads.username),
                first_name = COALESCE(excluded.first_name, outreach_leads.first_name)
        """, (user_id, username, first_name, last_name, phone, reason, message_snippet[:200], source_group))
        await db.commit()
        return True
    except Exception:
        return False

async def get_pending_outreach_leads(limit: int = 15) -> List[Dict[str, Any]]:
    """Hali taklif xati yuborilmagan dispetcherlarni olish (avval username borlar)."""
    db = await _get_db()
    async with db.execute("""
        SELECT * FROM outreach_leads 
        WHERE status = 'pending' 
        ORDER BY 
            (CASE WHEN username IS NOT NULL AND username != '' THEN 0 ELSE 1 END),
            created_at ASC 
        LIMIT ?
    """, (limit,)) as cur:
        rows = await cur.fetchall()
        return [dict(r) for r in rows]

async def mark_outreach_lead_sent(user_id: int):
    """Dispetcherga xabar muvaffaqiyatli yetkazilganini belgilash."""
    db = await _get_db()
    await db.execute("""
        UPDATE outreach_leads 
        SET status = 'sent', sent_at = CURRENT_TIMESTAMP 
        WHERE user_id = ?
    """, (user_id,))
    await db.commit()

async def mark_outreach_lead_failed(user_id: int, error_message: str):
    """Xabar yetkazib bo'lmaganini (masalan spam-blok yoki maxfiylik) qayd qilish."""
    db = await _get_db()
    await db.execute("""
        UPDATE outreach_leads 
        SET status = 'failed', error_message = ? 
        WHERE user_id = ?
    """, (error_message[:250], user_id))
    await db.commit()

async def get_outreach_stats() -> Dict[str, int]:
    """Outreach tizimi bo'yicha statistikani olish."""
    db = await _get_db()
    async with db.execute("""
        SELECT 
            COUNT(*) as total_leads,
            SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END) as pending_leads,
            SUM(CASE WHEN status = 'sent' THEN 1 ELSE 0 END) as sent_leads,
            SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed_leads
        FROM outreach_leads
    """) as cur:
        row = await cur.fetchone()
        return {
            "total_leads": row[0] or 0,
            "pending_leads": row[1] or 0,
            "sent_leads": row[2] or 0,
            "failed_leads": row[3] or 0,
        }

# ==========================================
# WHATSAPP OUTREACH QISMI (GREEN-API / ULTRAMSG)
# ==========================================

async def get_pending_whatsapp_leads(limit: int = 15) -> List[Dict[str, Any]]:
    """WhatsApp orqali xabar yuborilishi kutilayotgan dispetcherlarni olish (faqat telefon raqami borlar)."""
    db = await _get_db()
    async with db.execute("""
        SELECT * FROM outreach_leads 
        WHERE phone IS NOT NULL AND phone != '' 
          AND (whatsapp_status = 'pending' OR whatsapp_status IS NULL)
        ORDER BY created_at ASC 
        LIMIT ?
    """, (limit,)) as cur:
        rows = await cur.fetchall()
        return [dict(r) for r in rows]

async def mark_whatsapp_lead_sent(user_id: int):
    """Dispetcherga WhatsApp orqali xabar muvaffaqiyatli yuborilganini belgilash."""
    db = await _get_db()
    await db.execute("""
        UPDATE outreach_leads 
        SET whatsapp_status = 'sent', whatsapp_sent_at = CURRENT_TIMESTAMP 
        WHERE user_id = ?
    """, (user_id,))
    await db.commit()

async def mark_whatsapp_lead_failed(user_id: int, error_message: str, status: str = 'failed'):
    """WhatsApp xabar yetkazib bo'lmaganini (raqamda whatsapp yo'q yoki xatolik) qayd qilish."""
    db = await _get_db()
    await db.execute("""
        UPDATE outreach_leads 
        SET whatsapp_status = ?, error_message = ? 
        WHERE user_id = ?
    """, (status, error_message[:250], user_id))
    await db.commit()

async def get_whatsapp_outreach_stats() -> Dict[str, int]:
    """WhatsApp outreach statistikasi."""
    db = await _get_db()
    async with db.execute("""
        SELECT 
            COUNT(CASE WHEN phone IS NOT NULL AND phone != '' THEN 1 END) as total_with_phone,
            SUM(CASE WHEN phone IS NOT NULL AND phone != '' AND (whatsapp_status = 'pending' OR whatsapp_status IS NULL) THEN 1 ELSE 0 END) as pending_wa,
            SUM(CASE WHEN whatsapp_status = 'sent' THEN 1 ELSE 0 END) as sent_wa,
            SUM(CASE WHEN whatsapp_status = 'no_whatsapp' THEN 1 ELSE 0 END) as no_wa,
            SUM(CASE WHEN whatsapp_status = 'failed' THEN 1 ELSE 0 END) as failed_wa
        FROM outreach_leads
    """) as cur:
        row = await cur.fetchone()
        return {
            "total_with_phone": row[0] or 0,
            "pending_wa": row[1] or 0,
            "sent_wa": row[2] or 0,
            "no_wa": row[3] or 0,
            "failed_wa": row[4] or 0,
        }

# ==========================================
# GURUH HAVOLALARINI SO'RASH QISMI (OUTREACH TO USERS)
# ==========================================

async def get_users_pending_group_request(min_days: int = 2) -> List[Dict[str, Any]]:
    """Yangi qo'shilganidan so'ng min_days (2 kun) o'tgan va hali guruh so'rovi bormagan a'zolarni olish."""
    db = await _get_db()
    time_limit = (datetime.now() - timedelta(days=min_days)).strftime("%Y-%m-%d %H:%M:%S")
    async with db.execute("""
        SELECT user_id, username, full_name, joined_at
        FROM users
        WHERE (group_request_sent = 0 OR group_request_sent IS NULL)
          AND joined_at <= ?
        ORDER BY joined_at ASC
    """, (time_limit,)) as cursor:
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]

async def mark_user_group_request_sent(user_id: int):
    """Foydalanuvchiga guruh havolasi so'rovi yuborilganini belgilash."""
    db = await _get_db()
    await db.execute("""
        UPDATE users
        SET group_request_sent = 1
        WHERE user_id = ?
    """, (user_id,))
    await db.commit()

async def get_all_registered_users() -> List[Dict[str, Any]]:
    """Barcha ro'yxatdan o'tgan bot a'zolarini olish."""
    db = await _get_db()
    async with db.execute("""
        SELECT user_id, username, full_name, joined_at, group_request_sent
        FROM users
        ORDER BY joined_at ASC
    """) as cursor:
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]



