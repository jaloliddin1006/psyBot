#!/usr/bin/env python3
"""
Session Handlers for PsyBot
Manages therapy session scheduling and confirmation
"""

import logging
import re
from datetime import datetime, timedelta
from aiogram import Router, F, types
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.filters import StateFilter, Command
from src.database.session import get_session, close_session
from src.database.models import User, TherapySession
from src.constants import SESSION_DATE_TIME_INPUT, SESSION_CONFIRMATION
from src.handlers.utils import delete_previous_messages
from trial_manager import require_trial_access

logger = logging.getLogger(__name__)
router = Router(name=__name__)

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

def parse_datetime_input(input_text: str) -> tuple[datetime, str]:
    """
    Parse user input for date and time.
    Supports formats:
    - "15.12 в 14:30" (DD.MM at HH:MM)
    - "15.12.2024 в 14:30" (DD.MM.YYYY at HH:MM)
    - "завтра в 14:30" (tomorrow at HH:MM)
    - "сегодня в 14:30" (today at HH:MM)
    
    Returns: (datetime object, error_message)
    """
    input_text = input_text.strip().lower()
    current_year = datetime.now().year
    
    # Pattern for "DD.MM в HH:MM" or "DD.MM.YYYY в HH:MM"
    date_time_pattern = r'(\d{1,2})\.(\d{1,2})(?:\.(\d{4}))?\s*в\s*(\d{1,2}):(\d{2})'
    match = re.match(date_time_pattern, input_text)
    
    if match:
        day, month, year, hour, minute = match.groups()
        year = int(year) if year else current_year
        
        try:
            session_datetime = datetime(
                year=year,
                month=int(month),
                day=int(day),
                hour=int(hour),
                minute=int(minute)
            )
            
            # Check if the date is in the past
            if session_datetime < datetime.now():
                return None, "Указанная дата и время уже прошли. Пожалуйста, укажите будущую дату."
            
            return session_datetime, None
            
        except ValueError as e:
            return None, "Неверный формат даты или времени. Проверьте правильность введенных данных."
    
    # Pattern for "завтра в HH:MM"
    tomorrow_pattern = r'завтра\s*в\s*(\d{1,2}):(\d{2})'
    match = re.match(tomorrow_pattern, input_text)
    
    if match:
        hour, minute = match.groups()
        try:
            tomorrow = datetime.now() + timedelta(days=1)
            session_datetime = tomorrow.replace(
                hour=int(hour),
                minute=int(minute),
                second=0,
                microsecond=0
            )
            return session_datetime, None
        except ValueError:
            return None, "Неверный формат времени."
    
    # Pattern for "сегодня в HH:MM"
    today_pattern = r'сегодня\s*в\s*(\d{1,2}):(\d{2})'
    match = re.match(today_pattern, input_text)
    
    if match:
        hour, minute = match.groups()
        try:
            today = datetime.now()
            session_datetime = today.replace(
                hour=int(hour),
                minute=int(minute),
                second=0,
                microsecond=0
            )
            
            # Check if the time is in the past today
            if session_datetime < datetime.now():
                return None, "Указанное время уже прошло сегодня. Пожалуйста, укажите будущее время."
            
            return session_datetime, None
        except ValueError:
            return None, "Неверный формат времени."
    
    return None, "Не удалось распознать формат даты и времени. Пожалуйста, используйте один из предложенных форматов."

async def start_session_planning(message_or_callback, state: FSMContext):
    """Start session planning flow - can be called from command or callback"""
    if hasattr(message_or_callback, 'message'):
        # It's a callback query
        message = message_or_callback.message
        user_id = message_or_callback.from_user.id
    else:
        # It's a message
        message = message_or_callback
        user_id = message.from_user.id
    
    logger.info(f"Session planning triggered by user {user_id}")
    
    # Check if user is registered
    session = get_session()
    db_user = session.query(User).filter(User.telegram_id == user_id).first()
    
    if not db_user or not getattr(db_user, "registration_complete", False):
        close_session(session)
        await message.answer(
            "Для использования этой функции необходимо завершить регистрацию. "
            "Пожалуйста, введите /start для начала регистрации."
        )
        return
    
    close_session(session)
    
    # Clear previous state and start session scheduling
    await state.clear()
    
    format_examples = """
📅 **Форматы ввода даты и времени:**

• `15.12 в 14:30` - 15 декабря в 14:30
• `15.12.2024 в 14:30` - 15 декабря 2024 года в 14:30  
• `завтра в 14:30` - завтра в 14:30
• `сегодня в 16:00` - сегодня в 16:00

💡 Время указывайте в формате 24 часа (например: 14:30, а не 2:30)
"""
    
    sent_message = await message.answer(
        "Когда у тебя следующая встреча с психологом? "
        f"Укажи дату и время в одном из следующих форматов:\n\n{format_examples}"
    )
    
    # Add both messages to deletion list (if it's a message, add it too)
    messages_to_delete = []
    if not hasattr(message_or_callback, 'message'):
        # Only add to deletion list if it's a direct message (not callback)
        messages_to_delete.append(message.message_id)
    messages_to_delete.append(sent_message.message_id)
    
    await state.update_data(messages_to_delete=messages_to_delete)
    await state.set_state(SESSION_DATE_TIME_INPUT)

@router.message(Command("session"))
async def cmd_session(message: Message, state: FSMContext):
    """Handle /session command"""
    await start_session_planning(message, state)

@router.message(StateFilter(SESSION_DATE_TIME_INPUT))
async def handle_session_datetime_input(message: Message, state: FSMContext):
    """Handle user input for session date and time"""
    logger.info(f"Processing session datetime input from user {message.from_user.id}: {message.text}")
    
    # Parse the datetime input (no timezone conversion needed)
    session_datetime, error_message = parse_datetime_input(message.text)
    
    # Add current message to deletion list
    data = await state.get_data()
    messages_to_delete = data.get('messages_to_delete', [])
    messages_to_delete.append(message.message_id)
    
    if error_message:
        # Send error message and ask again
        error_msg = await message.answer(
            f"❌ {error_message}\n\n"
            "Пожалуйста, попробуйте еще раз, используя один из предложенных форматов."
        )
        messages_to_delete.append(error_msg.message_id)
        await state.update_data(messages_to_delete=messages_to_delete)
        return
    
    # Delete previous messages
    await state.update_data(messages_to_delete=messages_to_delete)
    await delete_previous_messages(message, state)
    
    # Format the datetime for confirmation (no conversion needed)
    formatted_datetime = session_datetime.strftime("%d.%m.%Y в %H:%M")
    day_name = session_datetime.strftime("%A")
    
    # Translate day name to Russian
    day_translations = {
        "Monday": "понедельник",
        "Tuesday": "вторник", 
        "Wednesday": "среда",
        "Thursday": "четверг",
        "Friday": "пятница",
        "Saturday": "суббота",
        "Sunday": "воскресенье"
    }
    day_name_ru = day_translations.get(day_name, day_name)
    
    # Calculate reflection time (5 hours after session)
    reflection_datetime = session_datetime + timedelta(hours=5)
    reflection_formatted = reflection_datetime.strftime("%d.%m.%Y в %H:%M")
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Да, все верно", callback_data="confirm_session")],
        [InlineKeyboardButton(text="❌ Нет, изменить", callback_data="change_session")],
    ])
    
    confirmation_text = (
        f"Твоя встреча: **{formatted_datetime}** ({day_name_ru})\n\n"
        f"Отлично! Я отправлю тебе форму для рефлексии **{reflection_formatted}** "
        f"(через 5 часов после встречи).\n\n"
        f"Все верно?"
    )
    
    sent_message = await message.answer(
        confirmation_text,
        reply_markup=keyboard
    )
    
    # Store session data for confirmation
    await state.update_data(
        messages_to_delete=[sent_message.message_id],
        session_datetime=session_datetime.isoformat(),
        reflection_datetime=reflection_datetime.isoformat(),
        formatted_datetime=formatted_datetime,
        day_name_ru=day_name_ru
    )
    await state.set_state(SESSION_CONFIRMATION)

@router.callback_query(F.data == "confirm_session", StateFilter(SESSION_CONFIRMATION))
@require_trial_access('therapy_themes')
async def handle_session_confirmation(callback: types.CallbackQuery, state: FSMContext):
    """Handle session confirmation"""
    await callback.answer()
    
    # Get stored session data
    data = await state.get_data()
    session_datetime_str = data.get('session_datetime')
    reflection_datetime_str = data.get('reflection_datetime')
    formatted_datetime = data.get('formatted_datetime')
    
    if not session_datetime_str or not reflection_datetime_str:
        await callback.message.answer("Произошла ошибка. Пожалуйста, попробуйте еще раз с /session")
        await state.clear()
        return
    
    # Parse datetime strings back to datetime objects
    session_datetime = datetime.fromisoformat(session_datetime_str)
    reflection_datetime = datetime.fromisoformat(reflection_datetime_str)
    
    # Save to database
    session = get_session()
    try:
        db_user = session.query(User).filter(User.telegram_id == callback.from_user.id).first()
        
        if not db_user:
            await callback.message.answer("Пользователь не найден. Пожалуйста, начните регистрацию с /start")
            return
        
        # Create new therapy session record
        therapy_session = TherapySession(
            user_id=db_user.id,
            session_datetime=session_datetime,
            reflection_datetime=reflection_datetime,
            reflection_sent=False
        )
        
        session.add(therapy_session)
        session.commit()
        
        logger.info(f"Therapy session scheduled for user {db_user.full_name} (ID: {db_user.id}) "
                   f"at {session_datetime}, reflection at {reflection_datetime}")
        
    except Exception as e:
        logger.error(f"Failed to save therapy session: {e}")
        await callback.message.answer("Произошла ошибка при сохранении. Пожалуйста, попробуйте еще раз.")
        session.rollback()
        return
    finally:
        close_session(session)
    
    # Delete previous messages and send confirmation
    await delete_previous_messages(callback.message, state)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏠 Главное меню", callback_data="session_to_main")]
    ])
    
    success_message = (
        f"✅ **Встреча запланирована!**\n\n"
        f"📅 Дата и время: {formatted_datetime}\n"
        f"🔔 Напоминание о рефлексии будет отправлено автоматически через 5 часов после встречи.\n\n"
        f"Удачной терапии! 💙"
    )
    
    sent_message = await callback.message.answer(
        success_message,
        reply_markup=keyboard
    )
    
    await state.update_data(messages_to_delete=[sent_message.message_id])
    await state.clear()

@router.callback_query(F.data == "change_session", StateFilter(SESSION_CONFIRMATION))
@require_trial_access('therapy_themes')
async def handle_session_change(callback: types.CallbackQuery, state: FSMContext):
    """Handle request to change session time"""
    await callback.answer()
    await delete_previous_messages(callback.message, state)
    
    format_examples = """
📅 **Форматы ввода даты и времени:**

• `15.12 в 14:30` - 15 декабря в 14:30
• `15.12.2024 в 14:30` - 15 декабря 2024 года в 14:30  
• `завтра в 14:30` - завтра в 14:30
• `сегодня в 16:00` - сегодня в 16:00

💡 Время указывайте в формате 24 часа (например: 14:30, а не 2:30)
"""
    
    sent_message = await callback.message.answer(
        f"Укажите новую дату и время встречи:\n\n{format_examples}"
    )
    
    await state.update_data(messages_to_delete=[sent_message.message_id])
    await state.set_state(SESSION_DATE_TIME_INPUT)

@router.callback_query(F.data == "session_to_main")
@require_trial_access('therapy_themes')
async def handle_session_to_main(callback: types.CallbackQuery, state: FSMContext):
    """Return to main menu from session scheduling"""
    from .utils import show_pin_recommendation_and_main_menu
    await show_pin_recommendation_and_main_menu(callback, state) 