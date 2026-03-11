"""Flask endpoint для webhook ЮKassa: payment.succeeded → groups.invite + DB + ЛС"""
import hashlib
import hmac
import logging
from datetime import datetime, timedelta

import config
from pathlib import Path

from flask import Flask, request, send_from_directory
from vk_api import VkApi

from bot.admin import admin_bp
from bot.db import add_payment, payment_exists, upsert_subscription
from bot.vk_utils import invite_to_group, remove_from_group, send_vk_message

logger = logging.getLogger(__name__)
app = Flask(__name__)
app.register_blueprint(admin_bp)

ADMIN_APP_DIR = Path(__file__).resolve().parent.parent / "admin-app"


def _verify_webhook_signature() -> bool:
    """Проверка подписи webhook (HMAC-SHA256). Если WEBHOOK_SECRET пуст — пропуск."""
    secret = config.WEBHOOK_SECRET
    if not secret:
        return True
    sig_header = request.headers.get("X-Webhook-Signature") or request.headers.get("X-Signature")
    if not sig_header:
        logger.warning("WEBHOOK_SECRET set but no signature header")
        return False
    body = request.get_data()
    expected = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, sig_header.strip())


def _invite_to_group(user_id: int) -> bool:
    return invite_to_group(user_id)


def _remove_from_group(user_id: int) -> bool:
    return remove_from_group(user_id)


def _send_vk_message(user_id: int, text: str) -> bool:
    return send_vk_message(user_id, text)


@app.route("/webhook", methods=["POST"])
def webhook():
    """Webhook отключён — оплата проверяется через polling (payment_poller). Возвращаем 200 для совместимости."""
    return "", 200


@app.route("/test-payment", methods=["POST"])
def test_payment():
    """Локальный тест: симулирует payment.succeeded. Работает только при TEST_MODE=1"""
    if not config.TEST_MODE:
        return "", 404
    data = request.get_json(silent=True) or {}
    user_id = data.get("user_id")
    if not user_id:
        return {"error": "user_id required"}, 400
    try:
        user_id = int(user_id)
    except (ValueError, TypeError):
        return {"error": "user_id must be int"}, 400
    try:
        tier_idx = int(data.get("tier", 0))
    except (ValueError, TypeError):
        tier_idx = 0
    tier = config.SUBSCRIPTION_TIERS[tier_idx] if 0 <= tier_idx < len(config.SUBSCRIPTION_TIERS) else config.SUBSCRIPTION_TIERS[0]
    days = int(data.get("days", tier["days"]))
    payment_id = f"test_{user_id}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
    if payment_exists(payment_id):
        return "", 200
    _invite_to_group(user_id)
    add_payment(payment_id, user_id, "0")
    end_date = datetime.utcnow() + timedelta(days=days)
    upsert_subscription(user_id, end_date, tier.get("label"))
    msg = config.INVITE_SUCCESS_MESSAGE.format(end_date=end_date.strftime("%d.%m.%Y"))
    _send_vk_message(user_id, msg)
    return {"ok": True, "user_id": user_id}, 200


@app.route("/admin-app/")
def admin_app_index():
    return send_from_directory(ADMIN_APP_DIR, "index.html")


@app.route("/admin-app/<path:path>")
def admin_app(path):
    return send_from_directory(ADMIN_APP_DIR, path)


@app.route("/return", methods=["GET"])
def return_url():
    """Страница после успешной оплаты (redirect от ЮKassa)"""
    return "<p>Оплата прошла. Проверьте сообщения бота — приглашение в группу должно прийти.</p>", 200
