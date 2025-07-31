#!/usr/bin/env python3
"""
Script to add synthetic emotion data and therapy themes for testing PDF generation
"""

import os
import sys
import random
from datetime import datetime, timedelta

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from database.session import get_session, close_session
from database.models import User, EmotionEntry, TherapyTheme

def create_synthetic_emotion_entry(user_id: int, state: str, emotion_type: str, 
                                 created_at: datetime, answer_text: str = None, 
                                 option: str = None):
    """Create a synthetic emotion entry"""
    return EmotionEntry(
        user_id=user_id,
        state=state,
        emotion_type=emotion_type,
        created_at=created_at,
        answer_text=answer_text,
        option=option
    )

def create_synthetic_therapy_theme(user_id: int, original_text: str, created_at: datetime,
                                 shortened_text: str = None, is_shortened: bool = False,
                                 is_marked_for_processing: bool = False):
    """Create a synthetic therapy theme"""
    return TherapyTheme(
        user_id=user_id,
        original_text=original_text,
        shortened_text=shortened_text,
        is_shortened=is_shortened,
        is_marked_for_processing=is_marked_for_processing,
        created_at=created_at
    )

def generate_therapy_themes_for_user(user_id: int):
    """Generate synthetic therapy themes data"""
    session = get_session()
    
    # Clear existing therapy themes for this user
    existing_themes = session.query(TherapyTheme).filter(TherapyTheme.user_id == user_id).count()
    if existing_themes > 0:
        print(f"🧹 Удаляем {existing_themes} существующих тем для проработки...")
        session.query(TherapyTheme).filter(TherapyTheme.user_id == user_id).delete()
        session.commit()
    
    now = datetime.now()
    themes_to_add = []
    
    # Sample therapy themes in Russian
    therapy_themes = [
        "Я постоянно сомневаюсь в себе и своих решениях, что мешает мне действовать уверенно",
        "У меня проблемы с установлением границ в отношениях, я не умею говорить 'нет'",
        "Я часто чувствую тревогу перед важными событиями и не знаю как с этим справляться",
        "Мне трудно выражать свои эмоции, особенно негативные, что создает напряжение",
        "Я склонна к перфекционизму и это истощает меня эмоционально",
        "У меня низкая самооценка, я постоянно сравниваю себя с другими",
        "Мне сложно доверять людям после негативного опыта в прошлом",
        "Я испытываю сильное чувство вины за события, которые не могла контролировать",
        "У меня есть страх одиночества, который влияет на мои отношения",
        "Мне трудно просить о помощи, я привыкла все делать сама",
        "Я часто откладываю важные дела из-за страха неудачи",
        "У меня проблемы с управлением гневом в стрессовых ситуациях",
        "Мне сложно принимать комплименты и признавать свои достижения",
        "Я боюсь конфликтов и избегаю сложных разговоров",
        "У меня есть навязчивые мысли, которые мешают сосредоточиться на настоящем"
    ]
    
    # Shortened versions for some themes
    shortened_themes = [
        "Проблемы с уверенностью в себе",
        "Сложности с границами в отношениях", 
        "Тревога перед важными событиями",
        "Трудности с выражением эмоций",
        "Перфекционизм и эмоциональное истощение",
        "Низкая самооценка",
        "Проблемы с доверием",
        "Чувство вины",
        "Страх одиночества",
        "Сложности с просьбами о помощи",
        "Прокрастинация из-за страха неудачи",
        "Управление гневом",
        "Принятие комплиментов",
        "Избегание конфликтов",
        "Навязчивые мысли"
    ]
    
    print("📝 Генерируем темы для проработки...")
    
    # Generate themes for last 2 months (60 days)
    for days_ago in range(60):
        theme_date = now - timedelta(days=days_ago)
        
        # Skip some days randomly
        if random.random() < 0.7:  # 70% chance to skip a day
            continue
        
        # Generate 1-2 themes per day when there are themes
        themes_per_day = random.randint(1, 2)
        
        for _ in range(themes_per_day):
            theme_time = theme_date.replace(
                hour=random.randint(9, 21),
                minute=random.randint(0, 59),
                second=random.randint(0, 59)
            )
            
            # Select random theme
            theme_index = random.randint(0, len(therapy_themes) - 1)
            original_text = therapy_themes[theme_index]
            
            # 40% chance to have shortened version
            is_shortened = random.random() < 0.4
            shortened_text = shortened_themes[theme_index] if is_shortened else None
            
            # 30% chance to be marked from thought diary
            is_marked = random.random() < 0.3
            
            theme = create_synthetic_therapy_theme(
                user_id=user_id,
                original_text=original_text,
                shortened_text=shortened_text,
                is_shortened=is_shortened,
                is_marked_for_processing=is_marked,
                created_at=theme_time
            )
            
            themes_to_add.append(theme)
    
    # Add some specific recent themes for testing
    print("🎯 Добавляем специфические темы для последних дней...")
    
    specific_recent_themes = [
        ("Сегодня снова был конфликт с мамой, не знаю как наладить отношения", "Конфликт с мамой", True),
        ("Мне предложили повышение но я боюсь что не справлюсь с новой ответственностью", None, False),
        ("Партнер не понимает моих потребностей в общении, чувствую себя одинокой", "Проблемы в общении с партнером", True),
        ("Не могу избавиться от мыслей о прошлых ошибках, они мешают двигаться дальше", None, False),
        ("Коллеги не ценят мою работу, думаю стоит ли искать новое место", "Проблемы на работе", True)
    ]
    
    for days_ago, (original, shortened, is_shortened) in enumerate(specific_recent_themes):
        theme_date = now - timedelta(days=days_ago)
        theme_time = theme_date.replace(
            hour=random.randint(15, 20),
            minute=random.randint(0, 59)
        )
        
        # Recent themes are more likely to be marked for processing
        is_marked = days_ago < 3
        
        theme = create_synthetic_therapy_theme(
            user_id=user_id,
            original_text=original,
            shortened_text=shortened,
            is_shortened=is_shortened,
            is_marked_for_processing=is_marked,
            created_at=theme_time
        )
        
        themes_to_add.append(theme)
    
    # Bulk insert therapy themes
    print(f"💾 Добавляем {len(themes_to_add)} тем для проработки в базу данных...")
    session.add_all(themes_to_add)
    session.commit()
    
    # Print therapy themes statistics
    total_themes = len(themes_to_add)
    shortened_count = len([t for t in themes_to_add if t.is_shortened])
    marked_count = len([t for t in themes_to_add if t.is_marked_for_processing])
    
    print(f"\n📋 Статистика тем для проработки:")
    print(f"  Всего тем: {total_themes}")
    print(f"  С сокращенным текстом: {shortened_count}")
    print(f"  Отмеченных из дневника мыслей: {marked_count}")
    
    close_session(session)
    return True

def generate_synthetic_data_for_user(user_id: int):
    """Generate synthetic emotion data for different time periods"""
    
    session = get_session()
    
    # Check if user exists
    user = session.query(User).filter(User.id == user_id).first()
    if not user:
        print(f"❌ Пользователь с ID {user_id} не найден")
        close_session(session)
        return False
    
    print(f"👤 Добавляем синтетические данные для пользователя: {user.full_name} (ID: {user_id})")
    
    # Clear existing emotion entries for this user
    existing_entries = session.query(EmotionEntry).filter(EmotionEntry.user_id == user_id).count()
    if existing_entries > 0:
        print(f"🧹 Удаляем {existing_entries} существующих записей...")
        session.query(EmotionEntry).filter(EmotionEntry.user_id == user_id).delete()
        session.commit()
    
    now = datetime.now()
    entries_to_add = []
    
    # Emotion states and contexts
    positive_states = [
        ("good_state_1", "Сегодня был отличный день на работе, все получалось легко"),
        ("good_state_2", "Провела время с семьей, очень спокойно и уютно"),
        ("good_state_3", "Встретилась с подругой, было тепло и душевно"),
        ("good_state_4", "Прочитала интересную книгу, вдохновляет на новые идеи"),
        ("good_state_5", "Справилась с трудной задачей, чувствую уверенность")
    ]
    
    negative_states = [
        ("bad_state_1", "Очень устала на работе, нет сил ни на что"),
        ("bad_state_2", "Беспокоюсь о предстоящем собеседовании"),
        ("bad_state_3", "Поссорилась с коллегой, очень раздражает его поведение"),
        ("bad_state_4", "Чувствую себя одинокой, хочется отстраниться от всех"),
        ("bad_state_5", "Сказала что-то неуместное, теперь стыдно")
    ]
    
    # Generate data for last 3 months (90 days)
    print("📅 Генерируем данные за последние 3 месяца...")
    
    for days_ago in range(90):
        entry_date = now - timedelta(days=days_ago)
        
        # Skip some days randomly (not every day has entries)
        if random.random() < 0.3:  # 30% chance to skip a day
            continue
        
        # Generate 1-4 entries per day
        entries_per_day = random.randint(1, 4)
        
        for entry_num in range(entries_per_day):
            # Add some hours variation
            entry_time = entry_date.replace(
                hour=random.randint(8, 22),
                minute=random.randint(0, 59),
                second=random.randint(0, 59)
            )
            
            # 60% positive, 40% negative emotions (realistic distribution)
            if random.random() < 0.6:
                state, context = random.choice(positive_states)
                emotion_type = "positive"
            else:
                state, context = random.choice(negative_states)
                emotion_type = "negative"
            
            # Generate option (0 or 1)
            option = f"{state.split('_')[0]}_{state.split('_')[1]}_{random.randint(0, 1)}"
            
            entry = create_synthetic_emotion_entry(
                user_id=user_id,
                state=state,
                emotion_type=emotion_type,
                created_at=entry_time,
                answer_text=context,
                option=option
            )
            
            entries_to_add.append(entry)
    
    # Add some specific patterns for testing
    print("🎯 Добавляем специфические паттерны для тестирования...")
    
    # Add more stress entries in the last week
    for days_ago in range(7):
        entry_date = now - timedelta(days=days_ago)
        if random.random() < 0.7:  # 70% chance for stress entry
            entry_time = entry_date.replace(
                hour=random.randint(18, 21),  # Evening stress
                minute=random.randint(0, 59)
            )
            
            stress_contexts = [
                "Дедлайн на работе приближается, очень нервничаю",
                "Много задач накопилось, не знаю с чего начать",
                "Конфликт в семье, очень переживаю",
                "Проблемы со здоровьем у близкого человека"
            ]
            
            entry = create_synthetic_emotion_entry(
                user_id=user_id,
                state="bad_state_2",  # Anxiety
                emotion_type="negative",
                created_at=entry_time,
                answer_text=random.choice(stress_contexts),
                option="bad_state_2_1"
            )
            
            entries_to_add.append(entry)
    
    # Add some joy entries in the last 3 days
    for days_ago in range(3):
        entry_date = now - timedelta(days=days_ago)
        entry_time = entry_date.replace(
            hour=random.randint(10, 16),  # Daytime joy
            minute=random.randint(0, 59)
        )
        
        joy_contexts = [
            "Получила комплимент от начальника",
            "Удачно провела презентацию",
            "Встретила старого друга на улице",
            "Купила что-то приятное для себя"
        ]
        
        entry = create_synthetic_emotion_entry(
            user_id=user_id,
            state="good_state_1",  # Joy/uplift
            emotion_type="positive",
            created_at=entry_time,
            answer_text=random.choice(joy_contexts),
            option="good_state_1_1"
        )
        
        entries_to_add.append(entry)
    
    # Bulk insert all entries
    print(f"💾 Добавляем {len(entries_to_add)} записей в базу данных...")
    session.add_all(entries_to_add)
    session.commit()
    
    # Print statistics
    total_entries = len(entries_to_add)
    positive_count = len([e for e in entries_to_add if e.emotion_type == "positive"])
    negative_count = len([e for e in entries_to_add if e.emotion_type == "negative"])
    
    print(f"\n📊 Статистика добавленных данных:")
    print(f"  Всего записей: {total_entries}")
    print(f"  Позитивных эмоций: {positive_count}")
    print(f"  Негативных эмоций: {negative_count}")
    
    # Show distribution by periods
    three_days_ago = now - timedelta(days=3)
    week_ago = now - timedelta(days=7)
    month_ago = now - timedelta(days=30)
    
    entries_3d = len([e for e in entries_to_add if e.created_at >= three_days_ago])
    entries_7d = len([e for e in entries_to_add if e.created_at >= week_ago])
    entries_30d = len([e for e in entries_to_add if e.created_at >= month_ago])
    entries_90d = total_entries
    
    print(f"\n📅 Распределение по периодам:")
    print(f"  Последние 3 дня: {entries_3d} записей")
    print(f"  Последние 7 дней: {entries_7d} записей")
    print(f"  Последние 30 дней: {entries_30d} записей")
    print(f"  Последние 90 дней: {entries_90d} записей")
    
    close_session(session)
    return True

def verify_user_exists(user_id: int):
    """Verify that user exists and show info"""
    session = get_session()
    user = session.query(User).filter(User.id == user_id).first()
    
    if user:
        print(f"✅ Пользователь найден:")
        print(f"  ID: {user.id}")
        print(f"  Имя: {user.full_name}")
        print(f"  Telegram ID: {user.telegram_id}")
        print(f"  Регистрация завершена: {getattr(user, 'registration_complete', 'Неизвестно')}")
        
        # Check existing emotion entries
        existing_count = session.query(EmotionEntry).filter(EmotionEntry.user_id == user_id).count()
        print(f"  Существующих записей эмоций: {existing_count}")
        
        # Check existing therapy themes
        existing_themes = session.query(TherapyTheme).filter(TherapyTheme.user_id == user_id).count()
        print(f"  Существующих тем для проработки: {existing_themes}")
        
        close_session(session)
        return True
    else:
        print(f"❌ Пользователь с ID {user_id} не найден")
        close_session(session)
        return False

def list_all_users():
    """List all users in the database"""
    session = get_session()
    users = session.query(User).all()
    
    print("👥 Все пользователи в базе данных:")
    print("-" * 50)
    
    for user in users:
        emotion_count = session.query(EmotionEntry).filter(EmotionEntry.user_id == user.id).count()
        theme_count = session.query(TherapyTheme).filter(TherapyTheme.user_id == user.id).count()
        print(f"ID: {user.id} | {user.full_name} | Telegram: {user.telegram_id} | Эмоций: {emotion_count} | Тем: {theme_count}")
    
    close_session(session)

def main():
    """Main function"""
    print("🧪 Генератор синтетических данных для тестирования функциональности")
    print("=" * 65)
    
    # List all users first
    list_all_users()
    
    print("\n" + "=" * 65)
    
    user_id = 8
    
    # Verify user exists
    if not verify_user_exists(user_id):
        print(f"\n💡 Создайте пользователя с ID {user_id} или измените user_id в скрипте")
        return
    
    print(f"\n🚀 Начинаем генерацию данных для пользователя ID {user_id}...")
    
    # Generate synthetic emotion data
    emotion_success = generate_synthetic_data_for_user(user_id)
    
    # Generate synthetic therapy themes data  
    themes_success = generate_therapy_themes_for_user(user_id)
    
    if emotion_success and themes_success:
        print(f"\n✅ Все синтетические данные успешно добавлены!")
        print(f"\n💡 Теперь вы можете протестировать функциональность:")
        print(f"  📊 Аналитика эмоций:")
        print(f"    • 3 дня - текстовый анализ")
        print(f"    • 7 дней - PDF отчет")
        print(f"    • 30 дней - PDF отчет")
        print(f"    • 90 дней - PDF отчет")
        print(f"  📝 Темы для проработки:")
        print(f"    • 3 дня - краткий список")
        print(f"    • неделя - краткий список")
        print(f"    • 2 недели - PDF отчет")
        print(f"    • месяц - PDF отчет")
        print(f"    • 3 месяца - PDF отчет")
        print(f"\n🤖 Запустите бота:")
        print(f"  • 'Аналитика эмоций' - для тестирования анализа")
        print(f"  • 'Темы для проработки' - для тестирования новой функции")
    else:
        print(f"\n❌ Ошибка при генерации данных")

if __name__ == "__main__":
    main() 