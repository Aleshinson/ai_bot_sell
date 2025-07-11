import os
from dotenv import load_dotenv
from typing import List

# Загрузка переменных окружения из .env файла
load_dotenv()


class Config:
    """Конфигурация приложения"""
    
    # Токен бота
    BOT_TOKEN: str = os.getenv("BOT_TOKEN")
    
    # URL базы данных
    DATABASE_URL: str = os.getenv("DATABASE_URL")
    
    # OpenAI API ключ для умного поиска
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY")
    
    # ID модераторов (можно задать через переменную окружения или использовать по умолчанию)
    MODERATOR_IDS: List[int] = [
        int(id_str) for id_str in os.getenv("MODERATOR_IDS").split(",")
        if id_str.strip().isdigit()
    ]
    
    @classmethod
    def validate(cls):
        """Валидация конфигурации"""
        if not cls.BOT_TOKEN:
            raise ValueError("BOT_TOKEN не найден в переменных окружения")
        
        if not cls.DATABASE_URL:
            raise ValueError("DATABASE_URL не найден в переменных окружения")
        
        # OpenAI API ключ не обязателен - если его нет, используем обычный поиск
        if not cls.OPENAI_API_KEY:
            print("⚠️ OPENAI_API_KEY не найден - будет использоваться обычный поиск")
        
        if not cls.MODERATOR_IDS:
            raise ValueError("MODERATOR_IDS не настроены")


# Валидация конфигурации при импорте
Config.validate()