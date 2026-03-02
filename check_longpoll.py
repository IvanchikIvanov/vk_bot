"""Диагностика Long Poll: проверка токена, сервера и событий"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / ".env")

VK_TOKEN = os.getenv("VK_TOKEN", "")
VK_GROUP_ID = os.getenv("VK_GROUP_ID", "0")

def main():
    if not VK_TOKEN or not VK_GROUP_ID:
        print("Ошибка: VK_TOKEN и VK_GROUP_ID должны быть в .env")
        return
    try:
        from vk_api import VkApi
        vk = VkApi(token=VK_TOKEN)
        print(f"Токен OK. group_id={VK_GROUP_ID}")
    except Exception as e:
        print(f"Ошибка VkApi: {e}")
        return

    # 0. Включить message_new если выключен
    try:
        settings = vk.method("groups.getLongPollSettings", {"group_id": int(VK_GROUP_ID)})
        if not settings.get("events", {}).get("message_new"):
            vk.method("groups.setLongPollSettings", {
                "group_id": int(VK_GROUP_ID),
                "message_new": 1,
            })
            print("message_new ВКЛЮЧЁН (было выключено)")
        else:
            print("message_new уже включён")
    except Exception as e:
        print(f"Ошибка настройки Long Poll: {e}")

    # 1. Проверка getLongPollServer
    try:
        r = vk.method("groups.getLongPollServer", {"group_id": int(VK_GROUP_ID)})
        print(f"Long Poll сервер: {r.get('server', '?')[:50]}...")
        print(f"key={r.get('key', '?')[:20]}... ts={r.get('ts')}")
    except Exception as e:
        print(f"ОШИБКА groups.getLongPollServer: {e}")
        print("\nВозможные причины:")
        print("1. Callback API включён — выключи в группе: Управление → Работа с API → Callback API → Выключить")
        print("2. Long Poll выключен — включи: Управление → Работа с API → Long Poll API → Включить")
        print("3. Токен не от этой группы — создай ключ в настройках группы")
        return

    # 2. Один запрос к Long Poll
    import requests
    url = r["server"]
    params = {"act": "a_check", "key": r["key"], "ts": r["ts"], "wait": 1}
    try:
        resp = requests.get(url, params=params, timeout=5)
        data = resp.json()
        if "updates" in data:
            print(f"События: {len(data['updates'])} шт.")
            for u in data["updates"][:3]:
                print(f"  - type={u.get('type')} object={str(u.get('object', {}))[:80]}...")
        elif "failed" in data:
            print(f"Long Poll failed={data['failed']}")
        else:
            print(f"Ответ: {data}")
    except Exception as e:
        print(f"Ошибка запроса: {e}")

if __name__ == "__main__":
    main()
