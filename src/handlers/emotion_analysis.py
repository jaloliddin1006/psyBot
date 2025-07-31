#!/usr/bin/env python3
"""
Emotion Analysis Handlers for PsyBot
Provides analytics and insights about user's emotional patterns
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
from collections import Counter
import os
import tempfile
from aiogram import types, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, FSInputFile
from aiogram.filters import StateFilter
from database.session import get_session, close_session
from database.models import User, EmotionEntry, WeeklyReflection
from .utils import delete_previous_messages
from constants import EMOTION_ANALYSIS_PERIOD_SELECTION, MAIN_MENU
from google import genai
import asyncio
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image as RLImage
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import urllib.request
from trial_manager import require_trial_access
from dotenv import load_dotenv
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
import matplotlib.dates as mdates
import numpy as np
from PIL import Image as PILImage  # For reading chart dimensions

# Initialize logger and router
logger = logging.getLogger(__name__)
router = Router(name=__name__)

client = genai.Client(
    api_key=os.environ.get("GOOGLE_GENAI_API_KEY"),
    http_options={"base_url": os.environ.get("API_URL")}
)

# Emotion mapping for better readability
EMOTION_MAPPING = {
    "good_state_1": "Подъем, легкость",
    "good_state_2": "Спокойствие, расслабленность", 
    "good_state_3": "Уют, близость",
    "good_state_4": "Интерес, вдохновение",
    "good_state_5": "Сила, уверенность",
    "bad_state_1": "Тяжесть, усталость",
    "bad_state_2": "Тревога, беспокойство",
    "bad_state_3": "Злость, раздражение",
    "bad_state_4": "Отстраненность, обида",
    "bad_state_5": "Вина, смущение"
}

OPTION_MAPPING = {
    "good_state_1": {0: "Приятно", 1: "Захватывает"},
    "good_state_2": {0: "Удовлетворение", 1: "Глубокий покой"},
    "good_state_3": {0: "Тепло", 1: "Близость"},
    "good_state_4": {0: "Интерес", 1: "Вдохновение"},
    "good_state_5": {0: "Сила", 1: "Уверенность"},
    "bad_state_1": {0: "Усталость", 1: "Потеря сил"},
    "bad_state_2": {0: "Тревога", 1: "Неуверенность"},
    "bad_state_3": {0: "Злость", 1: "Раздражение"},
    "bad_state_4": {0: "Отстраненность", 1: "Обида"},
    "bad_state_5": {0: "Вина", 1: "Смущение"}
}

async def start_emotion_analysis(message: types.Message, state: FSMContext):
    """Start emotion analysis flow"""
    logger.info(f"start_emotion_analysis invoked. message.from_user.id: {message.from_user.id}")
    
    session = get_session()
    db_user = session.query(User).filter(User.telegram_id == message.from_user.id).first()
    
    if not db_user or not getattr(db_user, 'registration_complete', False) or not db_user.full_name:
        close_session(session)
        await state.clear()
        await message.answer("Пожалуйста, завершите регистрацию с помощью /start перед использованием аналитики эмоций.")
        return MAIN_MENU
    
    close_session(session)
    
    # Check if user has any emotion entries
    session = get_session()
    emotion_count = session.query(EmotionEntry).filter(EmotionEntry.user_id == db_user.id).count()
    close_session(session)
    
    if emotion_count == 0:
        await message.answer("У вас пока нет записей в дневнике эмоций. Начните записывать свои эмоции, чтобы получить аналитику!")
        return MAIN_MENU
    
    # Store message for deletion
    data = await state.get_data()
    messages_to_delete = data.get('messages_to_delete', [])
    messages_to_delete.append(message.message_id)
    await state.update_data(messages_to_delete=messages_to_delete)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="3 дня", callback_data="period_3")],
        [InlineKeyboardButton(text="Неделя (7 дней)", callback_data="period_7")],
        [InlineKeyboardButton(text="Две недели (14 дней)", callback_data="period_14")],
        [InlineKeyboardButton(text="Месяц (30 дней)", callback_data="period_30")],
        [InlineKeyboardButton(text="3 месяца (90 дней)", callback_data="period_90")],
        [InlineKeyboardButton(text="Назад", callback_data="back_to_main")]
    ])
    
    sent = await message.answer("Какой период тебя интересует?", reply_markup=keyboard)
    messages_to_delete.append(sent.message_id)
    await state.update_data(messages_to_delete=messages_to_delete)
    await state.set_state(EMOTION_ANALYSIS_PERIOD_SELECTION)
    
    return EMOTION_ANALYSIS_PERIOD_SELECTION

@router.callback_query(F.data == "back_to_main")
@require_trial_access('emotion_analytics')
async def handle_back_to_main_from_analysis(callback: types.CallbackQuery, state: FSMContext):
    """Handle back to main menu from emotion analysis results"""
    await callback.answer()
    from handlers.main_menu import main_menu
    await delete_previous_messages(callback.message, state)
    await state.clear()
    await main_menu(callback, state)

@router.callback_query(StateFilter(EMOTION_ANALYSIS_PERIOD_SELECTION))
@require_trial_access('emotion_analytics')
async def handle_period_selection(callback: types.CallbackQuery, state: FSMContext):
    """Handle period selection for emotion analysis"""
    logger.info(f"handle_period_selection called with data: {callback.data}")
    await callback.answer()
    
    if callback.data == "back_to_main":
        from handlers.main_menu import main_menu
        await delete_previous_messages(callback.message, state)
        await state.clear()
        await main_menu(callback, state)
        return MAIN_MENU
    
    # Extract period days
    period_days = int(callback.data.split("_")[1])
    
    session = get_session()
    db_user = session.query(User).filter(User.telegram_id == callback.from_user.id).first()
    
    if not db_user:
        close_session(session)
        await callback.message.answer("Ошибка: пользователь не найден.")
        return MAIN_MENU
    
    # Get emotion entries for the period
    end_date = datetime.now()
    start_date = end_date - timedelta(days=period_days)
    
    emotion_entries = session.query(EmotionEntry).filter(
        EmotionEntry.user_id == db_user.id,
        EmotionEntry.created_at >= start_date,
        EmotionEntry.created_at <= end_date
    ).order_by(EmotionEntry.created_at.desc()).all()
    
    close_session(session)
    
    if not emotion_entries:
        await callback.message.edit_text(f"За последние {period_days} дней записей в дневнике эмоций не найдено.")
        await delete_previous_messages(callback.message, state, keep_current=True)
        await state.clear()
        from handlers.main_menu import main_menu
        await main_menu(callback, state)
        return MAIN_MENU
    
    if period_days == 3:
        # Generate short text analysis for 3 days
        await generate_short_analysis(callback, state, emotion_entries, period_days)
    else:
        # Generate PDF report for longer periods
        await generate_pdf_report(callback, state, emotion_entries, period_days)
    
    # Don't immediately return to main menu - let the analysis functions handle the flow
    return

async def generate_short_analysis(callback: types.CallbackQuery, state: FSMContext, 
                                emotion_entries: List[EmotionEntry], period_days: int):
    """Generate short text analysis for 3 days"""
    
    # Analyze emotions
    emotion_states = [entry.state for entry in emotion_entries if entry.state]
    emotion_counter = Counter(emotion_states)
    most_common_emotion = emotion_counter.most_common(1)[0] if emotion_counter else None
    
    # Group entries by day
    daily_emotions = {}
    for entry in emotion_entries:
        day = entry.created_at.date()
        if day not in daily_emotions:
            daily_emotions[day] = []
        daily_emotions[day].append(entry)
    
    # Build analysis text
    start_date = (datetime.now() - timedelta(days=period_days)).strftime("%d.%m.%Y")
    end_date = datetime.now().strftime("%d.%m.%Y")
    
    analysis_text = f"📊 **Анализ эмоций за период {start_date} - {end_date}**\n\n"
    
    if most_common_emotion:
        emotion_name = EMOTION_MAPPING.get(most_common_emotion[0], most_common_emotion[0])
        analysis_text += f"🎯 **Самая часто испытываемая эмоция за 3 дня:** {emotion_name}\n\n"
    
    # Key moments analysis section
    analysis_text += "📝 **Краткий разбор ключевых моментов:**\n"
    
    # Sort all entries chronologically
    all_entries = sorted(emotion_entries, key=lambda x: x.created_at)
    
    # Separate entries into those with detailed context and simple diary entries
    entries_with_context = []
    simple_diary_entries = []
    
    for entry in all_entries:
        if entry.answer_text and entry.answer_text.strip():
            if entry.answer_text == "Emotion recorded from diary":
                # This is a simple emotion diary entry without detailed context
                simple_diary_entries.append(entry)
            elif entry.answer_text.startswith("Marked for therapy work:") or entry.answer_text.startswith("Отмечено для проработки с терапевтом"):
                # This is marked for therapy work but might have context
                entries_with_context.append(entry)
            elif entry.answer_text.startswith("AI рекомендация помогла"):
                therapy_marker = " [AI помог]"
                if ":" in entry.answer_text:
                    context = entry.answer_text.split(":", 1)[1].strip()
                entries_with_context.append(entry)
            elif entry.answer_text not in ["Marked for therapy work:"]:
                # This has actual user context/dialog
                entries_with_context.append(entry)
    
    # Show entries with detailed context first
    if entries_with_context:
        analysis_text += "**Подробные записи с контекстом:**\n"
        for entry in entries_with_context:
            # Format date and time
            date_str = entry.created_at.strftime("%d.%m.%Y, %H:%M")
            
            # Get emotion name
            emotion_name = EMOTION_MAPPING.get(entry.state, entry.state) if entry.state else "эмоция"
            
            # Get context/reason
            context = entry.answer_text.strip()
            
            # Handle special cases for marked therapy work
            therapy_marker = ""
            if context.startswith("Marked for therapy work:"):
                therapy_marker = " [для терапии]"
                context = context.replace("Marked for therapy work:", "").strip()
                if context.startswith("Marked for work (text not found in FSM)"):
                    continue  # Skip entries without proper context
            elif context.startswith("Отмечено для проработки с терапевтом"):
                therapy_marker = " [для терапии]"
                if ":" in context:
                    context = context.split(":", 1)[1].strip()
            elif context.startswith("AI рекомендация помогла"):
                therapy_marker = " [AI помог]"
                if ":" in context:
                    context = context.split(":", 1)[1].strip()
            
            # Extract meaningful conversation from formatted text
            if context.startswith("Сообщение 1:"):
                # This is a formatted conversation, extract the main content
                messages = []
                for line in context.split("\n"):
                    if line.startswith("Сообщение ") and ":" in line:
                        msg_content = line.split(":", 1)[1].strip()
                        if msg_content:
                            messages.append(msg_content)
                
                if messages:
                    # Show the first message as the main context, mention if there are more
                    context = messages[0]
                    if len(messages) > 1:
                        context += f" [и ещё {len(messages)-1} сообщ.]"
            
            # Limit context length for readability
            if len(context) > 120:
                context = context[:120] + "..."
            
            # Create formatted entry
            analysis_text += f"• {date_str}, {emotion_name}: {context}{therapy_marker}\n"
        
        analysis_text += "\n"
    
    # Show simple diary entries
    if simple_diary_entries:
        analysis_text += "**Быстрые записи эмоций:**\n"
        for entry in simple_diary_entries:
            # Format date and time
            date_str = entry.created_at.strftime("%d.%m.%Y, %H:%M")
            
            # Get emotion name and option
            emotion_name = EMOTION_MAPPING.get(entry.state, entry.state) if entry.state else "эмоция"
            
            # Try to get specific option description
            option_text = ""
            if entry.state and entry.option and entry.option.startswith('option_'):
                try:
                    option_num = int(entry.option.split('_')[1])
                    option_description = OPTION_MAPPING.get(entry.state, {}).get(option_num, "")
                    if option_description:
                        option_text = f" ({option_description})"
                except (ValueError, IndexError):
                    pass
            
            # Create formatted entry
            analysis_text += f"• {date_str}, {emotion_name}{option_text}\n"
        
        analysis_text += "\n"
    
    # Show message if no entries at all
    if not entries_with_context and not simple_diary_entries:
        analysis_text += "Записи эмоций не найдены.\n\n"
    

    
    # Add positive moments section - including both emotion entries and weekly reflections
    positive_entries = [e for e in emotion_entries if e.emotion_type == "positive"]
    
    # Get weekly reflections from the same period
    session = get_session()
    try:
        user = session.query(User).filter(User.telegram_id == callback.from_user.id).first()
        weekly_reflections = []
        if user:
            start_datetime = datetime.now() - timedelta(days=period_days)
            weekly_reflections = session.query(WeeklyReflection).filter(
                WeeklyReflection.user_id == user.id,
                WeeklyReflection.created_at >= start_datetime
            ).order_by(WeeklyReflection.created_at.desc()).all()
    finally:
        close_session(session)
    
    if positive_entries or weekly_reflections:
        analysis_text += f"\n😊 **Радостные моменты:**\n"
        
        # Add positive emotion entries
        for entry in positive_entries[-3:]:  # Last 3 positive entries
            time_str = entry.created_at.strftime("%d.%m %H:%M")
            emotion_name = EMOTION_MAPPING.get(entry.state, entry.state) if entry.state else "позитивная эмоция"
            analysis_text += f"• {time_str}: {emotion_name}\n"
        
        # Add weekly reflection moments
        for reflection in weekly_reflections:
            reflection_date = reflection.created_at.strftime("%d.%m")
            analysis_text += f"\n**Еженедельная рефлексия ({reflection_date}):**\n"
            
            if reflection.smile_moment:
                analysis_text += f"• Момент улыбки: {reflection.smile_moment[:100]}{'...' if len(reflection.smile_moment) > 100 else ''}\n"
            
            if reflection.kindness:
                analysis_text += f"• Доброта: {reflection.kindness[:100]}{'...' if len(reflection.kindness) > 100 else ''}\n"
            
            if reflection.peace_moment:
                analysis_text += f"• Спокойствие: {reflection.peace_moment[:100]}{'...' if len(reflection.peace_moment) > 100 else ''}\n"
            
            if reflection.new_discovery:
                analysis_text += f"• Открытие: {reflection.new_discovery[:100]}{'...' if len(reflection.new_discovery) > 100 else ''}\n"
            
            if reflection.gratitude:
                analysis_text += f"• Благодарность: {reflection.gratitude[:100]}{'...' if len(reflection.gratitude) > 100 else ''}\n"
    
    # Generate emotion charts even for short analysis
    try:
        # Generate emotion frequency charts
        chart_path = await create_emotion_charts(emotion_entries, start_date, end_date)
        
        if chart_path:
            # Send emotion frequency chart
            chart_file = FSInputFile(chart_path, filename=f"emotion_charts_{start_date}_{end_date}.png")
            await callback.message.answer_photo(
                chart_file,
                caption=f"📊 Графики частоты эмоций за период {start_date} - {end_date}"
            )
            
            # Clean up chart file
            os.unlink(chart_path)
        
    except Exception as e:
        logger.error(f"Error generating charts: {e}")
    
    # Generate advice for most common negative emotion
    negative_entries = [e for e in emotion_entries if e.emotion_type == "negative"]
    if negative_entries:
        negative_states = [e.state for e in negative_entries if e.state]
        if negative_states:
            most_common_negative = Counter(negative_states).most_common(1)[0]
            await generate_advice_for_emotion(callback, analysis_text, most_common_negative[0], negative_entries)
            return
    
    # Send analysis without advice if no negative emotions
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="В главное меню", callback_data="back_to_main")]
    ])
    await callback.message.edit_text(analysis_text, reply_markup=keyboard, parse_mode="Markdown")

async def generate_advice_for_emotion(callback: types.CallbackQuery, analysis_text: str, 
                                    emotion_state: str, negative_entries: List[EmotionEntry]):
    """Generate AI advice for the most common negative emotion"""
    
    emotion_name = EMOTION_MAPPING.get(emotion_state, emotion_state)
    
    # Collect contexts for this emotion
    contexts = []
    for entry in negative_entries:
        if entry.state == emotion_state and entry.answer_text:
            contexts.append(entry.answer_text)
    
    context_text = " ".join(contexts[:3]) if contexts else ""
    
    prompt = f"""
    Пользователь часто испытывает эмоцию: {emotion_name}
    Контексты, в которых это происходит: {context_text}
    
    Дай краткий, практичный совет (2-3 предложения) по работе с этой эмоцией, 
    учитывая контексты. Будь эмпатичным и поддерживающим.
    Не используй markdown.
    """
    
    try:
        response = await asyncio.to_thread(
            client.models.generate_content,
            model="gemini-2.0-flash",
            contents=[prompt]
        )
        advice = response.text if hasattr(response, 'text') else str(response)
    except Exception as e:
        logger.error(f"Error generating advice: {e}")
        advice = f"Рекомендую обратить внимание на эмоцию '{emotion_name}' и подумать о том, что её вызывает. не исопльзуй markdown"
    
    analysis_text += f"\n💡 Совет по работе с эмоцией '{emotion_name}':\n{advice}"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="В главное меню", callback_data="back_to_main")]
    ])
    await callback.message.edit_text(analysis_text, reply_markup=keyboard, parse_mode="Markdown")



async def generate_pdf_report(callback: types.CallbackQuery, state: FSMContext, 
                            emotion_entries: List[EmotionEntry], period_days: int):
    """Generate PDF report for longer periods"""
    
    await callback.message.edit_text("📄 Генерирую PDF-отчет... Это может занять несколько секунд.")
    
    start_date = (datetime.now() - timedelta(days=period_days)).strftime("%d.%m.%Y")
    end_date = datetime.now().strftime("%d.%m.%Y")
    
    # Analyze emotions for the report
    emotion_states = [entry.state for entry in emotion_entries if entry.state]
    emotion_counter = Counter(emotion_states)
    
    positive_entries = [e for e in emotion_entries if e.emotion_type == "positive"]
    negative_entries = [e for e in emotion_entries if e.emotion_type == "negative"]
    
    # Generate therapy topics with AI
    therapy_topics = []
    if negative_entries:
        contexts = [e.answer_text for e in negative_entries if e.answer_text and len(e.answer_text) > 20]
        if contexts:
            therapy_topics = await generate_therapy_topics_text(contexts[:5])
    
    if not therapy_topics:
        therapy_topics = [
            "Работа с эмоциональной регуляцией",
            "Развитие навыков самоанализа", 
            "Управление стрессом"
        ]
    
    # Create emotion charts and collect their paths to embed into PDF later
    chart_paths = []
    try:
        # Generate emotion frequency charts
        chart_path = await create_emotion_charts(emotion_entries, start_date, end_date)
        
        if chart_path:
            chart_paths.append(chart_path)
        
    except Exception as e:
        logger.error(f"Error generating charts: {e}")
    
    # Create PDF
    try:
        pdf_path = await create_pdf_report(
            start_date, end_date, period_days, emotion_entries, 
            positive_entries, negative_entries, emotion_counter, therapy_topics, chart_paths
        )
        
        # Send PDF file
        pdf_file = FSInputFile(pdf_path, filename=f"emotion_report_{start_date}_{end_date}.pdf")
        await callback.message.answer_document(
            pdf_file,
            caption=f"📊 Отчет по эмоциям за период {start_date} - {end_date}"
        )
        
        # Send button to return to main menu
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="В главное меню", callback_data="back_to_main")]
        ])
        await callback.message.answer("Отчет готов! 📄", reply_markup=keyboard)
        
        # Clean up temporary file
        os.unlink(pdf_path)
        # Remove generated chart images after they are embedded
        for p in chart_paths:
            try:
                os.unlink(p)
            except Exception:
                pass
        
    except Exception as e:
        logger.error(f"Error generating PDF: {e}")
        # Fallback to text report
        await generate_text_report(callback, start_date, end_date, period_days, 
                                 emotion_entries, positive_entries, negative_entries, 
                                 emotion_counter, therapy_topics)

def transliterate_russian(text: str) -> str:
    """Convert Russian text to Latin transliteration for PDF compatibility"""
    russian_to_latin = {
        'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd', 'е': 'e', 'ё': 'yo',
        'ж': 'zh', 'з': 'z', 'и': 'i', 'й': 'y', 'к': 'k', 'л': 'l', 'м': 'm',
        'н': 'n', 'о': 'o', 'п': 'p', 'р': 'r', 'с': 's', 'т': 't', 'у': 'u',
        'ф': 'f', 'х': 'h', 'ц': 'ts', 'ч': 'ch', 'ш': 'sh', 'щ': 'sch',
        'ъ': '', 'ы': 'y', 'ь': '', 'э': 'e', 'ю': 'yu', 'я': 'ya',
        'А': 'A', 'Б': 'B', 'В': 'V', 'Г': 'G', 'Д': 'D', 'Е': 'E', 'Ё': 'Yo',
        'Ж': 'Zh', 'З': 'Z', 'И': 'I', 'Й': 'Y', 'К': 'K', 'Л': 'L', 'М': 'M',
        'Н': 'N', 'О': 'O', 'П': 'P', 'Р': 'R', 'С': 'S', 'Т': 'T', 'У': 'U',
        'Ф': 'F', 'Х': 'H', 'Ц': 'Ts', 'Ч': 'Ch', 'Ш': 'Sh', 'Щ': 'Sch',
        'Ъ': '', 'Ы': 'Y', 'Ь': '', 'Э': 'E', 'Ю': 'Yu', 'Я': 'Ya'
    }
    
    result = ""
    for char in text:
        result += russian_to_latin.get(char, char)
    return result

def setup_russian_fonts():
    """Download and register DejaVu fonts for Russian text support"""
    try:
        # First, try to find system fonts that support Russian
        import platform
        system = platform.system()
        
        # Try to register system fonts first
        system_fonts_registered = False
        
        if system == "Darwin":  # macOS
            # Try common macOS fonts that support Cyrillic
            macos_fonts = [
                "/System/Library/Fonts/Helvetica.ttc",
                "/Library/Fonts/Arial.ttf",
                "/System/Library/Fonts/Times.ttc"
            ]
            for font_path in macos_fonts:
                if os.path.exists(font_path):
                    try:
                        pdfmetrics.registerFont(TTFont('RussianFont', font_path))
                        pdfmetrics.registerFont(TTFont('RussianFont-Bold', font_path))
                        system_fonts_registered = True
                        logger.info(f"Registered system font: {font_path}")
                        break
                    except:
                        continue
        
        elif system == "Linux":
            # Try common Linux fonts
            linux_fonts = [
                "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
                "/usr/share/fonts/TTF/DejaVuSans.ttf"
            ]
            for font_path in linux_fonts:
                if os.path.exists(font_path):
                    try:
                        pdfmetrics.registerFont(TTFont('RussianFont', font_path))
                        bold_path = font_path.replace('Regular', 'Bold').replace('.ttf', '-Bold.ttf')
                        if os.path.exists(bold_path):
                            pdfmetrics.registerFont(TTFont('RussianFont-Bold', bold_path))
                        else:
                            pdfmetrics.registerFont(TTFont('RussianFont-Bold', font_path))
                        system_fonts_registered = True
                        logger.info(f"Registered system font: {font_path}")
                        break
                    except:
                        continue
        
        elif system == "Windows":
            # Try common Windows fonts
            windows_fonts = [
                "C:/Windows/Fonts/arial.ttf",
                "C:/Windows/Fonts/calibri.ttf",
                "C:/Windows/Fonts/tahoma.ttf"
            ]
            for font_path in windows_fonts:
                if os.path.exists(font_path):
                    try:
                        pdfmetrics.registerFont(TTFont('RussianFont', font_path))
                        bold_path = font_path.replace('.ttf', 'b.ttf')
                        if os.path.exists(bold_path):
                            pdfmetrics.registerFont(TTFont('RussianFont-Bold', bold_path))
                        else:
                            pdfmetrics.registerFont(TTFont('RussianFont-Bold', font_path))
                        system_fonts_registered = True
                        logger.info(f"Registered system font: {font_path}")
                        break
                    except:
                        continue
        
        if system_fonts_registered:
            return True
        
        # If system fonts failed, try to download DejaVu fonts
        # Create fonts directory if it doesn't exist
        fonts_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'fonts')
        os.makedirs(fonts_dir, exist_ok=True)
        
        # Check if fonts already exist
        dejavu_path = os.path.join(fonts_dir, 'DejaVuSans.ttf')
        dejavu_bold_path = os.path.join(fonts_dir, 'DejaVuSans-Bold.ttf')
        
        if os.path.exists(dejavu_path) and os.path.exists(dejavu_bold_path):
            # Fonts already downloaded, just register them
            pdfmetrics.registerFont(TTFont('RussianFont', dejavu_path))
            pdfmetrics.registerFont(TTFont('RussianFont-Bold', dejavu_bold_path))
            logger.info("Using existing DejaVu fonts")
            return True
        
        # Try to download fonts with SSL context handling
        import ssl
        import urllib.request
        
        # Create SSL context that doesn't verify certificates (for corporate networks)
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        
        # Font URLs and filenames
        fonts = {
            'DejaVuSans.ttf': 'https://github.com/dejavu-fonts/dejavu-fonts/raw/master/ttf/DejaVuSans.ttf',
            'DejaVuSans-Bold.ttf': 'https://github.com/dejavu-fonts/dejavu-fonts/raw/master/ttf/DejaVuSans-Bold.ttf'
        }
        
        # Download fonts if they don't exist
        for filename, url in fonts.items():
            font_path = os.path.join(fonts_dir, filename)
            if not os.path.exists(font_path):
                logger.info(f"Downloading font: {filename}")
                request = urllib.request.Request(url)
                with urllib.request.urlopen(request, context=ssl_context) as response:
                    with open(font_path, 'wb') as f:
                        f.write(response.read())
        
        # Register fonts with ReportLab
        if os.path.exists(dejavu_path):
            pdfmetrics.registerFont(TTFont('RussianFont', dejavu_path))
        if os.path.exists(dejavu_bold_path):
            pdfmetrics.registerFont(TTFont('RussianFont-Bold', dejavu_bold_path))
            
        return True
    except Exception as e:
        logger.error(f"Error setting up Russian fonts: {e}")
        # Try to register a basic font that might work
        try:
            # Use built-in fonts as last resort
            pdfmetrics.registerFont(TTFont('RussianFont', 'Helvetica'))
            pdfmetrics.registerFont(TTFont('RussianFont-Bold', 'Helvetica-Bold'))
            logger.info("Using fallback Helvetica fonts")
            return False  # Return False to indicate limited support
        except:
            return False

async def create_pdf_report(start_date: str, end_date: str, period_days: int,
                          emotion_entries: List[EmotionEntry], positive_entries: List[EmotionEntry],
                          negative_entries: List[EmotionEntry], emotion_counter: Counter,
                          therapy_topics: List[str], chart_paths: List[str]) -> str:
    """Create PDF report and return file path using ReportLab with transliteration.
    chart_paths: list of image file paths to embed into the PDF (emotion charts)."""
    
    # Setup Russian fonts
    fonts_available = setup_russian_fonts()
    
    # Create temporary file
    with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
        pdf_path = tmp_file.name
    
    # Create PDF document
    doc = SimpleDocTemplate(pdf_path, pagesize=A4)
    styles = getSampleStyleSheet()
    story = []
    
    # Define custom styles with Russian font support
    if fonts_available:
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=18,
            spaceAfter=30,
            alignment=1,  # Center alignment
            fontName='RussianFont-Bold'
        )
        
        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontSize=14,
            spaceAfter=12,
            fontName='RussianFont-Bold'
        )
        
        normal_style = ParagraphStyle(
            'CustomNormal',
            parent=styles['Normal'],
            fontSize=10,
            fontName='RussianFont'
        )
    else:
        # Fallback to default styles if fonts are not available
        title_style = styles['Heading1']
        heading_style = styles['Heading2']
        normal_style = styles['Normal']
    
    # Title
    story.append(Paragraph("Отчет по эмоциям", title_style))
    story.append(Paragraph(f"Период: {start_date} - {end_date}", normal_style))
    story.append(Spacer(1, 20))
    
    # Statistics section (text instead of table)
    story.append(Paragraph("Статистика", heading_style))
    stats_text = (
        f"Всего записей: {len(emotion_entries)}<br/>"
        f"Позитивных эмоций: {len(positive_entries)}<br/>"
        f"Негативных эмоций: {len(negative_entries)}<br/>"
        f"Дней с записями: {len(set(e.created_at.date() for e in emotion_entries))}"
    )
    story.append(Paragraph(stats_text, normal_style))
    story.append(Spacer(1, 20))

    # Embed emotion charts images while preserving aspect ratio (fit to page width)
    if chart_paths:
        story.append(Paragraph("Графики эмоций", heading_style))
        max_width = doc.width  # available drawing width inside page margins (in points)
        for img_path in chart_paths:
            try:
                # Determine original image aspect ratio
                with PILImage.open(img_path) as _pil_img:
                    img_w_px, img_h_px = _pil_img.size
                aspect = img_h_px / img_w_px if img_w_px else 0.75

                display_width = max_width
                display_height = display_width * aspect

                img = RLImage(img_path, width=display_width, height=display_height)
                story.append(img)
                story.append(Spacer(1, 15))
            except Exception as e:
                logger.error(f"Error embedding chart {img_path} into PDF: {e}")
    story.append(Spacer(1, 10))
    
    # Top emotions (bullet list instead of table)
    if emotion_counter:
        story.append(Paragraph("Топ-3 самые частые эмоции", heading_style))
        for state, count in emotion_counter.most_common(3):
            emotion_name = EMOTION_MAPPING.get(state, state)
            story.append(Paragraph(f"• {emotion_name}: {count}", normal_style))
        story.append(Spacer(1, 20))
    
    # Key moments analysis section
    story.append(Paragraph("Краткий разбор ключевых моментов", heading_style))
    
    # Sort all entries chronologically
    all_entries = sorted(emotion_entries, key=lambda x: x.created_at)
    
    # Separate entries into those with detailed context and simple diary entries
    entries_with_context = []
    simple_diary_entries = []
    
    for entry in all_entries:
        if entry.answer_text and entry.answer_text.strip():
            if entry.answer_text == "Emotion recorded from diary":
                # This is a simple emotion diary entry without detailed context
                simple_diary_entries.append(entry)
            elif entry.answer_text not in ["Marked for therapy work:"]:
                # This has actual user context/dialog
                entries_with_context.append(entry)
    
    # Show entries with detailed context first
    if entries_with_context:
        story.append(Paragraph("Подробные записи с контекстом:", normal_style))
        for entry in entries_with_context:
            # Format date and time
            date_str = entry.created_at.strftime("%d.%m.%Y, %H:%M")
            
            # Get emotion name
            emotion_name = EMOTION_MAPPING.get(entry.state, entry.state) if entry.state else "эмоция"
            
            # Get context/reason
            context = entry.answer_text.strip()
            
            # Handle special cases for marked therapy work
            if context.startswith("Marked for therapy work:"):
                context = context.replace("Marked for therapy work:", "").strip()
                if context.startswith("Marked for work (text not found in FSM)"):
                    continue  # Skip entries without proper context
            
            # Limit context length for readability
            if len(context) > 150:
                context = context[:150] + "..."
            
            # Create formatted entry
            entry_text = f"{date_str}, {emotion_name}: {context}"
            story.append(Paragraph(f"• {entry_text}", normal_style))
        
        story.append(Spacer(1, 10))
    
    # Show simple diary entries
    if simple_diary_entries:
        story.append(Paragraph("Быстрые записи эмоций:", normal_style))
        for entry in simple_diary_entries:
            # Format date and time
            date_str = entry.created_at.strftime("%d.%m.%Y, %H:%M")
            
            # Get emotion name and option
            emotion_name = EMOTION_MAPPING.get(entry.state, entry.state) if entry.state else "эмоция"
            
            # Try to get specific option description
            option_text = ""
            if entry.state and entry.option and entry.option.startswith('option_'):
                try:
                    option_num = int(entry.option.split('_')[1])
                    option_description = OPTION_MAPPING.get(entry.state, {}).get(option_num, "")
                    if option_description:
                        option_text = f" ({option_description})"
                except (ValueError, IndexError):
                    pass
            
            # Create formatted entry
            entry_text = f"{date_str}, {emotion_name}{option_text}"
            story.append(Paragraph(f"• {entry_text}", normal_style))
        
        story.append(Spacer(1, 20))
    
    # Show message if no entries at all
    if not entries_with_context and not simple_diary_entries:
        story.append(Paragraph("Записи эмоций не найдены.", normal_style))
        story.append(Spacer(1, 20))
    
    # Positive moments - including weekly reflections
    session = get_session()
    try:
        user = None
        weekly_reflections = []
        # Get user_id from emotion_entries if available
        if emotion_entries:
            user = session.query(User).filter(User.id == emotion_entries[0].user_id).first()
        
        if user:
            start_datetime = datetime.strptime(start_date, "%d.%m.%Y")
            end_datetime = datetime.strptime(end_date, "%d.%m.%Y")
            weekly_reflections = session.query(WeeklyReflection).filter(
                WeeklyReflection.user_id == user.id,
                WeeklyReflection.created_at >= start_datetime,
                WeeklyReflection.created_at <= end_datetime
            ).order_by(WeeklyReflection.created_at.desc()).all()
    finally:
        close_session(session)
    
    if positive_entries or weekly_reflections:
        story.append(Paragraph("Позитивные моменты", heading_style))
        
        # Add positive emotion entries
        for entry in positive_entries[-5:]:  # Last 5 positive entries
            time_str = entry.created_at.strftime("%d.%m %H:%M")
            emotion_name = EMOTION_MAPPING.get(entry.state, entry.state) if entry.state else "позитивная эмоция"
            story.append(Paragraph(f"• {time_str}: {emotion_name}", normal_style))
        
        # Add weekly reflection moments
        for reflection in weekly_reflections:
            reflection_date = reflection.created_at.strftime("%d.%m")
            story.append(Paragraph(f"Еженедельная рефлексия ({reflection_date}):", normal_style))
            
            if reflection.smile_moment:
                story.append(Paragraph(f"  • Момент улыбки: {reflection.smile_moment}", normal_style))
            
            if reflection.kindness:
                story.append(Paragraph(f"  • Доброта: {reflection.kindness}", normal_style))
            
            if reflection.peace_moment:
                story.append(Paragraph(f"  • Спокойствие: {reflection.peace_moment}", normal_style))
            
            if reflection.new_discovery:
                story.append(Paragraph(f"  • Открытие: {reflection.new_discovery}", normal_style))
            
            if reflection.gratitude:
                story.append(Paragraph(f"  • Благодарность: {reflection.gratitude}", normal_style))
        
        story.append(Spacer(1, 20))
    
    # Negative emotions analysis
    if negative_entries:
        negative_states = [e.state for e in negative_entries if e.state]
        if negative_states:
            negative_counter = Counter(negative_states)
            story.append(Paragraph("Деструктивные эмоции для проработки", heading_style))
            for i, (state, count) in enumerate(negative_counter.most_common(3), 1):
                emotion_name = EMOTION_MAPPING.get(state, state)
                story.append(Paragraph(f"{i}. {emotion_name} ({count} раз)", normal_style))
            story.append(Paragraph("Рекомендуется разобрать эти эмоции с психологом.", normal_style))
            story.append(Spacer(1, 20))
    
    # Therapy topics
    story.append(Paragraph("Темы для проработки с психологом", heading_style))
    for topic in therapy_topics:
        story.append(Paragraph(f"• {topic}", normal_style))
    story.append(Spacer(1, 20))
    
    # Praise section
    story.append(Paragraph("Похвала", heading_style))
    praise_text = f"Отлично! Ты ведешь дневник эмоций уже {period_days} дней. " \
                  "Это важный шаг к лучшему пониманию себя и своих эмоций. Продолжай в том же духе!"
    story.append(Paragraph(praise_text, normal_style))
    
    # Build PDF
    doc.build(story)
    return pdf_path

async def generate_therapy_topics_text(contexts: List[str]) -> List[str]:
    """Generate therapy topics based on emotion contexts using AI"""
    
    if not contexts:
        return [
            "Работа с эмоциональной регуляцией",
            "Развитие навыков самоанализа", 
            "Управление стрессом"
        ]
    
    # Clean and extract meaningful content from contexts
    cleaned_contexts = []
    for context in contexts:
        if not context or not context.strip():
            continue
            
        cleaned_context = context.strip()
        
        # Remove therapy work markers
        if cleaned_context.startswith("Marked for therapy work:"):
            cleaned_context = cleaned_context.replace("Marked for therapy work:", "").strip()
        elif cleaned_context.startswith("Отмечено для проработки с терапевтом"):
            if ":" in cleaned_context:
                cleaned_context = cleaned_context.split(":", 1)[1].strip()
        
        # Extract main content from formatted conversations
        if cleaned_context.startswith("Сообщение 1:"):
            messages = []
            for line in cleaned_context.split("\n"):
                if line.startswith("Сообщение ") and ":" in line:
                    msg_content = line.split(":", 1)[1].strip()
                    if msg_content:
                        messages.append(msg_content)
            
            if messages:
                cleaned_context = " ".join(messages)
        
        if cleaned_context and len(cleaned_context) > 10:  # Skip very short contexts
            cleaned_contexts.append(cleaned_context)
    
    context_text = " ".join(cleaned_contexts) if cleaned_contexts else " ".join(contexts)
    prompt = f"""
    На основе следующих контекстов эмоциональных переживаний пользователя:
    {context_text}
    
    Предложи 3-5 конкретных тем для работы с психологом. 
    Темы должны быть практичными и направленными на решение проблем.
    Отвечай списком, каждая тема с новой строки, без нумерации. Не используй markdown.
    """
    
    try:
        response = await asyncio.to_thread(
            client.models.generate_content,
            model="gemini-2.0-flash",
            contents=[prompt]
        )
        topics_text = response.text if hasattr(response, 'text') else str(response)
        topics = [topic.strip() for topic in topics_text.split('\n') if topic.strip()]
        return topics[:5] if topics else [
            "Работа с эмоциональной регуляцией",
            "Развитие навыков самоанализа", 
            "Управление стрессом"
        ]
    except Exception as e:
        logger.error(f"Error generating therapy topics: {e}")
        return [
            "Работа с эмоциональной регуляцией",
            "Развитие навыков самоанализа", 
            "Управление стрессом"
        ]

async def generate_text_report(callback: types.CallbackQuery, start_date: str, end_date: str,
                             period_days: int, emotion_entries: List[EmotionEntry],
                             positive_entries: List[EmotionEntry], negative_entries: List[EmotionEntry],
                             emotion_counter: Counter, therapy_topics: List[str]):
    """Generate text report as fallback"""
    
    report_text = f"📊 Отчет по эмоциям за период {start_date} - {end_date}\n\n"
    
    report_text += f"📈 Статистика:\n"
    report_text += f"• Всего записей: {len(emotion_entries)}\n"
    report_text += f"• Позитивных эмоций: {len(positive_entries)}\n"
    report_text += f"• Негативных эмоций: {len(negative_entries)}\n\n"
    
    if emotion_counter:
        report_text += "🎯 Топ-3 самые частые эмоции:\n"
        for i, (state, count) in enumerate(emotion_counter.most_common(3), 1):
            emotion_name = EMOTION_MAPPING.get(state, state)
            report_text += f"{i}. {emotion_name} ({count} раз)\n"
        report_text += "\n"
    
    # Key moments analysis section
    report_text += "📝 Краткий разбор ключевых моментов:\n"
    
    # Sort all entries chronologically
    all_entries = sorted(emotion_entries, key=lambda x: x.created_at)
    
    # Separate entries into those with detailed context and simple diary entries
    entries_with_context = []
    simple_diary_entries = []
    
    for entry in all_entries:
        if entry.answer_text and entry.answer_text.strip():
            if entry.answer_text == "Emotion recorded from diary":
                # This is a simple emotion diary entry without detailed context
                simple_diary_entries.append(entry)
            elif entry.answer_text.startswith("Marked for therapy work:") or entry.answer_text.startswith("Отмечено для проработки с терапевтом"):
                # This is marked for therapy work but might have context
                entries_with_context.append(entry)
            elif entry.answer_text.startswith("AI рекомендация помогла"):
                therapy_marker = " [AI помог]"
                if ":" in entry.answer_text:
                    context = entry.answer_text.split(":", 1)[1].strip()
                entries_with_context.append(entry)
            elif entry.answer_text not in ["Marked for therapy work:"]:
                # This has actual user context/dialog
                entries_with_context.append(entry)
    
    # Show entries with detailed context first
    if entries_with_context:
        report_text += "**Подробные записи с контекстом:**\n"
        for entry in entries_with_context:
            # Format date and time
            date_str = entry.created_at.strftime("%d.%m.%Y, %H:%M")
            
            # Get emotion name
            emotion_name = EMOTION_MAPPING.get(entry.state, entry.state) if entry.state else "эмоция"
            
            # Get context/reason
            context = entry.answer_text.strip()
            
            # Handle special cases for marked therapy work
            therapy_marker = ""
            if context.startswith("Marked for therapy work:"):
                therapy_marker = " [для терапии]"
                context = context.replace("Marked for therapy work:", "").strip()
                if context.startswith("Marked for work (text not found in FSM)"):
                    continue  # Skip entries without proper context
            elif context.startswith("Отмечено для проработки с терапевтом"):
                therapy_marker = " [для терапии]"
                if ":" in context:
                    context = context.split(":", 1)[1].strip()
            elif context.startswith("AI рекомендация помогла"):
                therapy_marker = " [AI помог]"
                if ":" in context:
                    context = context.split(":", 1)[1].strip()
            
            # Extract meaningful conversation from formatted text
            if context.startswith("Сообщение 1:"):
                # This is a formatted conversation, extract the main content
                messages = []
                for line in context.split("\n"):
                    if line.startswith("Сообщение ") and ":" in line:
                        msg_content = line.split(":", 1)[1].strip()
                        if msg_content:
                            messages.append(msg_content)
                
                if messages:
                    # Show the first message as the main context, mention if there are more
                    context = messages[0]
                    if len(messages) > 1:
                        context += f" [и ещё {len(messages)-1} сообщ.]"
            
            # Limit context length for readability
            if len(context) > 150:
                context = context[:150] + "..."
            
            # Create formatted entry
            report_text += f"• {date_str}, {emotion_name}: {context}{therapy_marker}\n"
        
        report_text += "\n"
    
    # Show simple diary entries
    if simple_diary_entries:
        report_text += "**Быстрые записи эмоций:**\n"
        for entry in simple_diary_entries:
            # Format date and time
            date_str = entry.created_at.strftime("%d.%m.%Y, %H:%M")
            
            # Get emotion name and option
            emotion_name = EMOTION_MAPPING.get(entry.state, entry.state) if entry.state else "эмоция"
            
            # Try to get specific option description
            option_text = ""
            if entry.state and entry.option and entry.option.startswith('option_'):
                try:
                    option_num = int(entry.option.split('_')[1])
                    option_description = OPTION_MAPPING.get(entry.state, {}).get(option_num, "")
                    if option_description:
                        option_text = f" ({option_description})"
                except (ValueError, IndexError):
                    pass
            
            # Create formatted entry
            report_text += f"• {date_str}, {emotion_name}{option_text}\n"
        
        report_text += "\n"
    
    # Show message if no entries at all
    if not entries_with_context and not simple_diary_entries:
        report_text += "Записи эмоций не найдены.\n\n"
    
    # Positive moments - including weekly reflections
    session = get_session()
    try:
        user = session.query(User).filter(User.telegram_id == callback.from_user.id).first()
        weekly_reflections = []
        if user:
            start_datetime = datetime.strptime(start_date, "%d.%m.%Y")
            end_datetime = datetime.strptime(end_date, "%d.%m.%Y")
            weekly_reflections = session.query(WeeklyReflection).filter(
                WeeklyReflection.user_id == user.id,
                WeeklyReflection.created_at >= start_datetime,
                WeeklyReflection.created_at <= end_datetime
            ).order_by(WeeklyReflection.created_at.desc()).all()
    finally:
        close_session(session)
    
    if positive_entries or weekly_reflections:
        report_text += "😊 Позитивные моменты:\n"
        
        # Add positive emotion entries
        for entry in positive_entries[-5:]:  # Last 5 positive entries
            time_str = entry.created_at.strftime("%d.%m %H:%M")
            emotion_name = EMOTION_MAPPING.get(entry.state, entry.state) if entry.state else "позитивная эмоция"
            report_text += f"• {time_str}: {emotion_name}\n"
        
        # Add weekly reflection moments
        for reflection in weekly_reflections:
            reflection_date = reflection.created_at.strftime("%d.%m")
            report_text += f"\nЕженедельная рефлексия ({reflection_date}):\n"
            
            if reflection.smile_moment:
                report_text += f"• Момент улыбки: {reflection.smile_moment[:100]}{'...' if len(reflection.smile_moment) > 100 else ''}\n"
            
            if reflection.kindness:
                report_text += f"• Доброта: {reflection.kindness[:100]}{'...' if len(reflection.kindness) > 100 else ''}\n"
            
            if reflection.peace_moment:
                report_text += f"• Спокойствие: {reflection.peace_moment[:100]}{'...' if len(reflection.peace_moment) > 100 else ''}\n"
            
            if reflection.new_discovery:
                report_text += f"• Открытие: {reflection.new_discovery[:100]}{'...' if len(reflection.new_discovery) > 100 else ''}\n"
            
            if reflection.gratitude:
                report_text += f"• Благодарность: {reflection.gratitude[:100]}{'...' if len(reflection.gratitude) > 100 else ''}\n"
        
        report_text += "\n"
    
    # Negative patterns analysis
    if negative_entries:
        negative_states = [e.state for e in negative_entries if e.state]
        if negative_states:
            negative_counter = Counter(negative_states)
            report_text += "⚠️ Топ-3 деструктивные эмоции для проработки:\n"
            for i, (state, count) in enumerate(negative_counter.most_common(3), 1):
                emotion_name = EMOTION_MAPPING.get(state, state)
                report_text += f"{i}. {emotion_name} ({count} раз)\n"
            report_text += "\nРекомендуется разобрать эти эмоции с психологом.\n\n"
    
    # Topics for therapy
    report_text += "🎯 Темы для проработки с психологом:\n"
    for topic in therapy_topics:
        report_text += f"• {topic}\n"
    report_text += "\n"
    
    # Praise
    report_text += "🌟 Похвала:\n"
    report_text += f"Отлично! Ты ведешь дневник эмоций уже {period_days} дней. "
    report_text += "Это важный шаг к лучшему пониманию себя и своих эмоций. Продолжай в том же духе!"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="В главное меню", callback_data="back_to_main")]
    ])
    await callback.message.edit_text(report_text, reply_markup=keyboard, parse_mode="Markdown")

async def create_emotion_charts(emotion_entries: List[EmotionEntry], start_date: str, end_date: str) -> str:
    """Create emotion visualization charts and return the image path"""
    try:
        # Set up Russian font for matplotlib
        plt.rcParams['font.family'] = ['DejaVu Sans', 'Arial Unicode MS', 'Liberation Sans', 'sans-serif']
        plt.rcParams['axes.unicode_minus'] = False
        
        # Prepare data
        positive_emotions = {}
        negative_emotions = {}
        
        # Count emotions by type
        for entry in emotion_entries:
            if not entry.state:
                continue
                
            emotion_name = EMOTION_MAPPING.get(entry.state, entry.state)
            
            if entry.emotion_type == "positive":
                positive_emotions[emotion_name] = positive_emotions.get(emotion_name, 0) + 1
            elif entry.emotion_type == "negative":
                negative_emotions[emotion_name] = negative_emotions.get(emotion_name, 0) + 1
        
        # Prepare unified dictionary with all emotions
        all_emotions_counts = {}
        for key, val in positive_emotions.items():
            all_emotions_counts[key] = val
        for key, val in negative_emotions.items():
            all_emotions_counts[key] = val

        # Ensure every emotion has a key even if 0 so chart is always shown
        for state in EMOTION_MAPPING.values():
            all_emotions_counts.setdefault(state, 0)

        # Sort emotions in defined order (positive first then negative) according to mapping keys
        emotion_order = [EMOTION_MAPPING[k] for k in EMOTION_MAPPING]

        # Build one combined bar chart with all 10 эмоций
        fig, ax = plt.subplots(figsize=(14, 7))
        fig.suptitle(f'Частота выбора эмоций\nПериод: {start_date} - {end_date}', fontsize=16, fontweight='bold')

        # Data for plotting
        counts = [all_emotions_counts[e] for e in emotion_order]
        x = np.arange(len(emotion_order))

        # Color bars by emotion valence
        bar_colors = []
        for emotion_name in emotion_order:
            orig_key = next(k for k, v in EMOTION_MAPPING.items() if v == emotion_name)
            bar_colors.append('#4CAF50' if orig_key.startswith('good') else '#FF9800')

        bars = ax.bar(x, counts, color=bar_colors, alpha=0.8)

        # Add value labels on top
        for rect, count in zip(bars, counts):
            height = rect.get_height()
            ax.annotate(f'{count}',
                        xy=(rect.get_x() + rect.get_width() / 2, height),
                        xytext=(0, 3),
                        textcoords="offset points",
                        ha='center', va='bottom', fontsize=9)

        # Axis formatting
        ax.set_xticks(x)
        ax.set_xticklabels(emotion_order, rotation=45, ha='right', fontsize=9)
        ax.set_ylabel('Количество')
        ax.set_ylim(0, max(counts) + 1)
        plt.tight_layout(rect=[0, 0, 1, 0.95])
        
        # Save to temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as tmp_file:
            chart_path = tmp_file.name
        
        plt.savefig(chart_path, dpi=300, bbox_inches='tight', facecolor='white')
        plt.close()
        
        return chart_path
        
    except Exception as e:
        logger.error(f"Error creating emotion charts: {e}")
        return None

 