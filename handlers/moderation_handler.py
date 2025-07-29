from aiogram import F
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from .base import BaseHandler, DatabaseMixin
from utils.messages import messages
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
        self.router.callback_query(F.data.startswith('approve_request_'))(self.approve_custom_request)
        self.router.callback_query(F.data.startswith('reject_request_'))(self.reject_custom_request)
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

            # Публикация объявления в чате
            await self._publish_to_chat(callback.message, announcement)

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
        Обработка комментария при отклонении объявления или заявки.

        Args:
            message: Объект сообщения
            state: Контекст состояния FSM
        """
        try:
            comment = message.text
            user_data = await state.get_data()
            moderator_id = user_data['moderator_id']
            is_request = user_data.get('is_request', False)

            if is_request:
                # Обработка отклонения заявки
                request_id = user_data['request_id']
                
                with self.get_db_session() as session:
                    # Обновляем статус заявки
                    custom_request = self.update_custom_request_status(session, request_id, False, moderator_id)

                    if not custom_request:
                        await message.answer(messages.get_message("moderation", "request", "not_found"))
                        await state.clear()
                        return

                    # Преобразуем в словарь для удобства
                    request_dict = {
                        'id': custom_request.id,
                        'user_id': custom_request.user_id,
                        'chat_id': custom_request.chat_id,
                        'business_description': custom_request.business_description,
                        'automation_task': custom_request.automation_task,
                        'budget': custom_request.budget,
                        'created_at': custom_request.created_at
                    }

                    # Уведомляем пользователя об отклонении
                await self._notify_user_request_rejection(message, request_dict, comment)

                # Уведомляем других модераторов
                await self._notify_other_moderators_request(
                    type('CallbackQuery', (),
                         {'message': message, 'from_user': type('User', (), {'id': moderator_id})})(),
                    moderator_id, False, request_dict
                )

                await message.answer(
                    messages.get_message(
                        "moderation", "request", "rejected_confirmation",
                        request_id=request_id,
                        comment=comment,
                        moderator_id=moderator_id
                    ),
                    parse_mode='HTML'
                )

            else:
                # Обработка отклонения объявления (существующий код)
                announcement_id = user_data['announcement_id']

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
            logger.error(f"Ошибка при обработке комментария отклонения: {e}")
            await message.answer(
                f"❌ Произошла ошибка: {str(e)}",
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
                                     task_solution=announcement['task_solution']),
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


    def get_chat_id(self):
        """
        Получение ID чата и топика для публикации.

        Returns:
            tuple: (chat_id, thread_id)
        """
        return getattr(Config, 'CHAT_ID'), getattr(Config, 'TOPIC_ID')


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
            'task_solution': announcement.task_solution,
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
            'task_solution': announcement.task_solution,
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
            'task_solution': announcement.task_solution,
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
            'chat_id': announcement.chat_id,
            'bot_name': announcement.bot_name,
            'task_solution': announcement.task_solution,
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
                                     task_solution=announcement['task_solution'],
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


    async def _publish_to_chat(self, message: Message, announcement: dict):
        """
        Публикация объявления в чате.

        Args:
            message: Объект сообщения
            announcement: Словарь с данными объявления
        """
        try:
            # Получаем ID чата и топика
            chat_id = getattr(Config, 'CHAT_ID')
            thread_id = getattr(Config, 'TOPIC_ID')
            
            if not chat_id:
                raise ValueError("CHAT_ID не указан в конфигурации")

            # Формируем красивое объявление для публикации в чате
            chat_announcement_text = f"""🤖 <b>{announcement['bot_name']}</b>

⚡ <b>Задача и решение:</b>
{announcement['task_solution']}

📦 <b>Включено:</b>
{announcement['included_features']}

📋 <b>Что нужно от клиента:</b>
{announcement['client_requirements']}

⏱️ <b>Срок запуска:</b>
{announcement['launch_time']}

💰 <b>Цена:</b>
{announcement['price']}

📊 <b>Сложность:</b>
{announcement['complexity']}

📅 <b>Дата создания:</b>
{announcement['created_at'].strftime('%d.%m.%Y')}"""

            # Создаем клавиатуру с кнопкой "Связаться с автором"
            keyboard = InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(
                        text="💬 Связаться с автором",
                        url=f"tg://user?id={announcement['user_id']}"
                    )]
                ]
            )

            # Публикуем текст объявления
            sent_message = await message.bot.send_message(
                chat_id=chat_id,
                text=chat_announcement_text,
                parse_mode='HTML',
                reply_markup=keyboard,
                message_thread_id=thread_id
            )

            # Если есть файлы, отправляем их
            if announcement.get('documents'):
                for doc in announcement['documents']:
                    try:
                        await message.bot.send_document(
                            chat_id=chat_id,
                            document=doc['file_id'],
                            reply_to_message_id=sent_message.message_id,
                            message_thread_id=thread_id
                        )
                    except Exception as e:
                        logger.error(f"Error sending document: {str(e)}")

            # Если есть видео, отправляем их
            if announcement.get('videos'):
                for video in announcement['videos']:
                    try:
                        await message.bot.send_video(
                            chat_id=chat_id,
                            video=video['file_id'],
                            reply_to_message_id=sent_message.message_id,
                            message_thread_id=thread_id
                        )
                    except Exception as e:
                        logger.error(f"Error sending video: {str(e)}")

            # Если есть демо-ссылка, отправляем её
            if announcement.get('demo_url'):
                try:
                    await message.bot.send_message(
                        chat_id=chat_id,
                        text=f"🌐 <b>Демо-версия:</b>\n{announcement['demo_url']}",
                        parse_mode='HTML',
                        reply_to_message_id=sent_message.message_id,
                        message_thread_id=thread_id
                    )
                except Exception as e:
                    logger.error(f"Error sending demo URL: {str(e)}")

        except Exception as e:
            logger.error(f"Ошибка публикации объявления в чат: {str(e)}")
            raise

    async def approve_custom_request(self, callback: CallbackQuery):
        """
        Одобрение заявки на индивидуальное решение.

        Args:
            callback: Объект обратного вызова
        """
        request_id = int(callback.data.split('_')[2])
        moderator_id = callback.from_user.id

        if not await self.check_permissions(moderator_id, self.moderator_ids):
            await callback.answer(messages.get_message("moderation", "request", "no_permissions"))
            return

        with self.get_db_session() as session:
            try:
                # Обновляем статус заявки
                custom_request = self.update_custom_request_status(session, request_id, True, moderator_id)
                
                if not custom_request:
                    await callback.answer(messages.get_message("moderation", "request", "not_found"))
                    return

                # Преобразуем в словарь для удобства
                request_dict = {
                    'id': custom_request.id,
                    'user_id': custom_request.user_id,
                    'chat_id': custom_request.chat_id,
                    'business_description': custom_request.business_description,
                    'automation_task': custom_request.automation_task,
                    'budget': custom_request.budget,
                    'created_at': custom_request.created_at
                }

                # Обновляем сообщение модератора
                await self._update_moderator_message_request(callback, request_dict, True)

                # Уведомляем пользователя об одобрении
                await self._notify_user_request_approval(callback.message, request_dict)

                # Уведомляем других модераторов
                await self._notify_other_moderators_request(callback, moderator_id, True, request_dict)

                # Публикуем в группу
                await self._publish_approved_request_to_group(callback.bot, request_dict)

                await callback.answer(messages.get_message("moderation", "request", "approval_success"))

            except Exception as e:
                logger.error(f"Ошибка при одобрении заявки: {e}")
                await callback.answer(messages.get_message("moderation", "request", "approval_error"))

    async def reject_custom_request(self, callback: CallbackQuery, state: FSMContext):
        """
        Отклонение заявки на индивидуальное решение.

        Args:
            callback: Объект обратного вызова
            state: Контекст состояния FSM
        """
        request_id = int(callback.data.split('_')[2])
        moderator_id = callback.from_user.id

        if not await self.check_permissions(moderator_id, self.moderator_ids):
            await callback.answer(messages.get_message("moderation", "request", "no_permissions"))
            return

        try:
            with self.get_db_session() as session:
                custom_request = self.get_custom_request_by_id(session, request_id)
                
                if not custom_request or custom_request.is_approved is not None:
                    await callback.answer(messages.get_message("moderation", "request", "not_found"))
                    return

            await callback.message.edit_text(
                messages.get_message("moderation", "request", "rejection_prompt"),
                parse_mode='HTML'
            )
            await state.set_state(ModerationForm.comment)
            await state.update_data(request_id=request_id, moderator_id=moderator_id, is_request=True)

        except Exception as e:
            await callback.message.answer(
                messages.get_message("moderation", "request", "rejection_error", error=str(e)),
                parse_mode='HTML'
            )

    async def _update_moderator_message_request(self, callback: CallbackQuery, request_dict: dict, approved: bool):
        """
        Обновление сообщения модератора для заявки.

        Args:
            callback: Объект обратного вызова
            request_dict: Словарь с данными заявки
            approved: Флаг одобрения
        """
        if approved:
            await callback.message.edit_text(
                messages.get_message(
                    "moderation", "request", "approved_status",
                    request_id=request_dict['id'],
                    user_id=request_dict['user_id'],
                    business_description=request_dict['business_description'],
                    automation_task=request_dict['automation_task'],
                    budget=request_dict['budget'],
                    created_at=request_dict['created_at'].strftime('%d.%m.%Y %H:%M')
                ),
                parse_mode='HTML',
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(
                        text=messages.get_message("moderation", "request", "buttons", "contact_client"),
                        url=f"tg://user?id={request_dict['user_id']}"
                    )]
                ])
            )

    async def _notify_user_request_approval(self, message: Message, request_dict: dict):
        """
        Уведомление пользователя об одобрении заявки.

        Args:
            message: Объект сообщения
            request_dict: Словарь с данными заявки
        """
        try:
            keyboard = InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(
                        text=messages.get_message("moderation", "request", "buttons", "main_menu"),
                        callback_data='main_menu'
                    )]
                ]
            )

            business_short = request_dict['business_description'][:100] + ('...' if len(request_dict['business_description']) > 100 else '')
            task_short = request_dict['automation_task'][:100] + ('...' if len(request_dict['automation_task']) > 100 else '')

            await message.bot.send_message(
                request_dict['chat_id'],
                messages.get_message(
                    "moderation", "request", "user_approval",
                    request_id=request_dict['id'],
                    business_description_short=business_short,
                    automation_task_short=task_short
                ),
                reply_markup=keyboard,
                parse_mode='HTML'
            )

        except Exception as e:
            logger.error(f"Ошибка при уведомлении пользователя об одобрении заявки: {e}")

    async def _notify_user_request_rejection(self, message: Message, request_dict: dict, comment: str):
        """
        Уведомление пользователя об отклонении заявки.

        Args:
            message: Объект сообщения
            request_dict: Словарь с данными заявки
            comment: Комментарий модератора
        """
        try:
            business_short = request_dict['business_description'][:100] + ('...' if len(request_dict['business_description']) > 100 else '')
            task_short = request_dict['automation_task'][:100] + ('...' if len(request_dict['automation_task']) > 100 else '')

            await message.bot.send_message(
                request_dict['chat_id'],
                messages.get_message(
                    "moderation", "request", "user_rejection",
                    request_id=request_dict['id'],
                    business_description_short=business_short,
                    automation_task_short=task_short,
                    comment=comment
                ),
                parse_mode='HTML'
            )
        except Exception as e:
            logger.error(f"Ошибка при уведомлении пользователя об отклонении заявки: {e}")

    async def _notify_other_moderators_request(self, callback: CallbackQuery, moderator_id: int, approved: bool,
                                               request_dict: dict):
        """
        Уведомление других модераторов о решении по заявке.

        Args:
            callback: Объект обратного вызова
            moderator_id: ID модератора
            approved: Флаг одобрения
            request_dict: Словарь с данными заявки
        """
        status = "✅ Одобрена" if approved else "❌ Отклонена"
        business_short = request_dict['business_description'][:50] + "..."

        message_text = messages.get_message(
            "moderation", "request", "moderator_notification",
            status=status,
            request_id=request_dict['id'],
            moderator_id=moderator_id,
            business_description_short=business_short
        )

        for mod_id in self.moderator_ids:
            if mod_id != moderator_id:
                try:
                    await callback.message.bot.send_message(
                        mod_id,
                        message_text,
                        parse_mode='HTML'
                    )
                except Exception:
                    continue

    async def _publish_approved_request_to_group(self, bot, request_dict: dict):
        """
        Публикация одобренной заявки в группу.

        Args:
            bot: Объект бота
            request_dict: Словарь с данными заявки
        """
        try:
            # Получаем ID чата и топика
            chat_id = getattr(Config, 'CHAT_ID')
            thread_id = getattr(Config, 'TOPIC_ID_CUSTOM')
            
            if not chat_id:
                raise ValueError("CHAT_ID не указан в конфигурации")

            # Формируем красивое объявление для публикации в чате
            chat_announcement_text = f"""🤖 <b>Заявка на индивидуальное решение</b>

⚡ <b>Описание бизнеса:</b>
{request_dict['business_description']}

📦 <b>Задача автоматизации:</b>
{request_dict['automation_task']}

💰 <b>Бюджет:</b>
{request_dict['budget']}

📅 <b>Дата создания:</b>
{request_dict['created_at'].strftime('%d.%m.%Y')}"""

            # Создаем клавиатуру с кнопкой "Связаться с автором"
            keyboard = InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(
                        text="💬 Связаться с автором",
                        url=f"tg://user?id={request_dict['user_id']}"
                    )]
                ]
            )

            # Публикуем текст объявления
            await bot.send_message(
                chat_id=chat_id,
                text=chat_announcement_text,
                parse_mode='HTML',
                reply_markup=keyboard,
                message_thread_id=thread_id
            )

        except Exception as e:
            logger.error(f"Ошибка публикации заявки в группу: {str(e)}")
            raise
