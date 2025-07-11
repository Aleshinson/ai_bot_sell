from aiogram import Router
from .start_handler import StartHandler
from .announcement_handler import AnnouncementHandler
from .moderation_handler import ModerationHandler
from .search_handler import SearchHandler


def setup_handlers() -> Router:
    """
    Настройка всех обработчиков бота

    Returns:
        Router: Главный роутер со всеми обработчиками
    """
    main_router = Router()

    # Инициализация обработчиков
    handlers = [
        StartHandler(),
        AnnouncementHandler(),
        ModerationHandler(),
        SearchHandler()
    ]

    # Добавление роутеров всех обработчиков к главному роутеру
    for handler in handlers:
        main_router.include_router(handler.router)

    return main_router


# Экспорт для удобства импорта
__all__ = [
    'setup_handlers',
    'StartHandler',
    'AnnouncementHandler',
    'ModerationHandler',
    'SearchHandler'
]
