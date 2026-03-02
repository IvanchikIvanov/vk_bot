"""APScheduler: напоминания 3/1/0 дней, блокировка при истечении + ЛС"""
import logging

import config
from apscheduler.schedulers.background import BackgroundScheduler

from bot.db import get_expired_user_ids, get_users_expiring_in_days, remove_subscription
from bot.vk_utils import remove_from_group, send_vk_message

logger = logging.getLogger(__name__)

REMINDER_MESSAGES = {3: config.REMINDER_3_DAYS, 1: config.REMINDER_1_DAY, 0: config.REMINDER_0_DAYS}


def send_reminders(days: int):
    """Напоминания за N дней до окончания (3, 1, 0)"""
    msg = REMINDER_MESSAGES.get(days)
    if not msg:
        return
    users = get_users_expiring_in_days(days)
    for row in users:
        send_vk_message(row["user_id"], msg)
        logger.info("Sent %s-day reminder to user_id=%s", days, row["user_id"])


def check_expired_subscriptions():
    """Удаление из группы + ЛС об истечении + очистка БД"""
    expired = get_expired_user_ids()
    for user_id in expired:
        send_vk_message(user_id, config.EXPIRED_MESSAGE)
        remove_from_group(user_id)
        remove_subscription(user_id)
        logger.info("Removed user_id=%s from group (subscription expired)", user_id)


def start_scheduler() -> BackgroundScheduler:
    sched = BackgroundScheduler()
    sched.add_job(check_expired_subscriptions, "cron", hour=3, minute=0)
    sched.add_job(lambda: send_reminders(3), "cron", hour=9, minute=0)
    sched.add_job(lambda: send_reminders(1), "cron", hour=9, minute=0)
    sched.add_job(lambda: send_reminders(0), "cron", hour=9, minute=0)
    sched.start()
    return sched
