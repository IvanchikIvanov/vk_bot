"""VK API: invite, remove, send message — общие утилиты"""
import logging

import config
from vk_api import VkApi

logger = logging.getLogger(__name__)


def _get_vk() -> VkApi:
    return VkApi(token=config.VK_TOKEN)


def _get_vk_user() -> VkApi:
    """Токен пользователя — для groups.invite, groups.removeUser (group token не поддерживает)"""
    return VkApi(token=config.VK_USER_TOKEN or config.VK_TOKEN)


def invite_to_group(user_id: int) -> bool:
    """Пригласить пользователя в группу (требует user token)."""
    try:
        vk = _get_vk_user()
        vk.method("groups.invite", {"group_id": config.VK_GROUP_ID, "user_id": user_id})
        logger.info("groups.invite ok: user_id=%s group_id=%s", user_id, config.VK_GROUP_ID)
        return True
    except Exception as e:
        logger.exception("groups.invite failed: user_id=%s group_id=%s error=%s", user_id, config.VK_GROUP_ID, e)
        return False


def remove_from_group(user_id: int) -> bool:
    """Удалить пользователя из группы (требует user token)."""
    try:
        vk = _get_vk_user()
        vk.method("groups.removeUser", {"group_id": config.VK_GROUP_ID, "user_id": user_id})
        logger.info("groups.removeUser ok: user_id=%s group_id=%s", user_id, config.VK_GROUP_ID)
        return True
    except Exception as e:
        logger.exception("groups.removeUser failed: user_id=%s group_id=%s error=%s", user_id, config.VK_GROUP_ID, e)
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
