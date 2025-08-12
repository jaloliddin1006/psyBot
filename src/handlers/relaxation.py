import logging
from aiogram import types
from aiogram.types import KeyboardButton, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup, FSInputFile
from aiogram.fsm.context import FSMContext
from src.database.session import get_session, close_session
from src.database.models import RelaxationMedia
from constants import MAIN_MENU, RELAXATION_FORMAT_SELECTION, RELAXATION_AUDIO_LIST, RELAXATION_VIDEO_LIST
from aiogram import Router, F
from .utils import delete_previous_messages
from trial_manager import require_trial_access

logger = logging.getLogger(__name__)
router = Router(name=__name__)

async def start_relaxation_methods(message: types.Message, state: FSMContext):
    """Start relaxation methods feature"""
    logger.info(f"Starting relaxation methods for user {message.from_user.id}")
    
    # Delete previous messages
    await delete_previous_messages(message, state)
    
    # Set state
    await state.set_state(RELAXATION_FORMAT_SELECTION)
    
    # Create keyboard for format selection
    keyboard = [
        [KeyboardButton(text="Аудио")],
        [KeyboardButton(text="Видео")],
        [KeyboardButton(text="На главную")]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)
    
    sent_message = await message.answer(
        "Отличный выбор! Расслабление помогает снизить стресс, восстановить силы и улучшить самочувствие. Выберите удобный формат:",
        reply_markup=reply_markup
    )
    
    # Save message for deletion
    data = await state.get_data()
    messages_to_delete = data.get('messages_to_delete', [])
    messages_to_delete.append(sent_message.message_id)
    messages_to_delete.append(message.message_id)
    await state.update_data(messages_to_delete=messages_to_delete)

@router.message(F.text == "Аудио")
async def handle_audio_selection(message: types.Message, state: FSMContext):
    """Handle audio format selection"""
    current_state = await state.get_state()
    if current_state != RELAXATION_FORMAT_SELECTION:
        return
    
    logger.info(f"User {message.from_user.id} selected audio relaxation")
    
    # Get audio files from database
    session = get_session()
    try:
        audio_files = session.query(RelaxationMedia).filter(
            RelaxationMedia.media_type == 'audio',
            RelaxationMedia.is_active == True
        ).order_by(RelaxationMedia.order_position).all()
        
        if not audio_files:
            await message.answer("К сожалению, аудиофайлы пока недоступны. Попробуйте позже.")
            await start_relaxation_methods(message, state)
            return
        
        # Create inline keyboard with audio files
        keyboard = []
        for audio in audio_files:
            keyboard.append([InlineKeyboardButton(
                text=f"🎵 {audio.title}",
                callback_data=f"relaxation_audio_{audio.id}"
            )])
        
        keyboard.append([InlineKeyboardButton(text="🔙 Назад", callback_data="relaxation_back")])
        reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
        
        # Delete previous messages
        await delete_previous_messages(message, state)
        
        sent_message = await message.answer(
            "Выберите аудиозапись для расслабления:",
            reply_markup=reply_markup
        )
        
        # Set new state and save message
        await state.set_state(RELAXATION_AUDIO_LIST)
        data = await state.get_data()
        messages_to_delete = data.get('messages_to_delete', [])
        messages_to_delete.append(sent_message.message_id)
        messages_to_delete.append(message.message_id)
        await state.update_data(messages_to_delete=messages_to_delete)
        
    finally:
        close_session(session)

@router.message(F.text == "Видео")
async def handle_video_selection(message: types.Message, state: FSMContext):
    """Handle video format selection"""
    current_state = await state.get_state()
    if current_state != RELAXATION_FORMAT_SELECTION:
        return
    
    logger.info(f"User {message.from_user.id} selected video relaxation")
    
    # Get video files from database
    session = get_session()
    try:
        video_files = session.query(RelaxationMedia).filter(
            RelaxationMedia.media_type == 'video',
            RelaxationMedia.is_active == True
        ).order_by(RelaxationMedia.order_position).all()
        
        if not video_files:
            await message.answer("К сожалению, видеофайлы пока недоступны. Попробуйте позже.")
            await start_relaxation_methods(message, state)
            return
        
        # Create inline keyboard with video files
        keyboard = []
        for video in video_files:
            keyboard.append([InlineKeyboardButton(
                text=f"📹 {video.title}",
                callback_data=f"relaxation_video_{video.id}"
            )])
        
        keyboard.append([InlineKeyboardButton(text="🔙 Назад", callback_data="relaxation_back")])
        reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
        
        # Delete previous messages
        await delete_previous_messages(message, state)
        
        sent_message = await message.answer(
            "Выберите видео для расслабления:",
            reply_markup=reply_markup
        )
        
        # Set new state and save message
        await state.set_state(RELAXATION_VIDEO_LIST)
        data = await state.get_data()
        messages_to_delete = data.get('messages_to_delete', [])
        messages_to_delete.append(sent_message.message_id)
        messages_to_delete.append(message.message_id)
        await state.update_data(messages_to_delete=messages_to_delete)
        
    finally:
        close_session(session)

@router.callback_query(F.data.startswith("relaxation_audio_"))
@require_trial_access('relaxation_methods')
async def handle_audio_playback(callback: types.CallbackQuery, state: FSMContext):
    """Handle audio file playback"""
    await callback.answer()
    
    media_id = int(callback.data.split("_")[-1])
    logger.info(f"User {callback.from_user.id} selected audio file {media_id}")
    
    session = get_session()
    try:
        audio_file = session.query(RelaxationMedia).filter(
            RelaxationMedia.id == media_id,
            RelaxationMedia.media_type == 'audio',
            RelaxationMedia.is_active == True
        ).first()
        
        if not audio_file:
            await callback.message.answer("Аудиофайл не найден.")
            return
        
        # Send audio file
        try:
            # Create back button
            keyboard = [[InlineKeyboardButton(text="🔙 К списку аудио", callback_data="relaxation_back_audio")]]
            reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
            
            description = f"🎵 **{audio_file.title}**"
            if audio_file.description:
                description += f"\n\n{audio_file.description}"
            if audio_file.duration:
                minutes = audio_file.duration // 60
                seconds = audio_file.duration % 60
                description += f"\n\n⏱ Длительность: {minutes}:{seconds:02d}"
            
            # Try to send as audio file
            audio_input = FSInputFile(audio_file.file_path)
            await callback.message.answer_audio(
                audio=audio_input,
                caption=description,
                reply_markup=reply_markup
            )
                
        except Exception as e:
            logger.error(f"Error sending audio file: {e}")
            await callback.message.answer(
                f"Ошибка при отправке аудиофайла. Попробуйте позже.\n\n"
                f"Название: {audio_file.title}"
            )
    
    finally:
        close_session(session)

@router.callback_query(F.data.startswith("relaxation_video_"))
@require_trial_access('relaxation_methods')
async def handle_video_playback(callback: types.CallbackQuery, state: FSMContext):
    """Handle video file playback"""
    await callback.answer()
    
    media_id = int(callback.data.split("_")[-1])
    logger.info(f"User {callback.from_user.id} selected video file {media_id}")
    
    session = get_session()
    try:
        video_file = session.query(RelaxationMedia).filter(
            RelaxationMedia.id == media_id,
            RelaxationMedia.media_type == 'video',
            RelaxationMedia.is_active == True
        ).first()
        
        if not video_file:
            await callback.message.answer("Видеофайл не найден.")
            return
        
        # Send video file
        try:
            # Create back button
            keyboard = [[InlineKeyboardButton(text="🔙 К списку видео", callback_data="relaxation_back_video")]]
            reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
            
            description = f"📹 **{video_file.title}**"
            if video_file.description:
                description += f"\n\n{video_file.description}"
            if video_file.duration:
                minutes = video_file.duration // 60
                seconds = video_file.duration % 60
                description += f"\n\n⏱ Длительность: {minutes}:{seconds:02d}"
            
            # Try to send as video file
            video_input = FSInputFile(video_file.file_path)
            await callback.message.answer_video(
                video=video_input,
                caption=description,
                reply_markup=reply_markup
            )
                
        except Exception as e:
            logger.error(f"Error sending video file: {e}")
            await callback.message.answer(
                f"Ошибка при отправке видеофайла. Попробуйте позже.\n\n"
                f"Название: {video_file.title}"
            )
    
    finally:
        close_session(session)

@router.callback_query(F.data == "relaxation_back")
@require_trial_access('relaxation_methods')
async def handle_back_to_format_selection(callback: types.CallbackQuery, state: FSMContext):
    """Handle back to format selection"""
    await callback.answer()
    await callback.message.delete()
    
    # Set state
    await state.set_state(RELAXATION_FORMAT_SELECTION)
    
    # Create keyboard for format selection
    keyboard = [
        [KeyboardButton(text="Аудио")],
        [KeyboardButton(text="Видео")],
        [KeyboardButton(text="На главную")]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)
    
    await callback.message.answer(
        "Отличный выбор! Расслабление помогает снизить стресс, восстановить силы и улучшить самочувствие. Выберите удобный формат:",
        reply_markup=reply_markup
    )

@router.callback_query(F.data == "relaxation_back_audio")
@require_trial_access('relaxation_methods')
async def handle_back_to_audio_list(callback: types.CallbackQuery, state: FSMContext):
    """Handle back to audio list"""
    await callback.answer()
    
    # Get audio files from database
    session = get_session()
    try:
        audio_files = session.query(RelaxationMedia).filter(
            RelaxationMedia.media_type == 'audio',
            RelaxationMedia.is_active == True
        ).order_by(RelaxationMedia.order_position).all()
        
        if not audio_files:
            await callback.message.edit_text("К сожалению, аудиофайлы пока недоступны. Попробуйте позже.")
            return
        
        # Create inline keyboard with audio files
        keyboard = []
        for audio in audio_files:
            keyboard.append([InlineKeyboardButton(
                text=f"🎵 {audio.title}",
                callback_data=f"relaxation_audio_{audio.id}"
            )])
        
        keyboard.append([InlineKeyboardButton(text="🔙 Назад", callback_data="relaxation_back")])
        reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
        
        await callback.message.edit_text(
            "Выберите аудиозапись для расслабления:",
            reply_markup=reply_markup
        )
        
        # Set new state
        await state.set_state(RELAXATION_AUDIO_LIST)
        
    finally:
        close_session(session)

@router.callback_query(F.data == "relaxation_back_video")
@require_trial_access('relaxation_methods')
async def handle_back_to_video_list(callback: types.CallbackQuery, state: FSMContext):
    """Handle back to video list"""
    await callback.answer()
    
    # Get video files from database
    session = get_session()
    try:
        video_files = session.query(RelaxationMedia).filter(
            RelaxationMedia.media_type == 'video',
            RelaxationMedia.is_active == True
        ).order_by(RelaxationMedia.order_position).all()
        
        if not video_files:
            await callback.message.edit_text("К сожалению, видеофайлы пока недоступны. Попробуйте позже.")
            return
        
        # Create inline keyboard with video files
        keyboard = []
        for video in video_files:
            keyboard.append([InlineKeyboardButton(
                text=f"📹 {video.title}",
                callback_data=f"relaxation_video_{video.id}"
            )])
        
        keyboard.append([InlineKeyboardButton(text="🔙 Назад", callback_data="relaxation_back")])
        reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
        
        await callback.message.edit_text(
            "Выберите видео для расслабления:",
            reply_markup=reply_markup
        )
        
        # Set new state
        await state.set_state(RELAXATION_VIDEO_LIST)
        
    finally:
        close_session(session)

@router.message(F.text == "На главную")
async def handle_back_to_main_menu(message: types.Message, state: FSMContext):
    """Handle back to main menu from relaxation methods"""
    current_state = await state.get_state()
    if current_state in [RELAXATION_FORMAT_SELECTION, RELAXATION_AUDIO_LIST, RELAXATION_VIDEO_LIST]:
        logger.info(f"User {message.from_user.id} returning to main menu from relaxation methods")
        from .main_menu import main_menu
        await main_menu(message, state) 