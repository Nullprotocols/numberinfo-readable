# database.py (SQLite Version - Complete)
import aiosqlite
import time
import re
from datetime import datetime, timedelta

DB_PATH = "bot_database.db"

async def get_db():
    """Return a connection to SQLite database with dict-like rows."""
    conn = await aiosqlite.connect(DB_PATH)
    conn.row_factory = aiosqlite.Row
    return conn

def parse_time_string(time_str):
    """
    Parse time string like '30m', '2h', '1h30m' into minutes.
    Returns None if invalid or 'none'.
    """
    if not time_str or str(time_str).lower() == 'none':
        return None
    time_str = str(time_str).lower()
    total_minutes = 0
    hour_match = re.search(r'(\d+)h', time_str)
    if hour_match:
        total_minutes += int(hour_match.group(1)) * 60
    minute_match = re.search(r'(\d+)m', time_str)
    if minute_match:
        total_minutes += int(minute_match.group(1))
    if not hour_match and not minute_match and time_str.isdigit():
        total_minutes = int(time_str)
    return total_minutes if total_minutes > 0 else None

async def init_db():
    """Initialize all database tables."""
    async with await get_db() as db:
        # Users table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                credits INTEGER DEFAULT 5,
                joined_date TEXT,
                referrer_id INTEGER,
                is_banned INTEGER DEFAULT 0,
                total_earned INTEGER DEFAULT 0,
                last_active TEXT,
                is_premium INTEGER DEFAULT 0,
                premium_expiry TEXT
            )
        """)
        # Admins table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS admins (
                user_id INTEGER PRIMARY KEY,
                level TEXT DEFAULT 'admin',
                added_by INTEGER,
                added_date TEXT
            )
        """)
        # Redeem codes table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS redeem_codes (
                code TEXT PRIMARY KEY,
                amount INTEGER,
                max_uses INTEGER,
                current_uses INTEGER DEFAULT 0,
                expiry_minutes INTEGER,
                created_date TEXT,
                is_active INTEGER DEFAULT 1
            )
        """)
        # Redeem logs
        await db.execute("""
            CREATE TABLE IF NOT EXISTS redeem_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                code TEXT,
                claimed_date TEXT,
                UNIQUE(user_id, code)
            )
        """)
        # Lookup logs
        await db.execute("""
            CREATE TABLE IF NOT EXISTS lookup_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                api_type TEXT,
                input_data TEXT,
                result TEXT,
                lookup_date TEXT
            )
        """)
        # Premium plans
        await db.execute("""
            CREATE TABLE IF NOT EXISTS premium_plans (
                plan_id TEXT PRIMARY KEY,
                price INTEGER,
                duration_days INTEGER,
                description TEXT
            )
        """)
        # Insert default plans
        await db.execute("""
            INSERT OR IGNORE INTO premium_plans (plan_id, price, duration_days, description)
            VALUES ('weekly', 69, 7, 'Weekly Plan')
        """)
        await db.execute("""
            INSERT OR IGNORE INTO premium_plans (plan_id, price, duration_days, description)
            VALUES ('monthly', 199, 30, 'Monthly Plan')
        """)
        # Discount codes
        await db.execute("""
            CREATE TABLE IF NOT EXISTS discount_codes (
                code TEXT PRIMARY KEY,
                plan_id TEXT,
                discount_percent INTEGER,
                max_uses INTEGER,
                current_uses INTEGER DEFAULT 0,
                expiry_minutes INTEGER,
                created_date TEXT,
                is_active INTEGER DEFAULT 1
            )
        """)
        await db.commit()

# ---------- User functions ----------
async def get_user(user_id):
    async with await get_db() as db:
        async with db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None

async def add_user(user_id, username, referrer_id=None):
    async with await get_db() as db:
        # Check existing
        async with db.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,)) as cursor:
            exists = await cursor.fetchone()
            if exists:
                return
        credits = 5
        current_time = str(time.time())
        await db.execute("""
            INSERT INTO users (user_id, username, credits, joined_date, referrer_id, is_banned, total_earned, last_active, is_premium, premium_expiry)
            VALUES (?, ?, ?, ?, ?, 0, 0, ?, 0, NULL)
        """, (user_id, username, credits, current_time, referrer_id, current_time))
        await db.commit()

async def update_credits(user_id, amount):
    async with await get_db() as db:
        if amount > 0:
            await db.execute("UPDATE users SET credits = credits + ?, total_earned = total_earned + ? WHERE user_id = ?",
                             (amount, amount, user_id))
        else:
            await db.execute("UPDATE users SET credits = credits + ? WHERE user_id = ?",
                             (amount, user_id))
        await db.commit()

async def set_ban_status(user_id, status):
    async with await get_db() as db:
        await db.execute("UPDATE users SET is_banned = ? WHERE user_id = ?", (status, user_id))
        await db.commit()

async def get_all_users():
    async with await get_db() as db:
        async with db.execute("SELECT user_id FROM users") as cursor:
            rows = await cursor.fetchall()
            return [row['user_id'] for row in rows]

async def get_user_by_username(username):
    async with await get_db() as db:
        async with db.execute("SELECT user_id FROM users WHERE username = ?", (username,)) as cursor:
            row = await cursor.fetchone()
            return row['user_id'] if row else None

async def update_last_active(user_id):
    async with await get_db() as db:
        await db.execute("UPDATE users SET last_active = ? WHERE user_id = ?",
                         (datetime.now().isoformat(), user_id))
        await db.commit()

# ---------- Premium functions ----------
async def set_user_premium(user_id, days=None):
    async with await get_db() as db:
        if days:
            expiry = (datetime.now() + timedelta(days=days)).isoformat()
            await db.execute("UPDATE users SET is_premium = 1, premium_expiry = ? WHERE user_id = ?",
                             (expiry, user_id))
        else:
            await db.execute("UPDATE users SET is_premium = 1, premium_expiry = NULL WHERE user_id = ?",
                             (user_id,))
        await db.commit()

async def remove_user_premium(user_id):
    async with await get_db() as db:
        await db.execute("UPDATE users SET is_premium = 0, premium_expiry = NULL WHERE user_id = ?",
                         (user_id,))
        await db.commit()

async def is_user_premium(user_id):
    async with await get_db() as db:
        async with db.execute("SELECT is_premium, premium_expiry FROM users WHERE user_id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            if not row:
                return False
            is_premium = row['is_premium']
            expiry = row['premium_expiry']
            if not is_premium:
                return False
            if expiry:
                expiry_dt = datetime.fromisoformat(expiry)
                if expiry_dt < datetime.now():
                    await remove_user_premium(user_id)
                    return False
            return True

async def get_premium_users():
    """Return list of (user_id, username, premium_expiry) for all premium users."""
    async with await get_db() as db:
        async with db.execute("SELECT user_id, username, premium_expiry FROM users WHERE is_premium = 1") as cursor:
            return await cursor.fetchall()

async def get_users_with_min_credits(min_credits=100):
    async with await get_db() as db:
        async with db.execute("SELECT user_id, username, credits FROM users WHERE credits >= ? ORDER BY credits DESC",
                              (min_credits,)) as cursor:
            return await cursor.fetchall()

# ---------- Premium plans ----------
async def get_plan_price(plan_id):
    async with await get_db() as db:
        async with db.execute("SELECT price FROM premium_plans WHERE plan_id = ?", (plan_id,)) as cursor:
            row = await cursor.fetchone()
            return row['price'] if row else None

async def update_plan_price(plan_id, price):
    async with await get_db() as db:
        await db.execute("UPDATE premium_plans SET price = ? WHERE plan_id = ?", (price, plan_id))
        await db.commit()

# ---------- Discount codes ----------
async def create_discount_code(code, plan_id, discount_percent, max_uses, expiry_minutes=None):
    async with await get_db() as db:
        await db.execute("""
            INSERT OR REPLACE INTO discount_codes
            (code, plan_id, discount_percent, max_uses, expiry_minutes, created_date, is_active)
            VALUES (?, ?, ?, ?, ?, ?, 1)
        """, (code, plan_id, discount_percent, max_uses, expiry_minutes, datetime.now().isoformat()))
        await db.commit()

async def get_discount_by_code(code):
    async with await get_db() as db:
        async with db.execute("SELECT discount_percent, plan_id, max_uses, current_uses, expiry_minutes, created_date, is_active FROM discount_codes WHERE code = ?", (code,)) as cursor:
            return await cursor.fetchone()

async def redeem_discount_code(user_id, code, plan_id):
    async with await get_db() as db:
        async with db.execute("SELECT discount_percent, max_uses, current_uses, expiry_minutes, created_date, is_active FROM discount_codes WHERE code = ?", (code,)) as cursor:
            data = await cursor.fetchone()
            if not data:
                return "invalid"
            discount_percent = data['discount_percent']
            max_uses = data['max_uses']
            current_uses = data['current_uses']
            expiry_minutes = data['expiry_minutes']
            created_date = data['created_date']
            is_active = data['is_active']
            if not is_active:
                return "inactive"
            if current_uses >= max_uses:
                return "limit_reached"
            if expiry_minutes:
                created_dt = datetime.fromisoformat(created_date)
                if datetime.now() > created_dt + timedelta(minutes=expiry_minutes):
                    return "expired"
            await db.execute("UPDATE discount_codes SET current_uses = current_uses + 1 WHERE code = ?", (code,))
            await db.commit()
            return discount_percent

# ---------- Redeem codes (regular) ----------
async def create_redeem_code(code, amount, max_uses, expiry_minutes=None):
    async with await get_db() as db:
        await db.execute("""
            INSERT OR REPLACE INTO redeem_codes
            (code, amount, max_uses, expiry_minutes, created_date, is_active)
            VALUES (?, ?, ?, ?, ?, 1)
        """, (code, amount, max_uses, expiry_minutes, datetime.now().isoformat()))
        await db.commit()

async def redeem_code_db(user_id, code):
    async with await get_db() as db:
        # Check already claimed
        async with db.execute("SELECT 1 FROM redeem_logs WHERE user_id = ? AND code = ?", (user_id, code)) as cursor:
            already = await cursor.fetchone()
            if already:
                return "already_claimed"

        async with db.execute("SELECT amount, max_uses, current_uses, expiry_minutes, created_date, is_active FROM redeem_codes WHERE code = ?", (code,)) as cursor:
            data = await cursor.fetchone()
            if not data:
                return "invalid"
            amount = data['amount']
            max_uses = data['max_uses']
            current_uses = data['current_uses']
            expiry_minutes = data['expiry_minutes']
            created_date = data['created_date']
            is_active = data['is_active']
            if not is_active:
                return "inactive"
            if current_uses >= max_uses:
                return "limit_reached"
            if expiry_minutes:
                created_dt = datetime.fromisoformat(created_date)
                if datetime.now() > created_dt + timedelta(minutes=expiry_minutes):
                    return "expired"

        # Update uses
        await db.execute("UPDATE redeem_codes SET current_uses = current_uses + 1 WHERE code = ?", (code,))
        # Add credits to user
        await db.execute("UPDATE users SET credits = credits + ?, total_earned = total_earned + ? WHERE user_id = ?",
                         (amount, amount, user_id))
        # Log claim
        await db.execute("INSERT INTO redeem_logs (user_id, code, claimed_date) VALUES (?, ?, ?)",
                         (user_id, code, datetime.now().isoformat()))
        await db.commit()
        return amount

async def get_all_codes():
    async with await get_db() as db:
        async with db.execute("SELECT code, amount, max_uses, current_uses, expiry_minutes, created_date, is_active FROM redeem_codes ORDER BY created_date DESC") as cursor:
            return await cursor.fetchall()

async def deactivate_code(code):
    async with await get_db() as db:
        await db.execute("UPDATE redeem_codes SET is_active = 0 WHERE code = ?", (code,))
        await db.commit()

async def get_active_codes():
    async with await get_db() as db:
        async with db.execute("SELECT code, amount, max_uses, current_uses FROM redeem_codes WHERE is_active = 1") as cursor:
            return await cursor.fetchall()

async def get_inactive_codes():
    async with await get_db() as db:
        async with db.execute("SELECT code, amount, max_uses, current_uses FROM redeem_codes WHERE is_active = 0") as cursor:
            return await cursor.fetchall()

async def get_expired_codes():
    async with await get_db() as db:
        now = datetime.now().isoformat()
        async with db.execute("""
            SELECT code, amount, current_uses, max_uses, expiry_minutes, created_date
            FROM redeem_codes
            WHERE is_active = 1 AND expiry_minutes IS NOT NULL AND expiry_minutes > 0
              AND datetime(created_date, '+' || expiry_minutes || ' minutes') < datetime(?)
        """, (now,)) as cursor:
            return await cursor.fetchall()

async def delete_redeem_code(code):
    async with await get_db() as db:
        await db.execute("DELETE FROM redeem_codes WHERE code = ?", (code,))
        await db.commit()

async def get_code_usage_stats(code):
    async with await get_db() as db:
        async with db.execute("""
            SELECT 
                rc.amount, rc.max_uses, rc.current_uses,
                COUNT(DISTINCT rl.user_id) as unique_users,
                GROUP_CONCAT(DISTINCT rl.user_id) as user_ids
            FROM redeem_codes rc
            LEFT JOIN redeem_logs rl ON rc.code = rl.code
            WHERE rc.code = ?
            GROUP BY rc.code
        """, (code,)) as cursor:
            return await cursor.fetchone()

# ---------- Lookup logs ----------
async def log_lookup(user_id, api_type, input_data, result):
    async with await get_db() as db:
        await db.execute("""
            INSERT INTO lookup_logs (user_id, api_type, input_data, result, lookup_date)
            VALUES (?, ?, ?, ?, ?)
        """, (user_id, api_type, input_data[:500], str(result)[:1000], datetime.now().isoformat()))
        await db.commit()

async def get_user_lookups(user_id, limit=20):
    async with await get_db() as db:
        async with db.execute("""
            SELECT api_type, input_data, lookup_date
            FROM lookup_logs
            WHERE user_id = ?
            ORDER BY lookup_date DESC
            LIMIT ?
        """, (user_id, limit)) as cursor:
            return await cursor.fetchall()

async def get_total_lookups():
    async with await get_db() as db:
        async with db.execute("SELECT COUNT(*) FROM lookup_logs") as cursor:
            row = await cursor.fetchone()
            return row[0] if row else 0

async def get_lookup_stats(user_id=None):
    async with await get_db() as db:
        if user_id:
            async with db.execute("SELECT api_type, COUNT(*) FROM lookup_logs WHERE user_id = ? GROUP BY api_type", (user_id,)) as cursor:
                return await cursor.fetchall()
        else:
            async with db.execute("SELECT api_type, COUNT(*) FROM lookup_logs GROUP BY api_type") as cursor:
                return await cursor.fetchall()

# ---------- Statistics ----------
async def get_bot_stats():
    async with await get_db() as db:
        async with db.execute("SELECT COUNT(*) FROM users") as cursor:
            total_users = (await cursor.fetchone())[0]
        async with db.execute("SELECT COUNT(*) FROM users WHERE credits > 0") as cursor:
            active_users = (await cursor.fetchone())[0]
        async with db.execute("SELECT SUM(credits) FROM users") as cursor:
            total_credits = (await cursor.fetchone())[0] or 0
        async with db.execute("SELECT SUM(total_earned) FROM users") as cursor:
            credits_distributed = (await cursor.fetchone())[0] or 0
        return {
            'total_users': total_users,
            'active_users': active_users,
            'total_credits': total_credits,
            'credits_distributed': credits_distributed
        }

async def get_user_stats(user_id):
    async with await get_db() as db:
        async with db.execute("SELECT COUNT(*) FROM users WHERE referrer_id = ?", (user_id,)) as cursor:
            referrals = (await cursor.fetchone())[0]
        async with db.execute("SELECT COUNT(*) FROM redeem_logs WHERE user_id = ?", (user_id,)) as cursor:
            codes_claimed = (await cursor.fetchone())[0]
        async with db.execute("""
            SELECT SUM(rc.amount) FROM redeem_logs rl
            JOIN redeem_codes rc ON rl.code = rc.code
            WHERE rl.user_id = ?
        """, (user_id,)) as cursor:
            total_from_codes = (await cursor.fetchone())[0] or 0
        return {
            'referrals': referrals,
            'codes_claimed': codes_claimed,
            'total_from_codes': total_from_codes
        }

async def get_recent_users(limit=20):
    async with await get_db() as db:
        async with db.execute("SELECT user_id, username, joined_date FROM users ORDER BY joined_date DESC LIMIT ?", (limit,)) as cursor:
            return await cursor.fetchall()

async def get_top_referrers(limit=10):
    async with await get_db() as db:
        async with db.execute("""
            SELECT referrer_id, COUNT(*) as referrals
            FROM users
            WHERE referrer_id IS NOT NULL
            GROUP BY referrer_id
            ORDER BY referrals DESC
            LIMIT ?
        """, (limit,)) as cursor:
            return await cursor.fetchall()

async def get_users_in_range(start_date, end_date):
    async with await get_db() as db:
        async with db.execute("""
            SELECT user_id, username, credits, joined_date FROM users
            WHERE CAST(joined_date AS REAL) BETWEEN ? AND ?
        """, (start_date, end_date)) as cursor:
            return await cursor.fetchall()

async def get_leaderboard(limit=10):
    async with await get_db() as db:
        async with db.execute("SELECT user_id, username, credits FROM users WHERE is_banned = 0 ORDER BY credits DESC LIMIT ?", (limit,)) as cursor:
            return await cursor.fetchall()

async def get_low_credit_users():
    async with await get_db() as db:
        async with db.execute("SELECT user_id, username, credits FROM users WHERE credits <= 5 ORDER BY credits ASC") as cursor:
            return await cursor.fetchall()

async def get_inactive_users(days=30):
    cutoff = (datetime.now() - timedelta(days=days)).isoformat()
    async with await get_db() as db:
        async with db.execute("""
            SELECT user_id, username, last_active FROM users
            WHERE last_active < ? AND is_banned = 0
            ORDER BY last_active ASC
        """, (cutoff,)) as cursor:
            return await cursor.fetchall()

async def get_daily_stats(days=7):
    async with await get_db() as db:
        async with db.execute("""
            SELECT 
                strftime('%Y-%m-%d', datetime(joined_date, 'unixepoch')) as join_date,
                COUNT(*) as new_users,
                (SELECT COUNT(*) FROM lookup_logs 
                 WHERE strftime('%Y-%m-%d', lookup_date) = strftime('%Y-%m-%d', datetime(users.joined_date, 'unixepoch'))) as lookups
            FROM users 
            WHERE datetime(joined_date, 'unixepoch') >= datetime('now', ? || ' days')
            GROUP BY join_date
            ORDER BY join_date DESC
        """, (-days,)) as cursor:
            return await cursor.fetchall()

# ---------- Admin management ----------
async def add_admin(user_id, level='admin'):
    async with await get_db() as db:
        await db.execute("INSERT OR REPLACE INTO admins (user_id, level) VALUES (?, ?)", (user_id, level))
        await db.commit()

async def remove_admin(user_id):
    async with await get_db() as db:
        await db.execute("DELETE FROM admins WHERE user_id = ?", (user_id,))
        await db.commit()

async def get_all_admins():
    async with await get_db() as db:
        async with db.execute("SELECT user_id, level FROM admins") as cursor:
            return await cursor.fetchall()

async def is_admin(user_id):
    async with await get_db() as db:
        async with db.execute("SELECT level FROM admins WHERE user_id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            return row['level'] if row else None

# ---------- Utility ----------
async def search_users(query):
    async with await get_db() as db:
        try:
            q_int = int(query)
        except:
            q_int = 0
        async with db.execute("""
            SELECT user_id, username, credits FROM users
            WHERE username LIKE ? OR user_id = ?
            LIMIT 20
        """, (f"%{query}%", q_int)) as cursor:
            return await cursor.fetchall()

async def delete_user(user_id):
    async with await get_db() as db:
        await db.execute("DELETE FROM users WHERE user_id = ?", (user_id,))
        await db.execute("DELETE FROM redeem_logs WHERE user_id = ?", (user_id,))
        await db.execute("UPDATE users SET referrer_id = NULL WHERE referrer_id = ?", (user_id,))
        await db.commit()

async def reset_user_credits(user_id):
    async with await get_db() as db:
        await db.execute("UPDATE users SET credits = 0 WHERE user_id = ?", (user_id,))
        await db.commit()

async def bulk_update_credits(user_ids, amount):
    async with await get_db() as db:
        for uid in user_ids:
            if amount > 0:
                await db.execute("UPDATE users SET credits = credits + ?, total_earned = total_earned + ? WHERE user_id = ?",
                                 (amount, amount, uid))
            else:
                await db.execute("UPDATE users SET credits = credits + ? WHERE user_id = ?",
                                 (amount, uid))
        await db.commit()
