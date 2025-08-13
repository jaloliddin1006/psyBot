#!/usr/bin/env python3
"""
Quick Emotion Generator - Simple script for fast testing
"""

import os
import sys

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from src.database.session import get_session, close_session
from src.database.models import User

def main():
    """Quick generation for the first available user"""
    
    print("🚀 Быстрый генератор синтетических эмоций")
    print("=" * 45)
    
    # Find first user
    session = get_session()
    user = session.query(User).first()
    
    if not user:
        print("❌ Нет пользователей в базе данных")
        print("💡 Создайте пользователя через бота или скрипт настройки")
        close_session(session)
        return
    
    user_id = user.id
    user_name = user.full_name
    close_session(session)
    
    print(f"👤 Найден пользователь: {user_name} (ID: {user_id})")
    
    # Import the main generator
    from generate_synthetic_emotions import generate_data_for_user
    
    # Generate data with default settings (90 days)
    print(f"\n🎯 Генерируем полный набор тестовых данных...")
    
    success = generate_data_for_user(
        user_id=user_id,
        days=90,  # 3 months of data
        include_themes=True,
        include_reflections=True,
        clear_existing=True
    )
    
    if success:
        print(f"\n✅ Готово! Тестовые данные созданы")
        print(f"\n🎮 Что можно протестировать:")
        print(f"  📊 Аналитика эмоций:")
        print(f"    • 3 дня - текстовый анализ с AI советами")
        print(f"    • 7/14/30/90 дней - PDF отчеты")
        print(f"  📝 Еженедельная рефлексия:")
        print(f"    • Данные включены в анализ и отчеты")
        print(f"  🎯 Темы для проработки:")
        print(f"    • Различные периоды анализа")
        print(f"\n🤖 Запустите бота: python src/main.py")
        print(f"   Или через Docker: docker-compose up")
    else:
        print(f"\n❌ Ошибка при генерации данных")

if __name__ == "__main__":
    main() 