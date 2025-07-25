from aiogram import F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from .base import BaseHandler, DatabaseMixin
from utils import messages
from config import Config
import os


class AnnouncementForm(StatesGroup):
    """Состояния формы создания объявления."""
    explanation_shown = State()
    template_shown = State()
    bot_name = State()
    task_solution = State()  # Combined state for task and solution
    included_features = State()
    client_requirements = State()
    launch_time = State()
    price = State()
    complexity = State()
    documents = State()
    edit_bot_name = State()
    edit_task_solution = State()  # Combined state for editing
    edit_included_features = State()
    edit_client_requirements = State()
    edit_launch_time = State()
    edit_price = State()
    edit_complexity = State()
    edit_documents = State()


class AnnouncementHandler(BaseHandler, DatabaseMixin):
    """Обработчик создания объявлений."""

    def __init__(self):
        """Инициализация обработчика объявлений."""
        self.moderator_ids = getattr(Config, 'MODERATOR_IDS')
        super().__init__()

    def setup_handlers(self):
        """Настройка обработчиков."""
        self.router.callback_query(F.data == 'add_announcement')(self.show_data_template)
        self.router.callback_query(F.data == 'next_step')(self.show_template)
        self.router.callback_query(F.data == 'start_filling')(self.start_announcement_creation)
        self.router.message(AnnouncementForm.bot_name)(self.process_bot_name)
        self.router.message(AnnouncementForm.task_solution)(self.process_task_solution)
        self.router.message(AnnouncementForm.included_features)(self.process_included_features)
        self.router.message(AnnouncementForm.client_requirements)(self.process_client_requirements)
        self.router.message(AnnouncementForm.launch_time)(self.process_launch_time)
        self.router.message(AnnouncementForm.price)(self.process_price)
        self.router.message(AnnouncementForm.complexity)(self.process_complexity)
        self.router.message(AnnouncementForm.documents)(self.process_documents)
        self.router.callback_query(F.data == "documents_done")(self.show_preview)
        # Обработчики навигации
        self.router.callback_query(F.data == "cancel_announcement")(self.cancel_announcement)
        self.router.callback_query(F.data.startswith("back_to_"))(self.handle_back_navigation)
        self.router.callback_query(F.data == "confirm_announcement")(self.confirm_announcement)
        # Обработчики редактирования
        self.router.callback_query(F.data == "edit_announcement")(self.show_edit_menu)
        self.router.callback_query(F.data.startswith("edit_field_"))(self.handle_edit_field)
        self.router.message(AnnouncementForm.edit_bot_name)(self.process_edit_bot_name)
        self.router.message(AnnouncementForm.edit_task_solution)(self.process_edit_task_solution)
        self.router.message(AnnouncementForm.edit_included_features)(self.process_edit_included_features)
        self.router.message(AnnouncementForm.edit_client_requirements)(self.process_edit_client_requirements)
        self.router.message(AnnouncementForm.edit_launch_time)(self.process_edit_launch_time)
        self.router.message(AnnouncementForm.edit_price)(self.process_edit_price)
        self.router.message(AnnouncementForm.edit_complexity)(self.process_edit_complexity)
        self.router.message(AnnouncementForm.edit_documents)(self.process_edit_documents)

    async def show_data_template(self, callback: CallbackQuery, state: FSMContext):
        """Показ объяснения перед шаблоном."""
        try:
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(
                    text=messages.get_message('announcement_creation', 'buttons', 'next_step'),
                    callback_data="next_step"
                )],
                [InlineKeyboardButton(
                    text=messages.get_message('announcement_creation', 'buttons', 'cancel'),
                    callback_data="cancel_announcement"
                )]
            ])

            await callback.message.edit_text(
                messages.get_message('announcement_creation', 'creation_explanation'),
                parse_mode='HTML',
                reply_markup=keyboard
            )
            await state.set_state(AnnouncementForm.explanation_shown)
            await callback.answer()

        except Exception as e:
            await self.send_error_message(callback, 'general_error', error=str(e))

    async def show_template(self, callback: CallbackQuery, state: FSMContext):
        """Показ шаблона после нажатия кнопки 'Следующий шаг'."""
        try:
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(
                    text=messages.get_message('announcement_creation', 'buttons', 'start_filling'),
                    callback_data="start_filling"
                )],
                [InlineKeyboardButton(
                    text=messages.get_message('announcement_creation', 'buttons', 'cancel'),
                    callback_data="cancel_announcement"
                )]
            ])

            await callback.message.edit_text(
                messages.get_message('announcement_creation', 'data_template'),
                parse_mode='HTML',
                reply_markup=keyboard
            )
            await state.set_state(AnnouncementForm.template_shown)
            await callback.answer()

        except Exception as e:
            await self.send_error_message(callback, 'general_error', error=str(e))

    async def start_announcement_creation(self, callback: CallbackQuery, state: FSMContext):
        """Начало создания объявления."""
        try:
            # Сохраняем ID сообщения для дальнейшего редактирования
            await state.update_data(message_id=callback.message.message_id)

            keyboard = self._create_navigation_keyboard("cancel_announcement")

            await callback.message.edit_text(
                messages.get_message('announcement_creation', 'enter_bot_name'),
                parse_mode='HTML',
                reply_markup=keyboard
            )
            await state.set_state(AnnouncementForm.bot_name)
            await callback.answer()

        except Exception as e:
            await self.send_error_message(callback, 'general_error', error=str(e))

    def _create_navigation_keyboard(self, back_action: str | None = None, additional_buttons: list | None = None):
        """Создание клавиатуры с навигацией."""
        buttons = []

        if additional_buttons:
            for row in additional_buttons:
                buttons.append(row)

        nav_row = []
        if back_action and back_action != "cancel_announcement":
            nav_row.append(InlineKeyboardButton(
                text=messages.get_message('announcement_creation', 'buttons', 'back'),
                callback_data=back_action
            ))

        nav_row.append(InlineKeyboardButton(
            text=messages.get_message('announcement_creation', 'buttons', 'cancel'),
            callback_data="cancel_announcement"
        ))

        buttons.append(nav_row)
        return InlineKeyboardMarkup(inline_keyboard=buttons)

    async def _edit_message_with_navigation(self, message: Message, text: str, state: FSMContext, back_action=None,
                                            additional_buttons=None):
        """Редактирование сообщения с навигацией."""
        keyboard = self._create_navigation_keyboard(back_action, additional_buttons)

        # Пытаемся отредактировать предыдущее сообщение
        try:
            # Удаляем сообщение пользователя
            await message.delete()
        except:
            pass

        # Получаем данные состояния для ID сообщения
        data = await state.get_data()

        if 'message_id' in data:
            try:
                await message.bot.edit_message_text(
                    chat_id=message.chat.id,
                    message_id=data['message_id'],
                    text=text,
                    parse_mode='HTML',
                    reply_markup=keyboard
                )
                return
            except:
                pass

        # Если редактирование не удалось, отправляем новое сообщение
        new_message = await message.answer(text, parse_mode='HTML', reply_markup=keyboard)
        await state.update_data(message_id=new_message.message_id)

    async def process_bot_name(self, message: Message, state: FSMContext):
        """Обработка названия бота."""
        try:
            await state.update_data(bot_name=message.text)

            await self._edit_message_with_navigation(
                message,
                messages.get_message('announcement_creation', 'enter_task_solution'),
                state,
                "back_to_bot_name"
            )
            await state.set_state(AnnouncementForm.task_solution)

        except Exception as e:
            await self.send_error_message(message, 'general_error', error=str(e))

    async def process_task_solution(self, message: Message, state: FSMContext):
        """Обработка задачи и решения."""
        try:
            await state.update_data(task_solution=message.text)

            await self._edit_message_with_navigation(
                message,
                messages.get_message('announcement_creation', 'enter_included_features'),
                state,
                "back_to_task_solution"
            )
            await state.set_state(AnnouncementForm.included_features)

        except Exception as e:
            await self.send_error_message(message, 'general_error', error=str(e))

    async def process_included_features(self, message: Message, state: FSMContext):
        """Обработка списка включенных возможностей."""
        try:
            await state.update_data(included_features=message.text)

            await self._edit_message_with_navigation(
                message,
                messages.get_message('announcement_creation', 'enter_client_requirements'),
                state,
                "back_to_included_features"
            )
            await state.set_state(AnnouncementForm.client_requirements)

        except Exception as e:
            await self.send_error_message(message, 'general_error', error=str(e))

    async def process_client_requirements(self, message: Message, state: FSMContext):
        """Обработка требований к клиенту."""
        try:
            await state.update_data(client_requirements=message.text)

            await self._edit_message_with_navigation(
                message,
                messages.get_message('announcement_creation', 'enter_launch_time'),
                state,
                "back_to_client_requirements"
            )
            await state.set_state(AnnouncementForm.launch_time)

        except Exception as e:
            await self.send_error_message(message, 'general_error', error=str(e))

    async def process_launch_time(self, message: Message, state: FSMContext):
        """Обработка срока запуска."""
        try:
            await state.update_data(launch_time=message.text)

            await self._edit_message_with_navigation(
                message,
                messages.get_message('announcement_creation', 'enter_price'),
                state,
                "back_to_launch_time"
            )
            await state.set_state(AnnouncementForm.price)

        except Exception as e:
            await self.send_error_message(message, 'general_error', error=str(e))

    async def process_price(self, message: Message, state: FSMContext):
        """Обработка цены."""
        try:
            await state.update_data(price=message.text)

            await self._edit_message_with_navigation(
                message,
                messages.get_message('announcement_creation', 'enter_complexity'),
                state,
                "back_to_price"
            )
            await state.set_state(AnnouncementForm.complexity)

        except Exception as e:
            await self.send_error_message(message, 'general_error', error=str(e))

    async def process_complexity(self, message: Message, state: FSMContext):
        """Обработка сложности."""
        try:
            await state.update_data(complexity=message.text)

            # Создаем кнопку "Готово" для документов
            documents_buttons = [
                [InlineKeyboardButton(
                    text=messages.get_message('announcement_creation', 'buttons', 'documents_done'),
                    callback_data="documents_done"
                )]
            ]

            await self._edit_message_with_navigation(
                message,
                messages.get_message('announcement_creation', 'enter_documents'),
                state,
                "back_to_complexity",
                documents_buttons
            )
            await state.set_state(AnnouncementForm.documents)

        except Exception as e:
            await self.send_error_message(message, 'general_error', error=str(e))

    async def show_edit_menu(self, callback: CallbackQuery, state: FSMContext):
        """Показ меню редактирования."""
        try:
            data = await state.get_data()
            documents_count = len(data.get('documents', [])) + len(data.get('videos', [])) + (
                1 if data.get('demo_url') else 0)

            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="🤖 Название",
                        callback_data="edit_field_bot_name"
                    ),
                    InlineKeyboardButton(
                        text="⚡ Задача и решение",
                        callback_data="edit_field_task_solution"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="📦 Решение включает в себя:",
                        callback_data="edit_field_included_features"
                    ),
                    InlineKeyboardButton(
                        text="📋 Требования",
                        callback_data="edit_field_client_requirements"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="⏱️ Срок",
                        callback_data="edit_field_launch_time"
                    ),
                    InlineKeyboardButton(
                        text="💰 Цена",
                        callback_data="edit_field_price"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="📊 Сложность",
                        callback_data="edit_field_complexity"
                    ),
                    InlineKeyboardButton(
                        text="📝 Материалы",
                        callback_data="edit_field_documents"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text=messages.get_message('announcement_creation', 'buttons', 'back'),
                        callback_data="back_to_preview"
                    ),
                    InlineKeyboardButton(
                        text=messages.get_message('announcement_creation', 'buttons', 'cancel'),
                        callback_data="cancel_announcement"
                    )
                ]
            ])

            await callback.message.edit_text(
                messages.get_message(
                    'announcement_creation', 'edit_menu',
                    bot_name=data.get('bot_name', 'Не указано'),
                    task_solution=data.get('task_solution', 'Не указано'),
                    included_features=data.get('included_features', 'Не указано'),
                    client_requirements=data.get('client_requirements', 'Не указано'),
                    launch_time=data.get('launch_time', 'Не указано'),
                    price=data.get('price', 'Не указано'),
                    documents_count=documents_count
                ),
                parse_mode='HTML',
                reply_markup=keyboard
            )
            await callback.answer()

        except Exception as e:
            await self.send_error_message(callback, 'general_error', error=str(e))

    async def handle_edit_field(self, callback: CallbackQuery, state: FSMContext):
        """Обработка выбора поля для редактирования."""
        try:
            field = callback.data.replace("edit_field_", "")
            data = await state.get_data()

            edit_map = {
                "bot_name": (AnnouncementForm.edit_bot_name, 'edit_bot_name_prompt', data.get('bot_name', '')),
                "task_solution": (AnnouncementForm.edit_task_solution, 'edit_task_solution_prompt', data.get('task_solution', '')),
                "included_features": (AnnouncementForm.edit_included_features, 'edit_included_features_prompt',
                                     data.get('included_features', '')),
                "client_requirements": (AnnouncementForm.edit_client_requirements, 'edit_client_requirements_prompt',
                                      data.get('client_requirements', '')),
                "launch_time": (AnnouncementForm.edit_launch_time, 'edit_launch_time_prompt', data.get('launch_time', '')),
                "price": (AnnouncementForm.edit_price, 'edit_price_prompt', data.get('price', '')),
                "complexity": (AnnouncementForm.edit_complexity, 'enter_complexity', data.get('complexity', '')),
                "documents": (AnnouncementForm.edit_documents, 'edit_documents_prompt', self._format_documents(data))
            }

            if field in edit_map:
                new_state, message_key, current_value = edit_map[field]

                additional_buttons = None
                if field == "documents":
                    additional_buttons = [
                        [InlineKeyboardButton(
                            text=messages.get_message('announcement_creation', 'buttons', 'documents_done'),
                            callback_data="documents_done"
                        )]
                    ]

                await callback.message.edit_text(
                    messages.get_message('announcement_creation', message_key, current_value=current_value),
                    parse_mode='HTML',
                    reply_markup=self._create_navigation_keyboard("back_to_edit_menu", additional_buttons)
                )
                await state.set_state(new_state)
                await callback.answer()

        except Exception as e:
            await self.send_error_message(callback, 'general_error', error=str(e))

    async def process_edit_bot_name(self, message: Message, state: FSMContext):
        """Обработка редактирования названия бота."""
        try:
            await state.update_data(bot_name=message.text)
            await self._edit_message_with_navigation(
                message,
                self._generate_preview_text(await state.get_data()),
                state,
                None,
                self._create_preview_buttons()
            )
            await state.set_state(AnnouncementForm.documents)

        except Exception as e:
            await self.send_error_message(message, 'general_error', error=str(e))

    async def process_edit_task_solution(self, message: Message, state: FSMContext):
        """Обработка редактирования задачи и решения."""
        try:
            await state.update_data(task_solution=message.text)
            await self._edit_message_with_navigation(
                message,
                self._generate_preview_text(await state.get_data()),
                state,
                None,
                self._create_preview_buttons()
            )
            await state.set_state(AnnouncementForm.documents)

        except Exception as e:
            await self.send_error_message(message, 'general_error', error=str(e))

    async def process_edit_included_features(self, message: Message, state: FSMContext):
        """Обработка редактирования списка включенных возможностей."""
        try:
            await state.update_data(included_features=message.text)
            await self._edit_message_with_navigation(
                message,
                self._generate_preview_text(await state.get_data()),
                state,
                None,
                self._create_preview_buttons()
            )
            await state.set_state(AnnouncementForm.documents)

        except Exception as e:
            await self.send_error_message(message, 'general_error', error=str(e))

    async def process_edit_client_requirements(self, message: Message, state: FSMContext):
        """Обработка редактирования требований к клиенту."""
        try:
            await state.update_data(client_requirements=message.text)
            await self._edit_message_with_navigation(
                message,
                self._generate_preview_text(await state.get_data()),
                state,
                None,
                self._create_preview_buttons()
            )
            await state.set_state(AnnouncementForm.documents)

        except Exception as e:
            await self.send_error_message(message, 'general_error', error=str(e))

    async def process_edit_launch_time(self, message: Message, state: FSMContext):
        """Обработка редактирования срока запуска."""
        try:
            await state.update_data(launch_time=message.text)
            await self._edit_message_with_navigation(
                message,
                self._generate_preview_text(await state.get_data()),
                state,
                None,
                self._create_preview_buttons()
            )
            await state.set_state(AnnouncementForm.documents)

        except Exception as e:
            await self.send_error_message(message, 'general_error', error=str(e))

    async def process_edit_price(self, message: Message, state: FSMContext):
        """Обработка редактирования цены."""
        try:
            await state.update_data(price=message.text)
            await self._edit_message_with_navigation(
                message,
                self._generate_preview_text(await state.get_data()),
                state,
                None,
                self._create_preview_buttons()
            )
            await state.set_state(AnnouncementForm.documents)

        except Exception as e:
            await self.send_error_message(message, 'general_error', error=str(e))

    async def process_edit_complexity(self, message: Message, state: FSMContext):
        """Обработка редактирования сложности."""
        try:
            await state.update_data(complexity=message.text)
            await self._edit_message_with_navigation(
                message,
                self._generate_preview_text(await state.get_data()),
                state,
                None,
                self._create_preview_buttons()
            )
            await state.set_state(AnnouncementForm.documents)

        except Exception as e:
            await self.send_error_message(message, 'general_error', error=str(e))

    async def process_edit_documents(self, message: Message, state: FSMContext):
        """Обработка редактирования документов."""
        try:
            data = await state.get_data()
            documents = data.get('documents', [])
            videos = data.get('videos', [])
            demo_url = data.get('demo_url', '')

            if message.text and message.text.lower() == 'готово':
                await self._edit_message_with_navigation(
                    message,
                    self._generate_preview_text(await state.get_data()),
                    state,
                    None,
                    self._create_preview_buttons()
                )
                await state.set_state(AnnouncementForm.documents)
                return

            if message.document:
                if message.document.file_size > 50 * 1024 * 1024:
                    await message.answer("❌ Файл слишком большой. Максимальный размер: 50 МБ")
                    return

                allowed_extensions = ['.docx', '.pdf', '.xlsx', '.pptx', '.mp4', '.avi', '.mov', '.jpg', '.png']
                file_extension = os.path.splitext(message.document.file_name)[1].lower()
                if file_extension not in allowed_extensions:
                    await message.answer(
                        f"❌ Неподдерживаемый формат файла. Доступные форматы: {', '.join(allowed_extensions)}"
                    )
                    return

                documents.append({
                    'file_id': message.document.file_id,
                    'file_name': message.document.file_name,
                    'file_size': message.document.file_size,
                    'mime_type': message.document.mime_type
                })

            elif message.video:
                if message.video.file_size > 50 * 1024 * 1024:
                    await message.answer("❌ Видео слишком большое. Максимальный размер: 50 МБ")
                    return

                videos.append({
                    'file_id': message.video.file_id,
                    'file_name': message.video.file_name,
                    'file_size': message.video.file_size,
                    'mime_type': message.video.mime_type,
                    'duration': message.video.duration
                })

            elif message.text and not message.text.startswith("/"):
                if message.text.lower().startswith(('http://', 'https://')):
                    demo_url = message.text
                else:
                    await message.answer(
                        "❌ Пожалуйста, отправьте файл, ссылку на демо или напишите 'готово'"
                    )
                    return

            await state.update_data(
                documents=documents,
                videos=videos,
                demo_url=demo_url
            )

            done_keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="✅ Готово",
                        callback_data="documents_done"
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
                '✅ Файл успешно загружен. Вы можете загрузить еще файлы или нажать "Готово"',
                reply_markup=done_keyboard
            )

        except Exception as e:
            await self.send_error_message(message, 'general_error', error=str(e))

    def _format_documents(self, data: dict) -> str:
        """Форматирование списка документов для отображения."""
        documents_text = ""
        documents = data.get('documents', [])
        videos = data.get('videos', [])
        demo_url = data.get('demo_url', '')

        if documents:
            documents_text += "📄 Документы:\n"
            for doc in documents:
                documents_text += f"• {doc['file_name']} ({doc['file_size'] / 1024 / 1024:.1f} MB)\n"

        if videos:
            if documents_text:
                documents_text += "\n"
            documents_text += "🎥 Видео:\n"
            for video in videos:
                documents_text += f"• {video['file_name']} ({video['duration']}s)\n"

        if demo_url:
            if documents_text:
                documents_text += "\n"
            documents_text += f"🔗 Демо: {demo_url}"

        return documents_text if documents_text else "Не загружено"

    def _generate_preview_text(self, data: dict) -> str:
        """Генерация текста превью."""
        documents_text = self._format_documents(data)
        return messages.get_message(
            'announcement_creation', 'preview_template',
            bot_name=data.get('bot_name', 'Не указано'),
            task_solution=data.get('task_solution', 'Не указано'),
            included_features=data.get('included_features', 'Не указано'),
            client_requirements=data.get('client_requirements', 'Не указано'),
            launch_time=data.get('launch_time', 'Не указано'),
            price=data.get('price', 'Не указано'),
            complexity=data.get('complexity', 'Не указано'),
            documents=documents_text
        )

    def _create_preview_buttons(self) -> list:
        """Создание кнопок для превью."""
        return [
            [
                InlineKeyboardButton(
                    text="✅ Отправить на модерацию",
                    callback_data="confirm_announcement"
                ),
                InlineKeyboardButton(
                    text="✏️ Редактировать",
                    callback_data="edit_announcement"
                )
            ]
        ]

    async def handle_back_navigation(self, callback: CallbackQuery, state: FSMContext):
        """Обработка навигации назад."""
        try:
            action = callback.data.replace("back_to_", "")

            navigation_map = {
                "bot_name": (AnnouncementForm.bot_name, 'enter_bot_name', "cancel_announcement"),
                "task_solution": (AnnouncementForm.task_solution, 'enter_task_solution', "back_to_bot_name"),
                "included_features": (
                AnnouncementForm.included_features, 'enter_included_features', "back_to_task_solution"),
                "client_requirements": (
                AnnouncementForm.client_requirements, 'enter_client_requirements', "back_to_included_features"),
                "launch_time": (AnnouncementForm.launch_time, 'enter_launch_time', "back_to_client_requirements"),
                "price": (AnnouncementForm.price, 'enter_price', "back_to_launch_time"),
                "complexity": (AnnouncementForm.complexity, 'enter_complexity', "back_to_price"),
                "edit_menu": (AnnouncementForm.documents, None, None)
            }

            if action == "edit_menu":
                await self.show_edit_menu(callback, state)
                return

            if action == "preview":
                data = await state.get_data()
                await callback.message.edit_text(
                    self._generate_preview_text(data),
                    parse_mode='HTML',
                    reply_markup=self._create_navigation_keyboard("back_to_edit_menu", self._create_preview_buttons())
                )
                await state.set_state(AnnouncementForm.documents)
                await callback.answer()
                return

            if action in navigation_map:
                new_state, message_key, back_action = navigation_map[action]

                additional_buttons = None

                await callback.message.edit_text(
                    messages.get_message('announcement_creation', message_key),
                    parse_mode='HTML',
                    reply_markup=self._create_navigation_keyboard(back_action, additional_buttons)
                )
                await state.set_state(new_state)

            await callback.answer()

        except Exception as e:
            await self.send_error_message(callback, 'general_error', error=str(e))

    async def process_documents(self, message: Message, state: FSMContext):
        """Обработка загрузки документов."""
        try:
            data = await state.get_data()
            documents = data.get('documents', [])
            videos = data.get('videos', [])
            demo_url = data.get('demo_url', '')

            if message.document:
                if message.document.file_size > 50 * 1024 * 1024:
                    await message.answer("❌ Файл слишком большой. Максимальный размер: 50 МБ")
                    return

                allowed_extensions = ['.docx', '.pdf', '.xlsx', '.pptx', '.mp4', '.avi', '.mov', '.jpg', '.png']
                file_extension = os.path.splitext(message.document.file_name)[1].lower()
                if file_extension not in allowed_extensions:
                    await message.answer(
                        f"❌ Неподдерживаемый формат файла. Доступные форматы: {', '.join(allowed_extensions)}"
                    )
                    return

                documents.append({
                    'file_id': message.document.file_id,
                    'file_name': message.document.file_name,
                    'file_size': message.document.file_size,
                    'mime_type': message.document.mime_type
                })

            elif message.video:
                if message.video.file_size > 50 * 1024 * 1024:
                    await message.answer("❌ Видео слишком большое. Максимальный размер: 50 МБ")
                    return

                videos.append({
                    'file_id': message.video.file_id,
                    'file_name': message.video.file_name,
                    'file_size': message.video.file_size,
                    'mime_type': message.video.mime_type,
                    'duration': message.video.duration
                })

            elif message.text and not message.text.startswith("/"):
                if message.text.lower().startswith(('http://', 'https://')):
                    demo_url = message.text
                else:
                    await message.answer(
                        "❌ Пожалуйста, отправьте файл или ссылку на демо"
                    )
                    return

            await state.update_data(
                documents=documents,
                videos=videos,
                demo_url=demo_url
            )

            done_keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="✅ Готово",
                        callback_data="documents_done"
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
                '✅ Файл успешно загружен. Вы можете загрузить еще файлы или нажать "Готово"',
                reply_markup=done_keyboard
            )

        except Exception as e:
            await message.answer(
                messages.get_message('announcement_creation', 'save_error', error=str(e)),
                parse_mode='HTML'
            )
            await state.clear()

    async def show_preview(self, callback: CallbackQuery, state: FSMContext):
        """Показ превью объявления перед отправкой на модерацию."""
        try:
            data = await state.get_data()
            await callback.message.edit_text(
                self._generate_preview_text(data),
                parse_mode='HTML',
                reply_markup=self._create_navigation_keyboard(None, self._create_preview_buttons())
            )
            await state.set_state(AnnouncementForm.documents)
            await callback.answer()

        except Exception as e:
            await self.send_error_message(callback, 'general_error', error=str(e))

    async def confirm_announcement(self, callback: CallbackQuery, state: FSMContext):
        """Подтверждение отправки объявления на модерацию."""
        try:
            data = await state.get_data()
            bot_name = data.get('bot_name')
            task_solution = data.get('task_solution')
            included_features = data.get('included_features')
            client_requirements = data.get('client_requirements')
            launch_time = data.get('launch_time')
            price = data.get('price')
            complexity = data.get('complexity')
            documents = data.get('documents', [])
            videos = data.get('videos', [])
            demo_url = data.get('demo_url', '')

            announcement = self.safe_db_operation(
                self._create_announcement_in_db,
                callback.from_user.id,
                callback.message.chat.id,
                bot_name,
                task_solution,
                included_features,
                client_requirements,
                launch_time,
                price,
                complexity,
                demo_url,
                documents,
                videos
            )

            await self._notify_moderators(callback.message, announcement)

            keyboard = InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(
                        text=messages.get_button_text('moderation', 'back_to_menu'),
                        callback_data='main_menu'
                    )]
                ]
            )

            await callback.message.edit_text(
                messages.get_message('announcement_creation', 'announcement_sent').format(bot_name=announcement['bot_name']),
                keyboard=keyboard,
                parse_mode='HTML'
                )

            await state.clear()

        except Exception as e:
            await self.send_error_message(callback, 'general_error', error=str(e))

    async def cancel_announcement(self, callback: CallbackQuery, state: FSMContext):
        """Отмена создания объявления."""
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
            await self.send_error_message(callback, 'general_error', error=str(e))

    def _create_announcement_in_db(self, session, user_id: int, chat_id: int,
                                   bot_name: str, task_solution: str, included_features: str,
                                   client_requirements: str, launch_time: str, price: str, complexity: str,
                                   demo_url: str, documents: list, videos: list) -> dict:
        """Создание объявления в базе данных."""
        announcement = self.create_announcement(session, user_id, chat_id, bot_name, task_solution,
                                                included_features, client_requirements, launch_time, price, complexity,
                                                demo_url, documents, videos)
        return {
            'id': announcement.id,
            'user_id': announcement.user_id,
            'chat_id': announcement.chat_id,
            'bot_name': announcement.bot_name,
            'task_solution': announcement.task_solution,
            'included_features': announcement.included_features,
            'client_requirements': announcement.client_requirements,
            'launch_time': announcement.launch_time,
            'price': announcement.price,
            'complexity': announcement.complexity,
            'is_approved': announcement.is_approved,
            'created_at': announcement.created_at,
            'demo_url': announcement.demo_url,
            'documents': announcement.documents,
            'videos': announcement.videos
        }

    async def _notify_moderators(self, message: Message, announcement: dict):
        """Уведомление модераторов о новом объявлении."""
        try:
            # Формируем список файлов
            files_list = []
            if announcement['documents']:
                for i, doc in enumerate(announcement['documents'], 1):
                    files_list.append(f"{i}. 📄 {doc['file_name']}")
            if announcement['videos']:
                for i, video in enumerate(announcement['videos'], len(announcement['documents']) + 1):
                    files_list.append(f"{i}. 🎬 {video['file_name']}")
            if announcement['demo_url']:
                files_list.append(f"🌐 Демо-версия: {announcement['demo_url']}")

            # Формируем текст объявления с файлами
            announcement_text = messages.get_message('moderation', 'new_announcement_template',
                bot_name=announcement['bot_name'],
                task_solution=announcement['task_solution'],
                included_features=announcement['included_features'],
                client_requirements=announcement['client_requirements'],
                launch_time=announcement['launch_time'],
                price=announcement['price'],
                complexity=announcement['complexity'],
                user_info=f"Пользователь ID: {announcement['user_id']}",
                created_date=announcement['created_at'],
                files_list="\n".join(files_list)
            )

            # Создаем клавиатуру для модерации
            keyboard = self._create_moderation_keyboard(announcement['id'], message.chat.id)

            # Отправляем объявление и файлы модераторам
            for moderator_id in self.moderator_ids:
                try:
                    # Отправляем текст объявления
                    await message.bot.send_message(
                        moderator_id,
                        announcement_text,
                        parse_mode='HTML',
                        reply_markup=keyboard
                    )

                    # Отправляем сами файлы
                    if announcement['documents']:
                        for doc in announcement['documents']:
                            try:
                                await message.bot.send_document(
                                    moderator_id,
                                    doc['file_id']
                                )
                            except Exception as e:
                                continue

                    if announcement['videos']:
                        for video in announcement['videos']:
                            try:
                                await message.bot.send_video(
                                    moderator_id,
                                    video['file_id']
                                )
                            except Exception as e:
                                continue

                except Exception as e:
                    continue

        except Exception as e:
            await self.send_error_message(message, 'general_error', error=str(e))

    def _create_moderation_keyboard(self, announcement_id: int, chat_id: int) -> InlineKeyboardMarkup:
        """Создание клавиатуры для модерации."""
        buttons = [
            [
                InlineKeyboardButton(
                    text=messages.get_button_text('moderation', 'approve'),
                    callback_data=f'approve_{announcement_id}'
                ),
                InlineKeyboardButton(
                    text=messages.get_button_text('moderation', 'reject'),
                    callback_data=f'reject_{announcement_id}'
                ),
                InlineKeyboardButton(
                    text=messages.get_button_text('moderation', 'contact'),
                    url=f'tg://user?id={chat_id}'
                )
            ]
        ]

        return InlineKeyboardMarkup(inline_keyboard=buttons)