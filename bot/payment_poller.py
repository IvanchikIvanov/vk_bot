"""Проверка статуса платежей ЮKassa через GET /payments/{id} (polling вместо webhook)"""
import logging
from datetime import datetime, timedelta

import config
import requests
from requests.auth import HTTPBasicAuth

from bot.db import (
    add_payment,
    get_pending_payments,
    payment_exists,
    remove_pending_payment,
    upsert_subscription,
)
from bot.vk_utils import invite_user_to_chat, send_vk_message

logger = logging.getLogger(__name__)

POLL_TIMEOUT_HOURS = 24  # не проверять платежи старше 24ч


def get_payment_status(payment_id: str) -> dict | None:
    """GET /payments/{id} — возвращает объект платежа или None при ошибке"""
    url = f"https://api.yookassa.ru/v3/payments/{payment_id}"
    try:
        resp = requests.get(
            url,
            auth=HTTPBasicAuth(config.YOOKASSA_SHOP_ID, config.YOOKASSA_SECRET_KEY),
            headers={"Content-Type": "application/json"},
            timeout=15,
        )
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException as e:
        logger.warning("get_payment_status failed: payment_id=%s error=%s", payment_id, e)
        return None


def _process_succeeded(pending: dict) -> None:
    """Обработка успешной оплаты: invite, add_payment, upsert_subscription, ЛС"""
    payment_id = pending["payment_id"]
    user_id = pending["user_id"]
    amount = pending["amount"]
    days = pending["days"]
    tier_label = pending.get("tier_label") or ""

    if payment_exists(payment_id):
        logger.info("Poll: payment_id=%s already processed, skipping", payment_id)
        remove_pending_payment(payment_id)
        return

    logger.info("Poll: processing succeeded user_id=%s payment_id=%s amount=%s days=%s", user_id, payment_id, amount, days)
    ok = invite_user_to_chat(user_id)
    if not ok:
        logger.warning("Poll: addChatUser failed for user_id=%s payment_id=%s", user_id, payment_id)
    add_payment(payment_id, user_id, amount)
    end_date = datetime.utcnow() + timedelta(days=days)
    upsert_subscription(user_id, end_date, tier_label or None)

    end_str = end_date.strftime("%d.%m.%Y")
    msg = config.INVITE_SUCCESS_MESSAGE.format(end_date=end_str)
    send_vk_message(user_id, msg)
    logger.info("Poll: success message sent user_id=%s end_date=%s", user_id, end_str)

    remove_pending_payment(payment_id)
    logger.info("Poll: payment completed user_id=%s payment_id=%s", user_id, payment_id)


def poll_pending_payments() -> None:
    """Проверяет все pending платежи и обрабатывает succeeded"""
    if not config.YOOKASSA_SHOP_ID or not config.YOOKASSA_SECRET_KEY:
        return

    pending_list = get_pending_payments()
    cutoff = datetime.utcnow() - timedelta(hours=POLL_TIMEOUT_HOURS)

    for p in pending_list:
        payment_id = p["payment_id"]
        created_str = p.get("created_at", "")
        try:
            created = datetime.fromisoformat(created_str.replace("Z", "").split("+")[0])
        except (ValueError, TypeError):
            created = datetime.utcnow()

        if created < cutoff:
            remove_pending_payment(payment_id)
            logger.info("Poll: removed stale pending payment_id=%s", payment_id)
            continue

        data = get_payment_status(payment_id)
        if not data:
            continue

        status = data.get("status")

        if status == "succeeded":
            _process_succeeded(p)
        elif status == "canceled":
            remove_pending_payment(payment_id)
            logger.info("Poll: payment canceled payment_id=%s", payment_id)
        # pending, waiting_for_capture — оставляем в pending


def start_polling() -> None:
    """Запуск фонового polling (вызывается из scheduler)"""
    pass  # poll_pending_payments вызывается scheduler'ом
