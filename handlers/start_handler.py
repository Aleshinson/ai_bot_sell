from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from .base import BaseHandler
from utils import messages


class StartHandler(BaseHandler):
    """Обработчик стартовой команды и основного меню"""

    def setup_handlers(self):
        """Настройка обработчиков"""
        self.router.message(Command("start"))(self.start_command)

    async def start_command(self, message: Message):
        """Обработка команды /start"""
        try:
            keyboard = self._create_main_menu_keyboard()
            welcome_text = messages.get_message('start_command', 'welcome_message')

            await message.answer(
                welcome_text,
                reply_markup=keyboard,
                parse_mode='HTML'
            )

        except Exception as e:
            await self.send_error_message(message, 'general_error', error=str(e))

    async def show_main_menu(self, message: Message):
        """Показать главное меню"""
        keyboard = self._create_main_menu_keyboard()
        welcome_text = messages.get_message('start_command', 'welcome_message')

        await message.answer(
            welcome_text,
            reply_markup=keyboard,
            parse_mode='HTML'
        )

    def _create_main_menu_keyboard(self) -> InlineKeyboardMarkup:
        """Создание клавиатуры главного меню"""
        buttons = [
            [InlineKeyboardButton(
                text=messages.get_button_text('start_command', 'go_to_chat'),
                url=messages.get_message('start_command', 'chat_url')
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
