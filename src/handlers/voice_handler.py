#!/usr/bin/env python3
"""
Voice Message Handler for PsyBot
Handles voice message transcription and processing
"""

import logging
import asyncio
import os
import tempfile
from pathlib import Path
from typing import Optional
from aiogram import Router, F, types
from aiogram.types import Message, Voice, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.filters import StateFilter
import openai
from dotenv import load_dotenv
from pydub import AudioSegment
from src.constants import VOICE_TRANSCRIPTION_CONFIRMATION
from src.database.models import User
from src.database.session import get_session, close_session
from src.handlers.utils import delete_previous_messages
from src.trial_manager import require_trial_access

load_dotenv()

logger = logging.getLogger(__name__)
router = Router(name=__name__)

# Configure OpenAI client with proxy support
def get_openai_client():
    """Get OpenAI client with proxy configuration if available"""
    api_key = os.getenv("GOOGLE_GENAI_API_KEY")
    if not api_key:
        logger.error("GOOGLE_GENAI_API_KEY not found in environment variables")
        return None
    
    # Check for proxy configuration
    proxy_url = os.getenv("VOICE_API_URL")
    
    if proxy_url:
        # Configure client with proxy
        client = openai.OpenAI(
            api_key=api_key,
            base_url=proxy_url,
            # Add timeout and other configurations as needed
            timeout=60.0
        )
        logger.info(f"OpenAI client configured with voice proxy: {proxy_url}")
    else:
        # Standard OpenAI client
        client = openai.OpenAI(api_key=api_key)
        logger.info("OpenAI client configured with standard endpoint")
    
    return client

async def transcribe_voice_message(voice: Voice, bot) -> Optional[str]:
    """
    Download voice message, convert to MP3, and transcribe it using OpenAI
    Returns transcribed text or None if transcription fails
    """
    client = get_openai_client()
    if not client:
        return None
    
    oga_temp_path = None
    mp3_temp_path = None
    
    try:
        # Download voice file (OGA format)
        file_info = await bot.get_file(voice.file_id)
        
        # Create temporary file for OGA
        with tempfile.NamedTemporaryFile(suffix=".oga", delete=False) as temp_file:
            oga_temp_path = temp_file.name
            
        # Download the OGA file
        await bot.download_file(file_info.file_path, oga_temp_path)
        logger.info(f"Downloaded OGA file: {oga_temp_path}")
        
        # Convert OGA to MP3
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as temp_file:
            mp3_temp_path = temp_file.name
        
        # Use pydub to convert OGA to MP3
        audio = AudioSegment.from_ogg(oga_temp_path)
        audio.export(mp3_temp_path, format="mp3")
        logger.info(f"Converted to MP3: {mp3_temp_path}")
        
        try:
            # Transcribe using the MP3 file
            with open(mp3_temp_path, "rb") as audio_file:
                transcription = client.audio.transcriptions.create(
                    model="gpt-4o-transcribe",
                    file=audio_file,
                    language="ru"
                )
            
            transcribed_text = transcription.text.strip()
            logger.info(f"Voice message transcribed successfully. Length: {len(transcribed_text)} characters")
            return transcribed_text
            
        except Exception as e:
            logger.error(f"OpenAI transcription failed: {e}")
            return None
            
    except Exception as e:
        logger.error(f"Failed to download or process voice message: {e}")
        return None
    finally:
        # Clean up temporary files
        for temp_path in [oga_temp_path, mp3_temp_path]:
            if temp_path and os.path.exists(temp_path):
                try:
                    os.unlink(temp_path)
                    logger.debug(f"Cleaned up temporary file: {temp_path}")
                except Exception as e:
                    logger.warning(f"Failed to clean up temporary file {temp_path}: {e}")

class MockMessage:
    """Mock message class to simulate text message from transcribed voice"""
    def __init__(self, original_message: Message, transcribed_text: str):
        # Copy all essential attributes from original message
        self.message_id = original_message.message_id
        self.from_user = original_message.from_user
        self.chat = original_message.chat
        self.date = original_message.date
        self.bot = original_message.bot
        
        # Set the transcribed text
        self.text = transcribed_text
        
        # Copy other necessary message methods and attributes
        for attr in ['answer', 'reply', 'edit_text', 'delete', 'reply_to_message', 
                     'message_thread_id', 'content_type']:
            if hasattr(original_message, attr):
                setattr(self, attr, getattr(original_message, attr))

@router.message(F.voice)
async def handle_voice_message(message: Message, state: FSMContext):
    """
    Handle voice messages by transcribing them and processing as text
    Only works in states that expect text input, not for menu navigation
    """
    user_id = message.from_user.id
    voice = message.voice
    
    logger.info(f"Received voice message from user {user_id}, duration: {voice.duration}s")
    
    # Check current FSM state
    current_state = await state.get_state()
    
    # Define states where voice input is allowed (text input states)
    TEXT_INPUT_STATES = {
        # Registration states that expect text
        "NAME",
        "AGE",
        
        # Thought diary text input states
        "THOUGHT_DIARY_AWAITING_POSITIVE_ENTRY_STATE",
        "THOUGHT_DIARY_AWAITING_NEGATIVE_ENTRY_STATE",
        
        # Reflection text input states
        "REFLECTION_VALUABLE_LEARNED_STATE",
        "REFLECTION_OPENNESS_LEVEL_STATE", 
        "REFLECTION_OBSTACLES_STATE",
        "REFLECTION_NEXT_TOPICS_STATE",
        
        # Weekly reflection text input states
        "WEEKLY_REFLECTION_SMILE_MOMENT_STATE",
        "WEEKLY_REFLECTION_KINDNESS_STATE",
        "WEEKLY_REFLECTION_PEACE_STATE",
        "WEEKLY_REFLECTION_NEW_DISCOVERY_STATE",
        "WEEKLY_REFLECTION_GRATITUDE_STATE",
        
        # Therapy themes text input states
        "THERAPY_THEMES_ADD_INPUT_STATE",
        "THERAPY_THEMES_DELETE_INPUT_STATE",
        
        # Session scheduling text input
        "SESSION_DATE_TIME_INPUT_STATE",
    }
    
    # Check if current state allows voice input
    if current_state not in TEXT_INPUT_STATES:
        await message.reply(
            "🎤 Голосовые сообщения можно использовать только для ввода текста "
            "(например, при заполнении дневника эмоций или рефлексии).\n\n"
            "Для навигации по меню используйте кнопки."
        )
        return
    
    # Check if OpenAI is configured
    if not os.getenv("GOOGLE_GENAI_API_KEY"):
        await message.reply(
            "🔧 Извините, функция распознавания голосовых сообщений временно недоступна. "
            "Пожалуйста, отправьте текстовое сообщение."
        )
        return
    
    # Send processing message
    processing_msg = await message.reply("🎤 Обрабатываю голосовое сообщение...")
    
    try:
        # Transcribe the voice message
        transcribed_text = await transcribe_voice_message(voice, message.bot)
        
        if not transcribed_text:
            await processing_msg.edit_text(
                "❌ Не удалось распознать голосовое сообщение. "
                "Попробуйте записать сообщение заново или отправьте текст."
            )
            return
        
        # Update processing message with transcription result and add accept/reject buttons
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Принять", callback_data="voice_accept"),
                InlineKeyboardButton(text="❌ Отклонить", callback_data="voice_reject")
            ]
        ])
        
        await processing_msg.edit_text(
            f"🎤 Распознано: *{transcribed_text}*\n\nПравильно ли распознан текст?",
            reply_markup=keyboard
        )
        
        # Store transcription data and original state for later processing
        data = await state.get_data()
        await state.update_data(
            voice_transcribed_text=transcribed_text,
            voice_original_message_id=message.message_id,
            voice_original_state=current_state,
            voice_confirmation_msg_id=processing_msg.message_id,
            messages_to_delete=data.get('messages_to_delete', [])
        )
        
        # Set state to wait for confirmation
        await state.set_state(VOICE_TRANSCRIPTION_CONFIRMATION)
            
    except Exception as e:
        logger.error(f"Error processing voice message: {e}")
        await processing_msg.edit_text(
            "❌ Произошла ошибка при обработке голосового сообщения. "
            "Попробуйте отправить текстовое сообщение."
        )

async def route_to_text_input_handler(mock_message: MockMessage, state: FSMContext, current_state: str):
    """Route to existing FSM state handlers for text input"""
    try:
        logger.info(f"Routing voice message to text input handler for state: {current_state}")
        
        # Import handlers to access their functions
        from .thought_diary import process_positive_entry, process_negative_entry
        from .weekly_reflection import handle_smile_moment, handle_kindness, handle_peace_moment, handle_new_discovery, handle_gratitude
        from .reflection import handle_valuable_learned, handle_openness_level, handle_obstacles, handle_next_topics
        from .therapy_themes import handle_add_theme_input, handle_delete_time_input
        from .session import handle_session_datetime_input
        
        # Route based on current FSM state
        if current_state == "THOUGHT_DIARY_AWAITING_POSITIVE_ENTRY_STATE":
            await process_positive_entry(mock_message, state)
        elif current_state == "THOUGHT_DIARY_AWAITING_NEGATIVE_ENTRY_STATE":
            await process_negative_entry(mock_message, state)
        elif current_state == "WEEKLY_REFLECTION_SMILE_MOMENT_STATE":
            await handle_smile_moment(mock_message, state)
        elif current_state == "WEEKLY_REFLECTION_KINDNESS_STATE":
            await handle_kindness(mock_message, state)
        elif current_state == "WEEKLY_REFLECTION_PEACE_STATE":
            await handle_peace_moment(mock_message, state)
        elif current_state == "WEEKLY_REFLECTION_NEW_DISCOVERY_STATE":
            await handle_new_discovery(mock_message, state)
        elif current_state == "WEEKLY_REFLECTION_GRATITUDE_STATE":
            await handle_gratitude(mock_message, state)
        elif current_state == "REFLECTION_VALUABLE_LEARNED_STATE":
            await handle_valuable_learned(mock_message, state)
        elif current_state == "REFLECTION_OPENNESS_LEVEL_STATE":
            await handle_openness_level(mock_message, state)
        elif current_state == "REFLECTION_OBSTACLES_STATE":
            await handle_obstacles(mock_message, state)
        elif current_state == "REFLECTION_NEXT_TOPICS_STATE":
            await handle_next_topics(mock_message, state)
        elif current_state == "THERAPY_THEMES_ADD_INPUT_STATE":
            await handle_add_theme_input(mock_message, state)
        elif current_state == "THERAPY_THEMES_DELETE_INPUT_STATE":
            await handle_delete_time_input(mock_message, state)
        elif current_state == "SESSION_DATE_TIME_INPUT_STATE":
            await handle_session_datetime_input(mock_message, state)
        elif current_state == "NAME":
            # Handle registration name input
            from .registration import handle_name_input
            await handle_name_input(mock_message, state)
        elif current_state == "AGE":
            # Handle registration age input
            from .registration import handle_age_input
            await handle_age_input(mock_message, state)
        else:
            # Unknown text input state
            logger.warning(f"Unknown text input state for voice routing: {current_state}")
            await mock_message.reply(
                f"✅ Голосовое сообщение распознано: \"{mock_message.text}\"\n\n"
                "Пожалуйста, используйте кнопки для продолжения."
            )
            
    except Exception as e:
        logger.error(f"Error routing to text input handler {current_state}: {e}")
        # Fallback - just show the transcribed text
        await mock_message.reply(
            f"✅ Голосовое сообщение распознано: \"{mock_message.text}\"\n\n"
            "Произошла ошибка при обработке. Пожалуйста, используйте кнопки для продолжения."
        )

# Callback handlers for voice transcription confirmation
@router.callback_query(StateFilter(VOICE_TRANSCRIPTION_CONFIRMATION), F.data == "voice_accept")
@require_trial_access('emotion_diary')
async def handle_voice_accept(callback: types.CallbackQuery, state: FSMContext):
    """Handle acceptance of voice transcription"""
    await callback.answer()
    user_id = callback.from_user.id
    logger.info(f"User {user_id} accepted voice transcription")
    
    # Get stored transcription data
    data = await state.get_data()
    transcribed_text = data.get('voice_transcribed_text')
    original_message_id = data.get('voice_original_message_id')
    original_state = data.get('voice_original_state')
    confirmation_msg_id = data.get('voice_confirmation_msg_id')
    
    if not transcribed_text or not original_state:
        logger.error(f"Missing voice transcription data for user {user_id}")
        await callback.message.edit_text("❌ Ошибка: данные голосового сообщения не найдены.")
        await state.clear()
        return
    
    # Update confirmation message to show acceptance
    await callback.message.edit_text(
        f"✅ Принято: *{transcribed_text}*",
    )
    
    # Create mock message for processing using callback message as base
    try:
        # Create mock message using callback message as base
        mock_message = MockMessage(callback.message, transcribed_text)
        
        # Add confirmation message to deletion list
        messages_to_delete = data.get('messages_to_delete', [])
        messages_to_delete.append(confirmation_msg_id)
        await state.update_data(messages_to_delete=messages_to_delete)
        
        # Restore original state and route to handler
        await state.set_state(original_state)
        await route_to_text_input_handler(mock_message, state, original_state)
        
    except Exception as e:
        logger.error(f"Error processing accepted voice transcription for user {user_id}: {e}")
        await callback.message.answer(
            f"✅ Принято: {transcribed_text}\n\n"
            "Произошла ошибка при обработке. Пожалуйста, введите текст вручную или попробуйте снова."
        )
        await state.clear()

@router.callback_query(StateFilter(VOICE_TRANSCRIPTION_CONFIRMATION), F.data == "voice_reject")
@require_trial_access('emotion_diary')
async def handle_voice_reject(callback: types.CallbackQuery, state: FSMContext):
    """Handle rejection of voice transcription"""
    await callback.answer()
    user_id = callback.from_user.id
    logger.info(f"User {user_id} rejected voice transcription")
    
    # Get stored transcription data
    data = await state.get_data()
    original_state = data.get('voice_original_state')
    
    # Update message to show rejection
    await callback.message.edit_text(
        "❌ Распознавание отклонено.\n\n"
        "Попробуйте записать голосовое сообщение заново или введите текст вручную."
    )
    
    # Restore original state
    if original_state:
        await state.set_state(original_state)
        # Restore original state data without voice-related keys
        clean_data = {k: v for k, v in data.items() 
                     if not k.startswith('voice_')}
        await state.set_data(clean_data)
    else:
        await state.clear()

# Helper function to check if voice messages are enabled
def is_voice_enabled() -> bool:
    """Check if voice message support is properly configured"""
    return bool(os.getenv("GOOGLE_GENAI_API_KEY")) 