#!/usr/bin/env python3
"""
Freemium Configuration for PsyBot
Contains settings for trial periods and premium features
"""

import os
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()

# Trial period configuration
TRIAL_DURATION_DAYS = int(os.getenv('TRIAL_DURATION_DAYS', '14'))  # Default 2 weeks, configurable via .env
TRIAL_DURATION = timedelta(days=TRIAL_DURATION_DAYS)

# Trial expiry messages
TRIAL_EXPIRED_MESSAGE = """
Пробный период завершен

Ваш 2-недельный пробный период использования PsyBot истек.

Чтобы продолжить использование всех функций бота, необходимо оформить подписку.

Что включает премиум доступ
- Безлимитный доступ к дневнику эмоций
- Развернутая аналитика настроения
- Персональные рекомендации
- Неограниченное количество тем для терапии
- Все техники релаксации
- Приоритетная поддержка

Варианты подписки
- Месячная подписка: 990р в месяц
- Квартальная подписка: 2490р (экономия 480р)
- Годовая подписка: 7990р (экономия 4000р)

Оплата
Напишите @maryasha_mi, пришлите скриншот перевода и ожидайте активацию максимум 24 часа.

Реквизиты для перевода
Получатель: Мирзоева Марьям Иброхимовна
Номер карты: 2200240481906044
Банк получателя: Филиал номер 2754 Банка ВТБ (ПАО)
БИК: 040813713
ИНН: 7702070139
КС: 30101810708130000713
Счет: 40817810525566017265

Возврат средств - Гарантия возврата в течение 7 дней

Спасибо за использование PsyBot! 💙
"""

# Quick payment message for feature access attempts
FEATURE_ACCESS_PAYMENT_MESSAGE = """
Требуется подписка

Для доступа к этой функции необходима активная подписка.

Тарифы
- Месячная: 990р
- Квартальная: 2490р (экономия 480р)
- Годовая: 7990р (экономия 4000р)

Оплата
Напишите @maryasha_mi, пришлите скриншот перевода и ожидайте активацию максимум 24 часа.

Реквизиты для перевода
Получатель: Мирзоева Марьям Иброхимовна
Номер карты: 2200240481906044
Банк получателя: Филиал номер 2754 Банка ВТБ (ПАО)
БИК: 040813713
ИНН: 7702070139
КС: 30101810708130000713
Счет: 40817810525566017265

Активация в течение 24 часов после подтверждения оплаты!
"""

TRIAL_WARNING_3_DAYS = """
Напоминание о пробном периоде

До окончания вашего пробного периода осталось 3 дня.

После завершения пробного периода доступ к боту будет ограничен.

Чтобы продолжить пользоваться всеми функциями, рассмотрите возможность оформления подписки.

Тарифы подписки
- Месячная: 990р в месяц
- Квартальная: 2490р (экономия 480р)
- Годовая: 7990р (экономия 4000р)

Оплата
Напишите @maryasha_mi, пришлите скриншот перевода и ожидайте активацию максимум 24 часа.

Реквизиты
Карта: 2200 2404 8190 6044
Получатель: Мирзоева Марьям Иброхимовна
"""

TRIAL_WARNING_1_DAY = """
Последний день пробного периода

Завтра ваш пробный доступ к PsyBot будет завершен.

Не теряйте прогресс! Оформите подписку сегодня, чтобы продолжить работу с ботом без перерыва.

Быстрое оформление
- Месячная подписка: 990р
- Квартальная: 2490р (выгоднее на 480р)
- Годовая: 7990р (выгоднее на 4000р)

Оплата прямо сейчас
Напишите @maryasha_mi, пришлите скриншот перевода и ожидайте активацию максимум 24 часа.

Реквизиты
Карта: 2200 2404 8190 6044
Получатель: Мирзоева Марьям Иброхимовна

Гарантия возврата 7 дней
"""

# Features available for trial users (same as premium for now)
TRIAL_FEATURES = {
    'emotion_diary': True,
    'emotion_analytics': True,
    'therapy_themes': True,
    'relaxation_methods': True,
    'reflection': True,
    'weekly_reflection': True,
    'notifications': True
}

# Features available for premium users
PREMIUM_FEATURES = {
    'emotion_diary': True,
    'emotion_analytics': True,
    'therapy_themes': True,
    'relaxation_methods': True,
    'reflection': True,
    'weekly_reflection': True,
    'notifications': True
}

# Features available for expired users (very limited)
EXPIRED_FEATURES = {
    'emotion_diary': False,
    'emotion_analytics': False,
    'therapy_themes': False,
    'relaxation_methods': False,
    'reflection': False,
    'weekly_reflection': False,
    'notifications': False
} 