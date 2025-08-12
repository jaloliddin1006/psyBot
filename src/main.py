import os
import logging
import asyncio
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, CommandStart, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile, BotCommand
from src.database.models import User
from src.database.session import get_session, close_session
from src.handlers.aichat import router as aichat_router
from src.handlers.main_menu import router as main_menu_router
from src.handlers.main_menu import main_menu
from src.handlers.emotion_diary import router as emotion_diary_router
from src.handlers.emotion_analysis import router as emotion_analysis_router
from src.handlers.thought_diary import router as thought_diary_router
from src.handlers.notifications import router as notifications_router
from src.handlers.reflection import router as reflection_router
from src.handlers.weekly_reflection import router as weekly_reflection_router
from src.handlers.weekly_reflection import start_weekly_reflection
from src.handlers.session import router as session_router
from src.handlers.therapy_themes import router as therapy_themes_router
from src.handlers.relaxation import router as relaxation_router
from src.handlers.voice_handler import router as voice_handler_router
from src.notification_scheduler import NotificationScheduler
from src.activity_tracker import update_user_activity

# Load environment variables
load_dotenv()

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
bot = Bot(token=TELEGRAM_BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# Activity tracking middleware
from aiogram.types import TelegramObject
from aiogram import BaseMiddleware

class ActivityTrackingMiddleware(BaseMiddleware):
    async def __call__(self, handler, event: TelegramObject, data: dict):
        # Track activity for messages and callback queries
        if hasattr(event, 'from_user') and event.from_user:
            update_user_activity(event.from_user.id)
        
        # Call the next handler
        return await handler(event, data)

# Register middleware
dp.message.middleware(ActivityTrackingMiddleware())
dp.callback_query.middleware(ActivityTrackingMiddleware())

dp.include_router(voice_handler_router)  # Add voice handler first for priority
dp.include_router(main_menu_router)
dp.include_router(emotion_diary_router)
dp.include_router(emotion_analysis_router)
dp.include_router(thought_diary_router)
dp.include_router(notifications_router)
dp.include_router(reflection_router)
dp.include_router(weekly_reflection_router)
dp.include_router(session_router)
dp.include_router(therapy_themes_router)
dp.include_router(relaxation_router)
dp.include_router(aichat_router)
# States
WELCOME_STATE = "WELCOME_STATE"
TERMS_AGREEMENT_STATE = "TERMS_AGREEMENT_STATE"
NAME_STATE = "NAME_STATE"
GENDER_STATE = "GENDER_STATE"
AGE_STATE = "AGE_STATE"
TIMEZONE_SELECTION_STATE = "TIMEZONE_SELECTION_STATE"
NOTIFICATION_FREQUENCY_STATE = "NOTIFICATION_FREQUENCY_STATE"
THERAPIST_QUESTION_STATE = "THERAPIST_QUESTION_STATE"
REFERRAL_SOURCE_STATE = "REFERRAL_SOURCE_STATE"
REFERRAL_SOURCE_INPUT_STATE = "REFERRAL_SOURCE_INPUT_STATE"
BOT_CAPABILITIES_STATE = "BOT_CAPABILITIES_STATE"

LICENSE_AGREEMENT = """
*Terms and Conditions for PsyBot*

By using this bot, you agree to the following terms:

1. This bot is not a replacement for professional psychological help.
2. All conversations are confidential but not encrypted.
3. Your data will be stored securely and used only to improve your experience.
4. You can request deletion of your data at any time.

Do you agree to these terms?
"""

async def delete_previous_messages(message: types.Message, state: FSMContext, keep_current: bool = False):
    data = await state.get_data()
    messages_to_delete = data.get('messages_to_delete', [])
    new_messages_to_delete_list = [] # To rebuild the list if keep_current is true

    for msg_id in messages_to_delete:
        if keep_current and msg_id == message.message_id:
            new_messages_to_delete_list.append(msg_id) # Keep it in the list for next time if needed
            continue # Skip deleting this one
        try:
            await message.bot.delete_message(message.chat.id, msg_id)
        except Exception as e:
            # Log error or handle specific exceptions if necessary
            logger.debug(f"Failed to delete message {msg_id} in chat {message.chat.id}: {e}")
            pass # Continue trying to delete other messages
    
    if keep_current:
        # If we kept the current message, the list should reflect that for future deletions.
        # However, typically, if we keep a message, it's the *last* one and shouldn't be in future lists immediately.
        # For simplicity, if keep_current is true, we assume the current message (if it was in the list) is preserved,
        # and the list effectively becomes empty *for this deletion cycle* except for the one we preserved.
        # A more robust approach might involve explicitly removing other IDs from state if only current is kept.
        # For now, if keep_current, we put only the current message back if it was targeted, or empty the list.
        if message.message_id in messages_to_delete:
             await state.update_data(messages_to_delete=[message.message_id])
        else:
             await state.update_data(messages_to_delete=[])
    else:
        await state.update_data(messages_to_delete=[])

@dp.message(CommandStart())
async def cmd_start(message: types.Message, state: FSMContext):
    session = get_session()
    db_user = session.query(User).filter(User.telegram_id == message.from_user.id).first()

    if db_user and getattr(db_user, "registration_complete", False):
        close_session(session)
        await state.clear()  # Clear previous state for a registered user

        # main_menu will add the /start message (message.message_id)
        # and its own menu message to the state's messages_to_delete list.
        await main_menu(message, state)

        # Delete messages collected by main_menu (including /start and the menu prompt itself)
        # await delete_previous_messages(message, state) # <--- Commented out as per request
        return

    # Path for new users or users with incomplete registration
    if not db_user:
        db_user = User(
            telegram_id=message.from_user.id,
            username=message.from_user.username,
            first_name=message.from_user.first_name,
        )
        session.add(db_user)
        session.commit()
    close_session(session)

    # For new user path, collect messages to be deleted by the next handler (e.g., welcome_callback)
    current_data = await state.get_data()
    messages_to_delete = current_data.get('messages_to_delete', [])
    if messages_to_delete is None:  # Should ideally always be a list
        messages_to_delete = []

    if message.message_id not in messages_to_delete:
        messages_to_delete.append(message.message_id)  # Add the /start command message

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Давайте начнем", callback_data="begin")]
    ])
    sent_reply = await message.answer(
        "Привет! Я — твой персональный помощник по психологическому здоровью. С радостью помогу тебе отслеживать эмоции и поддерживать твой прогресс между сессиями с психологом. Готов(-а) начать?",
        reply_markup=keyboard
    )
    if sent_reply.message_id not in messages_to_delete:
        messages_to_delete.append(sent_reply.message_id)  # Add the bot's reply message

    await state.update_data(messages_to_delete=messages_to_delete)
  
    # The actual deletion for new users will happen in a subsequent handler like welcome_callback

@dp.callback_query(F.data == "begin")
async def welcome_callback(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    await delete_previous_messages(callback.message, state)
    
    header_msg = await callback.message.answer(
        'Чтобы продолжить использование бота, необходимо ознакомиться и принять "Пользовательское соглашение" и "Политику обработки персональных данных". Нажимая кнопку далее, ты подтверждаешь, что ты ознакомлен(-а) и принимаешь условия.'
    )
    
    messages_to_delete = [header_msg.message_id]
    
    # Send PDF documents from static folder
    static_folder = os.path.join(os.path.dirname(__file__), "static")
    
    try:
        # Send User Agreement PDF
        user_agreement_path = os.path.join(static_folder, "Пользовательское соглашение.pdf")
        if os.path.exists(user_agreement_path):
            with open(user_agreement_path, "rb") as pdf_file:
                pdf_msg = await callback.message.answer_document(
                    document=FSInputFile(user_agreement_path),
                    caption="📄 Пользовательское соглашение"
                )
                messages_to_delete.append(pdf_msg.message_id)
        
        # Send Privacy Policy PDF  
        privacy_policy_path = os.path.join(static_folder, "Политика_обработки_персональных_данных.pdf")
        if os.path.exists(privacy_policy_path):
            with open(privacy_policy_path, "rb") as pdf_file:
                pdf_msg = await callback.message.answer_document(
                    document=FSInputFile(privacy_policy_path),
                    caption="📄 Политика обработки персональных данных"
                )
                messages_to_delete.append(pdf_msg.message_id)
                
    except Exception as e:
        logger.error(f"Error sending PDF documents: {e}")
        # Continue with registration even if PDFs fail to send
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Согласен с условиями", callback_data="agree")],
        [InlineKeyboardButton(text="Не согласен", callback_data="disagree")]
    ])
    
    agreement_msg = await callback.message.answer(
        "Вы ознакомились и согласны с Пользовательским соглашением и Политикой обработки персональных данных?",
        reply_markup=keyboard
    )
    messages_to_delete.append(agreement_msg.message_id)
    
    await state.update_data(messages_to_delete=messages_to_delete)

@dp.callback_query(F.data.in_(["agree", "disagree"]))
async def terms_callback(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    await delete_previous_messages(callback.message, state)
    if callback.data == "disagree":
        await callback.message.answer(
            text="Вы должны согласиться с условиями использования этого бота. Если вы передумаете, вы можете начать с /start."
        )
        return
    session = get_session()
    db_user = session.query(User).filter(User.telegram_id == callback.from_user.id).first()
    if not db_user:
        close_session(session)
        await callback.message.answer(
            text="Произошла ошибка: пользователь не найден. Пожалуйста, начните регистрацию заново с помощью /start."
        )
        return
    db_user.agreed_to_terms = True
    session.commit()
    close_session(session)
    msg = await callback.message.answer(
        text='Отлично! Давайте начнем с небольшого знакомства. Как мне к вам обращаться?'
    )
    await state.update_data(messages_to_delete=[msg.message_id])
    await state.set_state(NAME_STATE)
    logger.info(f"State set to NAME_STATE in terms_callback. Current state: {await state.get_state()}")

@dp.message(F.text, StateFilter(NAME_STATE))
async def save_name(message: types.Message, state: FSMContext):
    logger.info(f"save_name handler triggered with text: {message.text}")
    name = message.text
    data = await state.get_data()
    messages_to_delete = data.get('messages_to_delete', [])
    if message.message_id not in messages_to_delete:
        messages_to_delete.append(message.message_id)
    await state.update_data(messages_to_delete=messages_to_delete)
    await delete_previous_messages(message, state)
    session = get_session()
    db_user = session.query(User).filter(User.telegram_id == message.from_user.id).first()
    db_user.full_name = name
    session.commit()
    close_session(session)
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Мужской", callback_data="man")],
        [InlineKeyboardButton(text="Женский", callback_data="woman")],
    ])
    msg = await message.answer(
        f"Приятно познакомиться, {name}! В каком роде мне обращаться к тебе?",
        reply_markup=keyboard
    )
    await state.update_data(messages_to_delete=[msg.message_id])
    current_state_before_gender = await state.get_state()
    logger.info(f"Current state before setting to GENDER_STATE: {current_state_before_gender}")
    await state.set_state(GENDER_STATE)
    current_state_after_gender = await state.get_state()
    logger.info(f"Current state after setting to GENDER_STATE: {current_state_after_gender}")

@dp.callback_query(F.data.in_(["man", "woman"]), StateFilter(GENDER_STATE))
async def save_gender(callback: types.CallbackQuery, state: FSMContext):
    logger.info(f"save_gender handler triggered. Callback data: {callback.data}")
    current_fsm_state = await state.get_state()
    logger.info(f"Current FSM state in save_gender: {current_fsm_state}")
    await callback.answer()
    await delete_previous_messages(callback.message, state)
    gender = callback.data
    session = get_session()
    db_user = session.query(User).filter(User.telegram_id == callback.from_user.id).first()
    db_user.gender = gender
    session.commit()
    close_session(session)
    msg = await callback.message.answer(
        text=f"Сколько вам лет?"
    )
    await state.update_data(messages_to_delete=[msg.message_id])
    await state.set_state(AGE_STATE)

@dp.message(F.text.regexp(r"^\d+$"), StateFilter(AGE_STATE))
async def save_age(message: types.Message, state: FSMContext):
    try:
        age = int(message.text)
        if age < 0 or age > 150:
            raise ValueError
    except ValueError:
        msg = await message.answer(
            text="Пожалуйста, введите корректный возраст (число от 0 до 150)."
        )
        await state.update_data(messages_to_delete=[msg.message_id])
        return
    
    data = await state.get_data()
    messages_to_delete = data.get('messages_to_delete', [])
    if message.message_id not in messages_to_delete:
        messages_to_delete.append(message.message_id)
    await state.update_data(messages_to_delete=messages_to_delete)
    await delete_previous_messages(message, state)
    session = get_session()
    db_user = session.query(User).filter(User.telegram_id == message.from_user.id).first()
    db_user.age = age
    db_user.time_format = "24h"
    session.commit()
    close_session(session)
    
    # Ask for current time to calculate timezone
    from datetime import datetime
    server_time = datetime.now()
    server_time_str = server_time.strftime("%H:%M")
    
    msg = await message.answer(
        f"Чтобы настроить уведомления под ваше время, скажите, сколько сейчас времени у вас?\n\n"
        f"⏰ Напишите текущее время в формате ЧЧ:ММ (например: 16:54)\n\n"
        f"💡 Это поможет мне рассчитать ваш часовой пояс и отправлять уведомления в удобное время."
    )
    await state.update_data(messages_to_delete=[msg.message_id], server_time=server_time_str)
    await state.set_state(TIMEZONE_SELECTION_STATE)

@dp.message(F.text.regexp(r"^\d{1,2}:\d{2}$"), StateFilter(TIMEZONE_SELECTION_STATE))
async def save_timezone_from_time(message: types.Message, state: FSMContext):
    logger.info(f"save_timezone_from_time handler triggered with text: {message.text}")
    
    # Get server time from state
    data = await state.get_data()
    server_time_str = data.get('server_time')
    user_time_str = message.text.strip()
    
    # Import timezone utility
    from src.timezone_utils import calculate_timezone_offset
    
    # Calculate timezone offset
    timezone_offset, user_timezone, error_msg = calculate_timezone_offset(user_time_str, server_time_str)
    
    if error_msg:
        # Handle error
        msg = await message.answer(f"❌ {error_msg}")
        messages_to_delete = data.get('messages_to_delete', [])
        messages_to_delete.extend([message.message_id, msg.message_id])
        await state.update_data(messages_to_delete=messages_to_delete)
        return
    
    # Add user message to deletion list
    messages_to_delete = data.get('messages_to_delete', [])
    messages_to_delete.append(message.message_id)
    await state.update_data(messages_to_delete=messages_to_delete)
    await delete_previous_messages(message, state)
    
    # Save to database
    session = get_session()
    db_user = session.query(User).filter(User.telegram_id == message.from_user.id).first()
    db_user.timezone_offset = timezone_offset
    db_user.user_timezone = user_timezone
    session.commit()
    close_session(session)
    
    # Ask for notification frequency preference
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="1 раз в день", callback_data="reg_freq_1")],
        [InlineKeyboardButton(text="2 раза в день", callback_data="reg_freq_2")],
        [InlineKeyboardButton(text="4 раза в день", callback_data="reg_freq_4")],
        [InlineKeyboardButton(text="6 раз в день", callback_data="reg_freq_6")],
        [InlineKeyboardButton(text="🔕 Не получать уведомления", callback_data="reg_freq_0")]
    ])
    
    msg = await message.answer(
        f"Отлично! Определил ваш часовой пояс: {user_timezone}\n\n"
        f"Ваше время: {user_time_str}, время сервера: {server_time_str}\n\n"
        "Как часто вы хотите получать напоминания о дневнике эмоций?\n\n"
        "💡 Вы можете изменить эти настройки в любое время с помощью команды /notify.",
        reply_markup=keyboard
    )
    await state.update_data(messages_to_delete=[msg.message_id])
    await state.set_state(NOTIFICATION_FREQUENCY_STATE)

@dp.callback_query(F.data.in_(["reg_freq_1", "reg_freq_2", "reg_freq_4", "reg_freq_6", "reg_freq_0"]), StateFilter(NOTIFICATION_FREQUENCY_STATE))
async def save_notification_frequency(callback: types.CallbackQuery, state: FSMContext):
    logger.info(f"save_notification_frequency handler triggered. Callback data: {callback.data}")
    await callback.answer()
    await delete_previous_messages(callback.message, state)
    
    # Extract frequency from callback data
    frequency = int(callback.data.split("_")[2])
    
    session = get_session()
    db_user = session.query(User).filter(User.telegram_id == callback.from_user.id).first()
    db_user.notification_frequency = frequency
    session.commit()
    close_session(session)
    
    # Create personalized message based on notification preference
    if frequency == 0:
        notification_note = "Уведомления отключены."
    else:
        frequency_text = {
            1: "1 раз в день",
            2: "2 раза в день", 
            4: "4 раза в день",
            6: "6 раз в день"
        }
        notification_note = f"Ты будешь получать напоминания о дневнике эмоций {frequency_text[frequency]}."
    
    # Ask about working with therapist
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Да", callback_data="therapist_yes")],
        [InlineKeyboardButton(text="Нет", callback_data="therapist_no")]
    ])
    
    msg = await callback.message.answer(
        f"Отлично! {notification_note}\n\n"
        "Ты работаешь с психологом/психотерапевтом?",
        reply_markup=keyboard
    )
    await state.update_data(messages_to_delete=[msg.message_id])
    await state.set_state(THERAPIST_QUESTION_STATE)

@dp.callback_query(F.data.in_(["therapist_yes", "therapist_no"]), StateFilter(THERAPIST_QUESTION_STATE))
async def save_therapist_info(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    await delete_previous_messages(callback.message, state)
    
    # Save therapist info to database
    works_with_therapist = callback.data == "therapist_yes"
    session = get_session()
    db_user = session.query(User).filter(User.telegram_id == callback.from_user.id).first()
    db_user.works_with_therapist = works_with_therapist
    session.commit()
    close_session(session)
    
    # Store therapist info for later use
    await state.update_data(works_with_therapist=works_with_therapist)
    
    # Ask about referral source
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Рекомендация знакомого", callback_data="ref_friend")],
        [InlineKeyboardButton(text="Канал бота", callback_data="ref_bot_channel")],
        [InlineKeyboardButton(text="Реклама в другом канале", callback_data="ref_other_channel")],
        [InlineKeyboardButton(text="Другое (напишу свой)", callback_data="ref_other")]
    ])
    
    msg = await callback.message.answer(
        "Перед тем как узнать, что умеет бот, ответь, пожалуйста, на вопрос: Откуда ты узнал о боте?",
        reply_markup=keyboard
    )
    await state.update_data(messages_to_delete=[msg.message_id])
    await state.set_state(REFERRAL_SOURCE_STATE)

@dp.callback_query(F.data.in_(["ref_friend", "ref_bot_channel", "ref_other_channel", "ref_other"]), StateFilter(REFERRAL_SOURCE_STATE))
async def save_referral_source(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    await delete_previous_messages(callback.message, state)
    
    if callback.data == "ref_other":
        # User wants to input custom source
        msg = await callback.message.answer(
            "Напиши, откуда ты узнал о боте:"
        )
        await state.update_data(messages_to_delete=[msg.message_id])
        await state.set_state(REFERRAL_SOURCE_INPUT_STATE)
        return
    
    # Save predefined referral source
    referral_sources = {
        "ref_friend": "Рекомендация знакомого",
        "ref_bot_channel": "Канал бота", 
        "ref_other_channel": "Реклама в другом канале"
    }
    
    referral_source = referral_sources[callback.data]
    await save_referral_and_complete_registration(callback, state, referral_source)

@dp.message(F.text, StateFilter(REFERRAL_SOURCE_INPUT_STATE))
async def save_custom_referral_source(message: types.Message, state: FSMContext):
    # Add message to deletion list
    data = await state.get_data()
    messages_to_delete = data.get('messages_to_delete', [])
    messages_to_delete.append(message.message_id)
    await state.update_data(messages_to_delete=messages_to_delete)
    await delete_previous_messages(message, state)
    
    # Save custom referral source
    referral_source = f"Другое: {message.text}"
    await save_referral_and_complete_registration(message, state, referral_source)

async def save_referral_and_complete_registration(message_or_callback, state: FSMContext, referral_source: str):
    """Save referral source and complete registration"""
    if hasattr(message_or_callback, 'message'):
        # It's a callback query
        user_id = message_or_callback.from_user.id
        message = message_or_callback.message
    else:
        # It's a message
        user_id = message_or_callback.from_user.id
        message = message_or_callback
    
    # Get stored data
    data = await state.get_data()
    works_with_therapist = data.get('works_with_therapist', False)
    
    # Save referral source and complete registration
    session = get_session()
    db_user = session.query(User).filter(User.telegram_id == user_id).first()
    db_user.referral_source = referral_source
    db_user.registration_complete = True
    
    # Start trial period for new user
    from src.trial_manager import start_trial_period
    start_trial_period(db_user)
    
    session.commit()
    
    # Save important details before closing the session
    committed_full_name = db_user.full_name
    close_session(session)
    
    name = committed_full_name
    
    # Create capabilities text based on whether user works with therapist
    if works_with_therapist:
        # User works with therapist - trigger session command
        capabilities_text = f"""
Отлично, {name}! Я помогу тебе лучше понимать себя, отслеживать настроение и закреплять навыки, которые ты осваиваешь на терапии.

🎯 Пробный период: У тебя есть 2 недели бесплатного доступа ко всем функциям!

Вот что я могу делать для тебя:
🔹 Фиксировать настроение – помогу замечать, как меняются твои эмоции.
🔹 Предлагать техники самопомощи – дыхательные упражнения, когнитивные техники и другие способы справляться с тревогой и стрессом.
🔹 Помочь отслеживать темы сессий – я буду запоминать важные для тебя темы и выводить отчет.
🔹 Помогать осознавать мысли – если у тебя тревожные или навязчивые мысли, мы можем вместе разобраться, что с ними делать.
🔹 Показывать твой прогресс – помогу увидеть, как меняется твое состояние со временем.

Давайте сразу запланируем вашу следующую встречу с психологом, чтобы я мог отправить вам напоминание для рефлексии!
"""
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Запланировать встречу", callback_data="start_session_planning")],
            [InlineKeyboardButton(text="Пропустить", callback_data="start_using")]
        ])
    else:
        # User doesn't work with therapist
        capabilities_text = f"""
Привет, {name}! Я помогу тебе лучше понимать себя, отслеживать настроение и развивать навыки самопомощи.

🎯 Пробный период: У тебя есть 2 недели бесплатного доступа ко всем функциям!

Вот что я могу делать для тебя:
🔹 Фиксировать настроение – помогу замечать, как меняются твои эмоции.
🔹 Предлагать техники самопомощи – дыхательные упражнения, когнитивные техники и другие способы справляться с тревогой и стрессом.
🔹 Помогать осознавать мысли – если у тебя тревожные или навязчивые мысли, мы можем вместе разобраться, что с ними делать.
🔹 Показывать твой прогресс – помогу увидеть, как меняется твое состояние со временем.

Хочешь попробовать прямо сейчас?
"""
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Начать", callback_data="start_using")],
        ])
    
    msg = await message.answer(
        text=capabilities_text,
        reply_markup=keyboard
    )
    await state.update_data(messages_to_delete=[msg.message_id])
    await state.set_state(BOT_CAPABILITIES_STATE)

@dp.callback_query(F.data == "start_session_planning", StateFilter(BOT_CAPABILITIES_STATE))
async def start_session_planning_callback(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    await delete_previous_messages(callback.message, state)
    await state.clear()
    
    # Import and start session planning
    from src.handlers.session import start_session_planning
    await start_session_planning(callback, state)

@dp.callback_query(F.data == "start_using", StateFilter(BOT_CAPABILITIES_STATE))
async def start_using_callback(callback: types.CallbackQuery, state: FSMContext):
    from src.handlers.utils import show_pin_recommendation_and_main_menu
    await show_pin_recommendation_and_main_menu(callback, state)

@dp.message(Command("weekly"))
async def cmd_weekly_reflection(message: types.Message, state: FSMContext):
    """Command to start weekly reflection"""
    await start_weekly_reflection(message, state)

@dp.message(Command("reset"))
async def reset_user(message: types.Message, state: FSMContext):
    session = get_session()
    db_user = session.query(User).filter(User.telegram_id == message.from_user.id).first()
    if db_user:
        session.delete(db_user)
        session.commit()
    close_session(session)
    await state.clear()
    await message.answer(
        "Ваши данные удалены. Чтобы начать заново, пожалуйста, введите /start."
    )
    # No longer adding message to messages_to_delete or sending a button

async def setup_bot_commands():
    """Set up bot menu commands"""
    commands = [
        BotCommand(command="help", description="🆘 Помощь и информация о боте"),
        BotCommand(command="hotline", description="📞 Телефон горячей линии"),
        BotCommand(command="notify", description="🔔 Настройки уведомлений"),
        BotCommand(command="reflection", description="💭 Рефлексия"),
        BotCommand(command="session", description="📅 Планирование сессии с психологом"),
        BotCommand(command="weekly", description="📊 Еженедельная рефлексия")
    ]
    
    await bot.set_my_commands(commands)
    logger.info("✅ Bot menu commands have been set up")

async def main():
    # Set up bot commands
    await setup_bot_commands()
    
    # Initialize and start the notification scheduler as a background task
    scheduler = NotificationScheduler()
    scheduler_task = asyncio.create_task(scheduler.run_scheduler())
    
    logger.info("🤖 Starting PsyBot with notification scheduler...")
    
    try:
        # Start the bot polling
        await dp.start_polling(bot)
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    finally:
        # Stop the scheduler when bot is shutting down
        scheduler.stop()
        scheduler_task.cancel()
        try:
            await scheduler_task
        except asyncio.CancelledError:
            logger.info("Notification scheduler stopped")

if __name__ == "__main__":
    asyncio.run(main())