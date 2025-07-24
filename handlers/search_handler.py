from aiogram import F
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from .base import BaseHandler, DatabaseMixin
from database.models import Announcement
from services import AISearchService
from utils import messages
from typing import List


class SearchForm(StatesGroup):
    """Состояния формы поиска."""
    search_query = State()


class SearchHandler(BaseHandler, DatabaseMixin):
    """Обработчик умного поиска AI-решений."""

    def __init__(self):
        """Инициализация обработчика поиска."""
        super().__init__()
        self.ai_search = AISearchService()

    def setup_handlers(self):
        """Настройка обработчиков."""
        self.router.callback_query(F.data == 'search_announcements')(self.start_search)
        self.router.message(SearchForm.search_query)(self.process_search_query)
        # Обработчик для выбора конкретного решения
        self.router.callback_query(F.data.startswith('view_solution_'))(self.view_solution_details)
        # Обработчик отмены поиска
        self.router.callback_query(F.data == 'cancel_search')(self.cancel_search)


    @staticmethod
    async def start_search(callback: CallbackQuery, state: FSMContext):
        """
        Начало умного поиска AI-решений.
        
        Args:
            callback: Объект обратного вызова
            state: Контекст состояния FSM
        """
        try:
            # Создаем кнопку отмены
            cancel_keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(
                    text=messages.get_message('search', 'buttons', 'cancel'),
                    callback_data='cancel_search'
                )]
            ])

            await callback.message.edit_text(
                messages.get_message('search', 'enter_search_query'),
                parse_mode='HTML',
                reply_markup=cancel_keyboard
            )
            await state.set_state(SearchForm.search_query)
            await callback.answer()

        except Exception as e:
            await callback.message.answer(
                messages.get_message('search', 'search_error', error=str(e))
            )


    async def process_search_query(self, message: Message, state: FSMContext):
        """
        Обработка поискового запроса с помощью AI.
        
        Args:
            message: Объект сообщения
            state: Контекст состояния FSM
        """
        try:
            search_query = message.text.strip()

            if not search_query:
                await message.answer(
                    messages.get_message('search', 'enter_search_query'),
                    parse_mode='HTML'
                )
                return

            # Показываем индикатор обработки
            processing_msg = await message.answer('🤖 Анализирую ваш запрос...')

            # Получаем все одобренные объявления
            all_announcements = self.safe_db_operation(
                self._get_all_approved_announcements
            )

            if not all_announcements:
                await processing_msg.edit_text(
                    '😔 В базе пока нет одобренных AI-решений'
                )
                await state.clear()
                return

            # Используем AI для умного поиска
            search_result = await self.ai_search.smart_search(search_query, all_announcements)

            # Обновляем сообщение с результатами поиска
            if not search_result['found']:
                # Если ничего не найдено - предлагаем перейти в чат
                no_results_text = (
                    '🔍 Подходящих объявлений не найдено\n\n'
                    '💬 Вы можете перейти в чат и посмотреть то, что имеется у нас'
                )

                # Добавляем кнопку перехода в чат
                chat_keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(
                        text='💬 Перейти в чат',
                        url=self.get_chat_url()
                    )]
                ])

                await message.answer(
                    no_results_text,
                    reply_markup=chat_keyboard,
                    parse_mode='HTML'
                )
            else:
                results = search_result['results']

                if len(results) == 1:
                    # Если найдено одно объявление - показываем его полностью
                    await self._show_full_announcement(message, results[0])
                else:
                    # Если найдено много - показываем список с кнопками
                    await self._show_announcements_list(message, results)

            await state.clear()

        except Exception as e:
            await message.answer(
                messages.get_message('search', 'search_error', error=str(e))
            )


    async def view_solution_details(self, callback: CallbackQuery):
        """
        Просмотр детальной информации о решении.
        
        Args:
            callback: Объект обратного вызова
        """
        try:
            solution_id = int(callback.data.split('_')[-1])

            # Получаем полную информацию о решении из БД
            announcement_data = self.safe_db_operation(
                self._get_full_announcement_by_id, solution_id
            )

            if not announcement_data:
                await callback.message.answer(
                    messages.get_message('moderation', 'announcement_not_found')
                )
                return

            # Показываем полную информацию
            await self._show_full_announcement(callback.message, announcement_data)
            await callback.answer()

        except Exception as e:
            await callback.message.answer(
                messages.get_message('search', 'search_error', error=str(e))
            )


    async def _show_full_announcement(self, message: Message, announcement: dict):
        """
        Показать полное объявление.
        
        Args:
            message: Объект сообщения
            announcement: Словарь с данными объявления
        """
        try:
            # Форматируем полную информацию об объявлении
            full_text = (
                f"🤖 <b>{announcement['bot_name']}</b>\n\n"
                f"⚡ <b>Проблема:</b>\n{announcement['bot_function']}\n\n"
            )

            # Добавляем дополнительные поля если они есть
            if announcement.get('solution_description'):
                full_text += f"🎯 <b>Функционал:</b>\n{announcement['solution_description']}\n\n"

            if announcement.get('included_features'):
                full_text += f"📦 <b>Включено:</b>\n{announcement['included_features']}\n\n"

            if announcement.get('client_requirements'):
                full_text += f"📋 <b>Требования к клиенту:</b>\n{announcement['client_requirements']}\n\n"

            if announcement.get('launch_time'):
                full_text += f"⏱️ <b>Срок запуска:</b> {announcement['launch_time']}\n\n"

            if announcement.get('price'):
                full_text += f"💰 <b>Цена:</b> {announcement['price']}\n\n"

            if announcement.get('complexity'):
                full_text += f"📊 <b>Сложность:</b> {announcement['complexity']}\n\n"

            full_text += f"📅 <b>Создано:</b> {announcement['created_at'].strftime('%d.%m.%Y')}"

            # Создаем кнопку для связи с автором
            contact_keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(
                    text=messages.get_message('search', 'buttons', 'contact_author'),
                    url=f"tg://user?id={announcement['user_id']}"
                )]
            ])

            await message.answer(
                full_text,
                reply_markup=contact_keyboard,
                parse_mode='HTML'
            )

        except Exception as e:
            await message.answer(
                messages.get_message('search', 'search_error', error=str(e))
            )


    async def _show_announcements_list(self, message: Message, announcements: List[dict]):
        """
        Показать список объявлений одним сообщением с кнопками.
        
        Args:
            message: Объект сообщения
            announcements: Список объявлений
        """
        try:
            # Создаем короткие описания через GPT
            short_descriptions = await self.ai_search.create_short_descriptions(announcements)

            # Формируем текст списка
            list_text = "📋 <b>Найденные AI-решения:</b>\n\n"

            # Создаем кнопки для каждого объявления
            keyboard = []

            for i, announcement in enumerate(announcements[:10], 1):  # Максимум 10 результатов
                # Получаем короткое описание от GPT или fallback
                short_desc = short_descriptions.get(
                    str(announcement['id']),
                    announcement['bot_function'][:50] + '...'
                )

                # Добавляем в текст списка
                list_text += f"{i}. <b>{announcement['bot_name']}</b>\n"
                list_text += f"   {short_desc}\n\n"

                # Добавляем кнопку для этого объявления
                keyboard.append([
                    InlineKeyboardButton(
                        text=f"{i}. {announcement['bot_name']}",
                        callback_data=f"view_solution_{announcement['id']}"
                    )
                ])

            # Создаем клавиатуру
            reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard)

            # Отправляем одно сообщение со списком и кнопками
            await message.answer(
                list_text,
                reply_markup=reply_markup,
                parse_mode='HTML'
            )

        except Exception as e:
            await message.answer(
                messages.get_message('search', 'search_error', error=str(e))
            )


    @staticmethod
    async def cancel_search(callback: CallbackQuery, state: FSMContext):
        """
        Отмена поиска.
        
        Args:
            callback: Объект обратного вызова
            state: Контекст состояния FSM
        """
        try:
            await state.clear()

            # Возвращаем главное меню
            from .start_handler import StartHandler
            start_handler = StartHandler()
            keyboard = start_handler._create_main_menu_keyboard()
            welcome_text = messages.get_message('start_command', 'welcome_message')

            await callback.message.edit_text(
                welcome_text,
                reply_markup=keyboard,
                parse_mode='HTML'
            )
            await callback.answer()

        except Exception as e:
            await callback.message.answer(
                messages.get_message('search', 'search_error', error=str(e))
            )


    @staticmethod
    def get_chat_url():
        """
        Получение URL чата из переменной окружения.
        
        Returns:
            URL чата
        """
        from config import Config
        return Config.CHAT_URL


    @staticmethod
    def _get_all_approved_announcements(session):
        """
        Получение всех одобренных объявлений для AI поиска.
        
        Args:
            session: Сессия базы данных
            
        Returns:
            Список одобренных объявлений
        """
        announcements = session.query(Announcement).filter(
            Announcement.is_approved == True
        ).order_by(Announcement.created_at.desc()).all()

        return [
            {
                'id': ann.id,
                'user_id': ann.user_id,
                'chat_id': ann.chat_id,
                'bot_name': ann.bot_name,
                'bot_function': ann.bot_function,
                'solution_description': ann.solution_description,
                'included_features': ann.included_features,
                'client_requirements': ann.client_requirements,
                'launch_time': ann.launch_time,
                'price': ann.price,
                'complexity': ann.complexity,
                'is_approved': ann.is_approved,
                'created_at': ann.created_at
            }
            for ann in announcements
        ]


    @staticmethod
    def _get_full_announcement_by_id(session, announcement_id: int):
        """
        Получение полной информации об объявлении по ID.
        
        Args:
            session: Сессия базы данных
            announcement_id: ID объявления
            
        Returns:
            Словарь с данными объявления или None
        """
        announcement = session.query(Announcement).filter(
            Announcement.id == announcement_id,
            Announcement.is_approved == True
        ).first()

        if announcement:
            return {
                'id': announcement.id,
                'user_id': announcement.user_id,
                'chat_id': announcement.chat_id,
                'bot_name': announcement.bot_name,
                'bot_function': announcement.bot_function,
                'solution_description': announcement.solution_description,
                'included_features': announcement.included_features,
                'client_requirements': announcement.client_requirements,
                'launch_time': announcement.launch_time,
                'price': announcement.price,
                'complexity': announcement.complexity,
                'is_approved': announcement.is_approved,
                'created_at': announcement.created_at
            }
        return None