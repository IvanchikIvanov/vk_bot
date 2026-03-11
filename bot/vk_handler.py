"""Long Poll: обработка message_new, главное меню, навигация"""
import json
import logging
import time
from datetime import datetime, timedelta

import config
from vk_api import VkApi
from vk_api.bot_longpoll import VkBotEventType, VkBotLongPoll

from bot.db import add_payment, add_pending_payment, get_subscription_info, is_subscribed, upsert_subscription
from bot.payment import create_payment
from bot.vk_utils import invite_to_group

logger = logging.getLogger(__name__)

BACK_LABEL = "⬅️ Главное меню"
SELECT_TIER_LABEL = "Выбрать тариф"
RENEW_LABEL = "Продлить"
RESEND_INVITE_LABEL = "📨 Отправить приглашение повторно"


def _get_user_id(event) -> int | None:
    msg = event.object.get("message", event.object)
    return msg.get("from_id") if isinstance(msg, dict) else getattr(msg, "from_id", None)


def _get_peer_id(event) -> int:
    msg = event.object.get("message", event.object)
    pid = msg.get("peer_id") if isinstance(msg, dict) else getattr(msg, "peer_id", None)
    return pid or 0


def _send(vk: VkApi, peer_id: int, text: str, keyboard: dict | None = None) -> None:
    params = {"peer_id": peer_id, "message": text, "random_id": 0}
    if keyboard:
        params["keyboard"] = json.dumps(keyboard)
    vk.method("messages.send", params)


def _btn(label: str, color: str = "secondary") -> dict:
    return {"action": {"type": "text", "label": label}, "color": color}


def _get_main_keyboard() -> dict:
    """Главное меню: 6 кнопок в 2 ряда"""
    labels = [b["label"] for b in config.MAIN_MENU_BUTTONS]
    row1 = [_btn(labels[0]), _btn(labels[1]), _btn(labels[2])]
    row2 = [_btn(labels[3]), _btn(labels[4]), _btn(labels[5])]
    return {"one_time": False, "buttons": [row1, row2]}


def _get_tiers_keyboard() -> dict:
    """Клавиатура с тарифами + назад"""
    buttons = [[_btn(t["label"], "primary")] for t in config.SUBSCRIPTION_TIERS]
    buttons.append([_btn(BACK_LABEL)])
    return {"one_time": False, "buttons": buttons}


def _get_select_tier_keyboard() -> dict:
    """Одна кнопка «Выбрать тариф» + назад"""
    return {"one_time": False, "buttons": [[_btn(SELECT_TIER_LABEL, "primary")], [_btn(BACK_LABEL)]]}


def _get_my_access_keyboard(has_subscription: bool) -> dict:
    """Мой доступ: Повторное приглашение + Продлить или тарифы + назад"""
    if has_subscription:
        return {
            "one_time": False,
            "buttons": [
                [_btn(RESEND_INVITE_LABEL, "primary")],
                [_btn(RENEW_LABEL)],
                [_btn(BACK_LABEL)],
            ],
        }
    return _get_tiers_keyboard()


def _find_tier_by_text(text: str) -> dict | None:
    t = text.strip()
    for tier in config.SUBSCRIPTION_TIERS:
        if tier["label"] == t:
            return tier
    return None


def _find_menu_by_text(text: str) -> dict | None:
    t = text.strip()
    for b in config.MAIN_MENU_BUTTONS:
        if b["label"] == t:
            return b
    return None


def _format_product_card() -> str:
    p = config.PRODUCT_INFO
    min_price = min(config.SUBSCRIPTION_TIERS, key=lambda t: float(t["price"]))["price"]
    return f"""📚 {p['name']}

{p['description']}

⏱ Длительность: {p['duration']}

✅ Результат: {p['result']}

💰 Стоимость: от {min_price} ₽"""


def _format_tier_card(tier: dict) -> str:
    lines = [f"💰 {tier['name']} — {tier['label']}", ""]
    lines.append("Входит:")
    for inc in tier["includes"]:
        lines.append(f"• {inc}")
    if tier.get("bonus"):
        lines.append(f"\n🎁 {tier['bonus']}")
    return "\n".join(lines)


def _format_tiers_list() -> str:
    parts = []
    for i, t in enumerate(config.SUBSCRIPTION_TIERS, 1):
        parts.append(f"{i}️⃣ {t['name']} — {t['label']}")
    return "Выберите тариф для оплаты:\n\n" + "\n".join(parts)


def _format_my_access(user_id: int) -> str:
    info = get_subscription_info(user_id)
    if not info:
        return "Доступа нет. Выберите тариф для оформления подписки."
    end = info["end_date"][:10]
    try:
        dt = datetime.fromisoformat(info["end_date"])
        end = dt.strftime("%d.%m.%Y")
    except (ValueError, TypeError):
        pass
    return f"""👤 Мой доступ

Тариф: {info['tier_label']}
Окончание: {end}
Статус: {info['status']}"""


def _handle_message(vk: VkApi, user_id: int, peer_id: int, text: str) -> None:
    text = (text or "").strip()

    # Навигация: главное меню
    if text == BACK_LABEL:
        logger.info("Action: back_to_menu user_id=%s", user_id)
        _send(vk, peer_id, config.WELCOME_MESSAGE, keyboard=_get_main_keyboard())
        return

    # Главное меню: обработка кнопок
    menu = _find_menu_by_text(text)
    if menu:
        mid = menu.get("id", "")
        logger.info("Action: menu user_id=%s menu_id=%s", user_id, mid)
        if mid == "courses":
            _send(vk, peer_id, _format_product_card(), keyboard=_get_select_tier_keyboard())
        elif mid == "tariffs":
            parts = [_format_tiers_list()]
            for t in config.SUBSCRIPTION_TIERS:
                parts.append(_format_tier_card(t))
            _send(vk, peer_id, "\n\n".join(parts), keyboard=_get_tiers_keyboard())
        elif mid == "faq":
            _send(vk, peer_id, config.FAQ_TEXT, keyboard={"one_time": False, "buttons": [[_btn(BACK_LABEL)]]})
        elif mid == "my_access":
            info_text = _format_my_access(user_id)
            _send(vk, peer_id, info_text, keyboard=_get_my_access_keyboard(is_subscribed(user_id)))
        elif mid == "pay":
            _send(vk, peer_id, _format_tiers_list(), keyboard=_get_tiers_keyboard())
        elif mid == "support":
            _send(
                vk,
                peer_id,
                f"📩 Связаться с поддержкой:\n{config.SUPPORT_LINK}",
                keyboard={"one_time": False, "buttons": [[_btn(BACK_LABEL)]]},
            )
        return

    # Отправить приглашение повторно (только при активной подписке)
    if text == RESEND_INVITE_LABEL:
        logger.info("Action: resend_invite user_id=%s", user_id)
        if is_subscribed(user_id):
            if invite_to_group(user_id):
                _send(vk, peer_id, "Приглашение отправлено. Проверьте уведомления ВК (🔔).", keyboard=_get_my_access_keyboard(True))
            else:
                _send(vk, peer_id, "Не удалось отправить приглашение. Обратитесь в поддержку.", keyboard=_get_my_access_keyboard(True))
        else:
            _send(vk, peer_id, "Доступа нет. Выберите тариф для оформления подписки.", keyboard=_get_tiers_keyboard())
        return

    # Выбрать тариф / Продлить -> показать тарифы
    if text == SELECT_TIER_LABEL or text == RENEW_LABEL:
        logger.info("Action: show_tiers user_id=%s", user_id)
        _send(vk, peer_id, _format_tiers_list(), keyboard=_get_tiers_keyboard())
        return

    # Выбор тарифа -> оплата
    tier = _find_tier_by_text(text)
    if tier:
        logger.info("Action: tier_selected user_id=%s tier=%s price=%s days=%s", user_id, tier["label"], tier["price"], tier["days"])
        if is_subscribed(user_id):
            logger.info("Action: blocked_already_subscribed user_id=%s", user_id)
            _send(vk, peer_id, "У вас уже есть активная подписка.", keyboard=_get_main_keyboard())
            return

        if config.TEST_MODE:
            try:
                from bot.webhook import _invite_to_group
                _invite_to_group(user_id)
                pid = f"test_{user_id}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
                add_payment(pid, user_id, tier["price"])
                upsert_subscription(user_id, datetime.utcnow() + timedelta(days=tier["days"]), tier["label"])
                _send(vk, peer_id, f"Тест: подписка {tier['label']} активирована, приглашение в группу отправлено.", keyboard=_get_main_keyboard())
                logger.info("TEST_MODE: activated %s for user_id=%s", tier["label"], user_id)
            except Exception as e:
                logger.exception("TEST_MODE activation failed: %s", e)
                _send(vk, peer_id, f"Ошибка теста: {e}")
            return

        result = create_payment(user_id, tier["price"], tier["days"], tier["label"])
        if result:
            payment_id, url = result
            add_pending_payment(payment_id, user_id, tier["price"], tier["days"], tier.get("label", ""))
            logger.info("Payment: created payment_id=%s user_id=%s tier=%s", payment_id, user_id, tier["label"])
            _send(
                vk,
                peer_id,
                f"Оплатите подписку по ссылке:\n{url}\n\nТариф: {tier['label']}",
                keyboard={"one_time": False, "buttons": [[_btn(BACK_LABEL)]]},
            )
            logger.info("Payment: link sent user_id=%s payment_id=%s tier=%s", user_id, payment_id, tier["label"])
        else:
            _send(vk, peer_id, "Ошибка создания платежа. Попробуйте позже.", keyboard=_get_main_keyboard())
            logger.error("Payment creation failed for user_id=%s", user_id)
        return

    # Любое другое сообщение -> главное меню
    _send(vk, peer_id, config.WELCOME_MESSAGE, keyboard=_get_main_keyboard())


def run_longpoll():
    vk = VkApi(token=config.VK_TOKEN)
    longpoll = VkBotLongPoll(vk, config.VK_GROUP_ID)
    logger.info("Long Poll started, group_id=%s, listening for events", config.VK_GROUP_ID)

    last_heartbeat = time.time()
    while True:
        try:
            events = longpoll.check()
        except (ConnectionError, Exception) as e:
            logger.warning("Long Poll check failed: %s, reconnecting in 5s", e)
            time.sleep(5)
            longpoll = VkBotLongPoll(vk, config.VK_GROUP_ID)
            logger.info("Long Poll reconnected")
            continue

        if not events and time.time() - last_heartbeat > 30:
            logger.info("Heartbeat: still waiting for events (no messages received yet)")
            last_heartbeat = time.time()

        if not events:
            time.sleep(1)
            continue

        for event in events:
            last_heartbeat = time.time()
            ev_type = getattr(event, "type", None)
            logger.info("Event: type=%s", ev_type)

            if event.type != VkBotEventType.MESSAGE_NEW:
                logger.info("Skip: not message_new (type=%s)", event.type)
                continue

            user_id = _get_user_id(event)
            peer_id = _get_peer_id(event)
            msg_text = (event.object.get("message", event.object) or {}).get("text", "")[:100]
            logger.info("message_new: user_id=%s peer_id=%s text=%r", user_id, peer_id, msg_text)

            if not user_id or user_id < 0:
                logger.warning("Skip: invalid user_id=%s", user_id)
                continue

            text = (event.object.get("message", event.object) or {}).get("text", "")
            try:
                _handle_message(vk, user_id, peer_id, text)
            except Exception as e:
                logger.exception("Handle message failed: %s", e)
                try:
                    _send(vk, peer_id, "Произошла ошибка. Попробуйте позже.", keyboard=_get_main_keyboard())
                except Exception:
                    pass
