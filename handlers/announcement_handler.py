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
    solution_description = State()
    included_features = State()
    client_requirements = State()
    launch_time = State()
    price = State()
    complexity = State()


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
        self.router.message(AnnouncementForm.solution_description)(self.process_solution_description)
        self.router.message(AnnouncementForm.included_features)(self.process_included_features)
        self.router.message(AnnouncementForm.client_requirements)(self.process_client_requirements)
        self.router.message(AnnouncementForm.launch_time)(self.process_launch_time)
        self.router.message(AnnouncementForm.price)(self.process_price)
        self.router.callback_query(F.data.startswith("complexity_"))(self.process_complexity)
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
        """Обработка функционала бота"""
        try:
            await state.update_data(bot_function=message.text)

            # Создаем кнопку отмены
            cancel_keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(
                    text=messages.get_message('announcement_creation', 'buttons', 'cancel'),
                    callback_data="cancel_announcement"
                )]
            ])

            await message.answer(
                messages.get_message('announcement_creation', 'enter_solution_description'),
                parse_mode='HTML',
                reply_markup=cancel_keyboard
            )
            await state.set_state(AnnouncementForm.solution_description)

        except Exception as e:
            await self.send_error_message(message, 'general_error', error=str(e))

    async def process_solution_description(self, message: Message, state: FSMContext):
        """Обработка описания функционала"""
        try:
            await state.update_data(solution_description=message.text)

            # Создаем кнопку отмены
            cancel_keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(
                    text=messages.get_message('announcement_creation', 'buttons', 'cancel'),
                    callback_data="cancel_announcement"
                )]
            ])

            await message.answer(
                messages.get_message('announcement_creation', 'enter_included_features'),
                parse_mode='HTML',
                reply_markup=cancel_keyboard
            )
            await state.set_state(AnnouncementForm.included_features)

        except Exception as e:
            await self.send_error_message(message, 'general_error', error=str(e))

    async def process_included_features(self, message: Message, state: FSMContext):
        """Обработка списка включенных возможностей"""
        try:
            await state.update_data(included_features=message.text)

            # Создаем кнопку отмены
            cancel_keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(
                    text=messages.get_message('announcement_creation', 'buttons', 'cancel'),
                    callback_data="cancel_announcement"
                )]
            ])

            await message.answer(
                messages.get_message('announcement_creation', 'enter_client_requirements'),
                parse_mode='HTML',
                reply_markup=cancel_keyboard
            )
            await state.set_state(AnnouncementForm.client_requirements)

        except Exception as e:
            await self.send_error_message(message, 'general_error', error=str(e))

    async def process_client_requirements(self, message: Message, state: FSMContext):
        """Обработка списка требований к клиенту"""
        try:
            await state.update_data(client_requirements=message.text)

            # Создаем кнопку отмены
            cancel_keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(
                    text=messages.get_message('announcement_creation', 'buttons', 'cancel'),
                    callback_data="cancel_announcement"
                )]
            ])

            await message.answer(
                messages.get_message('announcement_creation', 'enter_launch_time'),
                parse_mode='HTML',
                reply_markup=cancel_keyboard
            )
            await state.set_state(AnnouncementForm.launch_time)

        except Exception as e:
            await self.send_error_message(message, 'general_error', error=str(e))

    async def process_launch_time(self, message: Message, state: FSMContext):
        """Обработка срока запуска"""
        try:
            await state.update_data(launch_time=message.text)

            # Создаем кнопку отмены
            cancel_keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(
                    text=messages.get_message('announcement_creation', 'buttons', 'cancel'),
                    callback_data="cancel_announcement"
                )]
            ])

            await message.answer(
                messages.get_message('announcement_creation', 'enter_price'),
                parse_mode='HTML',
                reply_markup=cancel_keyboard
            )
            await state.set_state(AnnouncementForm.price)

        except Exception as e:
            await self.send_error_message(message, 'general_error', error=str(e))

    async def process_price(self, message: Message, state: FSMContext):
        """Обработка цены"""
        try:
            # Проверяем, что цена не содержит "по договоренности"
            if "по договоренности" in message.text.lower():
                await message.answer(
                    '❌ Нельзя указывать "по договоренности". Пожалуйста, укажите конкретную цену.',
                    parse_mode='HTML'
                )
                return

            await state.update_data(price=message.text)

            # Создаем инлайн-кнопки для выбора сложности
            complexity_keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="🟢 Низкая — без интеграций",
                        callback_data="complexity_low"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="🟡 Средняя — нужны шаблоны, но без API",
                        callback_data="complexity_medium"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="🔴 Высокая — глубокая кастомизация, CRM, интеграции",
                        callback_data="complexity_high"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="❌ Отмена",
                        callback_data="cancel_announcement"
                    )
                ]
            ])

            await message.answer(
                messages.get_message('announcement_creation', 'enter_complexity'),
                parse_mode='HTML',
                reply_markup=complexity_keyboard
            )
            await state.set_state(AnnouncementForm.complexity)

        except Exception as e:
            await self.send_error_message(message, 'general_error', error=str(e))

    async def process_complexity(self, callback_query: CallbackQuery, state: FSMContext):
        """Обработка выбора сложности"""
        try:
            # Получаем значение сложности из callback_data
            complexity = callback_query.data.replace("complexity_", "")

            # Преобразуем в человекочитаемый формат
            complexity_map = {
                "low": "🟢 Низкая — без интеграций",
                "medium": "🟡 Средняя — нужны шаблоны, но без API",
                "high": "🔴 Высокая — глубокая кастомизация, CRM, интеграции"
            }

            await state.update_data(complexity=complexity_map[complexity])

            # Получаем данные из состояния
            data = await state.get_data()
            bot_name = data.get('bot_name')
            bot_function = data.get('bot_function')
            solution_description = data.get('solution_description')
            included_features = data.get('included_features')
            client_requirements = data.get('client_requirements')
            launch_time = data.get('launch_time')
            price = data.get('price')
            complexity = data.get('complexity')

            # Создание объявления через безопасную операцию с БД
            announcement = self.safe_db_operation(
                self._create_announcement_in_db,
                callback_query.from_user.id,
                callback_query.message.chat.id,
                bot_name,
                bot_function,
                solution_description,
                included_features,
                client_requirements,
                launch_time,
                price,
                complexity
            )

            # Уведомление модераторов
            await self._notify_moderators(callback_query.message, announcement)

            # Уведомление пользователя
            await callback_query.message.answer(
                messages.get_message('announcement_creation', 'announcement_sent',
                                   announcement_id=announcement['id']),
                parse_mode='HTML'
            )

            await state.clear()

        except Exception as e:
            await callback_query.message.answer(
                messages.get_message('announcement_creation', 'save_error', error=str(e)),
                parse_mode='HTML'
            )
            await state.clear()

    async def cancel_announcement(self, callback_query: CallbackQuery, state: FSMContext):
        """Отмена создания объявления"""
        try:
            await state.clear()
            await callback_query.message.answer(
                messages.get_message('announcement_creation', 'cancelled'),
                parse_mode='HTML'
            )
        except Exception as e:
            await self.send_error_message(callback_query.message, 'general_error', error=str(e))

    def _create_announcement_in_db(self, session, user_id: int, chat_id: int,
                                       bot_name: str, bot_function: str, solution_description: str,
                                       included_features: str, client_requirements: str,
                                       launch_time: str, price: str, complexity: str) -> dict:
        """Создание объявления в базе данных"""
        announcement = self.create_announcement(session, user_id, chat_id, bot_name, bot_function,
                                              solution_description, included_features, client_requirements,
                                              launch_time, price, complexity)
        # Возвращаем словарь с данными вместо объекта
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
                solution_description=announcement.get('solution_description', 'unknown'),
                included_features=announcement.get('included_features', 'unknown'),
                client_requirements=announcement.get('client_requirements', 'unknown'),
                launch_time=announcement.get('launch_time', 'unknown'),
                price=announcement.get('price', 'unknown'),
                complexity=announcement.get('complexity', 'unknown'),
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
