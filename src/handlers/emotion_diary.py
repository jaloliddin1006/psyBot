from aiogram import types, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.filters import StateFilter
from src.database.session import get_session, close_session
from src.database.models import User, EmotionEntry
from src.handlers.thought_diary import handle_emotion_choice
from .utils import delete_previous_messages
from src.constants import *
import os
from google import genai
import asyncio
import logging
from trial_manager import require_trial_access

# Initialize logger and router
logger = logging.getLogger(__name__)
router = Router(name=__name__)

client = genai.Client(
    api_key=os.environ.get("GOOGLE_GENAI_API_KEY"),
    http_options={"base_url": os.environ.get("API_URL")}
)

async def return_to_main_menu(message: types.Message, state: FSMContext):
    from src.handlers.main_menu import main_menu
    await delete_previous_messages(message, state)
    await state.clear()
    await main_menu(message, state)
    return MAIN_MENU

async def start_emotion_diary(message: types.Message, state: FSMContext):
    logger.info(f"start_emotion_diary invoked. message.from_user.id: {message.from_user.id}")
    session = get_session()
    db_user = session.query(User).filter(User.telegram_id == message.from_user.id).first()
    logger.info(f"db_user: {db_user}")
    if not db_user or not getattr(db_user, 'registration_complete', False) or not db_user.full_name:
        close_session(session)
        await state.clear()
        await message.answer("Пожалуйста, завершите регистрацию с помощью /start перед использованием дневника эмоций.")
        return MAIN_MENU
    close_session(session)
    data = await state.get_data()
    messages_to_delete = data.get('messages_to_delete', [])
    messages_to_delete.append(message.message_id)
    await state.update_data(messages_to_delete=messages_to_delete)
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Мне хорошо", callback_data="good")],
        [InlineKeyboardButton(text="Мне плохо", callback_data="bad")],
        [InlineKeyboardButton(text="Назад", callback_data="back_to_main")]
    ])
    sent = await message.answer("Как вы себя чувствуете?", reply_markup=keyboard)
    messages_to_delete.append(sent.message_id)
    await state.update_data(messages_to_delete=messages_to_delete)
    await state.set_state(EMOTION_SELECTION)
    logger.info(f"State set to EMOTION_SELECTION ({EMOTION_SELECTION}). Current state: {await state.get_state()}")
    return EMOTION_SELECTION

@router.callback_query(StateFilter(EMOTION_SELECTION), F.data.in_(["good", "bad", "back_to_main"]))
@require_trial_access('emotion_diary')
async def handle_emotion_selection(callback: types.CallbackQuery, state: FSMContext):
    # print(f"DEBUG: handle_emotion_selection triggered with {Zdata}")
    logger.info(f"handle_emotion_selection called with data: {callback.data} in state: {await state.get_state()}")
    await callback.answer()
    if callback.data == "back_to_main":
        from src.handlers.main_menu import main_menu
        await delete_previous_messages(callback.message, state)
        await state.clear()
        await main_menu(callback, state)
        return MAIN_MENU
    await state.update_data(selected_emotion=callback.data)
    if callback.data == "good":
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Подъем, легкость, хочу улыбаться", callback_data="good_state_1")],
            [InlineKeyboardButton(text="Спокойно, расслабленно", callback_data="good_state_2")],
            [InlineKeyboardButton(text="На душе уютно, хочется быть рядом", callback_data="good_state_3")],
            [InlineKeyboardButton(text="Тянет к новому, хочется открытий", callback_data="good_state_4")],
            [InlineKeyboardButton(text="Сила, внутренняя стабильность", callback_data="good_state_5")],
            [InlineKeyboardButton(text="Назад", callback_data="back_to_emotion")]
        ])
        await callback.message.edit_text("Что лучше описывает твое состояние? Выбери вариант:", reply_markup=keyboard)
        await state.set_state(GOOD_STATE_SELECTION)
        return GOOD_STATE_SELECTION
    elif callback.data == "bad":
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Тяжело, нет сил", callback_data="bad_state_1")],
            [InlineKeyboardButton(text="Я чувствую, будто что-то не так", callback_data="bad_state_2")],
            [InlineKeyboardButton(text="Меня что-то злит", callback_data="bad_state_3")],
            [InlineKeyboardButton(text="Неприятно, хочется отстраниться", callback_data="bad_state_4")],
            [InlineKeyboardButton(text="Неловко, будто поступила плохо", callback_data="bad_state_5")],
            [InlineKeyboardButton(text="Назад", callback_data="back_to_emotion")]
        ])
        await callback.message.edit_text("Что лучше описывает твое состояние? Выбери вариант:", reply_markup=keyboard)
        await state.set_state(BAD_STATE_SELECTION)
        return BAD_STATE_SELECTION

async def _handle_state_selection_logic(callback: types.CallbackQuery, state: FSMContext, is_good: bool):
    logger.info(f"_handle_state_selection_logic called with data: {callback.data}, from_user.id: {callback.from_user.id}, is_good: {is_good} in state: {await state.get_state()}")
    await callback.answer()
    if callback.data == "back_to_main":
        from src.handlers.main_menu import main_menu
        await delete_previous_messages(callback.message, state)
        await state.clear()
        await main_menu(callback, state)
        return MAIN_MENU
    if callback.data == "back_to_emotion":
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Мне хорошо", callback_data="good")],
            [InlineKeyboardButton(text="Мне плохо", callback_data="bad")],
            [InlineKeyboardButton(text="Назад", callback_data="back_to_main")]
        ])
        await callback.message.edit_text("Как вы себя чувствуете?", reply_markup=keyboard)
        await state.set_state(EMOTION_SELECTION)
        return EMOTION_SELECTION
    await state.update_data(selected_state=callback.data)
    options = {
        "good_state_1": ["Приятно", "Захватывает"],
        "good_state_2": ["Удовлетворение", "Глубокий покой"],
        "good_state_3": ["Тепло", "Близость"],
        "good_state_4": ["Интерес", "Вдохновение"],
        "good_state_5": ["Сила", "Уверенность"],
        "bad_state_1": ["Усталость", "Потеря сил"],
        "bad_state_2": ["Тревога", "Неуверенность"],
        "bad_state_3": ["Злость", "Раздражение"],
        "bad_state_4": ["Отстраненность", "Обида"],
        "bad_state_5": ["Переживаю", "Хочу исчезнуть"]
    }
    state_key = callback.data
    opts = options.get(state_key, [])
    
    # Specific messages for each state
    state_messages = {
        "good_state_1": "Ты в хорошем настроении или это ощущение настолько сильное, что захватывает дух?",
        "good_state_2": "Это легкая удовлетворенность или ты ощущаешь глубокий покой?",
        "good_state_3": "Это скорее мягкое доверие и чувство, что вы можете на кого-то положиться, или это более глубокая связь и привязанность?",
        "good_state_4": "Вы любопытны или испытываете мощный эмоциональный отклик от происходящего?",
        "good_state_5": "Это внутренняя уверенность или ощущение победы, которое хочется отметить?",
        "bad_state_1": "Вы погружены в свои мысли или чувствуете, что эта тяжесть становится невыносимой?",
        "bad_state_2": "Это легкое беспокойство, или ощущение настолько сильное, что вам трудно расслабиться?",
        "bad_state_3": "Вы слегка недовольны, или вам хочется выразить свое возмущение?",
        "bad_state_4": "Это небольшое внутреннее сопротивление, или вам настолько не нравится ситуация, что хочется отвернуться?",
        "bad_state_5": "Вы переживаете о случившемся, или вам хочется спрятаться и исчезнуть?"
    }
    
    message_text = state_messages.get(state_key, "Выбери наиболее подходящее описание:")
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=opt, callback_data=f"option_{i}") for i, opt in enumerate(opts)],
        [InlineKeyboardButton(text="Назад", callback_data="back_to_state")]
    ])
    await callback.message.edit_text(message_text, reply_markup=keyboard)
    if is_good:
        await state.set_state(GOOD_OPTION_SELECTION)
        return GOOD_OPTION_SELECTION
    else:
        await state.set_state(BAD_OPTION_SELECTION)
        return BAD_OPTION_SELECTION

@router.callback_query(StateFilter(GOOD_STATE_SELECTION))
@require_trial_access('emotion_diary')
async def handle_good_state_selection(callback: types.CallbackQuery, state: FSMContext):
    logger.info(f"handle_good_state_selection called with data: {callback.data}")
    await _handle_state_selection_logic(callback, state, is_good=True)

@router.callback_query(StateFilter(BAD_STATE_SELECTION))
@require_trial_access('emotion_diary')
async def handle_bad_state_selection(callback: types.CallbackQuery, state: FSMContext):
    logger.info(f"handle_bad_state_selection called with data: {callback.data}")
    await _handle_state_selection_logic(callback, state, is_good=False)

@router.callback_query(StateFilter(GOOD_OPTION_SELECTION))
@require_trial_access('emotion_diary')
async def handle_good_option_selection(callback: types.CallbackQuery, state: FSMContext):
    logger.info(f"handle_good_option_selection called with data: {callback.data}")
    await _handle_option_selection_logic(callback, state, is_good=True)

@router.callback_query(StateFilter(BAD_OPTION_SELECTION))
@require_trial_access('emotion_diary')
async def handle_bad_option_selection(callback: types.CallbackQuery, state: FSMContext):
    logger.info(f"handle_bad_option_selection called with data: {callback.data}")
    await _handle_option_selection_logic(callback, state, is_good=False)

async def _handle_option_selection_logic(callback: types.CallbackQuery, state: FSMContext, is_good: bool):
    logger.info(f"_handle_option_selection_logic called with data: {callback.data}, from_user.id: {callback.from_user.id}, is_good: {is_good} in state: {await state.get_state()}")
    await callback.answer()
    if callback.data == "back_to_state":
        # Вернуться к выбору состояния
        data = await state.get_data() # get data freshТ
        selected_emotion = data.get('selected_emotion')
        
        # Reconstruct the previous state's message and keyboard
        if selected_emotion == "good":
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="Подъем, легкость, хочу улыбаться", callback_data="good_state_1")],
                [InlineKeyboardButton(text="Спокойно, расслабленно", callback_data="good_state_2")],
                [InlineKeyboardButton(text="На душе уютно, хочется быть рядом", callback_data="good_state_3")],
                [InlineKeyboardButton(text="Тянет к новому, хочется открытий", callback_data="good_state_4")],
                [InlineKeyboardButton(text="Сила, внутренняя стабильность", callback_data="good_state_5")],
                [InlineKeyboardButton(text="Назад", callback_data="back_to_emotion")]
            ])
            await callback.message.edit_text("Что лучше описывает твое состояние? Выбери вариант:", reply_markup=keyboard)
            await state.set_state(GOOD_STATE_SELECTION)
            return GOOD_STATE_SELECTION
        elif selected_emotion == "bad":
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="Тяжело, нет сил", callback_data="bad_state_1")],
                [InlineKeyboardButton(text="Я чувствую, будто что-то не так", callback_data="bad_state_2")],
                [InlineKeyboardButton(text="Меня что-то злит", callback_data="bad_state_3")],
                [InlineKeyboardButton(text="Неприятно, хочется отстраниться", callback_data="bad_state_4")],
                [InlineKeyboardButton(text="Мне неловко", callback_data="bad_state_5")],
                [InlineKeyboardButton(text="Назад", callback_data="back_to_emotion")]
            ])
            await callback.message.edit_text("Что лучше описывает твое состояние? Выбери вариант:", reply_markup=keyboard)
            await state.set_state(BAD_STATE_SELECTION)
            return BAD_STATE_SELECTION
        else: # Fallback if selected_emotion is not found, though it should be
            from src.handlers.main_menu import main_menu
            await delete_previous_messages(callback.message, state)
            await state.clear()
            await main_menu(callback, state)
            return MAIN_MENU

    await state.update_data(selected_option=callback.data)
    
    # Save emotion entry to database
    session = get_session()
    db_user = session.query(User).filter(User.telegram_id == callback.from_user.id).first()
    if db_user:
        await save_emotion_entry_simple(db_user.id, state)
    close_session(session)
    
    # Генерация и отправка поддерживающего сообщения
    emotion_type = (await state.get_data()).get('selected_emotion')
    option_data = callback.data # This is 'option_0', 'option_1' etc.
    
    # To get the actual text like "Приятно", "Захватывает" you need to map option_data back or store more context
    # For now, send_support_message will receive "good, option_0"
    await send_support_message(callback.message, state, f"{emotion_type}, {option_data}")
    await state.set_state(AFTER_SUPPORT_MESSAGE) # Set state for next step
    return AFTER_SUPPORT_MESSAGE # Return a known constant if your FSM uses them for transitions

@router.callback_query(StateFilter(AFTER_SUPPORT_MESSAGE))
@require_trial_access('emotion_diary')
async def handle_after_support_choice(callback: types.CallbackQuery, state: FSMContext):
    logger.info(f"handle_after_support_choice called with data: {callback.data}")
    await callback.answer()
    await delete_previous_messages(callback.message, state) # Clean up the support message with buttons

    if callback.data == "to_thought_diary":
        # Переход к дневнику мыслей
        # We need to pass the original callback query and state correctly
        # Assuming handle_emotion_choice is designed to be called here
        await handle_emotion_choice(callback, state) # Pass the current callback
        # The thought diary flow will handle its own state and menu returns.
        return # End of this path
    elif callback.data == "to_main_menu":
        from src.handlers.main_menu import main_menu
        await state.clear()
        await main_menu(callback, state)
        return MAIN_MENU
    # Fallback or error, though ideally one of the buttons is always pressed.
    from src.handlers.main_menu import main_menu
    await state.clear()
    await main_menu(callback, state)
    return MAIN_MENU

async def save_emotion_entry_simple(user_id: int, state: FSMContext):
    """Save emotion entry to database from emotion diary flow"""
    session = get_session()
    try:
        data = await state.get_data()
        
        # Get emotion data from FSM state
        selected_emotion = data.get('selected_emotion')  # 'good' or 'bad'
        selected_state = data.get('selected_state')      # e.g. 'good_state_1', 'bad_state_2'
        selected_option = data.get('selected_option')    # e.g. 'option_0', 'option_1'
        
        # Convert to emotion_type for database
        emotion_type = "positive" if selected_emotion == "good" else "negative"
        
        # Create emotion entry
        entry = EmotionEntry(
            user_id=user_id,
            emotion_type=emotion_type,
            state=selected_state,
            option=selected_option,
            answer_text="Emotion recorded from diary"  # Simple placeholder
        )
        
        session.add(entry)
        session.commit()
        logger.info(f"Saved emotion entry for user {user_id}: {emotion_type}, {selected_state}, {selected_option}")
        
    except Exception as e:
        logger.error(f"Error saving emotion entry for user {user_id}: {e}")
        session.rollback()
    finally:
        close_session(session)

async def send_support_message(message: types.Message, state: FSMContext, emotion_text: str):
    ai_prompt = f"Пользователь выбрал эмоцию: '{emotion_text}'. Напиши короткий поддерживающий комментарий, чтобы помочь человеку почувствовать поддержку. Не используй markdown."
    try:
        response = await asyncio.to_thread(
            client.models.generate_content,
            model="gemini-2.0-flash",
            contents=[ai_prompt]
        )
        ai_text = response.text if hasattr(response, 'text') else str(response)
    except Exception as e:
        logging.error(f"Failed to get AI-generated support message: {e!r}")
        ai_text = "Спасибо, что поделились своими чувствами. Я рядом!"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="В главное меню", callback_data="to_main_menu")],
        [InlineKeyboardButton(text="В дневник мыслей", callback_data="to_thought_diary")]
    ])
    
    sent_message = await message.answer(ai_text, reply_markup=keyboard)
    # Store message_id to delete it later if needed
    data = await state.get_data()
    messages_to_delete = data.get('messages_to_delete', [])
    messages_to_delete.append(sent_message.message_id)
    await state.update_data(messages_to_delete=messages_to_delete)
