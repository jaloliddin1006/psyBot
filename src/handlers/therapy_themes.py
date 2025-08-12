import logging
from aiogram import types, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, FSInputFile
from aiogram.filters import StateFilter
from src.database.session import get_session, close_session
from src.database.models import User, TherapyTheme
from .utils import delete_previous_messages
from constants import *
from datetime import datetime, timedelta
import os
import tempfile
import asyncio
from google import genai
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from collections import defaultdict
from .emotion_analysis import setup_russian_fonts
from trial_manager import require_trial_access

# Initialize logger and router
logger = logging.getLogger(__name__)
router = Router(name=__name__)

# Initialize GenAI client
client = genai.Client(
    api_key=os.environ.get("GOOGLE_GENAI_API_KEY"),
    http_options={"base_url": os.environ.get("API_URL")}
)

async def start_therapy_themes(message: types.Message, state: FSMContext):
    """Start therapy themes management flow"""
    logger.info(f"start_therapy_themes called for user {message.from_user.id}")
    
    # Check user registration
    session = get_session()
    db_user = session.query(User).filter(User.telegram_id == message.from_user.id).first()
    
    if not db_user or not getattr(db_user, 'registration_complete', False) or not db_user.full_name:
        close_session(session)
        await message.answer("Пожалуйста, завершите регистрацию с помощью /start")
        return
    
    close_session(session)
    
    # Clean up previous messages
    data = await state.get_data()
    messages_to_delete = data.get('messages_to_delete', [])
    messages_to_delete.append(message.message_id)
    await state.update_data(messages_to_delete=messages_to_delete)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Посмотреть темы", callback_data="view_themes")],
        [InlineKeyboardButton(text="Добавить тему", callback_data="add_theme")],
        [InlineKeyboardButton(text="В главное меню", callback_data="back_to_main")]
    ])
    
    sent = await message.answer(
        "Что бы ты хотела сделать со списком тем для проработки с психотерапевтом?",
        reply_markup=keyboard
    )
    
    messages_to_delete.append(sent.message_id)
    await state.update_data(messages_to_delete=messages_to_delete)
    await state.set_state(THERAPY_THEMES_MENU)

@router.callback_query(StateFilter(THERAPY_THEMES_MENU), F.data.in_(["view_themes", "add_theme", "back_to_main"]))
@require_trial_access('therapy_themes')
async def handle_themes_menu(callback: types.CallbackQuery, state: FSMContext):
    """Handle therapy themes menu selection"""
    await callback.answer()
    logger.info(f"handle_themes_menu called with data: {callback.data}")
    
    if callback.data == "back_to_main":
        from .main_menu import main_menu
        await delete_previous_messages(callback.message, state)
        await state.clear()
        await main_menu(callback, state)
        return
    
    elif callback.data == "view_themes":
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="3 дня", callback_data="period_3")],
            [InlineKeyboardButton(text="Неделя (7 дней)", callback_data="period_7")],
            [InlineKeyboardButton(text="Две недели (14 дней)", callback_data="period_14")],
            [InlineKeyboardButton(text="Месяц (30 дней)", callback_data="period_30")],
            [InlineKeyboardButton(text="3 месяца (90 дней)", callback_data="period_90")],
            [InlineKeyboardButton(text="Назад", callback_data="back_to_themes_menu")]
        ])
        
        await callback.message.edit_text(
            "За какой период показать темы для проработки?",
            reply_markup=keyboard
        )
        await state.set_state(THERAPY_THEMES_PERIOD_SELECTION)
    
    elif callback.data == "add_theme":
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Назад", callback_data="back_to_themes_menu")]
        ])
        
        await callback.message.edit_text(
            "Напиши тему, которую хочешь проработать с психотерапевтом:",
            reply_markup=keyboard
        )
        await state.set_state(THERAPY_THEMES_ADD_INPUT)

@router.callback_query(StateFilter(THERAPY_THEMES_PERIOD_SELECTION), F.data.startswith("period_"))
@require_trial_access('therapy_themes')
async def handle_period_selection(callback: types.CallbackQuery, state: FSMContext):
    """Handle period selection for viewing themes"""
    await callback.answer()
    period_days = int(callback.data.split("_")[1])
    
    logger.info(f"handle_period_selection called with period: {period_days} days")
    
    session = get_session()
    db_user = session.query(User).filter(User.telegram_id == callback.from_user.id).first()
    
    if not db_user:
        close_session(session)
        await callback.message.edit_text("Ошибка: пользователь не найден")
        return
    
    # Get themes for the selected period
    cutoff_date = datetime.now() - timedelta(days=period_days)
    themes = session.query(TherapyTheme).filter(
        TherapyTheme.user_id == db_user.id,
        TherapyTheme.created_at >= cutoff_date
    ).order_by(TherapyTheme.created_at.desc()).all()
    
    close_session(session)
    
    if not themes:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Добавить тему", callback_data="add_theme")],
            [InlineKeyboardButton(text="Назад", callback_data="back_to_themes_menu")]
        ])
        
        await callback.message.edit_text(
            f"За последние {period_days} дней нет тем для проработки.",
            reply_markup=keyboard
        )
        return
    
    # Format themes for display
    if period_days <= 7:
        # Short format for 3 days or week
        await generate_short_themes_report(callback, state, themes, period_days)
    else:
        # PDF format for longer periods
        await generate_themes_pdf(callback, state, themes, period_days, db_user)

async def generate_short_themes_report(callback: types.CallbackQuery, state: FSMContext, 
                                     themes: list, period_days: int):
    """Generate short text report for themes"""
    report_lines = [f"Отчет за последние {period_days} дней:\n"]
    
    for theme in themes:
        date_str = theme.created_at.strftime("%d.%m.%Y, %H:%M")
        theme_text = theme.shortened_text if theme.is_shortened and theme.shortened_text else theme.original_text
        report_lines.append(f"• {date_str}: {theme_text}")
    
    report_text = "\n".join(report_lines)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Отметить проработанную", callback_data="mark_processed")],
        [InlineKeyboardButton(text="Удалить тему", callback_data="delete_theme")],
        [InlineKeyboardButton(text="Назад", callback_data="back_to_themes_menu")]
    ])
    
    await callback.message.edit_text(report_text, reply_markup=keyboard)
    await state.set_state(THERAPY_THEMES_VIEWING)

async def generate_themes_pdf(callback: types.CallbackQuery, state: FSMContext, 
                            themes: list, period_days: int, user):
    """Generate PDF report for themes"""
    await callback.message.edit_text("📄 Генерирую PDF-отчет... Это может занять несколько секунд.")
    
    try:
        # Create PDF file
        start_date = (datetime.now() - timedelta(days=period_days)).strftime("%d.%m.%Y")
        end_date = datetime.now().strftime("%d.%m.%Y")
        
        pdf_path = await create_therapy_themes_pdf(
            start_date, end_date, period_days, themes, user
        )
        
        # Send PDF file
        pdf_file = FSInputFile(pdf_path, filename=f"therapy_themes_{start_date}_{end_date}.pdf")
        await callback.message.answer_document(
            pdf_file,
            caption=f"📋 Темы для проработки за период {start_date} - {end_date}"
        )
        
        # Send navigation buttons
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Отметить проработанную", callback_data="mark_processed")],
            [InlineKeyboardButton(text="Удалить тему", callback_data="delete_theme")],
            [InlineKeyboardButton(text="Назад", callback_data="back_to_themes_menu")]
        ])
        await callback.message.answer("Отчет готов! 📄", reply_markup=keyboard)
        await state.set_state(THERAPY_THEMES_VIEWING)
        
        # Clean up temporary file
        os.unlink(pdf_path)
        
    except Exception as e:
        logger.error(f"Error generating PDF: {e}")
        # Fallback to text report
        await generate_themes_text_fallback(callback, state, themes, period_days)

@router.callback_query(StateFilter(THERAPY_THEMES_VIEWING), F.data.in_(["mark_processed", "delete_theme", "back_to_themes_menu"]))
@require_trial_access('therapy_themes')
async def handle_themes_viewing_actions(callback: types.CallbackQuery, state: FSMContext):
    """Handle actions from themes viewing"""
    await callback.answer()
    
    if callback.data == "back_to_themes_menu":
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Посмотреть темы", callback_data="view_themes")],
            [InlineKeyboardButton(text="Добавить тему", callback_data="add_theme")],
            [InlineKeyboardButton(text="В главное меню", callback_data="back_to_main")]
        ])
        
        await callback.message.edit_text(
            "Что бы ты хотела сделать со списком тем для проработки с психотерапевтом?",
            reply_markup=keyboard
        )
        await state.set_state(THERAPY_THEMES_MENU)
        return
    
    elif callback.data in ["mark_processed", "delete_theme"]:
        action_text = "отметить (удалить)" if callback.data == "mark_processed" else "удалить"
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Назад", callback_data="back_to_viewing")]
        ])
        
        await callback.message.edit_text(
            f"Укажи дату и время темы которую ты хочешь {action_text} в формате ДД.ММ.ГГГГ, ЧЧ:ММ",
            reply_markup=keyboard
        )
        
        await state.update_data(delete_action=callback.data)
        await state.set_state(THERAPY_THEMES_DELETE_INPUT)

@router.message(StateFilter(THERAPY_THEMES_DELETE_INPUT))
async def handle_delete_time_input(message: types.Message, state: FSMContext):
    """Handle time input for deleting/marking themes"""
    logger.info(f"handle_delete_time_input called with text: {message.text}")
    
    try:
        # Parse date and time
        date_time_str = message.text.strip()
        parsed_datetime = datetime.strptime(date_time_str, "%d.%m.%Y, %H:%M")
        
        # Find theme by datetime
        session = get_session()
        db_user = session.query(User).filter(User.telegram_id == message.from_user.id).first()
        
        # Look for theme within 5 minutes of specified time
        start_time = parsed_datetime - timedelta(minutes=5)
        end_time = parsed_datetime + timedelta(minutes=5)
        
        theme = session.query(TherapyTheme).filter(
            TherapyTheme.user_id == db_user.id,
            TherapyTheme.created_at >= start_time,
            TherapyTheme.created_at <= end_time
        ).first()
        
        if not theme:
            close_session(session)
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="Назад", callback_data="back_to_viewing")]
            ])
            
            await message.answer(
                "Кажется, время введено неверно. Напиши исправленный вариант, пожалуйста",
                reply_markup=keyboard
            )
            return
        
        # Show confirmation
        theme_text = theme.shortened_text if theme.is_shortened and theme.shortened_text else theme.original_text
        date_str = theme.created_at.strftime("%d.%m.%Y, %H:%M")
        
        data = await state.get_data()
        action = data.get('delete_action', 'delete_theme')
        action_text = "пометить (удалить)" if action == "mark_processed" else "удалить"
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Да", callback_data=f"confirm_delete_{theme.id}")],
            [InlineKeyboardButton(text="Нет", callback_data="back_to_viewing")]
        ])
        
        await message.answer(
            f"Ты хочешь {action_text} {date_str}: {theme_text[:100]}{'...' if len(theme_text) > 100 else ''}?",
            reply_markup=keyboard
        )
        
        await state.set_state(THERAPY_THEMES_DELETE_CONFIRMATION)
        close_session(session)
        
    except ValueError:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Назад", callback_data="back_to_viewing")]
        ])
        
        await message.answer(
            "Кажется, время введено неверно. Напиши исправленный вариант, пожалуйста",
            reply_markup=keyboard
        )

@router.callback_query(StateFilter(THERAPY_THEMES_DELETE_CONFIRMATION), F.data.startswith("confirm_delete_"))
@require_trial_access('therapy_themes')
async def handle_delete_confirmation(callback: types.CallbackQuery, state: FSMContext):
    """Handle delete confirmation"""
    await callback.answer()
    
    theme_id = int(callback.data.split("_")[2])
    
    session = get_session()
    theme = session.query(TherapyTheme).filter(TherapyTheme.id == theme_id).first()
    
    if theme:
        session.delete(theme)
        session.commit()
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Назад к темам", callback_data="back_to_themes_menu")]
        ])
        
        await callback.message.edit_text(
            "Тема была проработана и удалена из списка.",
            reply_markup=keyboard
        )
    else:
        await callback.message.edit_text("Ошибка: тема не найдена")
    
    close_session(session)
    await state.set_state(THERAPY_THEMES_MENU)

@router.message(StateFilter(THERAPY_THEMES_ADD_INPUT))
async def handle_add_theme_input(message: types.Message, state: FSMContext):
    """Handle new theme input"""
    logger.info(f"handle_add_theme_input called with text length: {len(message.text)}")
    
    theme_text = message.text.strip()
    
    if len(theme_text) < 5:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Назад", callback_data="back_to_themes_menu")]
        ])
        
        await message.answer(
            "Пожалуйста, напиши более подробную тему для проработки:",
            reply_markup=keyboard
        )
        return
    
    await state.update_data(theme_original_text=theme_text)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Сохранить оригинал", callback_data="save_original")],
        [InlineKeyboardButton(text="Сократить", callback_data="shorten_theme")]
    ])
    
    await message.answer(
        "Что делаем с темой?",
        reply_markup=keyboard
    )
    
    await state.set_state(THERAPY_THEMES_ADD_EDIT)

@router.callback_query(StateFilter(THERAPY_THEMES_ADD_EDIT), F.data.in_(["save_original", "shorten_theme"]))
@require_trial_access('therapy_themes')
async def handle_theme_edit_choice(callback: types.CallbackQuery, state: FSMContext):
    """Handle theme editing choice"""
    await callback.answer()
    
    data = await state.get_data()
    original_text = data.get('theme_original_text', '')
    
    if callback.data == "save_original":
        # Save original theme
        await save_therapy_theme(callback.from_user.id, original_text, None, False)
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Добавить еще", callback_data="add_theme")],
            [InlineKeyboardButton(text="В главное меню", callback_data="back_to_main")]
        ])
        
        await callback.message.edit_text(
            "Тема сохранена в оригинальном виде.",
            reply_markup=keyboard
        )
        await state.set_state(THERAPY_THEMES_MENU)
        
    elif callback.data == "shorten_theme":
        # Generate shortened version
        try:
            shortened_text = await generate_shortened_theme(original_text)
            await state.update_data(theme_shortened_text=shortened_text)
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="Сохранить", callback_data="save_shortened")],
                [InlineKeyboardButton(text="Сохранить оригинал", callback_data="save_original")]
            ])
            
            await callback.message.edit_text(
                f"Сокращенная версия:\n\n{shortened_text}\n\nСохранить эту версию?",
                reply_markup=keyboard
            )
            
        except Exception as e:
            logger.error(f"Error shortening theme: {e}")
            await callback.message.edit_text("Ошибка при сокращении темы. Сохраняю оригинал.")
            await save_therapy_theme(callback.from_user.id, original_text, None, False)

@router.callback_query(StateFilter(THERAPY_THEMES_ADD_EDIT), F.data == "save_shortened")
@require_trial_access('therapy_themes')
async def handle_save_shortened(callback: types.CallbackQuery, state: FSMContext):
    """Handle saving shortened theme"""
    await callback.answer()
    
    data = await state.get_data()
    original_text = data.get('theme_original_text', '')
    shortened_text = data.get('theme_shortened_text', '')
    
    await save_therapy_theme(callback.from_user.id, original_text, shortened_text, True)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Добавить еще", callback_data="add_theme")],
        [InlineKeyboardButton(text="В главное меню", callback_data="back_to_main")]
    ])
    
    await callback.message.edit_text(
        "Сокращенная тема сохранена.",
        reply_markup=keyboard
    )
    await state.set_state(THERAPY_THEMES_MENU)

async def save_therapy_theme(telegram_id: int, original_text: str, shortened_text: str = None, is_shortened: bool = False):
    """Save therapy theme to database"""
    session = get_session()
    
    db_user = session.query(User).filter(User.telegram_id == telegram_id).first()
    if not db_user:
        close_session(session)
        return
    
    theme = TherapyTheme(
        user_id=db_user.id,
        original_text=original_text,
        shortened_text=shortened_text,
        is_shortened=is_shortened
    )
    
    session.add(theme)
    session.commit()
    close_session(session)
    
    logger.info(f"Saved therapy theme for user {telegram_id}")

async def generate_shortened_theme(text: str) -> str:
    """Generate shortened version of theme using AI"""
    try:
        prompt = f"""Сократи следующий текст до 1-2 предложений, сохранив основную суть для работы с психотерапевтом:

{text}

Ответь только сокращенным текстом без дополнительных комментариев."""
        
        response = client.models.generate_content(
            model="gemini-1.5-flash",
            contents=prompt,
            config=genai.GenerateContentConfig(
                temperature=0.3,
                max_output_tokens=150
            )
        )
        
        return response.text.strip()
        
    except Exception as e:
        logger.error(f"Error generating shortened theme: {e}")
        return text

# Handle navigation callbacks
@router.callback_query(F.data == "back_to_themes_menu")
@require_trial_access('therapy_themes')
async def back_to_themes_menu(callback: types.CallbackQuery, state: FSMContext):
    """Handle back to themes menu"""
    await callback.answer()
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Посмотреть темы", callback_data="view_themes")],
        [InlineKeyboardButton(text="Добавить тему", callback_data="add_theme")],
        [InlineKeyboardButton(text="В главное меню", callback_data="back_to_main")]
    ])
    
    await callback.message.edit_text(
        "Что бы ты хотела сделать со списком тем для проработки с психотерапевтом?",
        reply_markup=keyboard
    )
    await state.set_state(THERAPY_THEMES_MENU)

@router.callback_query(F.data == "back_to_viewing")
@require_trial_access('therapy_themes')
async def back_to_viewing(callback: types.CallbackQuery, state: FSMContext):
    """Handle back to viewing themes"""
    await callback.answer()
    # This should regenerate the viewing interface
    # For now, redirect to themes menu
    await back_to_themes_menu(callback, state)

@router.callback_query(F.data == "back_to_main")
@require_trial_access('therapy_themes')
async def back_to_main_from_themes(callback: types.CallbackQuery, state: FSMContext):
    """Handle back to main menu from themes"""
    await callback.answer()
    from .main_menu import main_menu
    await delete_previous_messages(callback.message, state)
    await state.clear()
    await main_menu(callback, state)

async def create_therapy_themes_pdf(start_date: str, end_date: str, period_days: int,
                                  themes: list, user) -> str:
    """Create PDF report for therapy themes and return file path"""
    
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
        
        week_style = ParagraphStyle(
            'WeekStyle',
            parent=styles['Heading3'],
            fontSize=12,
            fontName='RussianFont-Bold',
            spaceAfter=8,
            spaceBefore=16
        )
    else:
        # Fallback to default styles if fonts are not available
        title_style = styles['Heading1']
        heading_style = styles['Heading2']
        normal_style = styles['Normal']
        week_style = styles['Heading3']
    
    # Title
    story.append(Paragraph("Темы для проработки с психотерапевтом", title_style))
    story.append(Paragraph(f"Период: {start_date} - {end_date}", normal_style))
    story.append(Spacer(1, 20))
    
    # 1. General summary (2-3 sentences)
    story.append(Paragraph("1. Общее краткое содержание", heading_style))
    
    total_themes = len(themes)
    summary = f"За период с {start_date} по {end_date} было добавлено {total_themes} тем для проработки с психотерапевтом. "
    
    if total_themes > 5:
        # Generate AI summary of common themes
        theme_texts = [theme.original_text for theme in themes]
        ai_summary = await generate_themes_summary(theme_texts)
        summary += ai_summary
    else:
        summary += "Основные направления работы включают личностное развитие и эмоциональную регуляцию. не используй markdown."
    
    story.append(Paragraph(summary, normal_style))
    story.append(Spacer(1, 20))
    
    # 2. Weekly breakdown
    story.append(Paragraph("2. По неделям", heading_style))
    
    # Group themes by week
    themes_by_week = defaultdict(list)
    
    for theme in themes:
        # Calculate week number from today (0 = current week, 1 = last week, etc.)
        days_ago = (datetime.now() - theme.created_at).days
        week_num = days_ago // 7
        themes_by_week[week_num].append(theme)
    
    # Process each week
    for week_num in sorted(themes_by_week.keys()):
        week_themes = sorted(themes_by_week[week_num], key=lambda x: x.created_at, reverse=True)
        
        # Week title
        if week_num == 0:
            week_title = "Текущая неделя"
        elif week_num == 1:
            week_title = "Прошлая неделя"
        else:
            week_title = f"{week_num} недель назад"
        
        story.append(Paragraph(week_title, week_style))
        
        # Generate weekly theme using AI
        week_theme_texts = [theme.original_text for theme in week_themes]
        weekly_common_theme = await generate_weekly_theme(week_theme_texts)
        story.append(Paragraph(f"Общая тема: {weekly_common_theme}", normal_style))
        story.append(Spacer(1, 8))
        
        # 3. Individual entries with date, time: brief content
        for theme in week_themes:
            date_str = theme.created_at.strftime("%d.%m.%Y, %H:%M")
            theme_text = theme.shortened_text if theme.is_shortened and theme.shortened_text else theme.original_text
            
            # Truncate very long themes for PDF readability
            if len(theme_text) > 120:
                theme_text = theme_text[:117] + "..."
            
            story.append(Paragraph(f"{date_str}: {theme_text}", normal_style))
        
        story.append(Spacer(1, 12))
    
    # Additional recommendations section
    story.append(Paragraph("Рекомендации", heading_style))
    recommendations = "Рекомендуется обсудить выделенные темы с психотерапевтом в порядке их актуальности. " \
                     "Особое внимание стоит уделить повторяющимся паттернам и эмоциональным реакциям."
    story.append(Paragraph(recommendations, normal_style))
    
    # Build PDF
    doc.build(story)
    return pdf_path

async def generate_themes_summary(theme_texts: list) -> str:
    """Generate AI summary of common themes"""
    if not theme_texts:
        return "Темы разнообразны и требуют индивидуального подхода."
    
    context_text = " ".join(theme_texts[:10])  # Limit to first 10 themes
    prompt = f"""
    Проанализируй следующие темы для психотерапии и дай краткое обобщение (1-2 предложения) основных направлений работы:
    {context_text}
    
    Отвечай кратко, без введений и заключений. Не используй markdown.
    """
    
    try:
        response = await asyncio.to_thread(
            client.models.generate_content,
            model="gemini-2.0-flash",
            contents=[prompt]
        )
        summary = response.text if hasattr(response, 'text') else str(response)
        return summary.strip()
    except Exception as e:
        logger.error(f"Error generating themes summary: {e}")
        return "Основные направления включают работу с эмоциональными реакциями и межличностными отношениями."

async def generate_weekly_theme(week_theme_texts: list) -> str:
    """Generate common theme for a week"""
    if not week_theme_texts:
        return "развитие личности"
    
    if len(week_theme_texts) == 1:
        # For single theme, extract key concept
        theme = week_theme_texts[0]
        if "отношения" in theme.lower():
            return "работа с отношениями"
        elif "тревога" in theme.lower() or "беспокойство" in theme.lower():
            return "управление тревогой"
        elif "самооценка" in theme.lower() or "уверенность" in theme.lower():
            return "работа с самооценкой"
        elif "работа" in theme.lower():
            return "профессиональные вопросы"
        else:
            return "эмоциональная регуляция"
    
    context_text = " ".join(week_theme_texts)
    prompt = f"""
    Определи общую тему для следующих психотерапевтических вопросов (дай ответ в 2-4 словах):
    {context_text}
    
    Примеры ответов: "работа с тревогой", "межличностные отношения", "самооценка и уверенность", "эмоциональная регуляция". Не используй markdown.
    """
    
    try:
        response = await asyncio.to_thread(
            client.models.generate_content,
            model="gemini-2.0-flash",
            contents=[prompt]
        )
        theme = response.text if hasattr(response, 'text') else str(response)
        return theme.strip().lower()
    except Exception as e:
        logger.error(f"Error generating weekly theme: {e}")
        return "эмоциональная регуляция"

async def generate_themes_text_fallback(callback: types.CallbackQuery, state: FSMContext, 
                                      themes: list, period_days: int):
    """Generate text report as fallback when PDF fails"""
    
    # Group themes by week
    themes_by_week = defaultdict(list)
    
    for theme in themes:
        days_ago = (datetime.now() - theme.created_at).days
        week_num = days_ago // 7
        themes_by_week[week_num].append(theme)
    
    start_date = (datetime.now() - timedelta(days=period_days)).strftime("%d.%m.%Y")
    end_date = datetime.now().strftime("%d.%m.%Y")
    
    report_text = f"📋 Темы для проработки за период {start_date} - {end_date}\n\n"
    
    total_themes = len(themes)
    report_text += f"1. Общее содержание:\n"
    report_text += f"За период добавлено {total_themes} тем для проработки с психотерапевтом.\n\n"
    
    report_text += "2. По неделям:\n\n"
    
    for week_num in sorted(themes_by_week.keys()):
        week_themes = sorted(themes_by_week[week_num], key=lambda x: x.created_at, reverse=True)
        
        if week_num == 0:
            week_title = "Текущая неделя"
        elif week_num == 1:
            week_title = "Прошлая неделя"
        else:
            week_title = f"{week_num} недель назад"
        
        report_text += f"{week_title}\n"
        report_text += "Общая тема: эмоциональная регуляция\n\n"
        
        for theme in week_themes:
            date_str = theme.created_at.strftime("%d.%m.%Y, %H:%M")
            theme_text = theme.shortened_text if theme.is_shortened and theme.shortened_text else theme.original_text
            if len(theme_text) > 100:
                theme_text = theme_text[:97] + "..."
            report_text += f"• {date_str}: {theme_text}\n"
        
        report_text += "\n"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Отметить проработанную", callback_data="mark_processed")],
        [InlineKeyboardButton(text="Удалить тему", callback_data="delete_theme")],
        [InlineKeyboardButton(text="Назад", callback_data="back_to_themes_menu")]
    ])
    
    # Split long messages
    if len(report_text) > 4000:
        parts = [report_text[i:i+4000] for i in range(0, len(report_text), 4000)]
        for i, part in enumerate(parts):
            if i == len(parts) - 1:  # Last part gets the keyboard
                await callback.message.answer(part, reply_markup=keyboard, parse_mode="Markdown")
            else:
                await callback.message.answer(part, parse_mode="Markdown")
    else:
        await callback.message.edit_text(report_text, reply_markup=keyboard, parse_mode="Markdown")
    
    await state.set_state(THERAPY_THEMES_VIEWING)

# Function to add therapy theme from thought diary (called externally)
async def add_theme_from_thought_diary(user_id: int, theme_text: str):
    """Add therapy theme from thought diary marking"""
    session = get_session()
    
    theme = TherapyTheme(
        user_id=user_id,
        original_text=theme_text,
        is_marked_for_processing=True
    )
    
    session.add(theme)
    session.commit()
    close_session(session)
    
    logger.info(f"Added therapy theme from thought diary for user {user_id}") 