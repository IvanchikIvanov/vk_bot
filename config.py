"""Загрузка конфигурации из .env"""
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / ".env")

VK_TOKEN = os.getenv("VK_TOKEN", "")
VK_GROUP_ID = int(os.getenv("VK_GROUP_ID", "0"))
YOOKASSA_SHOP_ID = os.getenv("YOOKASSA_SHOP_ID", "")
YOOKASSA_SECRET_KEY = os.getenv("YOOKASSA_SECRET_KEY", "")
SUBSCRIPTION_PRICE = os.getenv("SUBSCRIPTION_PRICE", "299.00")
SUBSCRIPTION_DAYS = int(os.getenv("SUBSCRIPTION_DAYS", "30"))

# Главное меню (6 кнопок по ТЗ)
MAIN_MENU_BUTTONS = [
    {"label": "📚 Курсы и интенсивы", "id": "courses"},
    {"label": "💰 Тарифы", "id": "tariffs"},
    {"label": "❓ Вопрос-ответ", "id": "faq"},
    {"label": "👤 Мой доступ", "id": "my_access"},
    {"label": "🛒 Оплатить", "id": "pay"},
    {"label": "📩 Связаться с поддержкой", "id": "support"},
]

# Карточка продукта для раздела «Курсы и интенсивы»
PRODUCT_INFO = {
    "name": "ГИБКАЯ СИЛА",
    "description": "Авторская система оздоровления тела и души: йога, пилатес, цигун, аэробика, данхак, соматика. Занятия в закрытом сообществе под руководством опытного тренера.",
    "duration": "Постоянный доступ на выбранный срок (1 мес — 1 год)",
    "result": "Укрепление опорно-двигательного аппарата, эластичность мышц, снятие стресса и блоков, улучшение показателей тела.",
}

# Приветствие при первом запуске
WELCOME_MESSAGE = """Добро пожаловать в закрытый клуб «ГИБКАЯ СИЛА» — пространство осознанного движения.

Выберите раздел в меню:"""

# Тарифы: цена, дни, метка, название, что входит, бонусы
SUBSCRIPTION_TIERS = [
    {
        "name": "Базовый",
        "price": "990.00",
        "days": 30,
        "label": "1 мес — 990 ₽",
        "includes": ["Доступ в закрытое сообщество", "Все занятия на месяц", "Обратная связь в комментариях"],
        "bonus": None,
    },
    {
        "name": "Стандарт",
        "price": "2250.00",
        "days": 90,
        "label": "3 мес — 2250 ₽",
        "includes": ["Всё из Базового", "3 месяца занятий", "Экономия 720 ₽"],
        "bonus": "Бонус: чек-лист «Утренняя практика»",
    },
    {
        "name": "Премиум",
        "price": "5000.00",
        "days": 180,
        "label": "6 мес — 5000 ₽",
        "includes": ["Всё из Стандарта", "6 месяцев занятий", "Экономия 940 ₽"],
        "bonus": "Бонус: мини-курс по дыхательным практикам",
    },
    {
        "name": "VIP",
        "price": "9500.00",
        "days": 365,
        "label": "12 мес — 9500 ₽",
        "includes": ["Всё из Премиум", "Год занятий", "Экономия 2380 ₽"],
        "bonus": "Бонус: персональная консультация 30 мин",
    },
]

FAQ_TEXT = """❓ Частые вопросы

• Как оплатить? — Выберите тариф, нажмите кнопку, перейдите по ссылке и оплатите картой.

• Когда получу доступ? — Сразу после успешной оплаты. Приглашение придёт в уведомлениях ВК (🔔). Примите его — доступ будет активирован.

• Можно ли продлить? — Да, нажмите «Мой доступ» → «Продлить» и выберите новый тариф.

• Вопросы по занятиям? — Пишите в комментариях паблика @guruyogaru или в поддержку."""

SUPPORT_LINK = "https://vk.com/guruyogaru"
GROUP_LINK = os.getenv("GROUP_LINK", "") or (f"https://vk.com/club{VK_GROUP_ID}" if VK_GROUP_ID > 0 else "")

# Сообщение после оплаты (без ссылки — приглашение личное в уведомлениях ВК)
INVITE_SUCCESS_MESSAGE = """✅ Оплата получена!

Вам отправлено приглашение в закрытое сообщество. Примите его в уведомлениях ВКонтакте (иконка колокольчика 🔔).

Доступ до {end_date}.

Если не нашли приглашение — нажмите «Мой доступ» → «Отправить приглашение повторно»."""
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "")
WEBHOOK_BASE_URL = os.getenv("WEBHOOK_BASE_URL", "https://example.com")
ADMIN_SECRET = os.getenv("ADMIN_SECRET", "")
# VK Mini App: ID админов (через запятую), секрет приложения из настроек VK
ADMIN_VK_IDS = [int(x.strip()) for x in os.getenv("ADMIN_VK_IDS", "").split(",") if x.strip().isdigit()]
VK_APP_SECRET = os.getenv("VK_APP_SECRET", "")
EXPIRED_MESSAGE = "Ваш доступ истёк. Продлите подписку, чтобы продолжить занятия."
REMINDER_3_DAYS = "Напоминание: ваш доступ заканчивается через 3 дня. Продлите подписку, чтобы не прерывать занятия."
REMINDER_1_DAY = "Напоминание: ваш доступ заканчивается завтра. Продлите подписку в разделе «Оплатить»."
REMINDER_0_DAYS = "Ваш доступ заканчивается сегодня. Продлите подписку, чтобы сохранить доступ к занятиям."
TEST_MODE = os.getenv("TEST_MODE", "").lower() in ("1", "true", "yes")
WEBHOOK_PORT = int(os.getenv("WEBHOOK_PORT", "5000"))
DB_PATH = os.getenv("DB_PATH", "subscriptions.db")
# Интервал проверки pending платежей (секунды)
PAYMENT_POLL_INTERVAL = int(os.getenv("PAYMENT_POLL_INTERVAL", "5"))
