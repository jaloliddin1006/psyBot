import logging
from aiogram import types
from aiogram.types import KeyboardButton, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.fsm.context import FSMContext
from src.database.session import get_session, close_session
from src.database.models import User
from src.constants import MAIN_MENU
from aiogram import Router, F
from aiogram.filters import Command
from .emotion_diary import start_emotion_diary

logger = logging.getLogger(__name__)
router = Router(name=__name__)

async def main_menu(source: types.Message | types.CallbackQuery, state: FSMContext) -> int:
    logger.info(f"main_menu invoked. Source type: {type(source)}, Source from_user.id: {source.from_user.id if source and hasattr(source, 'from_user') else 'N/A'}")
    actual_user: types.User
    answer_target: types.Message  # The object whose .answer() method we'll use
    message_to_potentially_delete_id: int | None = None

    if isinstance(source, types.Message):
        actual_user = source.from_user
        answer_target = source
        # This is the user's command message (e.g., /start) that we might want to delete
        message_to_potentially_delete_id = source.message_id
        logger.info(f"Entering main_menu from Message. User ID: {actual_user.id}, Message ID: {source.message_id}")
    elif isinstance(source, types.CallbackQuery):
        actual_user = source.from_user
        answer_target = source.message  # Reply to the message the button was on
        # The message with the button (source.message) is usually deleted by the callback handler itself
        logger.info(f"Entering main_menu from CallbackQuery. User ID: {actual_user.id}, CallbackQuery ID: {source.id}")
    else:
        logger.error(f"main_menu called with invalid source type: {type(source)}")
        # Optionally, try to reply with an error if possible, though answer_target is not set
        return MAIN_MENU # Or handle error appropriately

    data = await state.get_data()
    messages_to_delete = data.get('messages_to_delete', [])
    if messages_to_delete is None:
        messages_to_delete = []

    session = get_session()
    db_user = session.query(User).filter(User.telegram_id == actual_user.id).first()
    
    if db_user:
        logger.info(f"main_menu: Found db_user. ID: {db_user.id}, Telegram ID: {db_user.telegram_id}, Full Name: '{db_user.full_name}', Reg Complete: {getattr(db_user, 'registration_complete', 'N/A')}")
    else:
        logger.warning(f"main_menu: db_user not found for Telegram ID: {actual_user.id}")

    if not db_user or not getattr(db_user, 'registration_complete', False) or not db_user.full_name:
        logger.warning(f"main_menu: Registration incomplete or name missing. db_user: {bool(db_user)}, reg_complete: {getattr(db_user, 'registration_complete', 'N/A') if db_user else 'N/A'}, full_name: {db_user.full_name if db_user else 'N/A'} for User ID: {actual_user.id}")
        close_session(session)
        await answer_target.answer("Пожалуйста, завершите регистрацию с помощью /start aas")
        return MAIN_MENU

    # Check trial status
    from src.trial_manager import check_trial_status, get_access_denied_message, has_feature_access
    trial_status, days_remaining = check_trial_status(db_user)
    
    # If trial expired, show expiry message and block access
    if trial_status == 'trial_expired':
        close_session(session)
        await answer_target.answer(get_access_denied_message('main_menu'))
        return MAIN_MENU

    name = db_user.full_name
    
    # Show trial status info if in trial
    trial_info = ""
    if trial_status == 'trial_active':
        trial_info = f"\n🎯 Пробный период: осталось {days_remaining} дней"
    elif trial_status == 'premium':
        trial_info = "\n⭐ Премиум-доступ активен"
    
    close_session(session)
    
    current_fsm_state_data = await state.get_data()
    new_fsm_state_data = {'messages_to_delete': current_fsm_state_data.get('messages_to_delete', [])}
    await state.set_data(new_fsm_state_data)

    keyboard = [
        [KeyboardButton(text="Дневник эмоций")],
        [KeyboardButton(text="Аналитика эмоций")],
        [KeyboardButton(text="Темы для проработки")],
        [KeyboardButton(text="Методы релаксации")],
        [KeyboardButton(text="Рефлексия встречи с психотерапевтом"), KeyboardButton(text="На главную")]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)
    
    logger.info(f"main_menu: Sending main menu to {name} (User ID: {actual_user.id})")
    sent_menu_message = await answer_target.answer(
        f"Привет, {name}!{trial_info}\n\nЧто бы ты хотела сделать: зафиксировать свою эмоцию или поделиться впечатлениями после сессии с психотерапевтом?\n\n Если хочешь обсудить что-то или разобрать какую-либо ситуацию, я готов тебе помочь в этом. Просто напиши мне ☺️",
        reply_markup=reply_markup
    )
    
    messages_to_delete_updated = (await state.get_data()).get('messages_to_delete', [])
    if messages_to_delete_updated is None: messages_to_delete_updated = []
    
    messages_to_delete_updated.append(sent_menu_message.message_id)
    
    # If main_menu was triggered by a direct user message (like /start), add that message for deletion
    if message_to_potentially_delete_id and message_to_potentially_delete_id not in messages_to_delete_updated:
        messages_to_delete_updated.append(message_to_potentially_delete_id)

    await state.update_data(messages_to_delete=messages_to_delete_updated)
    logger.info(f"main_menu: Updated messages_to_delete: {messages_to_delete_updated} for User ID: {actual_user.id}")
    
    return MAIN_MENU

@router.message(F.text == "Дневник эмоций")
async def handle_emotion_diary_button(message: types.Message, state: FSMContext):
    logger.info(f"Handling 'Дневник эмоций' button press. message.from_user.id: {message.from_user.id}")
    
    # Check access permissions
    session = get_session()
    try:
        db_user = session.query(User).filter(User.telegram_id == message.from_user.id).first()
        if not db_user:
            await message.answer("Пожалуйста, завершите регистрацию с помощью /start")
            return
        
        from src.trial_manager import has_feature_access, get_access_denied_message
        if not has_feature_access(db_user, 'emotion_diary'):
            await message.answer(get_access_denied_message('emotion_diary'))
            return
    finally:
        close_session(session)
    
    await start_emotion_diary(message, state)

@router.message(F.text == "Аналитика эмоций")
async def handle_emotion_analysis_button(message: types.Message, state: FSMContext):
    logger.info(f"Handling 'Аналитика эмоций' button press. message.from_user.id: {message.from_user.id}")
    
    # Check access permissions
    session = get_session()
    try:
        db_user = session.query(User).filter(User.telegram_id == message.from_user.id).first()
        if not db_user:
            await message.answer("Пожалуйста, завершите регистрацию с помощью /start")
            return
        
        from src.trial_manager import has_feature_access, get_access_denied_message
        if not has_feature_access(db_user, 'emotion_analytics'):
            await message.answer(get_access_denied_message('emotion_analytics'))
            return
    finally:
        close_session(session)
    
    from .emotion_analysis import start_emotion_analysis
    await start_emotion_analysis(message, state)

@router.message(F.text == "Темы для проработки")
async def handle_therapy_themes_button(message: types.Message, state: FSMContext):
    logger.info(f"Handling 'Темы для проработки' button press. message.from_user.id: {message.from_user.id}")
    
    # Check access permissions
    session = get_session()
    try:
        db_user = session.query(User).filter(User.telegram_id == message.from_user.id).first()
        if not db_user:
            await message.answer("Пожалуйста, завершите регистрацию с помощью /start")
            return
        
        from src.trial_manager import has_feature_access, get_access_denied_message
        if not has_feature_access(db_user, 'therapy_themes'):
            await message.answer(get_access_denied_message('therapy_themes'))
            return
    finally:
        close_session(session)
    
    from .therapy_themes import start_therapy_themes
    await start_therapy_themes(message, state)

@router.message(F.text == "Методы релаксации")
async def handle_relaxation_methods_button(message: types.Message, state: FSMContext):
    logger.info(f"Handling 'Методы релаксации' button press. message.from_user.id: {message.from_user.id}")
    
    # Check access permissions
    session = get_session()
    try:
        db_user = session.query(User).filter(User.telegram_id == message.from_user.id).first()
        if not db_user:
            await message.answer("Пожалуйста, завершите регистрацию с помощью /start")
            return
        
        from src.trial_manager import has_feature_access, get_access_denied_message
        if not has_feature_access(db_user, 'relaxation_methods'):
            await message.answer(get_access_denied_message('relaxation_methods'))
            return
    finally:
        close_session(session)
    
    from .relaxation import start_relaxation_methods
    await start_relaxation_methods(message, state)

@router.message(Command("hotline"))
async def hotline_handler(message: types.Message, state: FSMContext) -> None:
    hotline_number = "+7 495 625-31-01"
    text = f"Телефон горячей линии: {hotline_number}\nВы можете позвонить по этому номеру в экстренной ситуации."
    await message.answer(text)

@router.message(Command("help"))
async def help_handler(message: types.Message, state: FSMContext) -> None:
    keyboard = [
        [InlineKeyboardButton(text="Какие есть функции", callback_data="help_features")],
        [InlineKeyboardButton(text="Как он отвечает", callback_data="help_how_answers")]
    ]
    reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
    await message.answer("Выберите интересующий вопрос:", reply_markup=reply_markup)

@router.callback_query(F.data.startswith("help_"))
async def help_callback_handler(callback: types.CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    if callback.data == "help_features":
        await callback.message.edit_text("Бот может вести дневник эмоций, помогать с рефлексией после сессии с психотерапевтом, давать рекомендации и сохранять ваш опыт. (Здесь ваш кастомный текст)")
    elif callback.data == "help_how_answers":
        await callback.message.edit_text("Бот отвечает на ваши сообщения с помощью искусственного интеллекта, используя ваш контекст и выбранные опции. (Здесь ваш кастомный текст)")

@router.message(F.text == "Рефлексия встречи с психотерапевтом")
async def reflection_with_psychotherapist_handler(message: types.Message, state: FSMContext) -> None:
    # Check access permissions
    session = get_session()
    try:
        db_user = session.query(User).filter(User.telegram_id == message.from_user.id).first()
        if not db_user:
            await message.answer("Пожалуйста, завершите регистрацию с помощью /start")
            return
        
        from src.trial_manager import has_feature_access, get_access_denied_message
        if not has_feature_access(db_user, 'reflection'):
            await message.answer(get_access_denied_message('reflection'))
            return
    finally:
        close_session(session)
    
    from .reflection import start_reflection
    await start_reflection(message, state)

@router.message(F.text == "На главную")
async def to_main_menu_handler(message: types.Message, state: FSMContext) -> None:
    await main_menu(message, state)