#!/usr/bin/env python3
"""
Advanced Synthetic Emotion Generator for PsyBot
Generates realistic emotion patterns for testing and demonstration purposes
"""

import os
import sys
import random
import argparse
from datetime import datetime, timedelta
from typing import List, Tuple, Dict, Optional

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from database.session import get_session, close_session
from database.models import User, EmotionEntry, TherapyTheme, WeeklyReflection

class EmotionPatternGenerator:
    """Advanced emotion pattern generator with realistic behavioral patterns"""
    
    def __init__(self):
        # Emotion states mapping
        self.emotion_states = {
            "positive": {
                "good_state_1": {
                    "name": "Подъем, легкость",
                    "options": ["Приятно", "Захватывает"],
                    "contexts": [
                        "Получила отличные новости на работе",
                        "Утренняя пробежка дала заряд энергии на весь день",
                        "Встретила старого друга и мы здорово поговорили",
                        "Удачно завершила сложный проект",
                        "Погода прекрасная, хочется улыбаться",
                        "Дети порадовали своими успехами",
                        "Получила комплимент от коллеги",
                        "Прочитала вдохновляющую книгу"
                    ]
                },
                "good_state_2": {
                    "name": "Спокойствие, расслабленность",
                    "options": ["Удовлетворение", "Глубокий покой"],
                    "contexts": [
                        "Провела выходные дома за любимыми делами",
                        "Медитация помогла успокоиться",
                        "Вечерняя ванна расслабила после тяжелого дня",
                        "Уютный вечер с чашкой чая и хорошей книгой",
                        "Закончила все дела и могу отдохнуть",
                        "Прогулка в парке принесла умиротворение",
                        "Качественно выспалась и чувствую себя отдохнувшей",
                        "Время наедине с собой дало внутреннее спокойствие"
                    ]
                },
                "good_state_3": {
                    "name": "Уют, близость",
                    "options": ["Тепло", "Близость"],
                    "contexts": [
                        "Семейный ужин прошел в теплой атмосфере",
                        "Обнялась с партнером и почувствовала близость",
                        "Провела время с лучшей подругой",
                        "Дети прижались ко мне перед сном",
                        "Искренний разговор с близким человеком",
                        "Семейные традиции создают ощущение единства",
                        "Поддержка друзей в трудный момент",
                        "Чувствую себя нужной и любимой"
                    ]
                },
                "good_state_4": {
                    "name": "Интерес, вдохновение",
                    "options": ["Интерес", "Вдохновение"],
                    "contexts": [
                        "Открыла для себя новое хобби",
                        "Интересная лекция дала пищу для размышлений",
                        "Планирую творческий проект",
                        "Изучаю новый язык и это увлекает",
                        "Посетила выставку современного искусства",
                        "Идея для решения рабочей задачи пришла неожиданно",
                        "Документальный фильм расширил мой кругозор",
                        "Вдохновилась успехом других людей"
                    ]
                },
                "good_state_5": {
                    "name": "Сила, уверенность",
                    "options": ["Сила", "Уверенность"],
                    "contexts": [
                        "Справилась с трудной ситуацией самостоятельно",
                        "Выступление прошло лучше, чем ожидала",
                        "Приняла важное решение и уверена в нем",
                        "Защитила свою точку зрения в споре",
                        "Достигла поставленной цели",
                        "Преодолела свой страх и сделала то, что боялась",
                        "Получила признание за свою работу",
                        "Чувствую внутреннюю силу и стабильность"
                    ]
                }
            },
            "negative": {
                "bad_state_1": {
                    "name": "Тяжесть, усталость",
                    "options": ["Усталость", "Потеря сил"],
                    "contexts": [
                        "Рабочая неделя была особенно тяжелой",
                        "Бессонная ночь сказалась на самочувствии",
                        "Много дел накопилось и нет сил на все",
                        "Эмоционально истощена после сложного периода",
                        "Домашние обязанности не оставляют времени на отдых",
                        "Чувствую себя выжатой как лимон",
                        "Постоянный стресс истощает ресурсы",
                        "Нет энергии даже на простые вещи"
                    ]
                },
                "bad_state_2": {
                    "name": "Тревога, беспокойство",
                    "options": ["Тревога", "Неуверенность"],
                    "contexts": [
                        "Беспокоюсь о результатах медицинских анализов",
                        "Предстоящее собеседование вызывает тревогу",
                        "Финансовые трудности не дают покоя",
                        "Волнуюсь за детей и их будущее",
                        "Неопределенность на работе создает напряжение",
                        "Конфликт в отношениях вызывает беспокойство",
                        "Новости в мире усиливают тревожные мысли",
                        "Страх перед неизвестностью парализует"
                    ]
                },
                "bad_state_3": {
                    "name": "Злость, раздражение",
                    "options": ["Злость", "Раздражение"],
                    "contexts": [
                        "Коллега подвел в важном проекте",
                        "Несправедливое отношение начальства раздражает",
                        "Партнер не слышит мои потребности",
                        "Пробки и опоздания выводят из себя",
                        "Грубость незнакомых людей в общественном транспорте",
                        "Невыполненные обещания близких расстраивают",
                        "Бюрократические проволочки бесят",
                        "Чувство несправедливости переполняет"
                    ]
                },
                "bad_state_4": {
                    "name": "Отстраненность, обида",
                    "options": ["Отстраненность", "Обида"],
                    "contexts": [
                        "Чувствую себя непонятой близкими людьми",
                        "Друзья не поддержали в трудный момент",
                        "Исключили из важного разговора",
                        "Не получила ожидаемой поддержки",
                        "Чувствую одиночество среди людей",
                        "Обидели неосторожным словом",
                        "Не замечают моих усилий",
                        "Хочется отгородиться от всех и побыть одной"
                    ]
                },
                "bad_state_5": {
                    "name": "Вина, смущение",
                    "options": ["Вина", "Смущение"],
                    "contexts": [
                        "Сказала что-то неуместное и теперь стыдно",
                        "Не успела помочь близкому человеку",
                        "Ошибка на работе привела к проблемам",
                        "Сорвалась на детях без причины",
                        "Нарушила обещание и подвела друга",
                        "Чувствую вину за прошлые поступки",
                        "Не оправдала чьи-то ожидания",
                        "Стыдно за свою реакцию в конфликте"
                    ]
                }
            }
        }
        
        # Weekly reflection templates
        self.weekly_reflection_templates = {
            "smile_moment": [
                "Дети рассмешили меня своими играми",
                "Неожиданный комплимент от незнакомца",
                "Смешное видео в интернете подняло настроение",
                "Воспоминание о хорошем моменте из прошлого",
                "Удачная шутка в компании друзей",
                "Милое поведение домашнего питомца",
                "Красивый закат во время прогулки"
            ],
            "kindness": [
                "Помогла соседке донести тяжелые сумки",
                "Выслушала подругу, когда ей было плохо",
                "Пожертвовала деньги на благотворительность",
                "Уступила место в транспорте пожилому человеку",
                "Принесла коллеге кофе в трудный день",
                "Поддержала знакомого в социальных сетях",
                "Покормила бездомное животное"
            ],
            "peace_moment": [
                "Утренняя медитация перед началом дня",
                "Тихий вечер дома под звуки дождя",
                "Прогулка в лесу наедине с природой",
                "Время за рукоделием успокаивает мысли",
                "Чтение в тишине перед сном",
                "Горячая ванна после трудного дня",
                "Созерцание звездного неба"
            ],
            "new_discovery": [
                "Узнала интересный факт из документального фильма",
                "Открыла для себя новый жанр музыки",
                "Попробовала необычное блюдо в ресторане",
                "Прочитала книгу, которая изменила мой взгляд",
                "Научилась новому навыку на работе",
                "Посетила место, где никогда не была",
                "Познакомилась с интересным человеком"
            ],
            "gratitude": [
                "Благодарна семье за постоянную поддержку",
                "Ценю возможность заниматься любимым делом",
                "Признательна друзьям за их честность",
                "Благодарю судьбу за хорошее здоровье",
                "Ценю возможность учиться новому",
                "Благодарна за крышу над головой и безопасность",
                "Признательна природе за ее красоту"
            ]
        }
        
        # Therapy themes based on common psychological issues
        self.therapy_themes = [
            "Постоянно сомневаюсь в правильности своих решений",
            "Трудно устанавливать границы в отношениях с коллегами",
            "Испытываю тревогу перед публичными выступлениями",
            "Сложно выражать негативные эмоции, всегда сдерживаюсь",
            "Перфекционизм мешает завершать проекты вовремя",
            "Низкая самооценка влияет на карьерные возможности",
            "После предательства сложно доверять новым людям",
            "Чувствую вину за события, которые не могла контролировать",
            "Страх одиночества заставляет цепляться за токсичные отношения",
            "Не умею просить о помощи, привыкла справляться сама",
            "Откладываю важные дела из-за страха неудачи",
            "Трудно контролировать гнев в стрессовых ситуациях",
            "Не могу принимать комплименты, всегда обесцениваю",
            "Избегаю конфликтов даже когда права",
            "Навязчивые мысли о прошлых ошибках мешают жить",
            "Синдром самозванца на работе не дает покоя",
            "Эмоциональная зависимость от мнения других",
            "Трудности с принятием собственного тела",
            "Страх близости мешает строить отношения",
            "Не умею говорить 'нет' и перегружаю себя"
        ]

    def generate_realistic_emotion_pattern(self, user_id: int, days: int = 90) -> List[EmotionEntry]:
        """Generate realistic emotion patterns for specified number of days"""
        entries = []
        now = datetime.now()
        
        # Create personality profile for consistent patterns
        personality = self._generate_personality_profile()
        
        for days_ago in range(days):
            entry_date = now - timedelta(days=days_ago)
            
            # Skip some days (people don't always log emotions)
            if random.random() < 0.25:  # 25% chance to skip a day
                continue
            
            # Generate 1-5 entries per day based on personality
            entries_per_day = self._calculate_daily_entries(personality, days_ago)
            
            for entry_num in range(entries_per_day):
                # Calculate emotion probability based on patterns
                emotion_type, state = self._select_emotion_with_patterns(
                    personality, days_ago, entry_num, entry_date
                )
                
                # Generate entry time (more realistic distribution)
                entry_time = self._generate_realistic_time(entry_date, entry_num, personality)
                
                # Select context and option
                context = self._select_context(state, personality)
                option = self._select_option(state)
                
                entry = EmotionEntry(
                    user_id=user_id,
                    state=state,
                    emotion_type=emotion_type,
                    created_at=entry_time,
                    answer_text=context,
                    option=option
                )
                
                entries.append(entry)
        
        return entries
    
    def generate_weekly_reflections(self, user_id: int, weeks: int = 12) -> List[WeeklyReflection]:
        """Generate weekly reflections for specified number of weeks"""
        reflections = []
        now = datetime.now()
        
        for weeks_ago in range(weeks):
            reflection_date = now - timedelta(weeks=weeks_ago)
            
            # Not every week has reflection (70% chance)
            if random.random() < 0.3:
                continue
            
            reflection_time = reflection_date.replace(
                hour=random.randint(19, 22),  # Evening reflections
                minute=random.randint(0, 59)
            )
            
            reflection = WeeklyReflection(
                user_id=user_id,
                smile_moment=random.choice(self.weekly_reflection_templates["smile_moment"]),
                kindness=random.choice(self.weekly_reflection_templates["kindness"]),
                peace_moment=random.choice(self.weekly_reflection_templates["peace_moment"]),
                new_discovery=random.choice(self.weekly_reflection_templates["new_discovery"]),
                gratitude=random.choice(self.weekly_reflection_templates["gratitude"]),
                created_at=reflection_time
            )
            
            reflections.append(reflection)
        
        return reflections
    
    def generate_therapy_themes(self, user_id: int, days: int = 90) -> List[TherapyTheme]:
        """Generate therapy themes for specified number of days"""
        themes = []
        now = datetime.now()
        
        for days_ago in range(days):
            theme_date = now - timedelta(days=days_ago)
            
            # Skip most days (themes are less frequent)
            if random.random() < 0.85:  # 15% chance to have themes
                continue
            
            # Generate 1-2 themes per day when they occur
            themes_per_day = random.randint(1, 2)
            
            for _ in range(themes_per_day):
                theme_time = theme_date.replace(
                    hour=random.randint(10, 22),
                    minute=random.randint(0, 59)
                )
                
                original_text = random.choice(self.therapy_themes)
                
                # 30% chance to have shortened version
                is_shortened = random.random() < 0.3
                shortened_text = self._create_shortened_theme(original_text) if is_shortened else None
                
                # Recent themes more likely to be marked
                is_marked = random.random() < (0.5 if days_ago < 7 else 0.2)
                
                theme = TherapyTheme(
                    user_id=user_id,
                    original_text=original_text,
                    shortened_text=shortened_text,
                    is_shortened=is_shortened,
                    is_marked_for_processing=is_marked,
                    created_at=theme_time
                )
                
                themes.append(theme)
        
        return themes
    
    def _generate_personality_profile(self) -> Dict:
        """Generate a personality profile for consistent emotion patterns"""
        return {
            "stress_level": random.uniform(0.2, 0.8),  # Base stress level
            "emotional_stability": random.uniform(0.3, 0.9),  # How stable emotions are
            "positivity_bias": random.uniform(0.4, 0.7),  # Tendency toward positive emotions
            "introversion": random.uniform(0.2, 0.8),  # Affects social emotion contexts
            "anxiety_prone": random.uniform(0.1, 0.6),  # Tendency toward anxiety
            "daily_pattern": random.choice(["morning", "afternoon", "evening", "mixed"])
        }
    
    def _calculate_daily_entries(self, personality: Dict, days_ago: int) -> int:
        """Calculate number of entries per day based on personality and recency"""
        base_entries = 2 if days_ago < 7 else 1  # More recent = more entries
        
        # Stressed people log more emotions
        if personality["stress_level"] > 0.6:
            base_entries += 1
        
        # Less emotionally stable people have more entries
        if personality["emotional_stability"] < 0.5:
            base_entries += 1
        
        return min(random.randint(1, base_entries + 1), 5)
    
    def _select_emotion_with_patterns(self, personality: Dict, days_ago: int, 
                                    entry_num: int, entry_date: datetime) -> Tuple[str, str]:
        """Select emotion type and state based on realistic patterns"""
        
        # Base probability toward positive/negative
        positive_prob = personality["positivity_bias"]
        
        # Recent stress affects emotions (last week more negative)
        if days_ago < 7:
            positive_prob *= 0.8
        
        # Weekends slightly more positive
        if entry_date.weekday() >= 5:  # Saturday or Sunday
            positive_prob *= 1.1
        
        # Anxiety-prone people have more negative emotions
        if personality["anxiety_prone"] > 0.5:
            positive_prob *= 0.7
        
        # Choose emotion type
        if random.random() < positive_prob:
            emotion_type = "positive"
            states = list(self.emotion_states["positive"].keys())
        else:
            emotion_type = "negative"
            states = list(self.emotion_states["negative"].keys())
        
        # Select specific state (some patterns)
        if emotion_type == "negative" and personality["anxiety_prone"] > 0.5:
            # Anxiety-prone people more likely to have bad_state_2 (anxiety)
            if random.random() < 0.4:
                state = "bad_state_2"
            else:
                state = random.choice(states)
        else:
            state = random.choice(states)
        
        return emotion_type, state
    
    def _generate_realistic_time(self, entry_date: datetime, entry_num: int, 
                               personality: Dict) -> datetime:
        """Generate realistic time based on personality and entry number"""
        
        if personality["daily_pattern"] == "morning":
            hour = random.randint(7, 11)
        elif personality["daily_pattern"] == "afternoon":
            hour = random.randint(12, 17)
        elif personality["daily_pattern"] == "evening":
            hour = random.randint(18, 22)
        else:  # mixed
            hour = random.randint(8, 22)
        
        # Spread entries throughout day
        hour += entry_num * 2
        hour = min(hour, 23)
        
        return entry_date.replace(
            hour=hour,
            minute=random.randint(0, 59),
            second=random.randint(0, 59)
        )
    
    def _select_context(self, state: str, personality: Dict) -> str:
        """Select appropriate context based on state and personality"""
        emotion_type = "positive" if state.startswith("good") else "negative"
        contexts = self.emotion_states[emotion_type][state]["contexts"]
        
        # Introverted people might have different contexts
        if personality["introversion"] > 0.6:
            # Filter for more solitary contexts when available
            solo_contexts = [c for c in contexts if any(word in c.lower() 
                           for word in ["дома", "одна", "книг", "медитац", "прогулк"])]
            if solo_contexts:
                return random.choice(solo_contexts)
        
        return random.choice(contexts)
    
    def _select_option(self, state: str) -> str:
        """Select option for the emotion state"""
        option_num = random.randint(0, 1)
        return f"option_{option_num}"
    
    def _create_shortened_theme(self, original_text: str) -> str:
        """Create a shortened version of therapy theme"""
        short_versions = {
            "сомневаюсь": "Неуверенность в решениях",
            "границы": "Проблемы с границами",
            "тревогу": "Тревога и беспокойство",
            "выражать": "Сложности с эмоциями",
            "перфекционизм": "Перфекционизм",
            "самооценка": "Низкая самооценка",
            "доверять": "Проблемы с доверием",
            "вину": "Чувство вины",
            "одиночества": "Страх одиночества",
            "помощи": "Сложности с просьбами",
            "откладываю": "Прокрастинация",
            "гнев": "Управление гневом",
            "комплименты": "Принятие похвалы",
            "конфликтов": "Избегание конфликтов",
            "навязчивые": "Навязчивые мысли"
        }
        
        for keyword, short_version in short_versions.items():
            if keyword in original_text.lower():
                return short_version
        
        # Fallback - take first part of sentence
        words = original_text.split()
        return " ".join(words[:4]) + "..."

def clear_user_data(user_id: int, data_types: List[str] = None):
    """Clear existing data for user"""
    if data_types is None:
        data_types = ["emotions", "themes", "reflections"]
    
    session = get_session()
    
    counts = {}
    
    if "emotions" in data_types:
        count = session.query(EmotionEntry).filter(EmotionEntry.user_id == user_id).count()
        if count > 0:
            session.query(EmotionEntry).filter(EmotionEntry.user_id == user_id).delete()
            counts["emotions"] = count
    
    if "themes" in data_types:
        count = session.query(TherapyTheme).filter(TherapyTheme.user_id == user_id).count()
        if count > 0:
            session.query(TherapyTheme).filter(TherapyTheme.user_id == user_id).delete()
            counts["themes"] = count
    
    if "reflections" in data_types:
        count = session.query(WeeklyReflection).filter(WeeklyReflection.user_id == user_id).count()
        if count > 0:
            session.query(WeeklyReflection).filter(WeeklyReflection.user_id == user_id).delete()
            counts["reflections"] = count
    
    session.commit()
    close_session(session)
    
    return counts

def generate_data_for_user(user_id: int, days: int = 90, include_themes: bool = True, 
                          include_reflections: bool = True, clear_existing: bool = True):
    """Generate comprehensive synthetic data for a user"""
    
    session = get_session()
    user = session.query(User).filter(User.id == user_id).first()
    
    if not user:
        print(f"❌ Пользователь с ID {user_id} не найден")
        close_session(session)
        return False
    
    print(f"👤 Генерируем данные для: {user.full_name} (ID: {user_id})")
    close_session(session)
    
    # Clear existing data if requested
    if clear_existing:
        data_types = ["emotions"]
        if include_themes:
            data_types.append("themes")
        if include_reflections:
            data_types.append("reflections")
        
        counts = clear_user_data(user_id, data_types)
        if counts:
            print(f"🧹 Очищены существующие данные: {counts}")
    
    # Initialize generator
    generator = EmotionPatternGenerator()
    
    # Generate emotion entries
    print(f"😊 Генерируем эмоции за {days} дней...")
    emotions = generator.generate_realistic_emotion_pattern(user_id, days)
    
    # Generate weekly reflections
    reflections = []
    if include_reflections:
        weeks = max(1, days // 7)
        print(f"📝 Генерируем еженедельные рефлексии за {weeks} недель...")
        reflections = generator.generate_weekly_reflections(user_id, weeks)
    
    # Generate therapy themes
    themes = []
    if include_themes:
        print(f"🎯 Генерируем темы для проработки за {days} дней...")
        themes = generator.generate_therapy_themes(user_id, days)
    
    # Calculate statistics before saving to avoid DetachedInstanceError
    stats = {}
    if emotions:
        stats['emotions_total'] = len(emotions)
        stats['emotions_positive'] = len([e for e in emotions if e.emotion_type == "positive"])
        stats['emotions_negative'] = len([e for e in emotions if e.emotion_type == "negative"])
    
    if reflections:
        stats['reflections_count'] = len(reflections)
    
    if themes:
        stats['themes_total'] = len(themes)
        stats['themes_marked'] = len([t for t in themes if t.is_marked_for_processing])
    
    # Save to database
    session = get_session()
    
    if emotions:
        session.add_all(emotions)
        print(f"💾 Сохранено {len(emotions)} записей эмоций")
    
    if reflections:
        session.add_all(reflections)
        print(f"💾 Сохранено {len(reflections)} еженедельных рефлексий")
    
    if themes:
        session.add_all(themes)
        print(f"💾 Сохранено {len(themes)} тем для проработки")
    
    session.commit()
    close_session(session)
    
    # Print statistics using pre-calculated values
    print("\n📊 Статистика сгенерированных данных:")
    if 'emotions_total' in stats:
        print(f"  Эмоции: {stats['emotions_total']} (позитивных: {stats['emotions_positive']}, негативных: {stats['emotions_negative']})")
    
    if 'reflections_count' in stats:
        print(f"  Еженедельные рефлексии: {stats['reflections_count']}")
    
    if 'themes_total' in stats:
        print(f"  Темы для проработки: {stats['themes_total']} (отмеченных: {stats['themes_marked']})")
    
    return True

def list_users():
    """List all users in the database"""
    session = get_session()
    users = session.query(User).all()
    
    print("\n👥 Пользователи в базе данных:")
    print("-" * 80)
    print(f"{'ID':<4} {'Имя':<20} {'Telegram ID':<12} {'Эмоций':<8} {'Тем':<6} {'Рефлексий':<10}")
    print("-" * 80)
    
    for user in users:
        emotion_count = session.query(EmotionEntry).filter(EmotionEntry.user_id == user.id).count()
        theme_count = session.query(TherapyTheme).filter(TherapyTheme.user_id == user.id).count()
        reflection_count = session.query(WeeklyReflection).filter(WeeklyReflection.user_id == user.id).count()
        
        print(f"{user.id:<4} {user.full_name[:19]:<20} {user.telegram_id:<12} {emotion_count:<8} {theme_count:<6} {reflection_count:<10}")
    
    close_session(session)

def main():
    """Main function with command line argument parsing"""
    parser = argparse.ArgumentParser(description="Generate synthetic emotions for PsyBot users")
    parser.add_argument("user_id", type=int, nargs='?', help="User ID to generate data for")
    parser.add_argument("-d", "--days", type=int, default=90, help="Number of days to generate data for")
    parser.add_argument("--no-themes", action="store_true", help="Don't generate therapy themes")
    parser.add_argument("--no-reflections", action="store_true", help="Don't generate weekly reflections")
    parser.add_argument("--keep-existing", action="store_true", help="Don't clear existing data")
    parser.add_argument("--list-users", action="store_true", help="List all users and exit")
    
    args = parser.parse_args()
    
    print("🧪 Генератор синтетических эмоций для PsyBot")
    print("=" * 50)
    
    if args.list_users or args.user_id is None:
        list_users()
        if args.user_id is None:
            print("\n💡 Использование: python generate_synthetic_emotions.py <user_id>")
            print("   Опции: -d DAYS, --no-themes, --no-reflections, --keep-existing")
        return
    
    # Verify user exists
    session = get_session()
    user = session.query(User).filter(User.id == args.user_id).first()
    if not user:
        print(f"❌ Пользователь с ID {args.user_id} не найден")
        print("\nДоступные пользователи:")
        close_session(session)
        list_users()
        return
    
    print(f"✅ Найден пользователь: {user.full_name} (Telegram ID: {user.telegram_id})")
    close_session(session)
    
    # Generate data
    success = generate_data_for_user(
        user_id=args.user_id,
        days=args.days,
        include_themes=not args.no_themes,
        include_reflections=not args.no_reflections,
        clear_existing=not args.keep_existing
    )
    
    if success:
        print(f"\n✅ Синтетические данные успешно сгенерированы!")
        print(f"\n💡 Рекомендации для тестирования:")
        print(f"  📊 Аналитика эмоций: 3 дня (текст), 7/14/30 дней (PDF)")
        print(f"  📝 Темы для проработки: различные периоды")
        print(f"  🔄 Еженедельная рефлексия: данные включены в анализ")
        print(f"\n🤖 Запустите бота и используйте функции аналитики")
    else:
        print(f"\n❌ Ошибка при генерации данных")

if __name__ == "__main__":
    main() 