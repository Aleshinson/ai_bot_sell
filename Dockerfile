# Базовый образ Python
FROM python:3.11-slim

# Установка рабочей директории
WORKDIR /app

# Установка зависимостей системы
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Установка Poetry для управления зависимостями
RUN pip install poetry

# Копирование файлов проекта
COPY pyproject.toml poetry.lock* ./

# Установка зависимостей через Poetry
RUN poetry config virtualenvs.create false
RUN poetry install --no-root --no-interaction --no-ansi

# Копирование остального кода приложения
COPY . .

# Команда для запуска приложения
CMD ["python", "main.py"]