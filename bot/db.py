"""SQLite: subscriptions, payments, CRUD"""
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta
from pathlib import Path

import config


def _get_db_path() -> Path:
    p = Path(config.DB_PATH)
    if not p.is_absolute():
        p = Path(__file__).resolve().parent.parent / p
    return p


@contextmanager
def _conn():
    conn = sqlite3.connect(_get_db_path())
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def _migrate_add_tier_label(conn):
    """Миграция: добавить tier_label в subscriptions"""
    cur = conn.execute("PRAGMA table_info(subscriptions)")
    cols = [r[1] for r in cur.fetchall()]
    if "tier_label" not in cols:
        conn.execute("ALTER TABLE subscriptions ADD COLUMN tier_label TEXT")


def init_db():
    """Создание таблиц при первом запуске"""
    with _conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS subscriptions (
                user_id INTEGER PRIMARY KEY,
                subscription_end TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS payments (
                payment_id TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL,
                amount TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS pending_payments (
                payment_id TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL,
                amount TEXT NOT NULL,
                days INTEGER NOT NULL,
                tier_label TEXT,
                created_at TEXT NOT NULL
            )
        """)
        _migrate_add_tier_label(conn)


def payment_exists(payment_id: str) -> bool:
    """Проверка идемпотентности: платёж уже обработан"""
    with _conn() as conn:
        cur = conn.execute(
            "SELECT 1 FROM payments WHERE payment_id = ?",
            (payment_id,),
        )
        return cur.fetchone() is not None


def add_payment(payment_id: str, user_id: int, amount: str) -> None:
    with _conn() as conn:
        conn.execute(
            "INSERT INTO payments (payment_id, user_id, amount, created_at) VALUES (?, ?, ?, ?)",
            (payment_id, user_id, amount, datetime.utcnow().isoformat()),
        )


def add_pending_payment(
    payment_id: str, user_id: int, amount: str, days: int, tier_label: str = ""
) -> None:
    with _conn() as conn:
        conn.execute(
            "INSERT INTO pending_payments (payment_id, user_id, amount, days, tier_label, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (payment_id, user_id, amount, days, tier_label or "", datetime.utcnow().isoformat()),
        )


def get_pending_payments(limit: int = 100) -> list[dict]:
    with _conn() as conn:
        cur = conn.execute(
            "SELECT payment_id, user_id, amount, days, tier_label, created_at FROM pending_payments ORDER BY created_at ASC LIMIT ?",
            (limit,),
        )
        return [dict(r) for r in cur.fetchall()]


def remove_pending_payment(payment_id: str) -> None:
    with _conn() as conn:
        conn.execute("DELETE FROM pending_payments WHERE payment_id = ?", (payment_id,))


def upsert_subscription(
    user_id: int, subscription_end: datetime, tier_label: str | None = None
) -> None:
    """Добавить или обновить подписку (продление — берём max end)"""
    with _conn() as conn:
        cur = conn.execute(
            "SELECT subscription_end, tier_label FROM subscriptions WHERE user_id = ?",
            (user_id,),
        )
        row = cur.fetchone()
        now = datetime.utcnow().isoformat()
        end_str = subscription_end.isoformat()
        if row:
            existing = row["subscription_end"]
            end_str = max(existing, end_str)
            tier = tier_label if tier_label else (row["tier_label"] if row["tier_label"] else None)
            conn.execute(
                "UPDATE subscriptions SET subscription_end = ?, tier_label = ? WHERE user_id = ?",
                (end_str, tier, user_id),
            )
        else:
            conn.execute(
                "INSERT INTO subscriptions (user_id, subscription_end, created_at, tier_label) VALUES (?, ?, ?, ?)",
                (user_id, end_str, now, tier_label),
            )


def get_subscription_info(user_id: int) -> dict | None:
    """Информация о подписке: end_date, tier_label, status"""
    with _conn() as conn:
        cur = conn.execute(
            "SELECT subscription_end, tier_label FROM subscriptions WHERE user_id = ?",
            (user_id,),
        )
        row = cur.fetchone()
        if not row:
            return None
        end_str = row["subscription_end"]
        now = datetime.utcnow().isoformat()
        status = "активен" if end_str >= now else "истёк"
        return {
            "end_date": end_str,
            "tier_label": row["tier_label"] or "—",
            "status": status,
        }


def get_users_expiring_in_days(days: int) -> list[dict]:
    """Подписки, истекающие ровно через N дней (для напоминаний: 3, 1, 0)"""
    with _conn() as conn:
        now = datetime.utcnow()
        target_date = (now + timedelta(days=days)).strftime("%Y-%m-%d")
        cur = conn.execute(
            "SELECT user_id, subscription_end FROM subscriptions WHERE subscription_end LIKE ?",
            (target_date + "%",),
        )
        return [{"user_id": r["user_id"], "subscription_end": r["subscription_end"]} for r in cur.fetchall()]


def get_expired_user_ids() -> list[int]:
    """Список user_id с истёкшей подпиской"""
    with _conn() as conn:
        cur = conn.execute(
            "SELECT user_id FROM subscriptions WHERE subscription_end < ?",
            (datetime.utcnow().isoformat(),),
        )
        return [r["user_id"] for r in cur.fetchall()]


def remove_subscription(user_id: int) -> None:
    with _conn() as conn:
        conn.execute("DELETE FROM subscriptions WHERE user_id = ?", (user_id,))


def clear_all_subscriptions() -> int:
    """Удалить все подписки (для теста). Returns count deleted."""
    with _conn() as conn:
        cur = conn.execute("SELECT COUNT(*) FROM subscriptions")
        n = cur.fetchone()[0]
        conn.execute("DELETE FROM subscriptions")
        return n


def is_subscribed(user_id: int) -> bool:
    with _conn() as conn:
        cur = conn.execute(
            "SELECT 1 FROM subscriptions WHERE user_id = ? AND subscription_end >= ?",
            (user_id, datetime.utcnow().isoformat()),
        )
        return cur.fetchone() is not None


def get_all_payments(limit: int = 100) -> list[dict]:
    """Список оплат для админки"""
    with _conn() as conn:
        cur = conn.execute(
            "SELECT payment_id, user_id, amount, created_at FROM payments ORDER BY created_at DESC LIMIT ?",
            (limit,),
        )
        return [dict(r) for r in cur.fetchall()]


def get_all_subscriptions() -> list[dict]:
    """Все подписки с датой окончания и статусом"""
    with _conn() as conn:
        cur = conn.execute(
            "SELECT user_id, subscription_end, tier_label, created_at FROM subscriptions"
        )
        now = datetime.utcnow().isoformat()
        return [
            {
                **dict(r),
                "status": "активен" if r["subscription_end"] >= now else "истёк",
            }
            for r in cur.fetchall()
        ]


def get_stats() -> dict:
    """Статистика: оплаты, сумма, активные подписки"""
    with _conn() as conn:
        cur = conn.execute("SELECT COUNT(*), COALESCE(SUM(CAST(amount AS REAL)), 0) FROM payments")
        row = cur.fetchone()
        payments_count = row[0] or 0
        total_amount = row[1] or 0
        cur = conn.execute(
            "SELECT COUNT(*) FROM subscriptions WHERE subscription_end >= ?",
            (datetime.utcnow().isoformat(),),
        )
        active_count = cur.fetchone()[0] or 0
        return {
            "payments_count": payments_count,
            "total_amount": round(total_amount, 2),
            "active_subscriptions": active_count,
        }
