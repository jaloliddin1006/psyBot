import logging
from aiogram import Router, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.filters import StateFilter
from src.database.session import get_session, close_session
from src.database.models import User, WeeklyReflection
from constants import (
    WEEKLY_REFLECTION_START,
    WEEKLY_REFLECTION_SMILE_MOMENT,
    WEEKLY_REFLECTION_KINDNESS,
    WEEKLY_REFLECTION_PEACE,
    WEEKLY_REFLECTION_NEW_DISCOVERY,
    WEEKLY_REFLECTION_GRATITUDE
)
from google import genai
from src.handlers.utils import delete_previous_messages
from trial_manager import require_trial_access

import os
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)
router = Router(name=__name__)

# Initialize Google Generative AI client
client = genai.Client(
    api_key=os.environ.get("GOOGLE_GENAI_API_KEY"),
    http_options={"base_url": os.environ.get("API_URL")}
)

async def delete_previous_messages(message: Message, state: FSMContext, keep_current: bool = False):
    """Helper function to delete previous messages"""
    data = await state.get_data()
    messages_to_delete = data.get('messages_to_delete', [])
    new_messages_to_delete_list = []

    for msg_id in messages_to_delete:
        if keep_current and msg_id == message.message_id:
            new_messages_to_delete_list.append(msg_id)
            continue
        try:
            await message.bot.delete_message(message.chat.id, msg_id)
        except Exception as e:
            logger.debug(f"Failed to delete message {msg_id} in chat {message.chat.id}: {e}")
            pass

    if keep_current:
        if message.message_id in messages_to_delete:
            await state.update_data(messages_to_delete=[message.message_id])
        else:
            await state.update_data(messages_to_delete=[])
    else:
        await state.update_data(messages_to_delete=[])

async def start_weekly_reflection(message: Message, state: FSMContext):
    """Start the weekly reflection process"""
    logger.info(f"Starting weekly reflection for user {message.from_user.id}")
    
    # Check if user is registered
    session = get_session()
    db_user = session.query(User).filter(User.telegram_id == message.from_user.id).first()
    
    if not db_user or not getattr(db_user, "registration_complete", False):
        close_session(session)
        await message.answer(
            "Для использования этой функции необходимо завершить регистрацию. "
            "Пожалуйста, введите /start для начала регистрации."
        )
        return
    
    close_session(session)
    
    # Clear previous state data
    await delete_previous_messages(message, state)
    
    # Initialize weekly reflection data
    await state.update_data({
        'messages_to_delete': [],
        'weekly_reflection_data': {
            'smile_moment': None,
            'kindness': None,
            'peace_moment': None,
            'new_discovery': None,
            'gratitude': None
        }
    })
    
    # Create keyboard with two buttons
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Начать рефлексию", callback_data="weekly_start_reflection"),
            InlineKeyboardButton(text="Отказаться", callback_data="weekly_decline_reflection")
        ]
    ])
    
    sent_message = await message.answer(
        "🌟 Время для еженедельной рефлексии!\n\n"
        "Давайте вместе вспомним хорошие моменты этой недели и подумаем о том, "
        "что принесло вам радость и благодарность.",
        reply_markup=keyboard
    )
    
    await state.update_data(messages_to_delete=[sent_message.message_id])
    await state.set_state(WEEKLY_REFLECTION_START)

@router.callback_query(F.data == "weekly_decline_reflection", StateFilter(WEEKLY_REFLECTION_START))
@require_trial_access('weekly_reflection')
async def handle_decline_reflection(callback: CallbackQuery, state: FSMContext):
    """Handle decline reflection button"""
    await callback.answer()
    logger.info(f"User {callback.from_user.id} declined weekly reflection")
    
    await delete_previous_messages(callback.message, state)
    
    # Create keyboard to go to main menu
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="На главную", callback_data="weekly_to_main")]
    ])
    
    sent_message = await callback.message.answer(
        "Давай вернемся к этому на следующей неделе. "
        "Иногда даже небольшая пауза помогает взглянуть на вещи по-новому.",
        reply_markup=keyboard
    )
    
    await state.update_data(messages_to_delete=[sent_message.message_id])
    await state.clear()

@router.callback_query(F.data == "weekly_start_reflection", StateFilter(WEEKLY_REFLECTION_START))
@require_trial_access('weekly_reflection')
async def handle_start_reflection(callback: CallbackQuery, state: FSMContext):
    """Handle start reflection button"""
    await callback.answer()
    logger.info(f"User {callback.from_user.id} started weekly reflection")
    
    await delete_previous_messages(callback.message, state)
    
    # Ask the first question
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Пропустить", callback_data="weekly_skip_smile"),
            InlineKeyboardButton(text="Завершить", callback_data="weekly_finish_early")
        ]
    ])
    
    sent_message = await callback.message.answer(
        "Какой маленький момент на этой неделе неожиданно заставил тебя улыбнуться или рассмеяться?",
        reply_markup=keyboard
    )
    
    await state.update_data(messages_to_delete=[sent_message.message_id])
    await state.set_state(WEEKLY_REFLECTION_SMILE_MOMENT)

@router.callback_query(F.data == "weekly_skip_smile", StateFilter(WEEKLY_REFLECTION_SMILE_MOMENT))
@require_trial_access('weekly_reflection')
async def handle_skip_smile(callback: CallbackQuery, state: FSMContext):
    """Handle skip smile moment"""
    await callback.answer()
    await move_to_kindness_question(callback.message, state)

@router.message(StateFilter(WEEKLY_REFLECTION_SMILE_MOMENT))
async def handle_smile_moment(message: Message, state: FSMContext):
    """Handle smile moment response"""
    logger.info(f"Handling smile moment response from user {message.from_user.id}")
    
    # Save the answer
    data = await state.get_data()
    weekly_reflection_data = data.get('weekly_reflection_data', {})
    weekly_reflection_data['smile_moment'] = message.text
    
    # Add current message to deletion list
    messages_to_delete = data.get('messages_to_delete', [])
    messages_to_delete.append(message.message_id)
    
    await delete_previous_messages(message, state)
    
    await state.update_data({
        'messages_to_delete': [],
        'weekly_reflection_data': weekly_reflection_data
    })
    
    await move_to_kindness_question(message, state)

async def move_to_kindness_question(message: Message, state: FSMContext):
    """Move to kindness question"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Пропустить", callback_data="weekly_skip_kindness"),
            InlineKeyboardButton(text="Завершить", callback_data="weekly_finish_early")
        ]
    ])
    
    sent_message = await message.answer(
        "Кто-то сделал для тебя что-то доброе или, может быть, ты сам помог кому-то так, что это запомнилось?",
        reply_markup=keyboard
    )
    
    await state.update_data(messages_to_delete=[sent_message.message_id])
    await state.set_state(WEEKLY_REFLECTION_KINDNESS)

@router.callback_query(F.data == "weekly_skip_kindness", StateFilter(WEEKLY_REFLECTION_KINDNESS))
@require_trial_access('weekly_reflection')
async def handle_skip_kindness(callback: CallbackQuery, state: FSMContext):
    """Handle skip kindness"""
    await callback.answer()
    await move_to_peace_question(callback.message, state)

@router.message(StateFilter(WEEKLY_REFLECTION_KINDNESS))
async def handle_kindness(message: Message, state: FSMContext):
    """Handle kindness response"""
    logger.info(f"Handling kindness response from user {message.from_user.id}")
    
    # Save the answer
    data = await state.get_data()
    weekly_reflection_data = data.get('weekly_reflection_data', {})
    weekly_reflection_data['kindness'] = message.text
    
    # Add current message to deletion list
    messages_to_delete = data.get('messages_to_delete', [])
    messages_to_delete.append(message.message_id)
    
    await delete_previous_messages(message, state)
    
    await state.update_data({
        'messages_to_delete': [],
        'weekly_reflection_data': weekly_reflection_data
    })
    
    await move_to_peace_question(message, state)

async def move_to_peace_question(message: Message, state: FSMContext):
    """Move to peace question"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Пропустить", callback_data="weekly_skip_peace"),
            InlineKeyboardButton(text="Завершить", callback_data="weekly_finish_early")
        ]
    ])
    
    sent_message = await message.answer(
        "В какой момент недели ты почувствовал(а) спокойствие, удовлетворение или был(а) по-настоящему собой?",
        reply_markup=keyboard
    )
    
    await state.update_data(messages_to_delete=[sent_message.message_id])
    await state.set_state(WEEKLY_REFLECTION_PEACE)

@router.callback_query(F.data == "weekly_skip_peace", StateFilter(WEEKLY_REFLECTION_PEACE))
@require_trial_access('weekly_reflection')
async def handle_skip_peace(callback: CallbackQuery, state: FSMContext):
    """Handle skip peace"""
    await callback.answer()
    await move_to_discovery_question(callback.message, state)

@router.message(StateFilter(WEEKLY_REFLECTION_PEACE))
async def handle_peace_moment(message: Message, state: FSMContext):
    """Handle peace moment response"""
    logger.info(f"Handling peace moment response from user {message.from_user.id}")
    
    # Save the answer
    data = await state.get_data()
    weekly_reflection_data = data.get('weekly_reflection_data', {})
    weekly_reflection_data['peace_moment'] = message.text
    
    # Add current message to deletion list
    messages_to_delete = data.get('messages_to_delete', [])
    messages_to_delete.append(message.message_id)
    
    await delete_previous_messages(message, state)
    
    await state.update_data({
        'messages_to_delete': [],
        'weekly_reflection_data': weekly_reflection_data
    })
    
    await move_to_discovery_question(message, state)

async def move_to_discovery_question(message: Message, state: FSMContext):
    """Move to discovery question"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Пропустить", callback_data="weekly_skip_discovery"),
            InlineKeyboardButton(text="Завершить", callback_data="weekly_finish_early")
        ]
    ])
    
    sent_message = await message.answer(
        "Что-то новое ты попробовал(а), узнал(а) или заметил(а) о себе или окружающем мире на этой неделе?",
        reply_markup=keyboard
    )
    
    await state.update_data(messages_to_delete=[sent_message.message_id])
    await state.set_state(WEEKLY_REFLECTION_NEW_DISCOVERY)

@router.callback_query(F.data == "weekly_skip_discovery", StateFilter(WEEKLY_REFLECTION_NEW_DISCOVERY))
@require_trial_access('weekly_reflection')
async def handle_skip_discovery(callback: CallbackQuery, state: FSMContext):
    """Handle skip discovery"""
    await callback.answer()
    await move_to_gratitude_question(callback.message, state)

@router.message(StateFilter(WEEKLY_REFLECTION_NEW_DISCOVERY))
async def handle_new_discovery(message: Message, state: FSMContext):
    """Handle new discovery response"""
    logger.info(f"Handling new discovery response from user {message.from_user.id}")
    
    # Save the answer
    data = await state.get_data()
    weekly_reflection_data = data.get('weekly_reflection_data', {})
    weekly_reflection_data['new_discovery'] = message.text
    
    # Add current message to deletion list
    messages_to_delete = data.get('messages_to_delete', [])
    messages_to_delete.append(message.message_id)
    
    await delete_previous_messages(message, state)
    
    await state.update_data({
        'messages_to_delete': [],
        'weekly_reflection_data': weekly_reflection_data
    })
    
    await move_to_gratitude_question(message, state)

async def move_to_gratitude_question(message: Message, state: FSMContext):
    """Move to gratitude question"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Пропустить", callback_data="weekly_skip_gratitude"),
            InlineKeyboardButton(text="Завершить", callback_data="weekly_finish_early")
        ]
    ])
    
    sent_message = await message.answer(
        "За что ты благодарен(на) на этой неделе — неважно, большое это или маленькое?",
        reply_markup=keyboard
    )
    
    await state.update_data(messages_to_delete=[sent_message.message_id])
    await state.set_state(WEEKLY_REFLECTION_GRATITUDE)

@router.callback_query(F.data == "weekly_skip_gratitude", StateFilter(WEEKLY_REFLECTION_GRATITUDE))
@require_trial_access('weekly_reflection')
async def handle_skip_gratitude(callback: CallbackQuery, state: FSMContext):
    """Handle skip gratitude"""
    await callback.answer()
    await complete_weekly_reflection(callback.message, state)

@router.message(StateFilter(WEEKLY_REFLECTION_GRATITUDE))
async def handle_gratitude(message: Message, state: FSMContext):
    """Handle gratitude response and complete the reflection"""
    logger.info(f"Handling gratitude response from user {message.from_user.id}")
    
    # Save the answer
    data = await state.get_data()
    weekly_reflection_data = data.get('weekly_reflection_data', {})
    weekly_reflection_data['gratitude'] = message.text
    
    # Add current message to deletion list
    messages_to_delete = data.get('messages_to_delete', [])
    messages_to_delete.append(message.message_id)
    
    await delete_previous_messages(message, state)
    
    await state.update_data({
        'messages_to_delete': [],
        'weekly_reflection_data': weekly_reflection_data
    })
    
    await complete_weekly_reflection(message, state)

@router.callback_query(F.data == "weekly_finish_early")
@require_trial_access('weekly_reflection')
async def handle_finish_early(callback: CallbackQuery, state: FSMContext):
    """Handle early finish button"""
    await callback.answer()
    await complete_weekly_reflection(callback.message, state)

async def complete_weekly_reflection(message: Message, state: FSMContext):
    """Complete the weekly reflection and save to database"""
    logger.info(f"Completing weekly reflection for user {message.from_user.id}")
    
    data = await state.get_data()
    weekly_reflection_data = data.get('weekly_reflection_data', {})
    
    # Generate AI summary
    try:
        ai_summary = await generate_ai_summary(weekly_reflection_data)
    except Exception as e:
        logger.error(f"Failed to generate AI summary: {e}")
        ai_summary = "Не удалось создать краткое изложение."
    
    # Save to database
    session = get_session()
    try:
        db_user = session.query(User).filter(User.telegram_id == message.from_user.id).first()
        if db_user:
            weekly_reflection = WeeklyReflection(
                user_id=db_user.id,
                smile_moment=weekly_reflection_data.get('smile_moment'),
                kindness=weekly_reflection_data.get('kindness'),
                peace_moment=weekly_reflection_data.get('peace_moment'),
                new_discovery=weekly_reflection_data.get('new_discovery'),
                gratitude=weekly_reflection_data.get('gratitude'),
                ai_summary=ai_summary
            )
            session.add(weekly_reflection)
            session.commit()
            logger.info(f"Successfully saved weekly reflection for user {message.from_user.id}")
        else:
            logger.error(f"User not found in database for telegram_id: {message.from_user.id}")
    except Exception as e:
        logger.error(f"Failed to save weekly reflection: {e}")
        session.rollback()
    finally:
        close_session(session)
    
    # Generate AI completion message
    try:
        completion_message = await generate_ai_completion_message(weekly_reflection_data, db_user.full_name if db_user else "")
    except Exception as e:
        logger.error(f"Failed to generate AI completion message: {e}")
        completion_message = f"Спасибо за завершение рефлексии! Ты проделал(а) важную работу, размышляя о хороших моментах недели. Желаю тебе отличной недели! 🌟"
    
    # Show completion message with button to main menu
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="На главную", callback_data="weekly_to_main")]
    ])
    
    sent_message = await message.answer(
        completion_message,
        reply_markup=keyboard
    )
    
    await state.update_data({
        'messages_to_delete': [sent_message.message_id],
        'weekly_reflection_data': {}
    })

async def generate_ai_summary(weekly_reflection_data: dict) -> str:
    """Generate AI summary of weekly reflection"""
    try:
        # Create a summary of non-empty responses
        responses = []
        if weekly_reflection_data.get('smile_moment'):
            responses.append(f"Момент радости: {weekly_reflection_data['smile_moment']}")
        if weekly_reflection_data.get('kindness'):
            responses.append(f"Доброта: {weekly_reflection_data['kindness']}")
        if weekly_reflection_data.get('peace_moment'):
            responses.append(f"Спокойствие: {weekly_reflection_data['peace_moment']}")
        if weekly_reflection_data.get('new_discovery'):
            responses.append(f"Открытие: {weekly_reflection_data['new_discovery']}")
        if weekly_reflection_data.get('gratitude'):
            responses.append(f"Благодарность: {weekly_reflection_data['gratitude']}")
        
        if not responses:
            return "Пользователь завершил рефлексию без ответов на вопросы."
        
        prompt = f"""
Создай краткое и позитивное изложение еженедельной рефлексии пользователя.
Ответы пользователя:

{chr(10).join(responses)}

Создай краткое изложение (2-3 предложения), которое отражает основные позитивные моменты недели.
Пиши от третьего лица, используя прошедшее время.
"""

        response = client.models.generate_content(
            model="gemini-1.5-flash",
            contents=[{
                "role": "user",
                "parts": [{"text": prompt}]
            }],
            config={
                "max_output_tokens": 200,
                "temperature": 0.7
            }
        )
        
        return response.candidates[0].content.parts[0].text.strip()
    
    except Exception as e:
        logger.error(f"Google Generative AI API error: {e}")
        # Fallback to simple summary
        return "Пользователь поделился своими размышлениями о прошедшей неделе."

async def generate_ai_completion_message(weekly_reflection_data: dict, user_name: str) -> str:
    """Generate AI completion message with praise and wishes"""
    try:
        # Count how many questions were answered
        answered_count = sum(1 for value in weekly_reflection_data.values() if value)
        
        prompt = f"""
Создай теплое и вдохновляющее сообщение для пользователя {user_name}, который только что завершил еженедельную рефлексию.
Пользователь ответил на {answered_count} из 5 вопросов о позитивных моментах недели.

Сообщение должно:
1. Поблагодарить за завершение рефлексии
2. Похвалить за проделанную работу
3. Пожелать отличной недели

Используй теплый, поддерживающий тон. Длина: 2-3 предложения.
Добавь подходящий эмодзи в конце.
"""

        response = client.models.generate_content(
            model="gemini-1.5-flash",
            contents=[{
                "role": "user",
                "parts": [{"text": prompt}]
            }],
            config={
                "max_output_tokens": 150,
                "temperature": 0.8
            }
        )
        
        return response.candidates[0].content.parts[0].text.strip()
    
    except Exception as e:
        logger.error(f"Google Generative AI API error: {e}")
        # Fallback message
        return f"Спасибо за завершение рефлексии, {user_name}! Ты проделал(а) важную работу, размышляя о хороших моментах недели. Желаю тебе отличной недели! 🌟"

@router.callback_query(F.data == "weekly_to_main")
@require_trial_access('weekly_reflection')
async def weekly_to_main_callback(callback: CallbackQuery, state: FSMContext):
    """Handle return to main menu from weekly reflection"""
    await callback.answer()
    
    # Import here to avoid circular imports
    from .main_menu import main_menu
    
    await delete_previous_messages(callback.message, state)
    await main_menu(callback, state) 