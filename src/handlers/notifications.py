#!/usr/bin/env python3
"""
Notification Settings Handlers for PsyBot
Manages user notification preferences and timezone settings
"""

import logging
from datetime import datetime
import pytz

from aiogram import Router, F, types
from aiogram.filters import StateFilter, Command
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton

from src.constants import NOTIFICATION_FREQUENCY_SELECTION, TIMEZONE_SELECTION_STATE
from src.database.models import User
from src.database.session import get_session, close_session
from src.handlers.utils import delete_previous_messages
from src.trial_manager import require_trial_access

# Initialize logger and router
logger = logging.getLogger(__name__)
router = Router(name=__name__)

@router.message(Command("notify"))
async def notify_command(message: types.Message, state: FSMContext):
    """Handle /notify command to set notification frequency"""
    logger.info(f"notify_command invoked. message.from_user.id: {message.from_user.id}")
    
    # Check if user is registered
    session = get_session()
    db_user = session.query(User).filter(User.telegram_id == message.from_user.id).first()
    
    if not db_user or not getattr(db_user, 'registration_complete', False) or not db_user.full_name:
        close_session(session)
        await state.clear()
        await message.answer("Пожалуйста, завершите регистрацию с помощью /start перед настройкой уведомлений.")
        return
    
    current_frequency = db_user.notification_frequency
    close_session(session)
    
    # Store message for deletion
    data = await state.get_data()
    messages_to_delete = data.get('messages_to_delete', [])
    messages_to_delete.append(message.message_id)
    await state.update_data(messages_to_delete=messages_to_delete)
    
    # Get user's timezone info
    user_timezone = getattr(db_user, 'user_timezone', 'UTC+0') or 'UTC+0'
    
    # Create keyboard with frequency options
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="1 раз в день", callback_data="freq_1")],
        [InlineKeyboardButton(text="2 раза в день", callback_data="freq_2")],
        [InlineKeyboardButton(text="4 раза в день", callback_data="freq_4")],
        [InlineKeyboardButton(text="6 раз в день", callback_data="freq_6")],
        [InlineKeyboardButton(text="🔕 Отключить уведомления", callback_data="freq_0")],
        [InlineKeyboardButton(text="🌍 Изменить часовой пояс", callback_data="change_timezone")],
        [InlineKeyboardButton(text="В главное меню", callback_data="back_to_main")]
    ])
    
    frequency_text = {
        0: "отключены",
        1: "1 раз в день",
        2: "2 раза в день",
        4: "4 раза в день",
        6: "6 раз в день"
    }
    
    sent = await message.answer(
        f"Настройки уведомлений:\n\n"
        f"📅 Частота: {frequency_text.get(current_frequency, 'не установлена')}\n"
        f"🌍 Часовой пояс: {user_timezone}\n\n"
        f"Как часто вы хотите получать напоминания о дневнике эмоций?\n\n"
        f"💡 Уведомления помогают регулярно отслеживать эмоции и лучше понимать себя.",
        reply_markup=keyboard
    )
    
    messages_to_delete.append(sent.message_id)
    await state.update_data(messages_to_delete=messages_to_delete)
    await state.set_state(NOTIFICATION_FREQUENCY_SELECTION)

@router.callback_query(StateFilter(NOTIFICATION_FREQUENCY_SELECTION), F.data.in_(["freq_1", "freq_2", "freq_4", "freq_6", "freq_0", "change_timezone", "back_to_main"]))
@require_trial_access('notifications')
async def handle_frequency_selection(callback: types.CallbackQuery, state: FSMContext):
    """Handle frequency selection"""
    logger.info(f"handle_frequency_selection called with data: {callback.data}")
    await callback.answer()
    
    if callback.data == "back_to_main":
        from src.handlers.main_menu import main_menu
        await delete_previous_messages(callback.message, state)
        await state.clear()
        await main_menu(callback, state)
        return
    
    if callback.data == "change_timezone":
        await delete_previous_messages(callback.message, state)
        
        # Ask for current time to calculate timezone
        server_time = datetime.now()
        server_time_str = server_time.strftime("%H:%M")
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Назад к настройкам", callback_data="back_to_notifications")]
        ])
        
        msg = await callback.message.answer(
            f"Чтобы обновить ваш часовой пояс, скажите, сколько сейчас времени у вас?\n\n"
            f"⏰ Напишите текущее время в формате ЧЧ:ММ (например: 16:54)\n\n"
            f"💡 Это поможет мне точно рассчитать ваш часовой пояс.",
            reply_markup=keyboard
        )
        
        await state.update_data(messages_to_delete=[msg.message_id], server_time=server_time_str)
        await state.set_state(TIMEZONE_SELECTION_STATE)
        return
    
    # Extract frequency from callback data
    frequency = int(callback.data.split("_")[1])
    
    # Update user's notification frequency in database
    session = get_session()
    db_user = session.query(User).filter(User.telegram_id == callback.from_user.id).first()
    
    if db_user:
        db_user.notification_frequency = frequency
        session.commit()
        
        # Create confirmation message
        frequency_text = {
            0: "отключены",
            1: "1 раз в день",
            2: "2 раза в день",
            4: "4 раза в день",
            6: "6 раз в день"
        }
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="В главное меню", callback_data="back_to_main")]
        ])
        
        if frequency == 0:
            confirmation_text = (
                f"✅ Настройки сохранены!\n\n"
                f"Уведомления отключены. Вы можете включить их в любое время с помощью команды /notify.\n\n"
                f"💡 Помните: регулярное отслеживание эмоций помогает лучше понимать себя!"
            )
        else:
            confirmation_text = (
                f"✅ Настройки сохранены!\n\n"
                f"Теперь вы будете получать напоминания о дневнике эмоций {frequency_text[frequency]}.\n\n"
                f"🔔 Первое уведомление придет в ближайшее запланированное время."
            )
        
        await callback.message.edit_text(
            confirmation_text,
            reply_markup=keyboard
        )
        
    close_session(session)

@router.message(StateFilter(TIMEZONE_SELECTION_STATE), F.text.regexp(r"^\d{1,2}:\d{2}$"))
async def handle_timezone_change_from_time(message: types.Message, state: FSMContext):
    """Handle timezone change from notification settings using time input"""
    logger.info(f"handle_timezone_change_from_time triggered with text: {message.text}")
    
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
    
    # Update user's timezone in database
    session = get_session()
    db_user = session.query(User).filter(User.telegram_id == message.from_user.id).first()
    
    if db_user:
        db_user.timezone_offset = timezone_offset
        db_user.user_timezone = user_timezone
        session.commit()
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Назад к настройкам", callback_data="back_to_notifications")],
            [InlineKeyboardButton(text="В главное меню", callback_data="back_to_main")]
        ])
        
        msg = await message.answer(
            f"✅ Часовой пояс обновлен!\n\n"
            f"Ваше время: {user_time_str}, время сервера: {server_time_str}\n"
            f"Определенный часовой пояс: {user_timezone}\n\n"
            f"🔔 Уведомления теперь будут приходить по вашему местному времени.",
            reply_markup=keyboard
        )
        
        await state.update_data(messages_to_delete=[msg.message_id])
        
    close_session(session)

@router.callback_query(F.data == "back_to_notifications")
@require_trial_access('notifications')
async def back_to_notifications(callback: types.CallbackQuery, state: FSMContext):
    """Handle back to notification settings"""
    await callback.answer()
    await delete_previous_messages(callback.message, state)
    
    # Get user data and show notification settings
    session = get_session()
    db_user = session.query(User).filter(User.telegram_id == callback.from_user.id).first()
    
    if not db_user or not getattr(db_user, 'registration_complete', False) or not db_user.full_name:
        close_session(session)
        await state.clear()
        await callback.message.answer("Пожалуйста, завершите регистрацию с помощью /start перед настройкой уведомлений.")
        return
    
    current_frequency = db_user.notification_frequency
    user_timezone = getattr(db_user, 'user_timezone', 'UTC+0') or 'UTC+0'
    close_session(session)
    
    # Create keyboard with frequency options
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="1 раз в день", callback_data="freq_1")],
        [InlineKeyboardButton(text="2 раза в день", callback_data="freq_2")],
        [InlineKeyboardButton(text="4 раза в день", callback_data="freq_4")],
        [InlineKeyboardButton(text="6 раз в день", callback_data="freq_6")],
        [InlineKeyboardButton(text="🔕 Отключить уведомления", callback_data="freq_0")],
        [InlineKeyboardButton(text="🌍 Изменить часовой пояс", callback_data="change_timezone")],
        [InlineKeyboardButton(text="В главное меню", callback_data="back_to_main")]
    ])
    
    frequency_text = {
        0: "отключены",
        1: "1 раз в день",
        2: "2 раза в день",
        4: "4 раза в день",
        6: "6 раз в день"
    }
    
    sent = await callback.message.answer(
        f"Настройки уведомлений:\n\n"
        f"📅 Частота: {frequency_text.get(current_frequency, 'не установлена')}\n"
        f"🌍 Часовой пояс: {user_timezone}\n\n"
        f"Как часто вы хотите получать напоминания о дневнике эмоций?\n\n"
        f"💡 Уведомления помогают регулярно отслеживать эмоции и лучше понимать себя.",
        reply_markup=keyboard
    )
    
    await state.update_data(messages_to_delete=[sent.message_id])
    await state.set_state(NOTIFICATION_FREQUENCY_SELECTION)

@router.callback_query(F.data == "back_to_main")
@require_trial_access('notifications')
async def back_to_main_from_notifications(callback: types.CallbackQuery, state: FSMContext):
    """Handle back to main menu from notifications"""
    await callback.answer()
    from src.handlers.main_menu import main_menu
    await delete_previous_messages(callback.message, state)
    await state.clear()
    await main_menu(callback, state) 