import logging
import random
from aiogram import types, F, Router
from aiogram.filters import StateFilter
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.fsm.context import FSMContext
from src.database.session import get_session, close_session
from src.database.models import User, EmotionEntry
import os
from google import genai
from .utils import delete_previous_messages
from src.constants import (
    MAIN_MENU,
    THOUGHT_DIARY_AWAITING_POSITIVE_ENTRY, THOUGHT_DIARY_AWAITING_NEGATIVE_ENTRY,
    THOUGHT_DIARY_NEGATIVE_QUESTIONING,
    THOUGHT_DIARY_AWAITING_POSITIVE_FEEDBACK, THOUGHT_DIARY_AWAITING_NEGATIVE_ACTION,
    THOUGHT_DIARY_AWAITING_RECOMMENDATION_FEEDBACK, THOUGHT_DIARY_AWAITING_RECONSIDER_FEEDBACK
)
from trial_manager import require_trial_access

logger = logging.getLogger(__name__)
router = Router(name=__name__) # New router for thought diary

client = genai.Client(
    api_key=os.environ.get("GOOGLE_GENAI_API_KEY"),
    http_options={"base_url": os.environ.get("API_URL")}
)

# Dictionary mapping state and option to messages
final_messages = {
    "bad_state_1": {
        "option_0": """
По контексту выбрать:
Психообразование: объяснение, что грусть — это естественная реакция на потерю, разочарование или жизненные сложности; она помогает «прожить» ситуацию.
Когнитивная реструктуризация: выявление и проработка искажений типа «Я никогда не буду счастлив», «Всё безнадёжно».
Поведенческая активация: поощрение к действию (прогулки, встречи с людьми, новые хобби) даже при отсутствии желания. Это помогает «переломить» пассивность, часто сопутствующую печали.
Ресурсные техники: акцент на положительных аспектах жизни, воспоминаниях об успехах; формирование.
Элементы самоподдержки и самосострадания: учить говорить с собой мягче и поддерживающе, а не критично.
        """,
        "option_1": """
По контексту выбрать:
Психообразование: объяснение, что грусть — это естественная реакция на потерю, разочарование или жизненные сложности; она помогает «прожить» ситуацию.
Когнитивная реструктуризация: выявление и проработка искажений типа «Я никогда не буду счастлив», «Всё безнадёжно».
Поведенческая активация: поощрение к действию (прогулки, встречи с людьми, новые хобби) даже при отсутствии желания. Это помогает «переломить» пассивность, часто сопутствующую печали.
Ресурсные техники: акцент на положительных аспектах жизни, воспоминаниях об успехах; формирование.
Элементы самоподдержки и самосострадания: учить говорить с собой мягче и поддерживающе, а не критично.
        """,
    },
    "bad_state_2": {
        "option_0": """
По контексту выбрать:Декатастрофизация: детальный разбор «самого страшного» сценария и уменьшение катастрофических ожиданий («А что, если…?» → «Какова реальная вероятность? Что я буду делать, если случится худшее?»).
Когнитивная терапия: осознавание автоматических тревожных мыслей («Я не справлюсь», «Со мной обязательно что-то произойдет»), проверка их на реальность.
Работа с образом «Я»: укрепление уверенности в своих способностях решать проблемы, справляться со сложностями.
        """,
        "option_1": """По контексту выбрать:
Декатастрофизация (как при тревоге): часто страх основан на завышенной оценке угрозы, поэтому важно снизить ощущение «ужасающего масштаба» возможных последствий.
Работа с убеждениями: «Мир опасен», «Я слишком слаб, чтобы это вынести», «Если что-то случится, я этого не выдержу». Проверка реальности этих убеждений и поиск альтернативных точек зрения.
Навыки саморегуляции: заземление (grounding), расслабление, самоподдерживающий внутренний диалог.
"""
    },
    "bad_state_3": {
        "option_0": """
По контексту выбрать:
Анализ триггеров: когда и в каких ситуациях возникает раздражение? Выделить внешние и внутренние факторы («Я не выспался», «Слишком много обязанностей», «Чувствую несправедливое отношение»).
Когнитивная реструктуризация: проработка мыслей вида «Все обязаны меня слушаться», «Они специальноделают мне назло». Переход к более реалистичным установкам.
Асертивная коммуникация: обучение спокойно выражать недовольство или просьбу вместо пассивной агрессии или вспышек гнева.
Самонаблюдение: Рекомендация ведение «дневника раздражения» (когда, где, почему, какие мысли и последствия) для лучшего понимания паттернов.
""",
        "option_1": """
По контексту выбрать:
Психообразование: гнев сам по себе не «плох» — это сигнал о нарушении границ или неудовлетворённой потребности. Проблема — в деструктивном выражении гнева.
Когнитивная терапия: поиск «возгорающих» мыслей («Он меня не уважает», «Мне должны помогать»), которые вызывают резкое обострение эмоции.
Тренировка альтернативных реакций: научить говорить прямо («Я злюсь, потому что…»), уходить на короткую «паузу» (тайм-аут), использовать юмор.
Работа над установками «долженствования»: замечать, где собственные ожидания слишком жёсткие и не учитывают реальность.
"""
    },
    "bad_state_4": {
        "option_0": """
По контексту выбрать:
Прояснение контекста: неприязнь к конкретному человеку/группе/ситуации может иметь под собой разные причины (личный опыт, стереотипы, конфликт интересов).
Когнитивная реструктуризация: обнаружение убеждений «Они все такие…», «Я не выношу их/это». Проверка на точность и поиск нюансов.
Эмпатия и переоценка: попытка взглянуть на ситуацию с точки зрения другого человека (если уместно и безопасно).
Границы и ценности: понять, не нарушает ли человек (или ситуация) важные личные ценности. Если да, то работать с тем, как экологично отстаивать эти ценности.
""",
        "option_1": """
По контексту выбрать:
Когнитивная проработка: часто брезгливость может быть усилена убеждениями вроде «Это абсолютнонеприемлемо/опасно/грязно». Изучается реальная степень угрозы и альтернативные точки зрения.
Работа с «идеями чистоты»: если в основе — культурные или личные установки о чистоте и порядке, анализ, насколько они адекватны и гибки.
Навыки саморегуляции: заметить телесную реакцию (тошнота, спазм) и научиться снижать её интенсивность через дыхание, растяжку, смену фокуса внимания.
"""
    },
    "bad_state_5": {
        "option_0": """
По контексту выбрать:
Анализ события: что именно вызвало сожаление (потерянная возможность, ошибка, неправильный выбор)? Каковы реальные последствия?
Когнитивная реструктуризация: склонны ли вы преувеличивать свою вину? Есть ли «эффект задним числом» («я должен был предвидеть»), который искажает оценку ситуаций?
Поиск уроков: превращение сожаления в опыт («Чему я могу научиться? Что я сделаю иначе в будущем?»).
Работа с принятием: если ситуацию уже не изменить, то важно научиться отпускать и направлять энергию в настоящее и будущее.
Самосострадание: мягкий взгляд на ошибки прошлого вместо самобичевания («Тогда я делал(а) лучшее из того, что умел(а)»).
        """,
        "option_1": """
По контексту выбрать:
Выявление убеждений о себе: стыд часто связан с идеей «со мной что-то не так», «я плохой». Важно отделять поступки от собственной ценности как личности.
Анализ стандартов: какие внутренние стандарты «должен/не должен» формируют стыд? Реалистичны ли они? Откуда они взялись?
Самосострадание: практика доброго и понимающего отношения к себе (напоминание, что каждый человек может ошибаться, что у всех есть несовершенства).
"""
    }
}


# Entry point from emotion_diary
async def handle_emotion_choice(callback_query: types.CallbackQuery, state: FSMContext):
    from src.handlers.main_menu import main_menu # For direct exit if needed

    user_id = callback_query.from_user.id
    current_fsm_state_at_entry = await state.get_state()
    logger.info(f"User {user_id}: Entering handle_emotion_choice. Current FSM state: {current_fsm_state_at_entry}. Transitioning to thought diary.")
    
    session = get_session()
    db_user = session.query(User).filter(User.telegram_id == user_id).first()
    if not db_user or not db_user.registration_complete:
        close_session(session)
        await callback_query.message.answer("Пожалуйста, завершите регистрацию с помощью /start перед использованием дневника мыслей.")
        await delete_previous_messages(callback_query.message, state)
        await state.clear()
        await main_menu(callback_query, state)
        return
    close_session(session)

    data = await state.get_data()
    # selected_emotion, selected_state, selected_option are passed from emotion_diary via FSM data
    emotion_type = data.get('selected_emotion') # 'good' or 'bad'
    logger.info(f"User {user_id}: In handle_emotion_choice, retrieved 'selected_emotion' from FSM data: '{emotion_type}'")

    if emotion_type == 'good':
        await state.update_data(current_emotion_type='positive') # Store for thought diary
        prompt_text = "Пользователь поделился хорошей эмоцией. Вырази эмпатию и порадуйся вместе с ним. Не используй markdown."
        next_fsm_state = THOUGHT_DIARY_AWAITING_POSITIVE_ENTRY
    elif emotion_type == 'bad':
        await state.update_data(current_emotion_type='negative') # Store for thought diary
        prompt_text = "Пользователь выбрал негативную эмоцию. Вырази понимание и предложи проработать ситуацию. Не используй markdown."
        next_fsm_state = THOUGHT_DIARY_AWAITING_NEGATIVE_ENTRY
    else:
        logger.warning(f"User {user_id}: 'selected_emotion' ('{emotion_type}') is not 'good' or 'bad' in handle_emotion_choice. Returning to main menu.")
        await callback_query.message.answer("Произошла ошибка при переходе в дневник мыслей. Пожалуйста, попробуйте снова из главного меню.")
        await delete_previous_messages(callback_query.message, state)
        await state.clear()
        await main_menu(callback_query, state)
        return

    try:
        response = client.models.generate_content(model="gemini-2.0-flash", contents=[prompt_text])
        ai_text = response.text if hasattr(response, 'text') else str(response)
    except Exception as e:
        logger.error(f"Error generating AI content for emotion type {emotion_type}: {e}")
        ai_text = "Рад, что вы готовы поделиться. Давайте продолжим." if emotion_type == 'good' else "Я здесь, чтобы помочь. Давайте разберемся."

    await callback_query.message.answer(ai_text)
    # await callback_query.message.answer(instruction_text)
    await state.set_state(next_fsm_state)
    logger.info(f"User {user_id}: Transitioned to thought diary. AI prompt sent. State successfully set to {next_fsm_state}. Previous state was {current_fsm_state_at_entry}.")


@router.message(StateFilter(THOUGHT_DIARY_AWAITING_POSITIVE_ENTRY))
async def process_positive_entry(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    logger.info(f"User {user_id}: Received positive entry in state {await state.get_state()}. Text: '{message.text}'")
    if not message.text:
        await message.answer("Пожалуйста, поделитесь своими мыслями в текстовом сообщении.")
        return

    await save_emotion_entry(message, state, "positive", message.text)
    
    keyboard = [[InlineKeyboardButton(text="В главное меню", callback_data="td_back_to_main_after_positive")]]
    reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
    sent = await message.answer("Это было зафиксировано в вашем дневнике мыслей.", reply_markup=reply_markup)
    
    data = await state.get_data()
    messages_to_delete = data.get('messages_to_delete', [])
    messages_to_delete.append(message.message_id) # User's text message
    messages_to_delete.append(sent.message_id) # Bot's confirmation message
    await state.update_data(messages_to_delete=messages_to_delete)
    await state.set_state(THOUGHT_DIARY_AWAITING_POSITIVE_FEEDBACK)
    logger.info(f"User {user_id}: Positive entry saved. State set to {THOUGHT_DIARY_AWAITING_POSITIVE_FEEDBACK}")


@router.callback_query(StateFilter(THOUGHT_DIARY_AWAITING_POSITIVE_FEEDBACK), F.data == "td_back_to_main_after_positive")
@require_trial_access('emotion_diary')
async def process_positive_feedback_to_main(callback_query: types.CallbackQuery, state: FSMContext):
    from src.handlers.main_menu import main_menu
    user_id = callback_query.from_user.id
    logger.info(f"User {user_id}: Chose 'back to main' after positive entry. State: {await state.get_state()}")
    await callback_query.answer()
    await delete_previous_messages(callback_query.message, state)
    await state.clear()
    await main_menu(callback_query, state)


@router.message(StateFilter(THOUGHT_DIARY_AWAITING_NEGATIVE_ENTRY))
async def process_negative_entry(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    logger.info(f"User {user_id}: Received negative entry in state {await state.get_state()}. Text: '{message.text}'")
    if not message.text:
        await message.answer("Пожалуйста, опишите вашу ситуацию в текстовом сообщении.")
        return

    # Initialize conversation history with first message
    conversation_history = [message.text]
    await state.update_data(
        negative_entry_text=message.text,  # Keep first message for "mark for work"
        conversation_history=conversation_history
    )
    
    # Generate follow-up question using LLM
    follow_up_question = await generate_follow_up_question(conversation_history)
    
    # Create keyboard with action buttons
    keyboard = [
        [InlineKeyboardButton(text="Получить рекомендацию", callback_data="td_get_recommendation")],
        [InlineKeyboardButton(text="Отметить для проработки", callback_data="td_mark_for_work")],
        [InlineKeyboardButton(text="На главную", callback_data="td_back_to_main_after_negative_entry")]
    ]
    reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
    
    sent_message = await message.answer(follow_up_question, reply_markup=reply_markup)
    
    data = await state.get_data()
    messages_to_delete = data.get('messages_to_delete', [])
    messages_to_delete.append(message.message_id) # User's text
    messages_to_delete.append(sent_message.message_id) # Bot's question with buttons
    await state.update_data(messages_to_delete=messages_to_delete)
    await state.set_state(THOUGHT_DIARY_NEGATIVE_QUESTIONING)
    logger.info(f"User {user_id}: First negative entry received. State set to {THOUGHT_DIARY_NEGATIVE_QUESTIONING}")


# New handler for follow-up messages in questioning state
@router.message(StateFilter(THOUGHT_DIARY_NEGATIVE_QUESTIONING))
async def process_negative_follow_up(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    logger.info(f"User {user_id}: Received follow-up message in questioning state. Text: '{message.text}'")
    
    if not message.text:
        await message.answer("Пожалуйста, ответьте на вопрос в текстовом сообщении.")
        return

    # Update conversation history
    data = await state.get_data()
    conversation_history = data.get('conversation_history', [])
    conversation_history.append(message.text)
    
    # Generate another follow-up question
    follow_up_question = await generate_follow_up_question(conversation_history)
    
    # Create keyboard with action buttons
    keyboard = [
        [InlineKeyboardButton(text="Получить рекомендацию", callback_data="td_get_recommendation")],
        [InlineKeyboardButton(text="Отметить для проработки", callback_data="td_mark_for_work")],
        [InlineKeyboardButton(text="На главную", callback_data="td_back_to_main_after_negative_entry")]
    ]
    reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
    
    sent_message = await message.answer(follow_up_question, reply_markup=reply_markup)
    
    # Update messages to delete and conversation history
    messages_to_delete = data.get('messages_to_delete', [])
    messages_to_delete.append(message.message_id)  # User's response
    messages_to_delete.append(sent_message.message_id)  # Bot's next question
    
    await state.update_data(
        conversation_history=conversation_history,
        messages_to_delete=messages_to_delete
    )
    
    logger.info(f"User {user_id}: Follow-up question sent. Staying in questioning state.")

@router.callback_query(StateFilter(THOUGHT_DIARY_NEGATIVE_QUESTIONING), F.data == "td_back_to_main_after_negative_entry")
@require_trial_access('emotion_diary')
async def process_negative_action_to_main(callback_query: types.CallbackQuery, state: FSMContext):
    from src.handlers.main_menu import main_menu
    user_id = callback_query.from_user.id
    logger.info(f"User {user_id}: Chose 'back to main' after negative entry. State: {await state.get_state()}")
    await callback_query.answer()
    
    # Save conversation history before clearing state
    data = await state.get_data()
    conversation_history = data.get('conversation_history', [])
    
    if conversation_history:
        full_conversation_text = "\n".join([f"Сообщение {i+1}: {msg}" for i, msg in enumerate(conversation_history)])
        await save_emotion_entry(callback_query, state, emotion_type_from_flow="negative", text_entry=full_conversation_text)
        logger.info(f"User {user_id}: Saved emotion entry with full conversation history before returning to main menu")
    
    await delete_previous_messages(callback_query.message, state)
    await state.clear()
    await main_menu(callback_query, state)


@router.callback_query(StateFilter(THOUGHT_DIARY_NEGATIVE_QUESTIONING), F.data == "td_get_recommendation")
@require_trial_access('emotion_diary')
async def process_get_recommendation(callback_query: types.CallbackQuery, state: FSMContext):
    user_id = callback_query.from_user.id
    await callback_query.answer()
    logger.info(f"User {user_id}: Requested recommendation. State: {await state.get_state()}")
    
    data = await state.get_data()
    fsm_option = data.get('selected_option') # From emotion diary
    fsm_state_val = data.get('selected_state') # From emotion diary
    conversation_history = data.get('conversation_history', [])
    
    if not conversation_history:
        logger.error(f"User {user_id}: Conversation history not found in state for recommendation.")
        await callback_query.message.answer("Произошла ошибка: не найдена история разговора. Пожалуйста, попробуйте снова.")
        return
    
    # Save emotion entry with full conversation before generating recommendation
    full_conversation_text = "\n".join([f"Сообщение {i+1}: {msg}" for i, msg in enumerate(conversation_history)])
    await save_emotion_entry(callback_query, state, emotion_type_from_flow="negative", text_entry=full_conversation_text)

    latest_entry = await get_latest_emotion_entry(user_id) # This might not be needed if we rely on FSM data
    option_to_use = fsm_option if fsm_option else (latest_entry.option if latest_entry else None)
    state_val_to_use = fsm_state_val if fsm_state_val else (latest_entry.state if latest_entry else None)

    emotion_message_prompt_text = None
    if state_val_to_use and option_to_use:
        emotion_message_prompt_text = final_messages.get(state_val_to_use, {}).get(option_to_use)
    
    # Prepare conversation context for recommendation
    conversation_context = "\n".join([f"Сообщение {i+1}: {msg}" for i, msg in enumerate(conversation_history)])
    
    if emotion_message_prompt_text:
        prompt = f"{emotion_message_prompt_text}. Пользователь рассказал о ситуации в ходе разговора:\n{conversation_context}\n\nДай короткую рекомендацию, как справиться с этой ситуацией, учитывая всю информацию. Не используй markdown."
    else:
        logger.warning(f"No specific prompt for state '{state_val_to_use}' and option '{option_to_use}'. Using generic prompt for user {user_id}.")
        prompt = f"Пользователь рассказал о проблеме в ходе разговора:\n{conversation_context}\n\n(Эмоция/состояние не найдено для специфического промпта, используем стандартный). Дай короткую поддерживающую рекомендацию на основе всей информации. Не используй markdown."
    
    try:
        response_content = client.models.generate_content(model="gemini-2.0-flash", contents=[prompt])
        ai_text = response_content.text if hasattr(response_content, 'text') else str(response_content)
    except Exception as e:
        logger.error(f"Error generating AI recommendation for user {user_id}: {e}")
        ai_text = "Вот рекомендация: попробуйте посмотреть на ситуацию с другой стороны и поддержать себя."
    
    await callback_query.message.edit_text(ai_text) # Edit the previous message ("Что вы хотите сделать дальше?")
    await state.update_data(last_ai_recommendation=ai_text) # Save for feedback
    
    feedback_keyboard = [
        [InlineKeyboardButton(text="Это помогло мне", callback_data="td_recommendation_helped")],
        [InlineKeyboardButton(text="Это не помогло мне", callback_data="td_recommendation_not_helped")]
    ]
    feedback_markup = InlineKeyboardMarkup(inline_keyboard=feedback_keyboard)
    # Send feedback request as a new message, as the previous one was edited
    feedback_message = await callback_query.message.answer("Этот совет был полезен?", reply_markup=feedback_markup)
    
    current_messages_to_delete = data.get('messages_to_delete', [])
    # The original message with "get recommendation" button was already in messages_to_delete
    # We edited it. The new AI text is now that message.
    # We add the new feedback_message to be deleted.
    current_messages_to_delete.append(feedback_message.message_id)
    await state.update_data(messages_to_delete=current_messages_to_delete)
    await state.set_state(THOUGHT_DIARY_AWAITING_RECOMMENDATION_FEEDBACK)
    logger.info(f"User {user_id}: Recommendation sent. State set to {THOUGHT_DIARY_AWAITING_RECOMMENDATION_FEEDBACK}")


@router.callback_query(StateFilter(THOUGHT_DIARY_NEGATIVE_QUESTIONING), F.data == "td_mark_for_work")
@require_trial_access('emotion_diary')
async def process_mark_for_work(callback_query: types.CallbackQuery, state: FSMContext):
    from src.handlers.main_menu import main_menu
    from src.handlers.therapy_themes import add_theme_from_thought_diary
    
    user_id = callback_query.from_user.id
    await callback_query.answer("Запись отмечена для проработки.")
    logger.info(f"User {user_id}: Chose 'mark for work'. State: {await state.get_state()}")
    
    data = await state.get_data()
    conversation_history = data.get('conversation_history', [])
    entry_text = data.get('negative_entry_text', 'Marked for work (text not found in FSM)')
    
    # Save emotion entry with full conversation history
    if conversation_history:
        full_conversation_text = "\n".join([f"Сообщение {i+1}: {msg}" for i, msg in enumerate(conversation_history)])
        await save_emotion_entry(callback_query, state, emotion_type_from_flow="negative", text_entry=full_conversation_text)
        logger.info(f"User {user_id}: Saved emotion entry with full conversation history for marking as therapy work")
    
    # Get user from database for therapy theme
    session_db = get_session()
    try:
        db_user = session_db.query(User).filter(User.telegram_id == user_id).first()
        if db_user:
            # Add to therapy themes
            await add_theme_from_thought_diary(db_user.id, entry_text)
            logger.info(f"User {user_id}: Added therapy theme from thought diary: {entry_text[:50]}...")
            
            # Update the emotion entry with therapy work marker
            if conversation_history:
                # Requery the latest entry in the current session to avoid session mixing
                latest_entry_in_session = session_db.query(EmotionEntry).filter(
                    EmotionEntry.user_id == db_user.id
                ).order_by(EmotionEntry.created_at.desc()).first()
                
                if latest_entry_in_session:
                    # Keep the full conversation but mark it for therapy
                    updated_text = f"Отмечено для проработки с терапевтом:\n{full_conversation_text}"
                    latest_entry_in_session.answer_text = updated_text
                    session_db.add(latest_entry_in_session)
                    session_db.commit()
                    logger.info(f"User {user_id}: DB entry {latest_entry_in_session.id} marked for work with full conversation.")
        else:
            logger.warning(f"User {user_id}: No db_user found for marking therapy theme.")
            
    except Exception as e:
        logger.error(f"Error processing mark_for_work for user {user_id}: {e}")
        session_db.rollback()
    finally:
        close_session(session_db)

    await callback_query.message.edit_text("Ваша запись отмечена для проработки с психотерапевтом.") # Edit previous message
    await delete_previous_messages(callback_query.message, state, keep_current=True) # Keep the edited message
    await state.clear() # Clear FSM state
    await main_menu(callback_query, state) # Navigate to main menu


@router.callback_query(StateFilter(THOUGHT_DIARY_AWAITING_RECOMMENDATION_FEEDBACK), F.data == "td_recommendation_helped")
@require_trial_access('emotion_diary')
async def process_recommendation_helped(callback_query: types.CallbackQuery, state: FSMContext):
    from src.handlers.main_menu import main_menu
    user_id = callback_query.from_user.id
    await callback_query.answer("Спасибо за обратную связь!")
    logger.info(f"User {user_id}: Recommendation helped. State: {await state.get_state()}")

    data = await state.get_data()
    conversation_history = data.get('conversation_history', [])
    last_ai_recommendation = data.get('last_ai_recommendation', '')
    last_entry = await get_latest_emotion_entry(user_id) # Or pass entry ID

    if last_entry:
        session_db = get_session()
        try:
            # Get the database user to get the correct internal user_id
            db_user = session_db.query(User).filter(User.telegram_id == user_id).first()
            if not db_user:
                logger.error(f"User with telegram_id {user_id} not found in database")
                return
            
            # Requery the latest entry in the current session to avoid session mixing
            latest_entry_in_session = session_db.query(EmotionEntry).filter(
                EmotionEntry.user_id == db_user.id
            ).order_by(EmotionEntry.created_at.desc()).first()
            
            if latest_entry_in_session:
                # Store conversation history with note that AI recommendation helped
                if conversation_history:
                    full_conversation_text = "\n".join([f"Сообщение {i+1}: {msg}" for i, msg in enumerate(conversation_history)])
                    latest_entry_in_session.answer_text = f"AI рекомендация помогла:\n{full_conversation_text}"
                else:
                    latest_entry_in_session.answer_text = f"AI рекомендация помогла: {last_ai_recommendation[:200]}"
                session_db.add(latest_entry_in_session)
                session_db.commit()
                logger.info(f"User {user_id}: DB entry {latest_entry_in_session.id} updated with conversation history and AI helped marker.")
            else:
                logger.warning(f"User {user_id}: No latest entry found for recommendation_helped.")
        except Exception as e:
            logger.error(f"Error updating DB for recommendation_helped for user {user_id}: {e}")
            session_db.rollback()
        finally:
            close_session(session_db)
    else:
        logger.warning(f"User {user_id}: No last_entry found for recommendation_helped.")
    
    await callback_query.message.edit_text("Спасибо за обратную связь! Ваш опыт сохранён.") # Edit "Этот совет был полезен?"
    await delete_previous_messages(callback_query.message, state, keep_current=True)
    await state.clear()
    await main_menu(callback_query, state)


@router.callback_query(StateFilter(THOUGHT_DIARY_AWAITING_RECOMMENDATION_FEEDBACK), F.data == "td_recommendation_not_helped")
@require_trial_access('emotion_diary')
async def process_recommendation_not_helped(callback_query: types.CallbackQuery, state: FSMContext):
    user_id = callback_query.from_user.id
    await callback_query.answer()
    logger.info(f"User {user_id}: Recommendation did not help. State: {await state.get_state()}")

    reconsider_keyboard = [
        [InlineKeyboardButton(text="Пересмотреть совет", callback_data="td_reconsider_advice")],
        # td_mark_for_work can be reused, or make a specific one if DB logic differs
        [InlineKeyboardButton(text="Отметить для проработки", callback_data="td_mark_for_work_after_not_helped")],
        [InlineKeyboardButton(text="На главную", callback_data="td_back_to_main_after_not_helped")]
    ]
    reconsider_markup = InlineKeyboardMarkup(inline_keyboard=reconsider_keyboard)
    # Edit the "Этот совет был полезен?" message
    await callback_query.message.edit_text("Мне жаль, что совет не помог. Что вы хотите сделать дальше?", reply_markup=reconsider_markup)
    
    await state.set_state(THOUGHT_DIARY_AWAITING_RECONSIDER_FEEDBACK)
    logger.info(f"User {user_id}: Prompting for reconsideration. State set to {THOUGHT_DIARY_AWAITING_RECONSIDER_FEEDBACK}")


@router.callback_query(StateFilter(THOUGHT_DIARY_AWAITING_RECONSIDER_FEEDBACK), F.data == "td_reconsider_advice")
@require_trial_access('emotion_diary')
async def process_reconsider_advice(callback_query: types.CallbackQuery, state: FSMContext):
    user_id = callback_query.from_user.id
    await callback_query.answer()
    logger.info(f"User {user_id}: Chose to reconsider advice. State: {await state.get_state()}")

    data = await state.get_data()
    fsm_option = data.get('selected_option')
    fsm_state_val = data.get('selected_state')
    conversation_history = data.get('conversation_history', [])
    last_ai_recommendation = data.get('last_ai_recommendation', 'предыдущий совет') # For prompt

    if not conversation_history:
        logger.error(f"User {user_id}: Conversation history not found in state for reconsideration.")
        await callback_query.message.answer("Произошла ошибка: не найдена история разговора. Пожалуйста, попробуйте снова.")
        return

    latest_entry = await get_latest_emotion_entry(user_id)
    option_to_use = fsm_option if fsm_option else (latest_entry.option if latest_entry else None)
    state_val_to_use = fsm_state_val if fsm_state_val else (latest_entry.state if latest_entry else None)
    
    emotion_message_prompt_text = None
    if state_val_to_use and option_to_use:
        emotion_message_prompt_text = final_messages.get(state_val_to_use, {}).get(option_to_use)

    # Prepare conversation context for reconsideration
    conversation_context = "\n".join([f"Сообщение {i+1}: {msg}" for i, msg in enumerate(conversation_history)])
    
    if emotion_message_prompt_text:
        prompt = f"{emotion_message_prompt_text}. Пользователь рассказал о ситуации в ходе разговора:\n{conversation_context}\n\nПредыдущий совет был: '{last_ai_recommendation}'. Дай ДРУГУЮ короткую рекомендацию, как справиться с этой ситуацией, учитывая всю информацию. Не используй markdown."
    else:
        logger.warning(f"No specific prompt for reconsideration for state '{state_val_to_use}' option '{option_to_use}'. User {user_id}.")
        prompt = f"Пользователь рассказал о проблеме в ходе разговора:\n{conversation_context}\n\nПредыдущий совет был: '{last_ai_recommendation}'. (Эмоция/состояние не найдено для специфического промпта). Пожалуйста, дай ДРУГОЙ совет на основе всей информации. Не используй markdown."
    
    try:
        response_content = client.models.generate_content(model="gemini-2.0-flash", contents=[prompt])
        ai_text = response_content.text if hasattr(response_content, 'text') else str(response_content)
    except Exception as e:
        logger.error(f"Error generating AI reconsideration for user {user_id}: {e}")
        ai_text = "Вот еще один совет: попробуйте сфокусироваться на маленьких шагах, которые вы можете предпринять прямо сейчас."
    
    await callback_query.message.edit_text(ai_text) # Edit the "Что вы хотите сделать дальше?" message
    await state.update_data(last_ai_recommendation=ai_text) # Update with new recommendation
    
    feedback_keyboard = [
        [InlineKeyboardButton(text="Это помогло мне", callback_data="td_recommendation_helped")],
        [InlineKeyboardButton(text="Это не помогло мне", callback_data="td_recommendation_not_helped")]
    ]
    feedback_markup = InlineKeyboardMarkup(inline_keyboard=feedback_keyboard)
    feedback_message = await callback_query.message.answer("Этот новый совет был полезен?", reply_markup=feedback_markup)
    
    current_messages_to_delete = data.get('messages_to_delete', [])
    current_messages_to_delete.append(feedback_message.message_id)
    await state.update_data(messages_to_delete=current_messages_to_delete)
    # Go back to awaiting_recommendation_feedback to handle response to this new advice
    await state.set_state(THOUGHT_DIARY_AWAITING_RECOMMENDATION_FEEDBACK) 
    logger.info(f"User {user_id}: Reconsidered advice sent. State set to {THOUGHT_DIARY_AWAITING_RECOMMENDATION_FEEDBACK}")


@router.callback_query(StateFilter(THOUGHT_DIARY_AWAITING_RECONSIDER_FEEDBACK), F.data == "td_mark_for_work_after_not_helped")
@require_trial_access('emotion_diary')
async def process_mark_for_work_after_not_helped(callback_query: types.CallbackQuery, state: FSMContext):
    # This is similar to the generic td_mark_for_work, but called from a different state/button
    from src.handlers.main_menu import main_menu
    from src.handlers.therapy_themes import add_theme_from_thought_diary
    
    user_id = callback_query.from_user.id
    await callback_query.answer("Запись отмечена для проработки.")
    logger.info(f"User {user_id}: Chose 'mark for work' after not helped. State: {await state.get_state()}")
    
    data = await state.get_data()
    conversation_history = data.get('conversation_history', [])
    # Use only the first message for therapy theme as requested
    first_message = data.get('negative_entry_text', 'Marked for work after AI advice (text not found in FSM)')
    # last_ai_recommendation is from the advice that didn't help
    ai_text_that_did_not_help = data.get('last_ai_recommendation', 'AI advice not found') 

    # Get user from database for therapy theme
    session_db = get_session()
    try:
        db_user = session_db.query(User).filter(User.telegram_id == user_id).first()
        if db_user:
            # Add to therapy themes with context that AI didn't help (using only first message)
            theme_text = f"{first_message} (AI совет не помог: {ai_text_that_did_not_help[:100]})"
            await add_theme_from_thought_diary(db_user.id, theme_text)
            logger.info(f"User {user_id}: Added therapy theme after AI not helpful: {first_message[:50]}...")
            
            # Update the emotion entry with full conversation history
            if conversation_history:
                full_conversation_text = "\n".join([f"Сообщение {i+1}: {msg}" for i, msg in enumerate(conversation_history)])
                
                # Check if entry exists, if not create it first
                latest_entry_in_session = session_db.query(EmotionEntry).filter(
                    EmotionEntry.user_id == db_user.id
                ).order_by(EmotionEntry.created_at.desc()).first()
                
                if not latest_entry_in_session:
                    # Create new entry if none exists
                    await save_emotion_entry(callback_query, state, emotion_type_from_flow="negative", text_entry=full_conversation_text)
                    # Requery after creation
                    latest_entry_in_session = session_db.query(EmotionEntry).filter(
                        EmotionEntry.user_id == db_user.id
                    ).order_by(EmotionEntry.created_at.desc()).first()
                
                # Requery the latest entry in the current session to avoid session mixing
                latest_entry_in_session = session_db.query(EmotionEntry).filter(
                    EmotionEntry.user_id == db_user.id
                ).order_by(EmotionEntry.created_at.desc()).first()
                
                if latest_entry_in_session:
                    updated_text = f"Отмечено для проработки с терапевтом (AI совет не помог):\n{full_conversation_text}"
                    latest_entry_in_session.answer_text = updated_text
                    session_db.add(latest_entry_in_session)
                    session_db.commit()
                    logger.info(f"User {user_id}: DB entry {latest_entry_in_session.id} marked for work after AI not helpful with full conversation.")
        else:
            logger.warning(f"User {user_id}: No db_user found for marking therapy theme after not helped.")
            
    except Exception as e:
        logger.error(f"Error processing mark_for_work_after_not_helped for user {user_id}: {e}")
        session_db.rollback()
    finally:
        close_session(session_db)

    await callback_query.message.edit_text("Ваш опыт отмечен для проработки с психотерапевтом.")
    await delete_previous_messages(callback_query.message, state, keep_current=True)
    await state.clear()
    await main_menu(callback_query, state)


@router.callback_query(StateFilter(THOUGHT_DIARY_AWAITING_RECONSIDER_FEEDBACK), F.data == "td_back_to_main_after_not_helped")
@require_trial_access('emotion_diary')
async def process_reconsider_to_main(callback_query: types.CallbackQuery, state: FSMContext):
    from src.handlers.main_menu import main_menu
    user_id = callback_query.from_user.id
    logger.info(f"User {user_id}: Chose 'back to main' after not helped. State: {await state.get_state()}")
    await callback_query.answer()
    await delete_previous_messages(callback_query.message, state)
    await state.clear()
    await main_menu(callback_query, state)


# Generic "back to main" handler if no specific state matched (should ideally not be hit if all states covered)
@router.callback_query(F.data.startswith("td_back_to_main")) # Catches any td_back_to_main_*
@require_trial_access('emotion_diary')
async def process_generic_back_to_main(callback_query: types.CallbackQuery, state: FSMContext):
    from src.handlers.main_menu import main_menu
    user_id = callback_query.from_user.id
    current_fsm_state = await state.get_state()
    logger.warning(f"User {user_id}: Hit generic 'td_back_to_main' handler from state {current_fsm_state} with data {callback_query.data}. Navigating to main menu.")
    await callback_query.answer()
    await delete_previous_messages(callback_query.message, state)
    await state.clear()
    await main_menu(callback_query, state)


async def save_emotion_entry(source_event: types.Message | types.CallbackQuery, state: FSMContext, emotion_type_from_flow: str = None, text_entry: str = None):
    session = get_session()
    try:
        telegram_user_id = source_event.from_user.id
        data = await state.get_data()
        
        # Get the database user to get the correct internal user_id
        db_user = session.query(User).filter(User.telegram_id == telegram_user_id).first()
        if not db_user:
            logger.error(f"User with telegram_id {telegram_user_id} not found in database")
            return
        
        # From emotion diary flow (passed via FSM data)
        selected_state_from_emotion_diary = data.get('selected_state') 
        selected_option_from_emotion_diary = data.get('selected_option')
        
        # This is 'positive' or 'negative', set in handle_emotion_choice or process_entry
        current_emotion_category = data.get('current_emotion_type', emotion_type_from_flow)

        # The detailed text provided by the user in the thought diary
        final_answer_text = text_entry if text_entry is not None else data.get('negative_entry_text', "No detailed text provided.")

        entry = EmotionEntry(
            user_id=db_user.id,  # Use database internal user_id, not telegram_user_id
            emotion_type=current_emotion_category, # 'positive'/'negative'
            answer_text=final_answer_text, # User's detailed text
            state=selected_state_from_emotion_diary, # e.g. "bad_state_1"
            option=selected_option_from_emotion_diary # e.g. "option_0"
        )
        session.add(entry)
        session.commit()
        session.refresh(entry) # To get the ID if needed
        await state.update_data(current_emotion_entry_id=entry.id) # Store current entry ID
        logger.info(f"Saved emotion entry ID {entry.id} for user {db_user.id} (telegram_id: {telegram_user_id}): category={current_emotion_category}, state={selected_state_from_emotion_diary}, option={selected_option_from_emotion_diary}")
    except Exception as e:
        logger.error(f"Error saving emotion entry for user {telegram_user_id}: {e}")
        session.rollback()
    finally:
        close_session(session)


async def generate_follow_up_question(conversation_history: list) -> str:
    """Generate a follow-up question based on conversation history"""
    try:
        conversation_text = "\n".join([f"Сообщение {i+1}: {msg}" for i, msg in enumerate(conversation_history)])
        
        prompt = f"""
Ты психологический помощник. Пользователь рассказывает о проблеме или негативной ситуации.
Твоя задача - задать один короткий, деликатный уточняющий вопрос, чтобы лучше понять ситуацию.

История разговора:
{conversation_text}

Задай один уточняющий вопрос, который поможет:
- Понять эмоции глубже
- Выяснить контекст ситуации
- Определить триггеры или причины
- Узнать, как это влияет на человека

Вопрос должен быть:
- Коротким (1-2 предложения максимум)
- Деликатным и поддерживающим
- Направленным на понимание, а не на решение
- Без markdown форматирования

Пример хороших вопросов:
- "Когда это чувство появилось впервые?"
- "Что именно в этой ситуации беспокоит больше всего?"
- "Как долго вы это переживаете?"
"""

        response = client.models.generate_content(
            model="gemini-2.0-flash", 
            contents=[prompt]
        )
        
        question = response.text if hasattr(response, 'text') else str(response)
        return question.strip()
        
    except Exception as e:
        logger.error(f"Error generating follow-up question: {e}")
        # Fallback questions
        fallback_questions = [
            "Расскажите больше об этой ситуации. Что именно вас беспокоит?",
            "Как долго вы это переживаете?",
            "Что в этой ситуации влияет на вас сильнее всего?",
            "Когда вы впервые почувствовали это?"
        ]
        return random.choice(fallback_questions)

async def get_latest_emotion_entry(telegram_user_id: int, entry_id: int = None):
    session = get_session()
    try:
        # Get the database user to get the correct internal user_id
        db_user = session.query(User).filter(User.telegram_id == telegram_user_id).first()
        if not db_user:
            logger.error(f"User with telegram_id {telegram_user_id} not found in database")
            return None
        
        if entry_id:
            entry = session.query(EmotionEntry).filter_by(id=entry_id, user_id=db_user.id).first()
        else: # Fallback to latest if no ID provided, though using ID is safer
            entry = session.query(EmotionEntry).filter_by(user_id=db_user.id).order_by(EmotionEntry.created_at.desc()).first()
        
        if entry:
             session.expunge(entry) # Detach from session before returning
        return entry
    except Exception as e:
        logger.error(f"Error fetching emotion entry for user {telegram_user_id} (entry_id: {entry_id}): {e}")
        return None
    finally:
        close_session(session)

# The old thought_diary_handler is no longer needed as its logic is distributed
# among the new state-specific handlers.

# Ensure this new router is imported and included in your main.py or bot setup.
# For example, in main.py:
# from handlers import thought_diary as thought_diary_handlers
# dp.include_router(thought_diary_handlers.router)