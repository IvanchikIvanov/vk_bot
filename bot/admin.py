"""Админ-панель: web + JSON API для VK Mini App"""
import base64
import hashlib
import hmac
import logging
from datetime import datetime, timedelta

import config
from flask import Blueprint, jsonify, request

from bot.db import (
    get_all_payments,
    get_all_subscriptions,
    get_stats,
    remove_subscription,
    upsert_subscription,
)
from bot.vk_utils import invite_user_to_chat, remove_from_chat, send_vk_message

logger = logging.getLogger(__name__)
admin_bp = Blueprint("admin", __name__, url_prefix="/admin")

MANUAL_DAYS = 30  # дней при ручной выдаче


def _verify_vk_sign(params: dict, sign: str) -> bool:
    """Проверка подписи VK Mini App (HMAC-SHA256, base64)."""
    if not config.VK_APP_SECRET:
        return True  # без секрета — пропуск проверки подписи
    if not sign:
        return True
    vk_params = sorted((k, str(v)) for k, v in params.items() if k.startswith("vk_"))
    sign_str = "&".join(f"{k}={v}" for k, v in vk_params)
    expected = base64.urlsafe_b64encode(
        hmac.new(config.VK_APP_SECRET.encode(), sign_str.encode(), hashlib.sha256).digest()
    ).decode().rstrip("=").replace("+", "-").replace("/", "_")
    return hmac.compare_digest(expected, sign)


def _require_admin():
    """ADMIN_SECRET (query/header) или VK: X-VK-User-Id в ADMIN_VK_IDS + X-VK-Sign."""
    secret = request.args.get("secret") or request.headers.get("X-Admin-Secret")
    if config.ADMIN_SECRET and secret == config.ADMIN_SECRET:
        return True
    vk_user_id = request.args.get("vk_user_id") or request.headers.get("X-VK-User-Id")
    if vk_user_id and config.ADMIN_VK_IDS:
        try:
            uid = int(vk_user_id)
            if uid in config.ADMIN_VK_IDS:
                vk_sign = request.args.get("sign") or request.headers.get("X-VK-Sign")
                vk_params = {k: v for k, v in request.args.items() if k.startswith("vk_")}
                if vk_params and vk_sign and not _verify_vk_sign(vk_params, vk_sign):
                    return False
                return True
        except (ValueError, TypeError):
            pass
    return False


def _html_page(title: str, body: str) -> tuple[str, int]:
    return (
        f"""<!DOCTYPE html><html><head><meta charset="utf-8"><title>{title}</title>
<style>body{{font-family:sans-serif;margin:20px}} table{{border-collapse:collapse}}
th,td{{border:1px solid #ccc;padding:8px}} th{{background:#eee}}</style></head>
<body><h1>{title}</h1>{body}</body></html>""",
        200,
    )


@admin_bp.before_request
def _check_admin():
    if request.method == "OPTIONS":
        return "", 204, {"Access-Control-Allow-Origin": "*", "Access-Control-Allow-Methods": "GET, POST, OPTIONS", "Access-Control-Allow-Headers": "Content-Type, X-VK-User-Id, X-VK-Sign, X-Admin-Secret"}
    if not _require_admin():
        return "", 403, {"Access-Control-Allow-Origin": "*"}
    return None


@admin_bp.route("")
def index():
    if not _require_admin():
        return "", 403
    stats = get_stats()
    links = """
    <p><a href="/admin/payments">Оплаты</a> |
    <a href="/admin/users">Пользователи</a> |
    <a href="/admin/stats">Статистика</a></p>
    <p>Добавьте ?secret=ВАШ_СЕКРЕТ к URL. Ручные действия: POST /admin/manual-invite, POST /admin/manual-block (JSON: user_id, header X-Admin-Secret)</p>
    """
    body = f"""
    <p>Оплат: {stats['payments_count']} | Сумма: {stats['total_amount']} ₽ | Активных подписок: {stats['active_subscriptions']}</p>
    {links}
    """
    return _html_page("Админ-панель", body)


@admin_bp.route("/payments")
def payments():
    rows = get_all_payments()
    if not rows:
        return _html_page("Оплаты", "<p>Нет оплат</p>")
    trs = "".join(
        f"<tr><td>{r['payment_id']}</td><td>{r['user_id']}</td><td>{r['amount']}</td><td>{r['created_at']}</td></tr>"
        for r in rows
    )
    return _html_page("Оплаты", f"<table><tr><th>ID</th><th>user_id</th><th>Сумма</th><th>Дата</th></tr>{trs}</table>")


@admin_bp.route("/users")
def users():
    rows = get_all_subscriptions()
    if not rows:
        return _html_page("Пользователи", "<p>Нет подписок</p>")
    trs = "".join(
        f"<tr><td>{r['user_id']}</td><td>{r['subscription_end'][:10]}</td><td>{r.get('tier_label','—')}</td><td>{r['status']}</td></tr>"
        for r in rows
    )
    return _html_page("Пользователи", f"<table><tr><th>user_id</th><th>Окончание</th><th>Тариф</th><th>Статус</th></tr>{trs}</table>")


@admin_bp.route("/stats")
def stats():
    s = get_stats()
    body = f"""
    <p>Всего оплат: {s['payments_count']}</p>
    <p>Сумма: {s['total_amount']} ₽</p>
    <p>Активных подписок: {s['active_subscriptions']}</p>
    """
    return _html_page("Статистика", body)


@admin_bp.route("/manual-invite", methods=["POST"])
def manual_invite():
    data = request.get_json(silent=True) or {}
    user_id = data.get("user_id")
    if not user_id:
        return {"error": "user_id required"}, 400
    try:
        user_id = int(user_id)
    except (ValueError, TypeError):
        return {"error": "user_id must be int"}, 400
    days = int(data.get("days", MANUAL_DAYS))
    tier_label = data.get("tier_label", "Ручная выдача")
    ok = invite_user_to_chat(user_id)
    if not ok:
        return {"error": "messages.addChatUser failed"}, 500
    end_date = datetime.utcnow() + timedelta(days=days)
    upsert_subscription(user_id, end_date, tier_label)
    send_vk_message(user_id, f"✅ Вам выдан доступ на {days} дн. до {end_date.strftime('%d.%m.%Y')}.")
    return {"ok": True, "user_id": user_id, "days": days}, 200


@admin_bp.route("/manual-block", methods=["POST"])
def manual_block():
    data = request.get_json(silent=True) or {}
    user_id = data.get("user_id")
    if not user_id:
        return {"error": "user_id required"}, 400
    try:
        user_id = int(user_id)
    except (ValueError, TypeError):
        return {"error": "user_id must be int"}, 400
    remove_from_chat(user_id)
    remove_subscription(user_id)
    send_vk_message(user_id, config.EXPIRED_MESSAGE)
    return {"ok": True, "user_id": user_id}, 200


# --- JSON API для VK Mini App ---

def _api_response(data, status=200):
    resp = jsonify(data)
    resp.headers["Access-Control-Allow-Origin"] = "*"
    resp.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    resp.headers["Access-Control-Allow-Headers"] = "Content-Type, X-VK-User-Id, X-VK-Sign, X-Admin-Secret"
    return resp, status


@admin_bp.route("/api/stats")
def api_stats():
    return _api_response(get_stats())


@admin_bp.route("/api/payments")
def api_payments():
    rows = get_all_payments()
    return _api_response([dict(r) for r in rows])


@admin_bp.route("/api/users")
def api_users():
    rows = get_all_subscriptions()
    return _api_response([dict(r) for r in rows])


@admin_bp.route("/api/manual-invite", methods=["POST", "OPTIONS"])
def api_manual_invite():
    if request.method == "OPTIONS":
        return "", 204, {"Access-Control-Allow-Origin": "*", "Access-Control-Allow-Methods": "POST, OPTIONS", "Access-Control-Allow-Headers": "Content-Type, X-VK-User-Id, X-VK-Sign"}
    data = request.get_json(silent=True) or {}
    user_id = data.get("user_id")
    if not user_id:
        return _api_response({"error": "user_id required"}, 400)
    try:
        user_id = int(user_id)
    except (ValueError, TypeError):
        return _api_response({"error": "user_id must be int"}, 400)
    days = int(data.get("days", MANUAL_DAYS))
    tier_label = data.get("tier_label", "Ручная выдача")
    ok = invite_user_to_chat(user_id)
    if not ok:
        return _api_response({"error": "messages.addChatUser failed"}, 500)
    end_date = datetime.utcnow() + timedelta(days=days)
    upsert_subscription(user_id, end_date, tier_label)
    send_vk_message(user_id, f"✅ Вам выдан доступ на {days} дн. до {end_date.strftime('%d.%m.%Y')}.")
    return _api_response({"ok": True, "user_id": user_id, "days": days})


@admin_bp.route("/api/manual-block", methods=["POST", "OPTIONS"])
def api_manual_block():
    if request.method == "OPTIONS":
        return "", 204, {"Access-Control-Allow-Origin": "*", "Access-Control-Allow-Methods": "POST, OPTIONS", "Access-Control-Allow-Headers": "Content-Type, X-VK-User-Id, X-VK-Sign"}
    data = request.get_json(silent=True) or {}
    user_id = data.get("user_id")
    if not user_id:
        return _api_response({"error": "user_id required"}, 400)
    try:
        user_id = int(user_id)
    except (ValueError, TypeError):
        return _api_response({"error": "user_id must be int"}, 400)
    remove_from_chat(user_id)
    remove_subscription(user_id)
    send_vk_message(user_id, config.EXPIRED_MESSAGE)
    return _api_response({"ok": True, "user_id": user_id})
