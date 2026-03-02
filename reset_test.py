"""Сброс подписок для теста"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from bot.db import clear_all_subscriptions, init_db

if __name__ == "__main__":
    init_db()
    n = clear_all_subscriptions()
    print(f"Удалено подписок: {n}")
