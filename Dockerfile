# Dockerfile
FROM python:3.11-slim

# Устанавливаем системные зависимости
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Копируем requirements.txt отдельно для кэширования слоев
COPY requirements.txt .

# Устанавливаем Python зависимости
RUN pip install --no-cache-dir -r requirements.txt

ENV PYTHONPATH=/app:/app/src:/app/app

# Копируем остальные файлы проекта
COPY . .

# Команда по умолчанию
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8080"]