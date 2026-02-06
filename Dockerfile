FROM python:3.11-slim

#системные зависимости
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

#копирование requirements.txt отдельно для кэширования слоев
COPY requirements.txt .

#питон зависимости
RUN pip install --no-cache-dir -r requirements.txt

ENV PYTHONPATH=/app:/app/src:/app/app

COPY . .

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8080"]