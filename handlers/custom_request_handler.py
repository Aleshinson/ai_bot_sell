from aiogram import F
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from .base import BaseHandler, DatabaseMixin
from database.models import CustomRequest
from config import Config
from utils.messages import messages
import logging

logger = logging.getLogger(__name__)


class CustomRequestForm(StatesGroup):
    """Состояния формы заявки на индивидуальное решение."""
    business_description = State()
    automation_task = State()
    budget = State()


class CustomRequestHandler(BaseHandler, DatabaseMixin):
    """Обработчик заявок на индивидуальные решения."""

    def setup_handlers(self):
        """Настройка обработчиков."""
        self.router.callback_query.register(
            self.start_custom_request,
            F.data == "custom_request"
        )
        self.router.message.register(
            self.process_business_description,
            CustomRequestForm.business_description
        )
        self.router.message.register(
            self.process_automation_task,
            CustomRequestForm.automation_task
        )
        self.router.message.register(
            self.process_budget,
            CustomRequestForm.budget
        )
        self.router.callback_query.register(
            self.set_budget_undefined,
            F.data == "budget_undefined"
        )
        self.router.callback_query.register(
            self.cancel_custom_request,
            F.data == "cancel_custom_request"
        )

    async def start_custom_request(self, callback: CallbackQuery, state: FSMContext):
        """
        Начало заполнения заявки на индивидуальное решение.

        Args:
            callback: Объект обратного вызова
            state: Контекст состояния FSM
        """
        try:
            await callback.answer()
            
            # Устанавливаем состояние для ввода описания бизнеса
            await state.set_state(CustomRequestForm.business_description)
            
            # Отправляем сообщение с инструкцией
            await callback.message.edit_text(
                messages.get_message("custom_request", "start", "message"),
                parse_mode='HTML',
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(
                        text=messages.get_message("custom_request", "start", "buttons", "cancel"), 
                        callback_data="cancel_custom_request"
                    )]
                ])
            )
            
            # Сохраняем ID сообщения бота для дальнейшего редактирования
            await state.update_data(bot_message_id=callback.message.message_id)
            
        except Exception as e:
            logger.error(f"Ошибка при начале заявки: {e}")
            await callback.answer(messages.get_message("custom_request", "budget_undefined", "error"))

    async def process_business_description(self, message: Message, state: FSMContext):
        """
        Обработка описания бизнеса.

        Args:
            message: Объект сообщения
            state: Контекст состояния FSM
        """
        try:
            business_description = message.text.strip()
            
            if len(business_description) < 10:
                await message.answer(
                    messages.get_message("custom_request", "business_description", "error_too_short")
                )
                return
            
            # Сохраняем описание бизнеса
            await state.update_data(business_description=business_description)
            
            # Переходим к следующему шагу
            await state.set_state(CustomRequestForm.automation_task)
            
            # Получаем данные состояния
            data = await state.get_data()
            bot_message_id = data.get('bot_message_id')
            
            # Удаляем сообщение пользователя
            try:
                await message.delete()
            except Exception:
                pass  # Игнорируем ошибки удаления
            
            # Редактируем сообщение бота
            if bot_message_id:
                await message.bot.edit_message_text(
                    chat_id=message.chat.id,
                    message_id=bot_message_id,
                    text=messages.get_message("custom_request", "business_description", "next_step"),
                    parse_mode='HTML',
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(
                            text=messages.get_message("custom_request", "start", "buttons", "cancel"), 
                            callback_data="cancel_custom_request"
                        )]
                    ])
                )
            
        except Exception as e:
            logger.error(f"Ошибка при обработке описания бизнеса: {e}")
            await message.answer(messages.get_message("custom_request", "business_description", "error"))

    async def process_automation_task(self, message: Message, state: FSMContext):
        """
        Обработка задачи автоматизации.

        Args:
            message: Объект сообщения
            state: Контекст состояния FSM
        """
        try:
            automation_task = message.text.strip()
            
            if len(automation_task) < 10:
                await message.answer(
                    messages.get_message("custom_request", "automation_task", "error_too_short")
                )
                return
            
            # Сохраняем задачу автоматизации
            await state.update_data(automation_task=automation_task)
            
            # Переходим к последнему шагу
            await state.set_state(CustomRequestForm.budget)
            
            # Получаем данные состояния
            data = await state.get_data()
            bot_message_id = data.get('bot_message_id')
            
            # Удаляем сообщение пользователя
            try:
                await message.delete()
            except Exception:
                pass  # Игнорируем ошибки удаления
            
            # Редактируем сообщение бота
            if bot_message_id:
                await message.bot.edit_message_text(
                    chat_id=message.chat.id,
                    message_id=bot_message_id,
                    text=messages.get_message("custom_request", "automation_task", "next_step"),
                    parse_mode='HTML',
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(
                            text=messages.get_message("custom_request", "automation_task", "buttons", "budget_undefined"), 
                            callback_data="budget_undefined"
                        )],
                        [InlineKeyboardButton(
                            text=messages.get_message("custom_request", "automation_task", "buttons", "cancel"), 
                            callback_data="cancel_custom_request"
                        )]
                    ])
                )
            
        except Exception as e:
            logger.error(f"Ошибка при обработке задачи автоматизации: {e}")
            await message.answer(messages.get_message("custom_request", "automation_task", "error"))

    async def process_budget(self, message: Message, state: FSMContext):
        """
        Обработка бюджета и сохранение заявки.

        Args:
            message: Объект сообщения
            state: Контекст состояния FSM
        """
        try:
            budget = message.text.strip()
            
            if len(budget) < 2:
                await message.answer(
                    messages.get_message("custom_request", "budget", "error_too_short")
                )
                return
            
            # Получаем все данные из состояния
            data = await state.get_data()
            bot_message_id = data.get('bot_message_id')
            
            # Сохраняем заявку в базу данных
            request_id = await self._save_custom_request(
                user_id=message.from_user.id,
                chat_id=message.chat.id,
                business_description=data['business_description'],
                automation_task=data['automation_task'],
                budget=budget,
                bot=message.bot
            )
            
            # Очищаем состояние
            await state.clear()
            
            # Подготавливаем данные для форматирования
            business_short = data['business_description'][:100] + ('...' if len(data['business_description']) > 100 else '')
            task_short = data['automation_task'][:100] + ('...' if len(data['automation_task']) > 100 else '')
            
            # Удаляем сообщение пользователя
            try:
                await message.delete()
            except Exception:
                pass  # Игнорируем ошибки удаления
            
            # Редактируем сообщение бота с подтверждением
            if bot_message_id:
                await message.bot.edit_message_text(
                    chat_id=message.chat.id,
                    message_id=bot_message_id,
                    text=messages.get_message(
                        "custom_request", "budget", "success",
                        business_description_short=business_short,
                        automation_task_short=task_short,
                        budget=budget
                    ),
                    parse_mode='HTML',
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(
                            text=messages.get_message("custom_request", "budget", "buttons", "main_menu"), 
                            callback_data="main_menu"
                        )]
                    ])
                )
            
        except Exception as e:
            logger.error(f"Ошибка при обработке бюджета: {e}")
            await message.answer(messages.get_message("custom_request", "budget", "error"))
            await state.clear()

    async def _save_custom_request(self, user_id: int, chat_id: int, business_description: str, 
                                 automation_task: str, budget: str, bot) -> int:
        """
        Сохранение заявки в базу данных и отправка на модерацию.

        Args:
            user_id: ID пользователя
            chat_id: ID чата
            business_description: Описание бизнеса
            automation_task: Задача автоматизации
            budget: Бюджет
            bot: Объект бота для отправки сообщений

        Returns:
            int: ID созданной заявки
        """
        with self.get_db_session() as session:
            try:
                custom_request = CustomRequest(
                    user_id=user_id,
                    chat_id=chat_id,
                    business_description=business_description,
                    automation_task=automation_task,
                    budget=budget
                )
                
                session.add(custom_request)
                session.commit()
                
                # Получаем ID созданной заявки
                session.refresh(custom_request)
                request_id = custom_request.id
                
                logger.info(f"Сохранена заявка от пользователя {user_id}, ID: {request_id}")
                
                # Отправляем уведомления модераторам
                await self._notify_moderators_about_request(
                    user_id, chat_id, business_description, 
                    automation_task, budget, request_id, 
                    custom_request.created_at, bot
                )
                
                return request_id
                
            except Exception as e:
                session.rollback()
                logger.error(f"Ошибка при сохранении заявки: {e}")
                raise

    async def _notify_moderators_about_request(self, user_id: int, chat_id: int,
                                             business_description: str, automation_task: str, 
                                             budget: str, request_id: int, created_at, bot):
        """
        Уведомление модераторов о новой заявке.

        Args:
            user_id: ID пользователя
            chat_id: ID чата
            business_description: Описание бизнеса
            automation_task: Задача автоматизации
            budget: Бюджет
            request_id: ID заявки
            created_at: Дата создания
            bot: Объект бота для отправки сообщений
        """
        try:
            moderator_ids = getattr(Config, 'MODERATOR_IDS')
            
            # Формируем сообщение для модераторов
            moderation_text = messages.get_message(
                "custom_request", "moderation", "new_request",
                request_id=request_id,
                user_id=user_id,
                business_description=business_description,
                automation_task=automation_task,
                budget=budget,
                created_at=created_at.strftime('%d.%m.%Y %H:%M')
            )
            
            # Создаем клавиатуру для модерации
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text=messages.get_message("custom_request", "moderation", "buttons", "approve"),
                        callback_data=f"approve_request_{request_id}"
                    ),
                    InlineKeyboardButton(
                        text=messages.get_message("custom_request", "moderation", "buttons", "reject"),
                        callback_data=f"reject_request_{request_id}"
                    )
                ]
            ])
            
            # Отправляем уведомления всем модераторам
            for moderator_id in moderator_ids:
                try:
                    await bot.send_message(
                        moderator_id,
                        moderation_text,
                        reply_markup=keyboard,
                        parse_mode='HTML'
                    )
                except Exception as e:
                    logger.error(f"Не удалось отправить уведомление модератору {moderator_id}: {e}")
                    continue
                    
        except Exception as e:
            logger.error(f"Ошибка при уведомлении модераторов: {e}")

    async def set_budget_undefined(self, callback: CallbackQuery, state: FSMContext):
        """
        Установка бюджета как "не определён".

        Args:
            callback: Объект обратного вызова
            state: Контекст состояния FSM
        """
        try:
            await callback.answer()
            
            # Получаем все данные из состояния
            data = await state.get_data()
            
            # Сохраняем заявку с неопределённым бюджетом
            request_id = await self._save_custom_request(
                user_id=callback.from_user.id,
                chat_id=callback.message.chat.id,
                business_description=data['business_description'],
                automation_task=data['automation_task'],
                budget="не определён",
                bot=callback.bot
            )
            
            # Очищаем состояние
            await state.clear()
            
            # Подготавливаем данные для форматирования
            business_short = data['business_description'][:100] + ('...' if len(data['business_description']) > 100 else '')
            task_short = data['automation_task'][:100] + ('...' if len(data['automation_task']) > 100 else '')
            
            # Редактируем сообщение бота с подтверждением
            await callback.message.edit_text(
                messages.get_message(
                    "custom_request", "budget_undefined", "success",
                    business_description_short=business_short,
                    automation_task_short=task_short
                ),
                parse_mode='HTML',
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(
                        text=messages.get_message("custom_request", "budget_undefined", "buttons", "main_menu"), 
                        callback_data="main_menu"
                    )]
                ])
            )
            
        except Exception as e:
            logger.error(f"Ошибка при установке неопределённого бюджета: {e}")
            await callback.answer(messages.get_message("custom_request", "budget_undefined", "error"))

    async def cancel_custom_request(self, callback: CallbackQuery, state: FSMContext):
        """
        Отмена заявки на индивидуальное решение.

        Args:
            callback: Объект обратного вызова
            state: Контекст состояния FSM
        """
        try:
            await callback.answer()
            await state.clear()
            
            await callback.message.edit_text(
                messages.get_message("custom_request", "cancel", "message"),
                parse_mode='HTML',
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(
                        text=messages.get_message("custom_request", "cancel", "buttons", "search"), 
                        callback_data="back_search"
                    )],
                    [InlineKeyboardButton(
                        text=messages.get_message("custom_request", "cancel", "buttons", "main_menu"), 
                        callback_data="main_menu"
                    )]
                ])
            )
            
        except Exception as e:
            logger.error(f"Ошибка при отмене заявки: {e}")
            await callback.answer(messages.get_message("custom_request", "cancel", "error"))
