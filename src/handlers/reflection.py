import logging
from aiogram import Router, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.filters import StateFilter, Command
from database.session import get_session, close_session
from database.models import User, ReflectionEntry
from constants import (
    REFLECTION_VALUABLE_LEARNED,
    REFLECTION_OPENNESS_LEVEL,
    REFLECTION_OBSTACLES,
    REFLECTION_NEXT_TOPICS,
    REFLECTION_CONFIRMATION
)
from google import genai
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

@router.message(Command("reflection"))
async def cmd_reflection(message: Message, state: FSMContext):
    """Handle /reflection command"""
    logger.info(f"Reflection command triggered by user {message.from_user.id}")
    
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
    
    # Start reflection process
    await start_reflection(message, state)

async def start_reflection(message: Message, state: FSMContext):
    """Start the reflection process"""
    logger.info(f"Starting reflection for user {message.from_user.id}")
    
    # Clear previous state data except for messages_to_delete
    current_data = await state.get_data()
    messages_to_delete = current_data.get('messages_to_delete', [])
    
    await delete_previous_messages(message, state)
    
    # Initialize reflection data
    await state.update_data({
        'messages_to_delete': [],
        'reflection_data': {
            'valuable_learned': None,
            'openness_level': None,
            'obstacles': None,
            'next_topics': None
        }
    })
    
    # Ask the first question
    sent_message = await message.answer(
        "Давайте проведем рефлексию вашей встречи с психотерапевтом.\n\n"
        "Что ценного ты узнала сегодня? Что стоит запомнить?"
    )
    
    await state.update_data(messages_to_delete=[sent_message.message_id])
    await state.set_state(REFLECTION_VALUABLE_LEARNED)

@router.message(StateFilter(REFLECTION_VALUABLE_LEARNED))
async def handle_valuable_learned(message: Message, state: FSMContext):
    """Handle the first question response"""
    logger.info(f"Handling valuable learned response from user {message.from_user.id}")
    
    # Save the answer
    data = await state.get_data()
    reflection_data = data.get('reflection_data', {})
    reflection_data['valuable_learned'] = message.text
    
    # Add current message to deletion list
    messages_to_delete = data.get('messages_to_delete', [])
    messages_to_delete.append(message.message_id)
    
    await delete_previous_messages(message, state)
    
    # Ask the second question
    sent_message = await message.answer(
        "Насколько полно ты смогла открыться психотерапевту сегодня?"
    )
    
    await state.update_data({
        'messages_to_delete': [sent_message.message_id],
        'reflection_data': reflection_data
    })
    await state.set_state(REFLECTION_OPENNESS_LEVEL)

@router.message(StateFilter(REFLECTION_OPENNESS_LEVEL))
async def handle_openness_level(message: Message, state: FSMContext):
    """Handle the second question response"""
    logger.info(f"Handling openness level response from user {message.from_user.id}")
    
    # Save the answer
    data = await state.get_data()
    reflection_data = data.get('reflection_data', {})
    reflection_data['openness_level'] = message.text
    
    # Add current message to deletion list
    messages_to_delete = data.get('messages_to_delete', [])
    messages_to_delete.append(message.message_id)
    
    await delete_previous_messages(message, state)
    
    # Ask the third question
    sent_message = await message.answer(
        "Было ли сегодня что-то, что мешало на терапии? Если да, что именно?"
    )
    
    await state.update_data({
        'messages_to_delete': [sent_message.message_id],
        'reflection_data': reflection_data
    })
    await state.set_state(REFLECTION_OBSTACLES)

@router.message(StateFilter(REFLECTION_OBSTACLES))
async def handle_obstacles(message: Message, state: FSMContext):
    """Handle the third question response"""
    logger.info(f"Handling obstacles response from user {message.from_user.id}")
    
    # Save the answer
    data = await state.get_data()
    reflection_data = data.get('reflection_data', {})
    reflection_data['obstacles'] = message.text
    
    # Add current message to deletion list
    messages_to_delete = data.get('messages_to_delete', [])
    messages_to_delete.append(message.message_id)
    
    await delete_previous_messages(message, state)
    
    # Ask the fourth question
    sent_message = await message.answer(
        "Какие темы ты хочешь обсудить на следующей неделе?"
    )
    
    await state.update_data({
        'messages_to_delete': [sent_message.message_id],
        'reflection_data': reflection_data
    })
    await state.set_state(REFLECTION_NEXT_TOPICS)

@router.message(StateFilter(REFLECTION_NEXT_TOPICS))
async def handle_next_topics(message: Message, state: FSMContext):
    """Handle the fourth question response and show reflection summary"""
    logger.info(f"Handling next topics response from user {message.from_user.id}")
    
    # Save the answer
    data = await state.get_data()
    reflection_data = data.get('reflection_data', {})
    reflection_data['next_topics'] = message.text
    
    # Add current message to deletion list
    messages_to_delete = data.get('messages_to_delete', [])
    messages_to_delete.append(message.message_id)
    
    await delete_previous_messages(message, state)
    
    # Get user name for AI transcription
    session = get_session()
    try:
        db_user = session.query(User).filter(User.telegram_id == message.from_user.id).first()
        user_name = db_user.full_name if db_user else None
    finally:
        close_session(session)
    
    # Generate AI transcription
    try:
        ai_transcription = await generate_ai_transcription(reflection_data, user_name)
    except Exception as e:
        logger.error(f"Failed to generate AI transcription: {e}")
        ai_transcription = "Не удалось создать краткое изложение."
    
    # Store AI transcription in the reflection data
    reflection_data['ai_transcription'] = ai_transcription
    
    # Show reflection summary to user
    summary_text = f"""📝 Ваша рефлексия готова! Проверьте, все ли правильно:

🌟 **Что ценного вы узнали сегодня:**
{reflection_data['valuable_learned']}

💝 **Насколько полно смогли открыться психотерапевту:**
{reflection_data['openness_level']}

🚧 **Что мешало на терапии:**
{reflection_data['obstacles']}

🎯 **Темы для следующей недели:**
{reflection_data['next_topics']}

🤖 **Краткое изложение:**
{ai_transcription}

Сохранить эту рефлексию?"""
    
    # Create confirmation keyboard
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Сохранить", callback_data="reflection_confirm_save"),
            InlineKeyboardButton(text="❌ Отменить", callback_data="reflection_cancel_save")
        ]
    ])
    
    summary_message = await message.answer(
        summary_text,
        reply_markup=keyboard,
    )
    
    await state.update_data({
        'messages_to_delete': [summary_message.message_id],
        'reflection_data': reflection_data
    })
    await state.set_state(REFLECTION_CONFIRMATION)

async def generate_ai_transcription(reflection_data: dict, user_name: str = None) -> str:
    """Generate AI transcription of user's reflection answers"""
    try:
        # Use provided name or default
        name_text = f"{user_name}" if user_name else "Пользователь"
        
        prompt = f"""
Создай краткое и структурированное изложение рефлексии пользователя после сессии с психотерапевтом. 
Используй следующие ответы:

1. Что ценного узнала: {reflection_data['valuable_learned']}
2. Уровень открытости: {reflection_data['openness_level']}
3. Препятствия на терапии: {reflection_data['obstacles']}
4. Темы для следующей недели: {reflection_data['next_topics']}

Создай краткое изложение (2-3 предложения), которое отражает основные моменты сессии и планы на будущее.
Пиши от третьего лица, используя прошедшее время. Используй имя "{name_text}" вместо "пользователь" или "пользовательница".
Обрати внимание на правильное согласование глаголов и прилагательных с именем.
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
        # Fallback to simple concatenation with name
        name_text = f"{user_name}" if user_name else "Пользователь"
        # Use gender-neutral verb form
        verb = "оценила сессию как ценную, узнав" if user_name else "узнал"
        return f"{name_text} {verb}: {reflection_data['valuable_learned'][:50]}... " \
               f"Планирует обсудить: {reflection_data['next_topics'][:50]}..."

@router.callback_query(F.data == "reflection_confirm_save")
@require_trial_access('reflection')
async def reflection_confirm_save_callback(callback, state: FSMContext):
    """Handle confirmation to save the reflection"""
    await callback.answer()
    
    logger.info(f"User {callback.from_user.id} confirmed saving reflection")
    
    # Get reflection data
    data = await state.get_data()
    reflection_data = data.get('reflection_data', {})
    
    # Save to database
    session = get_session()
    try:
        db_user = session.query(User).filter(User.telegram_id == callback.from_user.id).first()
        if db_user:
            logger.info(f"Found user in database: ID={db_user.id}, telegram_id={db_user.telegram_id}, name={db_user.full_name}")
            reflection_entry = ReflectionEntry(
                user_id=db_user.id,
                valuable_learned=reflection_data['valuable_learned'],
                openness_level=reflection_data['openness_level'],
                obstacles=reflection_data['obstacles'],
                next_topics=reflection_data['next_topics'],
                ai_transcription=reflection_data.get('ai_transcription', 'Не удалось создать краткое изложение.')
            )
            session.add(reflection_entry)
            session.commit()
            logger.info(f"Successfully saved reflection entry for user {callback.from_user.id} (DB ID: {db_user.id})")
        else:
            logger.error(f"User not found in database for telegram_id: {callback.from_user.id}")
            # Let's check what users exist
            all_users = session.query(User).all()
            logger.error(f"Available users in database: {[(u.id, u.telegram_id, u.full_name) for u in all_users]}")
    except Exception as e:
        logger.error(f"Failed to save reflection entry: {e}")
        import traceback
        logger.error(f"Full traceback: {traceback.format_exc()}")
        session.rollback()
    finally:
        close_session(session)
    
    await delete_previous_messages(callback.message, state)
    
    # Show completion message with button to main menu
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="На главную", callback_data="reflection_to_main")]
    ])
    
    completion_message = await callback.message.answer(
        "✅ Спасибо! Рефлексия успешно сохранена!",
        reply_markup=keyboard
    )
    
    await state.update_data({
        'messages_to_delete': [completion_message.message_id],
        'reflection_data': {}
    })

@router.callback_query(F.data == "reflection_cancel_save")
@require_trial_access('reflection')
async def reflection_cancel_save_callback(callback, state: FSMContext):
    """Handle cancellation of saving the reflection"""
    await callback.answer()
    
    logger.info(f"User {callback.from_user.id} cancelled saving reflection")
    
    await delete_previous_messages(callback.message, state)
    
    # Show cancellation message with button to main menu
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="На главную", callback_data="reflection_to_main")]
    ])
    
    cancel_message = await callback.message.answer(
        "❌ Рефлексия не сохранена. Вы можете начать заново в любое время.",
        reply_markup=keyboard
    )
    
    await state.update_data({
        'messages_to_delete': [cancel_message.message_id],
        'reflection_data': {}
    })

@router.callback_query(F.data == "reflection_to_main")
@require_trial_access('reflection')
async def reflection_to_main_callback(callback, state: FSMContext):
    """Handle return to main menu from reflection"""
    await callback.answer()
    
    # Import here to avoid circular imports
    from .main_menu import main_menu
    
    await delete_previous_messages(callback.message, state)
    await main_menu(callback, state) 