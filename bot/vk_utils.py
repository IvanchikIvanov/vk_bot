"""VK API: invite, remove, send message — общие утилиты"""
import logging

import config
from vk_api import VkApi

logger = logging.getLogger(__name__)


def _get_vk() -> VkApi:
    return VkApi(token=config.VK_TOKEN)


def _get_vk_user() -> VkApi:
    """Токен пользователя — для messages.addChatUser, messages.removeChatUser (group token не поддерживает)"""
    token = config.VK_USER_TOKEN
    if not token:
        logger.error("VK_USER_TOKEN is empty! messages.addChatUser/removeChatUser require a user token.")
        raise RuntimeError("VK_USER_TOKEN not configured — cannot call messages.addChatUser")
    return VkApi(token=token)


def invite_user_to_chat(user_id: int) -> bool:
    """Добавить пользователя в беседу (messages.addChatUser, требует user token)."""
    chat_id = config.VK_GROUP_CHAT_ID
    if not chat_id:
        logger.error("VK_GROUP_CHAT_ID is empty! Cannot add user to chat.")
        return False
    try:
        vk = _get_vk_user()
        vk.method("messages.addChatUser", {"chat_id": chat_id, "user_id": user_id})
        logger.info("messages.addChatUser ok: user_id=%s chat_id=%s", user_id, chat_id)
        return True
    except Exception as e:
        logger.exception("messages.addChatUser failed: user_id=%s chat_id=%s error=%s", user_id, chat_id, e)
        return False


def remove_from_chat(user_id: int) -> bool:
    """Удалить пользователя из беседы (messages.removeChatUser, требует user token)."""
    chat_id = config.VK_GROUP_CHAT_ID
    if not chat_id:
        logger.error("VK_GROUP_CHAT_ID is empty! Cannot remove user from chat.")
        return False
    try:
        vk = _get_vk_user()
        vk.method("messages.removeChatUser", {"chat_id": chat_id, "user_id": user_id})
        logger.info("messages.removeChatUser ok: user_id=%s chat_id=%s", user_id, chat_id)
        return True
    except Exception as e:
        logger.exception("messages.removeChatUser failed: user_id=%s chat_id=%s error=%s", user_id, chat_id, e)
        return False


def send_vk_message(user_id: int, text: str) -> bool:
    """Отправить ЛС пользователю."""
    try:
        vk = _get_vk()
        vk.method("messages.send", {"peer_id": user_id, "message": text, "random_id": 0})
        logger.info("messages.send ok: user_id=%s len=%d", user_id, len(text))
        return True
    except Exception as e:
        logger.warning("Failed to send VK message to user_id=%s: %s", user_id, e)
        return False
