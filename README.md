# VK-бот: доступ в группу по платной подписке

Бот принимает сообщения «подписка», «купить», «оплатить» и т.п., создаёт платёж в ЮKassa, после успешной оплаты приглашает пользователя в группу. Подписка ежемесячная; по истечении срока пользователь исключается из группы.

## Установка

```bash
pip install -r requirements.txt
cp .env.example .env
# Отредактировать .env
```

## Настройка VK

1. Создайте группу ВКонтакте (именно группу, не публичную страницу).
2. Включите «Сообщения сообщества» (Управление → Сообщения).
3. Создайте ключ доступа: Управление → Работа с API → Ключи доступа.
4. Права: «Сообщения сообщества», «Управление сообществом».
5. Скопируйте токен и ID группы в `.env` (`VK_TOKEN`, `VK_GROUP_ID`).

**Проверить права токена:** [vk.com/club236063535?act=api](https://vk.com/club236063535?act=api) — замените `236063535` на ваш `VK_GROUP_ID`. Вкладка «Ключи доступа» → у токена должны быть галочки «Сообщения сообщества» и «Управление сообществом».

**Тип сообщества:** [vk.com/groups?act=manage](https://vk.com/groups?act=manage) — список ваших сообществ. Группа = «Группа», публичная страница = «Публичная страница». Для `groups.invite` нужна именно группа.

## Настройка ЮKassa

1. Зарегистрируйтесь на [yookassa.ru](https://yookassa.ru).
2. В личном кабинете: Настройки → HTTP-уведомления.
3. URL: `https://ваш-домен.com/webhook`
4. События: `payment.succeeded`.
5. Shop ID и Secret Key — в `.env`.

## Запуск

```bash
python main.py
```

Требуется публичный URL для webhook (VPS, ngrok для тестов).

## Docker

```bash
# Локально
docker-compose up -d

# Или без compose
docker build -t vk-bot .
docker run -d --env-file .env -p 5000:5000 -v bot-data:/app/data vk-bot
```

**Продакшен:** образ собирается в [GitHub Actions](.github/workflows/docker.yml) при push в `main` и пушится в `ghcr.io/ivanchikivanov/vk_bot`. На VPS:

```bash
docker pull ghcr.io/ivanchikivanov/vk_bot:latest
docker run -d --env-file .env -p 5000:5000 -v bot-data:/app/data ghcr.io/ivanchikivanov/vk_bot:latest
```

## Переменные окружения (.env)

| Переменная | Описание |
|------------|----------|
| VK_TOKEN | Ключ доступа сообщества |
| VK_GROUP_ID | ID группы (число) |
| YOOKASSA_SHOP_ID | Идентификатор магазина |
| YOOKASSA_SECRET_KEY | Секретный ключ |
| SUBSCRIPTION_PRICE | Цена подписки (например, 299.00) |
| SUBSCRIPTION_DAYS | Срок подписки в днях (30) |
| WEBHOOK_BASE_URL | Базовый URL для return_url (https://ваш-домен.com) |
| WEBHOOK_PORT | Порт Flask (5000) |
| DB_PATH | Путь к SQLite (subscriptions.db) |
| ADMIN_SECRET | Секрет для web-админки (?secret=) |
| ADMIN_VK_IDS | VK ID админов через запятую (для Mini App) |
| VK_APP_SECRET | Секрет приложения VK (для проверки подписи Mini App) |

## Админка: Web и VK Mini App

**Web:** `https://ваш-домен.com/admin?secret=ВАШ_СЕКРЕТ`

**VK Mini App:**
1. Создайте приложение: [vk.com/apps?act=manage](https://vk.com/apps?act=manage) → Создать → Мини-приложение.
2. Адрес: `https://ваш-домен.com/admin-app/`
3. В `.env`: `ADMIN_VK_IDS=123456789` (ваш VK ID, можно несколько через запятую).
4. Опционально: скопируйте секрет приложения в `VK_APP_SECRET` для проверки подписи.
5. Добавьте приложение в меню группы или откройте по ссылке `vk.com/app123456789`.

**Локальный тест Mini App:** `http://localhost:5000/admin-app/?secret=ВАШ_СЕКРЕТ`

## systemd (VPS)

```ini
[Unit]
Description=VK Subscription Bot
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/path/to/VK_bot
ExecStart=/usr/bin/python3 main.py
Restart=always

[Install]
WantedBy=multi-user.target
```
