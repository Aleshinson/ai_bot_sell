import asyncio
import logging
from aiogram import Bot, Dispatcher
from config import Config
from handlers import setup_handlers
from database.models import create_tables
from utils import messages

# Настройка логирования
logging.basicConfig(level=logging.INFO)


async def main():
    """Главная функция запуска бота"""
    try:
        # Создание таблиц в базе данных
        create_tables()
        
        # Инициализация бота и диспетчера
        bot = Bot(token=Config.BOT_TOKEN)
        dp = Dispatcher()

        messages.reload_messages()
        
        # Настройка обработчиков
        main_router = setup_handlers()
        dp.include_router(main_router)
        
        # Запуск бота
        await dp.start_polling(bot)
        
    except KeyboardInterrupt:
        print(messages.get_message('system', 'bot_stopped'))
    except Exception as e:
        logging.error(f"Ошибка запуска бота: {e}")
        print(messages.get_message('system', 'startup_error', error=str(e)))


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Бот был остановлен вручную.")