from aiogram import F
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from .base import BaseHandler, DatabaseMixin
from utils import messages
from config import Config
from typing import List
from handlers.start_handler import StartHandler
import logging


# Используем логгер для модуля handlers
logger = logging.getLogger('handlers')


class ModerationForm(StatesGroup):
    """Состояния формы модерации."""
    comment = State()


class ModerationHandler(BaseHandler, DatabaseMixin):
    """Обработчик модерации объявлений."""

    def __init__(self):
        """Инициализация обработчика модерации."""
        self.moderator_ids: List[int] = getattr(Config, 'MODERATOR_IDS')
        super().__init__()

    def setup_handlers(self):
        """Настройка обработчиков."""
        # Специфичные обработчики должны идти ПЕРЕД общим
        self.router.callback_query(F.data.startswith('approve_'))(self.approve_announcement)
        self.router.callback_query(F.data.startswith('reject_'))(self.reject_announcement)
        self.router.callback_query(F.data == 'main_menu')(self.back_to_menu)
        self.router.message(ModerationForm.comment)(self.process_rejection_comment)


    async def approve_announcement(self, callback: CallbackQuery):
        """
        Одобрение объявления.
        
        Args:
            callback: Объект обратного вызова
        """
        announcement_id = int(callback.data.split('_')[1])
        moderator_id = callback.from_user.id

        if not await self.check_permissions(moderator_id, self.moderator_ids):
            await callback.answer(messages.get_message('moderation', 'no_permissions'))
            return

        try:
            result = self.safe_db_operation(
                self._approve_announcement_in_db,
                announcement_id,
                moderator_id
            )

            if not result:
                await callback.message.answer(
                    messages.get_message('moderation', 'announcement_not_found'),
                    parse_mode='HTML'
                )
                return

            if result.get('already_processed'):
                await callback.message.answer(
                    messages.get_message('moderation', 'already_processed'),
                    parse_mode='HTML'
                )
                return

            announcement = result

            # Уведомление автора объявления
            await self._notify_user_approval(callback.message, announcement)

            # Уведомление других модераторов
            await self._notify_other_moderators(callback, moderator_id, approved=True, announcement=announcement)

            # Обновление сообщения модератора
            await self._update_moderator_message(callback, announcement, approved=True)

        except Exception as e:
            await callback.message.answer(
                messages.get_message('moderation', 'approval_error', error=str(e)),
                parse_mode='HTML'
            )

        await callback.answer()


    async def reject_announcement(self, callback: CallbackQuery, state: FSMContext):
        """
        Начало процесса отклонения объявления.
        
        Args:
            callback: Объект обратного вызова
            state: Контекст состояния FSM
        """
        announcement_id = int(callback.data.split('_')[1])
        moderator_id = callback.from_user.id
        
        if not await self.check_permissions(moderator_id, self.moderator_ids):
            await callback.answer(messages.get_message('moderation', 'no_permissions'))
            return
        
        try:
            # Используем безопасную операцию с БД
            announcement = self.safe_db_operation(
                self._get_announcement_for_rejection,
                announcement_id
            )
            
            if not announcement:
                await callback.message.edit_text(
                    messages.get_message('moderation', 'announcement_not_found'),
                    parse_mode='HTML'
                )
                return
            
            if not announcement['is_pending']:
                await callback.message.edit_text(
                    messages.get_message('moderation', 'already_processed'),
                    parse_mode='HTML'
                )
                return
            
            await callback.message.edit_text(
                messages.get_message('moderation', 'rejection_reason_request'),
                parse_mode='HTML'
            )
            await state.set_state(ModerationForm.comment)
            await state.update_data(announcement_id=announcement_id, moderator_id=moderator_id)
            
        except Exception as e:
            await callback.message.answer(
                messages.get_message('moderation', 'general_error', error=str(e)),
                parse_mode='HTML'
            )
        
        await callback.answer()


    async def process_rejection_comment(self, message: Message, state: FSMContext):
        """
        Обработка комментария при отклонении объявления.
        
        Args:
            message: Объект сообщения
            state: Контекст состояния FSM
        """
        try:
            comment = message.text
            user_data = await state.get_data()
            announcement_id = user_data['announcement_id']
            moderator_id = user_data['moderator_id']

            result = self.safe_db_operation(
                self._reject_announcement_in_db,
                announcement_id,
                moderator_id,
                comment
            )

            if not result:
                await message.edit_text(
                    messages.get_message('moderation', 'announcement_not_found'),
                    parse_mode='HTML'
                )
                await state.clear()
                return

            if result.get('already_processed'):
                await message.edit_text(
                    messages.get_message('moderation', 'already_processed'),
                    parse_mode='HTML'
                )
                await state.clear()
                return

            announcement = result

            # Уведомляем пользователя
            await self._notify_user_rejection(message, announcement, comment)

            # Уведомляем других модераторов
            await self._notify_other_moderators_rejection(message, moderator_id, comment, announcement)

            await message.answer(
                messages.get_message('moderation', 'rejected_by_moderator',
                                     announcement_id=announcement_id,
                                     moderator_id=moderator_id,
                                     comment=comment,
                                     bot_name=announcement['bot_name']),
                parse_mode='HTML',
                reply_markup=self._create_contact_keyboard(announcement['chat_id'])
            )

        except Exception as e:
            await message.answer(
                messages.get_message('moderation', 'rejection_error', error=str(e)),
                parse_mode='HTML'
            )

        await state.clear()


    async def contact_user(self, callback: CallbackQuery, state: FSMContext):
        """
        Начало процесса связи с пользователем.
        
        Args:
            callback: Объект обратного вызова
            state: Контекст состояния FSM
        """
        if not await self.check_permissions(callback.from_user.id, self.moderator_ids):
            await callback.answer(messages.get_message('contact', 'no_permissions'))
            return

        await callback.message.answer(
            messages.get_message('contact', 'enter_announcement_id'),
            parse_mode='HTML'
        )
        await state.set_state(ModerationForm.comment)
        await callback.answer()


    async def process_contact_user(self, message: Message, state: FSMContext):
        """
        Обработка запроса на связь с пользователем.
        
        Args:
            message: Объект сообщения
            state: Контекст состояния FSM
        """
        try:
            announcement_id = int(message.text)

            # Используем безопасную операцию с БД
            announcement = self.safe_db_operation(
                self._get_announcement_for_contact,
                announcement_id
            )

            if not announcement:
                await message.answer(
                    messages.get_message('moderation', 'announcement_not_found'),
                    parse_mode='HTML'
                )
                await state.clear()
                return

            await message.answer(
                messages.get_message('contact', 'announcement_info_template',
                                     bot_name=announcement['bot_name'],
                                     bot_function=announcement['bot_function']),
                parse_mode='HTML',
                reply_markup=InlineKeyboardMarkup(
                    inline_keyboard=[
                        [InlineKeyboardButton(
                            text=messages.get_button_text('moderation', 'contact'),
                            url=f"tg://user?id={announcement['chat_id']}"
                        )]
                    ]
                )
            )

        except ValueError:
            await message.answer(messages.get_message('contact', 'invalid_id'))
        except Exception as e:
            await message.answer(messages.get_message('contact', 'contact_error', error=str(e)))

        await state.clear()


    @staticmethod
    async def back_to_menu(callback: CallbackQuery):
        """
        Обработчик кнопки 'В меню'.
        
        Args:
            callback: Объект обратного вызова
        """
        try:
            start_handler = StartHandler()
            await start_handler.show_main_menu(callback.message)
            await callback.answer()

        except Exception as e:
            logger.error(f"Error displaying main menu: {str(e)}")
            try:
                await callback.message.answer(
                    messages.get_message('moderation', 'general_error', error=str(e)),
                    parse_mode='HTML'
                )
            except Exception as answer_error:
                logger.error(f"Failed to send error message: {answer_error}")


    def _approve_announcement_in_db(self, session, announcement_id: int, moderator_id: int):
        """
        Одобрение объявления в БД.
        
        Args:
            session: Сессия базы данных
            announcement_id: ID объявления
            moderator_id: ID модератора
            
        Returns:
            Словарь с данными объявления или информацией об ошибке
        """
        announcement = self.get_announcement_by_id(session, announcement_id)
        if not announcement:
            return None

        if hasattr(announcement, 'is_processed') and announcement.is_processed:
            return {'already_processed': True}
        elif hasattr(announcement, 'moderator_id') and announcement.moderator_id is not None:
            return {'already_processed': True}

        announcement.is_approved = True
        announcement.moderator_id = moderator_id

        # Возвращаем данные объявления
        return {
            'id': announcement.id,
            'chat_id': announcement.chat_id,
            'user_id': announcement.user_id,
            'bot_name': announcement.bot_name,
            'bot_function': announcement.bot_function,
            'solution_description': announcement.solution_description,
            'included_features': announcement.included_features,
            'client_requirements': announcement.client_requirements,
            'launch_time': announcement.launch_time,
            'price': announcement.price,
            'complexity': announcement.complexity,
            'created_at': announcement.created_at
        }


    def _reject_announcement_in_db(self, session, announcement_id: int, moderator_id: int, comment: str):
        """
        Отклонение объявления в БД.
        
        Args:
            session: Сессия базы данных
            announcement_id: ID объявления
            moderator_id: ID модератора
            comment: Комментарий модератора
            
        Returns:
            Словарь с данными объявления или информацией об ошибке
        """
        announcement = self.get_announcement_by_id(session, announcement_id)
        if not announcement:
            return None
        
        if hasattr(announcement, 'is_processed') and announcement.is_processed:
            return {'already_processed': True}
        elif hasattr(announcement, 'moderator_id') and announcement.moderator_id is not None:
            return {'already_processed': True}
        
        announcement.is_approved = False
        announcement.moderator_id = moderator_id
        announcement.comment = comment
        
        # Возвращаем данные объявления
        return {
            'id': announcement.id,
            'chat_id': announcement.chat_id,
            'bot_name': announcement.bot_name,
            'bot_function': announcement.bot_function,
            'created_at': announcement.created_at
        }


    def _get_announcement_for_rejection(self, session, announcement_id: int):
        """
        Получение объявления для отклонения.
        
        Args:
            session: Сессия базы данных
            announcement_id: ID объявления
            
        Returns:
            Словарь с данными объявления или None
        """
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
            'is_pending': announcement.is_pending(),
            'created_at': announcement.created_at
        }


    def _get_announcement_for_contact(self, session, announcement_id: int):
        """
        Получение объявления для связи с пользователем.
        
        Args:
            session: Сессия базы данных
            announcement_id: ID объявления
            
        Returns:
            Словарь с данными объявления или None
        """
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


    @staticmethod
    async def _notify_user_approval(message: Message, announcement: dict):
        """
        Уведомление пользователя об одобрении объявления.
        
        Args:
            message: Объект сообщения
            announcement: Словарь с данными объявления
        """
        try:
            # Создаем клавиатуру с кнопкой "В меню"
            keyboard = InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(
                        text=messages.get_button_text('moderation', 'back_to_menu'),
                        callback_data='main_menu'
                    )]
                ]
            )

            # Отправляем уведомление с клавиатурой
            await message.bot.send_message(
                announcement['chat_id'],
                messages.get_message('moderation', 'approval_notification', bot_name=announcement['bot_name']),
                reply_markup=keyboard,
                parse_mode='HTML'
            )

        except Exception as e:
            await message.answer(
                messages.get_message('moderation', 'general_error', error=str(e)),
                parse_mode='HTML'
            )


    @staticmethod
    async def _notify_user_rejection(message: Message, announcement: dict, comment: str):
        """
        Уведомление пользователя об отклонении.
        
        Args:
            message: Объект сообщения
            announcement: Словарь с данными объявления
            comment: Комментарий модератора
        """
        try:
            await message.bot.send_message(
                announcement['chat_id'],
                messages.get_message('moderation', 'rejection_notification',
                                   announcement_id=announcement.get('id'),
                                   bot_name=announcement.get('bot_name'),
                                   comment=comment),
                parse_mode='HTML'
            )
        except Exception as e:
            print(f"Не удалось уведомить пользователя об отклонении: {e}")


    async def _notify_other_moderators(self, callback: CallbackQuery, moderator_id: int, approved: bool, announcement: dict):
        """
        Уведомление других модераторов.
        
        Args:
            callback: Объект обратного вызова
            moderator_id: ID модератора
            approved: Флаг одобрения
            announcement: Словарь с данными объявления
        """
        message_key = 'approved_by_moderator' if approved else 'rejected_by_moderator'

        for mod_id in self.moderator_ids:
            if mod_id != moderator_id:
                try:
                    await callback.message.bot.send_message(
                        mod_id,
                        messages.get_message('moderation', message_key, 
                                           moderator_id=moderator_id, 
                                           bot_name=announcement.get('bot_name')),
                        parse_mode='HTML'
                    )
                except Exception:
                    continue


    async def _notify_other_moderators_rejection(self, message: Message, moderator_id: int, comment: str, announcement: dict):
        """
        Уведомление других модераторов об отклонении.
        
        Args:
            message: Объект сообщения
            moderator_id: ID модератора
            comment: Комментарий модератора
            announcement: Словарь с данными объявления
        """
        for mod_id in self.moderator_ids:
            if mod_id != moderator_id:
                try:
                    await message.bot.send_message(
                        mod_id,
                        messages.get_message('moderation', 'rejected_by_moderator', 
                                           moderator_id=moderator_id, 
                                           comment=comment, 
                                           bot_name=announcement['bot_name']),
                        parse_mode='HTML'
                    )
                except Exception:
                    continue


    async def _update_moderator_message(self, callback: CallbackQuery, announcement: dict, approved: bool):
        """
        Обновление сообщения модератора.
        
        Args:
            callback: Объект обратного вызова
            announcement: Словарь с данными объявления
            approved: Флаг одобрения
        """
        if approved:
            await callback.message.edit_text(
                messages.get_message('moderation', 'moderator_approval_notification',
                                     bot_name=announcement['bot_name'],
                                     bot_function=announcement['bot_function'],
                                     solution_description=announcement['solution_description'],
                                     included_features=announcement['included_features'],
                                     client_requirements=announcement['client_requirements'],
                                     launch_time=announcement['launch_time'],
                                     price=announcement['price'],
                                     complexity=announcement['complexity'],
                                     user_info=f"Пользователь ID: {announcement['user_id']}",
                                     created_date=announcement['created_at']),

                parse_mode='HTML',
                reply_markup=self._create_contact_keyboard(announcement['chat_id'])
            )


    def _create_contact_keyboard(self, chat_id: int) -> InlineKeyboardMarkup:
        """
        Создание клавиатуры для связи с пользователем.
        
        Args:
            chat_id: ID чата пользователя
            
        Returns:
            Клавиатура для связи с пользователем
        """
        return InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text=messages.get_button_text('moderation', 'back_to_menu'), callback_data='main_menu')],
                [InlineKeyboardButton(text=messages.get_button_text('moderation', 'contact'), url=f"tg://user?id={chat_id}")]
            ]
        )
