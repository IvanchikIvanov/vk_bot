"""ЮKassa: создание платежа с metadata.user_id"""
import logging
import uuid
from typing import Optional

import config
from yookassa import Configuration, Payment

logger = logging.getLogger(__name__)


def _ensure_configured() -> None:
    if not Configuration.account_id:
        Configuration.configure(config.YOOKASSA_SHOP_ID, config.YOOKASSA_SECRET_KEY)


def create_payment(user_id: int, price: str, days: int, tier_label: str = "") -> Optional[str]:
    """
    Создаёт платёж в ЮKassa.
    Returns: confirmation_url или None при ошибке
    """
    _ensure_configured()
    idempotence_key = f"vk_{user_id}_{uuid.uuid4().hex[:16]}"
    return_url = f"{config.WEBHOOK_BASE_URL.rstrip('/')}/return"
    metadata = {"user_id": str(user_id), "days": str(days)}
    if tier_label:
        metadata["tier_label"] = tier_label[:64]  # YooKassa limit
    try:
        payment = Payment.create(
            {
                "amount": {"value": price, "currency": "RUB"},
                "capture": True,
                "confirmation": {"type": "redirect", "return_url": return_url},
                "description": f"Подписка на группу VK ({days} дн., user_id={user_id})",
                "metadata": metadata,
            },
            idempotence_key,
        )
        conf = getattr(payment, "confirmation", None)
        if isinstance(conf, dict):
            return conf.get("confirmation_url")
        if conf and hasattr(conf, "confirmation_url"):
            return conf.confirmation_url
        return None
    except Exception as e:
        logger.exception("create_payment failed: user_id=%s price=%s error=%s", user_id, price, e)
        return None
