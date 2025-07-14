from aiogram import F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from .base import BaseHandler, DatabaseMixin
from utils import messages
from config import Config


class AnnouncementForm(StatesGroup):
    """Состояния формы создания объявления"""
    bot_name = State()
    bot_function = State()


class AnnouncementHandler(BaseHandler, DatabaseMixin):
    """Обработчик создания объявлений"""

    def __init__(self):
        self.moderator_ids = getattr(Config, 'MODERATOR_IDS', [454590867, 591273485, 1146006262])
        super().__init__()

    def setup_handlers(self):
        """Настройка обработчиков"""
        self.router.callback_query(F.data == "add_announcement")(self.start_announcement_creation)
        self.router.message(AnnouncementForm.bot_name)(self.process_bot_name)
        self.router.message(AnnouncementForm.bot_function)(self.process_bot_function)
        # Обработчик отмены создания объявления
        self.router.callback_query(F.data == "cancel_announcement")(self.cancel_announcement)

    async def start_announcement_creation(self, callback: CallbackQuery, state: FSMContext):
        """Начало создания объявления"""
        try:
            # Создаем кнопку отмены
            cancel_keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(
                    text=messages.get_message('announcement_creation', 'buttons', 'cancel'),
                    callback_data="cancel_announcement"
                )]
            ])

            await callback.message.answer(
                messages.get_message('announcement_creation', 'enter_bot_name'),
                parse_mode='HTML',
                reply_markup=cancel_keyboard
            )
            await state.set_state(AnnouncementForm.bot_name)
            await callback.answer()

        except Exception as e:
            await self.send_error_message(callback, 'general_error', error=str(e))

    async def process_bot_name(self, message: Message, state: FSMContext):
        """Обработка названия бота"""
        try:
            await state.update_data(bot_name=message.text)

            # Создаем кнопку отмены
            cancel_keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(
                    text=messages.get_message('announcement_creation', 'buttons', 'cancel'),
                    callback_data="cancel_announcement"
                )]
            ])

            await message.answer(
                messages.get_message('announcement_creation', 'enter_bot_function'),
                parse_mode='HTML',
                reply_markup=cancel_keyboard
            )
            await state.set_state(AnnouncementForm.bot_function)

        except Exception as e:
            await self.send_error_message(message, 'general_error', error=str(e))

    async def process_bot_function(self, message: Message, state: FSMContext):
        """Обработка функционала бота и создание объявления"""
        try:
            user_data = await state.get_data()
            bot_name = user_data['bot_name']
            bot_function = message.text

            # Создание объявления через безопасную операцию с БД
            announcement = self.safe_db_operation(
                self._create_announcement_in_db,
                message.from_user.id,
                message.chat.id,
                bot_name,
                bot_function
            )

            # Уведомление модераторов
            await self._notify_moderators(message, announcement)

            # Уведомление пользователя
            await message.answer(
                messages.get_message('announcement_creation', 'announcement_sent',
                                   announcement_id=announcement['id']),
                parse_mode='HTML'
            )

            await state.clear()

        except Exception as e:
            await message.answer(
                messages.get_message('announcement_creation', 'save_error', error=str(e)),
                parse_mode='HTML'
            )
            await state.clear()

    async def cancel_announcement(self, callback: CallbackQuery, state: FSMContext):
        """Отмена создания объявления"""
        try:
            await state.clear()

            # Возвращаем главное меню
            from .start_handler import StartHandler
            start_handler = StartHandler()
            await start_handler.show_main_menu(callback.message)

            await callback.message.answer(
                messages.get_message('announcement_creation', 'cancelled'),
                parse_mode='HTML'
            )
            await callback.answer()

        except Exception as e:
            await self.send_error_message(callback, 'general_error', error=str(e))

    def _create_announcement_in_db(self, session, user_id: int, chat_id: int,
                                       bot_name: str, bot_function: str) -> dict:
        """Создание объявления в базе данных"""
        announcement = self.create_announcement(session, user_id, chat_id, bot_name, bot_function)
        # Возвращаем словарь с данными вместо объекта
        return {
            'id': announcement.id,
            'user_id': announcement.user_id,
            'chat_id': announcement.chat_id,
            'bot_name': announcement.bot_name,
            'bot_function': announcement.bot_function,
            'is_approved': announcement.is_approved,
            'created_at': announcement.created_at
        }

    async def _notify_moderators(self, message: Message, announcement: dict):
        """Уведомление модераторов о новом объявлении"""
        print(f"Debug: Notifying moderators. Announcement data - ID: {announcement.get('id', 'N/A')}, Bot Name: {announcement.get('bot_name', 'N/A')}, Bot Function: {announcement.get('bot_function', 'N/A')}")
        try:
            # Format the created date if available, or use a default
            created_date = announcement.get('created_at', 'N/A')
            if created_date != 'N/A' and hasattr(created_date, 'strftime'):
                created_date = created_date.strftime('%Y-%m-%d %H:%M:%S')

            notification_text = messages.get_message(
                'moderation', 'new_announcement_template',
                announcement_id=announcement.get('id', 'unknown'),
                bot_name=announcement.get('bot_name', 'unknown'),
                bot_function=announcement.get('bot_function', 'unknown'),
                username=announcement.get('user_id', 'unknown_user'),
                created_date=created_date
            )
        except Exception as e:
            print(f"Error in get_message: {e}. Fallback to default message.")
            notification_text = "Внутренняя ошибка: шаблон сообщения не доступен."
        moderation_keyboard = self._create_moderation_keyboard(announcement.get('id', 0), announcement.get('chat_id', 0))
        for mod_id in self.moderator_ids:
            try:
                await message.bot.send_message(
                    mod_id,
                    notification_text,
                    parse_mode='HTML',
                    reply_markup=moderation_keyboard
                )
            except Exception:
                # Игнорируем ошибки отправки конкретным модераторам
                continue

    def _create_moderation_keyboard(self, announcement_id: int, chat_id: int) -> InlineKeyboardMarkup:
        """Создание клавиатуры для модерации"""
        buttons = [
            [
                InlineKeyboardButton(
                    text=messages.get_button_text('moderation', 'approve'),
                    callback_data=f"approve_{announcement_id}"
                ),
                InlineKeyboardButton(
                    text=messages.get_button_text('moderation', 'reject'),
                    callback_data=f"reject_{announcement_id}"
                ),
                InlineKeyboardButton(
                    text=messages.get_button_text('moderation', 'contact'),
                    url=f"tg://user?id={chat_id}"
                )
            ]
        ]

        return InlineKeyboardMarkup(inline_keyboard=buttons)
