from sqlalchemy import Column, Integer, String, Boolean, DateTime, create_engine, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
import os
from dotenv import load_dotenv

load_dotenv()

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    telegram_id = Column(Integer, unique=True, nullable=False)
    username = Column(String, nullable=True)
    first_name = Column(String, nullable=True)
    full_name = Column(String, nullable=True)
    gender = Column(String, nullable=True)
    age = Column(Integer, nullable=True)
    time_format = Column(String, default="24h")
    timezone_offset = Column(Integer, default=0)  # Offset from server time in hours
    user_timezone = Column(String, nullable=True)  # User's timezone string (e.g., "UTC+3", "UTC-5")
    notification_frequency = Column(Integer, default=1)  # Times per day for emotion diary notifications
    works_with_therapist = Column(Boolean, nullable=True)  # Whether user works with psychologist/therapist
    referral_source = Column(String, nullable=True)  # How user found out about the bot
    agreed_to_terms = Column(Boolean, default=False)
    registration_complete = Column(Boolean, default=False)
    
    # Freemium trial fields
    trial_start_date = Column(DateTime, nullable=True)  # When trial started (set on registration completion)
    trial_end_date = Column(DateTime, nullable=True)    # When trial expires
    is_premium = Column(Boolean, default=False)         # Whether user has premium access
    trial_expired = Column(Boolean, default=False)      # Whether trial has expired and user is blocked
    
    # Activity tracking
    last_activity = Column(DateTime, nullable=True)     # When user last interacted with bot (messages/buttons)
    
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<User(telegram_id={self.telegram_id}, name={self.full_name})>"

class Admin(Base):
    __tablename__ = 'admins'

    id = Column(Integer, primary_key=True)
    username = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    last_login = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=func.now())

    def __repr__(self):
        return f"<Admin(username={self.username}, is_active={self.is_active})>"

class AdminSession(Base):
    __tablename__ = 'admin_sessions'

    id = Column(Integer, primary_key=True)
    admin_id = Column(Integer, nullable=False)
    session_token = Column(String, unique=True, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    ip_address = Column(String, nullable=True)
    user_agent = Column(String, nullable=True)
    created_at = Column(DateTime, default=func.now())

    def __repr__(self):
        return f"<AdminSession(admin_id={self.admin_id}, expires_at={self.expires_at})>"

class EmotionEntry(Base):
    __tablename__ = 'emotion_entries'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False)
    emotion_type = Column(String, nullable=False)
    answer_text = Column(String, nullable=True)
    state = Column(String, nullable=True)
    option = Column(String, nullable=True)
    created_at = Column(DateTime, default=func.now())

    def __repr__(self):
        return f"<EmotionEntry(user_id={self.user_id}, emotion_type={self.emotion_type}, created_at={self.created_at})>"

class ReflectionEntry(Base):
    __tablename__ = 'reflection_entries'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False)
    valuable_learned = Column(Text, nullable=True)  # Что ценного ты узнала сегодня?
    openness_level = Column(Text, nullable=True)    # Насколько полно ты смогла открыться психотерапевту?
    obstacles = Column(Text, nullable=True)         # Было ли что-то, что мешало на терапии?
    next_topics = Column(Text, nullable=True)       # Какие темы ты хочешь обсудить на следующей неделе?
    ai_transcription = Column(Text, nullable=True)  # AI-generated summary
    created_at = Column(DateTime, default=func.now())

    def __repr__(self):
        return f"<ReflectionEntry(user_id={self.user_id}, created_at={self.created_at})>"

class TherapySession(Base):
    __tablename__ = 'therapy_sessions'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False)
    session_datetime = Column(DateTime, nullable=False)  # When the therapy session is scheduled
    reflection_datetime = Column(DateTime, nullable=False)  # When to send reflection reminder (session + 5 hours)
    reflection_sent = Column(Boolean, default=False)  # Whether reflection reminder was sent
    created_at = Column(DateTime, default=func.now())

    def __repr__(self):
        return f"<TherapySession(user_id={self.user_id}, session_datetime={self.session_datetime}, reflection_sent={self.reflection_sent})>"

class WeeklyReflection(Base):
    __tablename__ = 'weekly_reflections'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False)
    smile_moment = Column(Text, nullable=True)      # Какой маленький момент на этой неделе неожиданно заставил тебя улыбнуться или рассмеяться?
    kindness = Column(Text, nullable=True)          # Кто-то сделал для тебя что-то доброе или, может быть, ты сам помог кому-то так, что это запомнилось?
    peace_moment = Column(Text, nullable=True)      # В какой момент недели ты почувствовал(а) спокойствие, удовлетворение или был(а) по-настоящему собой?
    new_discovery = Column(Text, nullable=True)     # Что-то новое ты попробовал(а), узнал(а) или заметил(а) о себе или окружающем мире на этой неделе?
    gratitude = Column(Text, nullable=True)         # За что ты благодарен(на) на этой неделе — неважно, большое это или маленькое?
    ai_summary = Column(Text, nullable=True)        # AI-generated summary
    created_at = Column(DateTime, default=func.now())

    def __repr__(self):
        return f"<WeeklyReflection(user_id={self.user_id}, created_at={self.created_at})>"

class TherapyTheme(Base):
    __tablename__ = 'therapy_themes'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False)
    original_text = Column(Text, nullable=False)    # Original user text
    shortened_text = Column(Text, nullable=True)    # AI-shortened version
    is_shortened = Column(Boolean, default=False)   # Whether the shortened version is used
    is_marked_for_processing = Column(Boolean, default=False)  # If marked from thought diary
    created_at = Column(DateTime, default=func.now())

    def __repr__(self):
        return f"<TherapyTheme(user_id={self.user_id}, created_at={self.created_at})>"

class RelaxationMedia(Base):
    __tablename__ = 'relaxation_media'

    id = Column(Integer, primary_key=True)
    title = Column(String, nullable=False)          # Display name of the media
    description = Column(Text, nullable=True)       # Description of the content
    media_type = Column(String, nullable=False)     # 'audio' or 'video'
    file_path = Column(String, nullable=False)      # Path to the file (relative or URL)
    duration = Column(Integer, nullable=True)       # Duration in seconds
    is_active = Column(Boolean, default=True)       # Whether media is available
    order_position = Column(Integer, default=0)     # For ordering in lists
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<RelaxationMedia(title={self.title}, media_type={self.media_type}, is_active={self.is_active})>"

# Initialize database connection
from pathlib import Path
def get_engine():
    default_path = Path(__file__).parent / "../database/psybot.db"
    abs_path = default_path.resolve()
    database_url = f"sqlite:///{abs_path}"
    return create_engine(database_url)

def init_db():
    engine = get_engine()
    Base.metadata.create_all(engine)