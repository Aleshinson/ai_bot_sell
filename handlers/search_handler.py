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
    """Состояния формы поиска"""
    search_query = State()


class SearchHandler(BaseHandler, DatabaseMixin):
    """Обработчик умного поиска AI-решений"""

    def __init__(self):
        super().__init__()
        self.ai_search = AISearchService()

    def setup_handlers(self):
        """Настройка обработчиков"""
        self.router.callback_query(F.data == "search_announcements")(self.start_search)
        self.router.message(SearchForm.search_query)(self.process_search_query)
        # Обработчик для выбора конкретного решения
        self.router.callback_query(F.data.startswith("view_solution_"))(self.view_solution_details)
        # Обработчик отмены поиска
        self.router.callback_query(F.data == "cancel_search")(self.cancel_search)

    @staticmethod
    async def start_search(callback: CallbackQuery, state: FSMContext):
        """Начало умного поиска AI-решений"""
        try:
            # Создаем кнопку отмены
            cancel_keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(
                    text=messages.get_message('search', 'buttons', 'cancel'),
                    callback_data="cancel_search"
                )]
            ])

            await callback.message.answer(
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
        """Обработка поискового запроса с помощью AI"""
        try:
            search_query = message.text.strip()

            if not search_query:
                await message.answer(
                    messages.get_message('search', 'enter_search_query'),
                    parse_mode='HTML'
                )
                return

            # Показываем индикатор обработки
            processing_msg = await message.answer("🤖 Анализирую ваш запрос с помощью AI...")

            # Получаем все одобренные объявления
            all_announcements = self.safe_db_operation(
                self._get_all_approved_announcements
            )

            if not all_announcements:
                await processing_msg.edit_text(
                    "😔 В базе пока нет одобренных AI-решений"
                )
                await state.clear()
                return

            # Используем AI для умного поиска
            search_result = await self.ai_search.smart_search(search_query, all_announcements)

            # Удаляем сообщение об обработке
            await processing_msg.delete()

            if not search_result["found"]:
                await message.answer(
                    f"🤖 {search_result['explanation']}\n\n💡 Попробуйте переформулировать запрос или использовать другие ключевые слова"
                )
            else:
                await self._send_ai_search_results(message, search_result, search_query)

        except Exception as e:
            await message.answer(
                messages.get_message('search', 'search_error', error=str(e))
            )
        finally:
            await state.clear()

    async def view_solution_details(self, callback: CallbackQuery):
        """Просмотр детальной информации о решении"""
        try:
            solution_id = int(callback.data.split("_")[-1])

            # Получаем информацию о решении из БД
            announcement_data = self.safe_db_operation(
                self._get_announcement_for_contact, solution_id
            )

            if not announcement_data:
                await callback.message.answer(
                    messages.get_message('moderation', 'announcement_not_found')
                )
                return

            # Форматируем детальную информацию
            details_text = messages.get_message(
                'search', 'solution_details_template',
                bot_name=announcement_data['bot_name'],
                bot_function=announcement_data['bot_function'],
                created_date=announcement_data['created_date'].strftime('%d.%m.%Y')
            )

            # Создаем кнопку для связи
            keyboard = [
                [InlineKeyboardButton(
                    text=messages.get_message('search', 'buttons', 'contact_author'),
                    url=f"tg://user?id={announcement_data['user_id']}"
                )]
            ]

            reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard)

            await callback.message.answer(
                details_text,
                parse_mode='HTML',
                reply_markup=reply_markup
            )
            await callback.answer()

        except Exception as e:
            await callback.message.answer(
                messages.get_message('search', 'search_error', error=str(e))
            )

    @staticmethod
    async def cancel_search(callback: CallbackQuery, state: FSMContext):
        """Отмена поиска"""
        try:
            await state.clear()

            # Возвращаем главное меню
            from .start_handler import StartHandler
            start_handler = StartHandler()
            await start_handler.show_main_menu(callback.message)

            await callback.message.answer(
                messages.get_message('search', 'search_cancelled'),
                parse_mode='HTML'
            )
            await callback.answer()

        except Exception as e:
            await callback.message.answer(
                messages.get_message('search', 'search_error', error=str(e))
            )

    @staticmethod
    def _get_announcement_for_contact(session, announcement_id: int) -> dict:
        """Получение объявления для контакта"""
        announcement = session.query(Announcement).filter(
            Announcement.id == announcement_id,
            Announcement.is_approved == True
        ).first()

        if announcement:
            return {
                'id': announcement.id,
                'bot_name': announcement.bot_name,
                'bot_function': announcement.bot_function,
                'user_id': announcement.user_id,
                'created_date': announcement.created_at
            }
        return None

    @staticmethod
    def _get_all_approved_announcements(session):
        """Получение всех одобренных объявлений для AI поиска"""
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
                'is_approved': ann.is_approved,
                'created_at': ann.created_at
            }
            for ann in announcements
        ]

    def _get_announcement_by_id_detailed(self, session, announcement_id: int):
        """Получение детальной информации об объявлении"""
        announcement = self.get_announcement_by_id(session, announcement_id)
        if not announcement:
            return None

        return {
            'id': announcement.id,
            'user_id': announcement.user_id,
            'chat_id': announcement.chat_id,
            'bot_name': announcement.bot_name,
            'bot_function': announcement.bot_function,
            'is_approved': announcement.is_approved,
            'created_at': announcement.created_at
        }

    async def _send_ai_search_results(self, message: Message, search_result: dict, query: str):
        """Отправка результатов AI поиска"""
        results = search_result["results"]
        explanation = search_result["explanation"]

        # Заголовок с объяснением от AI
        header_text = f"🤖 {explanation}\n\n🎯 Найдено решений: {len(results)}\n🔍 По запросу: \"{query}\"\n\n"
        await message.answer(header_text, parse_mode='HTML')

        if len(results) == 1:
            # Если найдено одно решение - показываем его детально
            solution = results[0]
            await self._send_detailed_solution(message, solution)
        else:
            # Если найдено несколько - показываем краткий список с кнопками выбора
            await self._send_solutions_list(message, results)

    @staticmethod
    async def _send_detailed_solution(message: Message, solution: dict):
        """Отправка детальной информации об одном решении"""
        ai_explanation = solution.get('ai_explanation', '')
        relevance_score = solution.get('relevance_score', 0)

        solution_text = (
            f"🤖 <b>{solution['bot_name']}</b>\n"
            f"⚡ <i>{solution['bot_function']}</i>\n"
            f"📅 Создано: {solution['created_at'].strftime('%d.%m.%Y')}\n"
        )

        if ai_explanation:
            solution_text += f"🎯 <i>Почему подходит: {ai_explanation}</i>\n"

        if relevance_score:
            solution_text += f"📊 Релевантность: {relevance_score}/10\n"

        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(
                    text=messages.get_message('search', 'buttons', 'contact_author'),
                    url=f"tg://user?id={solution['chat_id']}"
                )]
            ]
        )

        await message.answer(
            solution_text,
            reply_markup=keyboard,
            parse_mode='HTML'
        )

    @staticmethod
    async def _send_solutions_list(message: Message, solutions: List[dict]):
        """Отправка списка решений с кнопками выбора"""
        keyboard = []
        for i, result in enumerate(solutions[:5], 1):  # Показываем максимум 5 результатов
            keyboard.append([
                InlineKeyboardButton(
                    text=f"📋 {i}. {result['bot_name'][:30]}...",
                    callback_data=f"view_solution_{result['id']}"
                )
            ])

        reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard)

        for i, result in enumerate(solutions[:5], 1):  # Показываем максимум 5 результатов
            solution_text = (
                f"🤖 <b>{i}. {result['bot_name']}</b>\n"
                f"⚡ <i>{result['bot_function'][:100]}{'...' if len(result['bot_function']) > 100 else ''}</i>\n"
            )

            await message.answer(
                solution_text,
                reply_markup=reply_markup,
                parse_mode='HTML'
            )
