# Explanation: multi-stage не нужен — один образ, Python slim
FROM python:3.12-slim

WORKDIR /app

# Explanation: зависимости системы не требуются для vk_api/flask/sqlite
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Explanation: DB_PATH задаётся через env; по умолчанию /app/data для volume
ENV DB_PATH=/app/data/subscriptions.db

EXPOSE 5000

CMD ["python", "main.py"]
