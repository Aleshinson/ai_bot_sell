from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from .base import BaseHandler
from utils import messages
import logging

# Используем логгер для модуля handlers
logger = logging.getLogger('handlers')


class StartHandler(BaseHandler):
    """Обработчик стартовой команды и основного меню"""

    def setup_handlers(self):
        """Настройка обработчиков"""
        self.router.message(Command("start"))(self.start_command)

    async def start_command(self, message: Message):
        """Обработка команды /start"""
        try:
            await self.show_main_menu(message)
        except Exception as e:
            await self.send_error_message(message, 'general_error', error=str(e))

    async def show_main_menu(self, message: Message):
        """Отправка главного меню с кнопками"""
        try:
            keyboard = self._create_main_menu_keyboard()
            welcome_text = messages.get_message('start_command', 'welcome_message')
            
            # Удаляем предыдущее сообщение если возможно
            try:
                await message.delete()
            except Exception:
                pass  # Игнорируем ошибки удаления
                
            await message.answer(
                welcome_text,
                reply_markup=keyboard,
                parse_mode='HTML'
            )
            
        except Exception as e:
            logger.error(f"Error displaying main menu: {str(e)}")
            await self.send_error_message(message, 'general_error', error=str(e))

    @staticmethod
    def _create_main_menu_keyboard() -> InlineKeyboardMarkup:
        """Создание клавиатуры главного меню"""
        buttons = [
            [InlineKeyboardButton(
                text=messages.get_button_text('start_command', 'go_to_chat'),
                url=messages.get_chat_url()
            )],
            [InlineKeyboardButton(
                text=messages.get_button_text('start_command', 'add_announcement'),
                callback_data="add_announcement"
            )],
            [InlineKeyboardButton(
                text=messages.get_button_text('start_command', 'search_announcements'),
                callback_data="search_announcements"
            )]
        ]

        return InlineKeyboardMarkup(inline_keyboard=buttons)
