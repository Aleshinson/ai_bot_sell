from aiogram import F
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from .base import BaseHandler, DatabaseMixin
from database.models import Announcement
from utils import messages
from config import Config
from typing import List


class ModerationForm(StatesGroup):
    """Состояния формы модерации"""
    comment = State()


class ModerationHandler(BaseHandler, DatabaseMixin):
    """Обработчик модерации объявлений"""

    def __init__(self):
        self.moderator_ids: List[int] = getattr(Config, 'MODERATOR_IDS', [454590867, 591273485, 1146006262])
        super().__init__()

    def setup_handlers(self):
        """Настройка обработчиков"""
        self.router.callback_query(F.data.startswith("approve_"))(self.approve_announcement)
        self.router.callback_query(F.data.startswith("reject_"))(self.reject_announcement)
        self.router.message(ModerationForm.comment)(self.process_rejection_comment)

    async def approve_announcement(self, callback: CallbackQuery):
        """Одобрение объявления"""
        announcement_id = int(callback.data.split("_")[1])
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
            await self._notify_other_moderators(callback, announcement_id, moderator_id, approved=True)

            # Обновление сообщения модератора
            await self._update_moderator_message(callback, announcement, approved=True)

        except Exception as e:
            await callback.message.answer(
                messages.get_message('moderation', 'approval_error', error=str(e)),
                parse_mode='HTML'
            )

        await callback.answer()

    async def reject_announcement(self, callback: CallbackQuery, state: FSMContext):
        """Начало процесса отклонения объявления"""
        announcement_id = int(callback.data.split("_")[1])
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
                await callback.message.answer(
                    messages.get_message('moderation', 'announcement_not_found'),
                    parse_mode='HTML'
                )
                return
            
            if not announcement['is_pending']:
                await callback.message.answer(
                    messages.get_message('moderation', 'already_processed'),
                    parse_mode='HTML'
                )
                return
            
            await callback.message.answer(
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
                await message.answer(
                    messages.get_message('moderation', 'announcement_not_found'),
                    parse_mode='HTML'
                )
                await state.clear()
                return

            if result.get('already_processed'):
                await message.answer(
                    messages.get_message('moderation', 'already_processed'),
                    parse_mode='HTML'
                )
                await state.clear()
                return

            announcement = result

            # Уведомляем пользователя
            await self._notify_user_rejection(message, announcement, comment)

            # Уведомляем других модераторов
            await self._notify_other_moderators_rejection(message, announcement_id, moderator_id, comment)

            await message.answer(
                messages.get_message('moderation', 'rejected_by_moderator',
                                     announcement_id=announcement_id,
                                     moderator_id=moderator_id,
                                     comment=comment),
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
        """Начало процесса связи с пользователем"""
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
        """Обработка запроса на связь с пользователем"""
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

    # Приватные методы для работы с БД
    def _approve_announcement_in_db(self, session, announcement_id: int, moderator_id: int):
        """Одобрение объявления в БД"""
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
            'bot_name': announcement.bot_name,
            'bot_function': announcement.bot_function,
            'created_at': announcement.created_at
        }
    
    def _reject_announcement_in_db(self, session, announcement_id: int, moderator_id: int, comment: str):
        """Отклонение объявления в БД"""
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
        """Получение объявления для отклонения"""
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
        """Получение объявления для связи с пользователем"""
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

    # Приватные методы для уведомлений
    async def _notify_user_approval(self, message: Message, announcement: dict):
        """Уведомление пользователя об одобрении"""
        try:
            # Создаем кнопку "В меню"
            menu_keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(
                    text=messages.get_message('navigation', 'buttons', 'back_to_menu'),
                    callback_data="back_to_menu"
                )]
            ])
            
            await message.bot.send_message(
                announcement['chat_id'],
                messages.get_message('moderation', 'approval_notification',
                                   announcement_id=announcement['id'],
                                   bot_name=announcement.get('bot_name', 'Unknown'),
                                   bot_function=announcement.get('bot_function', 'Not specified')),
                parse_mode='HTML',
                reply_markup=menu_keyboard
            )
        except Exception as e:
            print(f"Failed to notify user about approval: {e}")

    async def _notify_user_rejection(self, message: Message, announcement: dict, comment: str):
        """Уведомление пользователя об отклонении"""
        try:
            # Создаем кнопку "В меню"
            menu_keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(
                    text=messages.get_message('navigation', 'buttons', 'back_to_menu'),
                    callback_data="back_to_menu"
                )]
            ])
            
            await message.bot.send_message(
                announcement['chat_id'],
                messages.get_message('moderation', 'rejection_notification',
                                   announcement_id=announcement.get('id', 'unknown'),
                                   bot_name=announcement.get('bot_name', 'Неизвестно'),
                                   comment=comment),
                parse_mode='HTML',
                reply_markup=menu_keyboard
            )
        except Exception as e:
            print(f"Не удалось уведомить пользователя об отклонении: {e}")

    async def _notify_other_moderators(self, callback: CallbackQuery, announcement_id: int,
                                     moderator_id: int, approved: bool):
        """Уведомление других модераторов"""
        message_key = 'approved_by_moderator' if approved else 'rejected_by_moderator'

        for mod_id in self.moderator_ids:
            if mod_id != moderator_id:
                try:
                    await callback.message.bot.send_message(
                        mod_id,
                        messages.get_message('moderation', message_key,
                                           announcement_id=announcement_id,
                                           moderator_id=moderator_id),
                        parse_mode='HTML'
                    )
                except Exception:
                    continue

    async def _notify_other_moderators_rejection(self, message: Message, announcement_id: int,
                                               moderator_id: int, comment: str):
        """Уведомление других модераторов об отклонении"""
        for mod_id in self.moderator_ids:
            if mod_id != moderator_id:
                try:
                    await message.bot.send_message(
                        mod_id,
                        messages.get_message('moderation', 'rejected_by_moderator',
                                           announcement_id=announcement_id,
                                           moderator_id=moderator_id,
                                           comment=comment),
                        parse_mode='HTML'
                    )
                except Exception:
                    continue

    async def _update_moderator_message(self, callback: CallbackQuery, announcement: dict, approved: bool):
        """Обновление сообщения модератора"""
        if approved:
            await callback.message.edit_text(
                messages.get_message('moderation', 'approval_notification',
                                   announcement_id=announcement['id'],
                                   bot_name=announcement.get('bot_name', 'Unknown'),
                                   bot_function=announcement.get('bot_function', 'Not specified')),
                parse_mode='HTML',
                reply_markup=self._create_contact_keyboard(announcement['chat_id'])
            )

    def _create_contact_keyboard(self, chat_id: int) -> InlineKeyboardMarkup:
        """Создание клавиатуры для связи с пользователем"""
        return InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(
                    text=messages.get_button_text('moderation', 'contact'),
                    url=f"tg://user?id={chat_id}"
                )]
            ]
        )
