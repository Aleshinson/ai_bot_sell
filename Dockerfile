# Базовый образ Python
FROM python:3.11-slim

# Установка рабочей директории
WORKDIR /app

# Копирование файла зависимостей
COPY requirements.txt ./

# Установка зависимостей
RUN pip install -r requirements.txt

# Копирование остального кода приложения
COPY . .

# Команда для запуска приложения
CMD ["python", "main.py"]