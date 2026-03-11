"""Запуск Long Poll + Flask webhook + APScheduler"""
import logging
import threading

import config
from bot.db import init_db
from bot.vk_handler import run_longpoll
from bot.webhook import app
from scheduler import start_scheduler

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)
# Убрать шум APScheduler: Running job / executed successfully каждые 5 сек
logging.getLogger("apscheduler.executors.default").setLevel(logging.WARNING)


def main():
    init_db()
    start_scheduler()

    def run_flask():
        app.run(host="0.0.0.0", port=config.WEBHOOK_PORT, use_reloader=False)

    t = threading.Thread(target=run_flask, daemon=True)
    t.start()

    logger.info("Flask webhook on port %s, Long Poll starting", config.WEBHOOK_PORT)
    run_longpoll()


if __name__ == "__main__":
    main()
