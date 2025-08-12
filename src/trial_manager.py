#!/usr/bin/env python3
"""
Trial Management Utilities for PsyBot Freemium Model
"""

from datetime import datetime, timedelta
from typing import Optional, Tuple, Dict
import logging
from functools import wraps
from aiogram import types
from aiogram.fsm.context import FSMContext
from src.database.models import User
from src.database.session import get_session, close_session
from src.freemium_config import (
    TRIAL_DURATION, TRIAL_FEATURES, PREMIUM_FEATURES, EXPIRED_FEATURES,
    TRIAL_EXPIRED_MESSAGE, TRIAL_WARNING_3_DAYS, TRIAL_WARNING_1_DAY,
    FEATURE_ACCESS_PAYMENT_MESSAGE
)

logger = logging.getLogger(__name__)

def require_trial_access(feature: str):
    """
    Decorator to check trial access for callback handlers
    
    Args:
        feature: Feature name to check access for
        
    Returns:
        Decorator function
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(callback: types.CallbackQuery, state: FSMContext, *args, **kwargs):
            # Get user from database
            session = get_session()
            try:
                db_user = session.query(User).filter(User.telegram_id == callback.from_user.id).first()
                
                if not db_user or not getattr(db_user, 'registration_complete', False):
                    await callback.answer()
                    await callback.message.answer("Пожалуйста, завершите регистрацию с помощью /start")
                    return
                
                # Check trial access
                if not has_feature_access(db_user, feature):
                    await callback.answer()
                    await callback.message.answer(get_access_denied_message(feature))
                    return
                
                # If access is granted, proceed with the original function
                return await func(callback, state, *args, **kwargs)
                
            finally:
                close_session(session)
        
        return wrapper
    return decorator

def start_trial_period(user: User) -> None:
    """
    Start trial period for a user (called during registration completion)
    
    Args:
        user: User object to start trial for
    """
    now = datetime.now()
    user.trial_start_date = now
    user.trial_end_date = now + TRIAL_DURATION
    user.is_premium = False
    user.trial_expired = False
    logger.info(f"Started trial period for user {user.telegram_id}: {user.trial_start_date} - {user.trial_end_date}")

def check_trial_status(user: User) -> Tuple[str, int]:
    """
    Check user's trial status and return status and days remaining
    
    Args:
        user: User object to check
        
    Returns:
        Tuple of (status, days_remaining) where status is:
        - 'premium': User has premium access
        - 'trial_active': Trial is active
        - 'trial_expired': Trial has expired
        - 'no_trial': No trial set (shouldn't happen for registered users)
    """
    if user.is_premium:
        return 'premium', -1
    
    if not user.trial_start_date or not user.trial_end_date:
        return 'no_trial', 0
    
    now = datetime.now()
    
    if now > user.trial_end_date:
        if not user.trial_expired:
            # Mark as expired in database
            session = get_session()
            try:
                db_user = session.query(User).filter(User.telegram_id == user.telegram_id).first()
                if db_user:
                    db_user.trial_expired = True
                    session.commit()
                    # Update the passed user object too
                    user.trial_expired = True
                    logger.info(f"Marked trial as expired for user {user.telegram_id}")
            except Exception as e:
                logger.error(f"Failed to update trial_expired status: {e}")
                session.rollback()
            finally:
                close_session(session)
        return 'trial_expired', 0
    
    days_remaining = (user.trial_end_date - now).days
    return 'trial_active', days_remaining

def has_feature_access(user: User, feature: str) -> bool:
    """
    Check if user has access to a specific feature
    
    Args:
        user: User object to check
        feature: Feature name to check access for
        
    Returns:
        Boolean indicating if user has access
    """
    status, _ = check_trial_status(user)
    
    if status == 'premium':
        return PREMIUM_FEATURES.get(feature, False)
    elif status == 'trial_active':
        return TRIAL_FEATURES.get(feature, False)
    else:  # trial_expired or no_trial
        return EXPIRED_FEATURES.get(feature, False)

def get_trial_warning_message(user: User) -> Optional[str]:
    """
    Get appropriate warning message based on trial status
    
    Args:
        user: User object to check
        
    Returns:
        Warning message string or None if no warning needed
    """
    status, days_remaining = check_trial_status(user)
    
    if status == 'trial_active':
        if days_remaining <= 1:
            return TRIAL_WARNING_1_DAY
        elif days_remaining <= 3:
            return TRIAL_WARNING_3_DAYS
    
    return None

def get_access_denied_message(feature: str) -> str:
    """
    Get message to show when access is denied to a feature
    
    Args:
        feature: Feature name that was denied
        
    Returns:
        Formatted denial message
    """
    return FEATURE_ACCESS_PAYMENT_MESSAGE

def upgrade_to_premium(user_telegram_id: int) -> bool:
    """
    Upgrade user to premium (admin function)
    
    Args:
        user_telegram_id: Telegram ID of user to upgrade
        
    Returns:
        Boolean indicating success
    """
    session = get_session()
    try:
        user = session.query(User).filter(User.telegram_id == user_telegram_id).first()
        if user:
            user.is_premium = True
            user.trial_expired = False
            session.commit()
            logger.info(f"Upgraded user {user_telegram_id} to premium")
            return True
        return False
    except Exception as e:
        logger.error(f"Failed to upgrade user {user_telegram_id} to premium: {e}")
        session.rollback()
        return False
    finally:
        close_session(session)

def get_users_needing_trial_warnings() -> Dict[str, list]:
    """
    Get users who need trial expiry warnings
    
    Returns:
        Dictionary with 'warning_3_days' and 'warning_1_day' lists
    """
    session = get_session()
    result = {'warning_3_days': [], 'warning_1_day': []}
    
    try:
        now = datetime.now()
        three_days_from_now = now + timedelta(days=3)
        one_day_from_now = now + timedelta(days=1)
        
        # Users whose trial expires in 3 days
        users_3_days = session.query(User).filter(
            User.trial_end_date.isnot(None),
            User.trial_end_date >= now,
            User.trial_end_date <= three_days_from_now,
            User.is_premium == False,
            User.trial_expired == False,
            User.registration_complete == True
        ).all()
        
        # Users whose trial expires in 1 day
        users_1_day = session.query(User).filter(
            User.trial_end_date.isnot(None),
            User.trial_end_date >= now,
            User.trial_end_date <= one_day_from_now,
            User.is_premium == False,
            User.trial_expired == False,
            User.registration_complete == True
        ).all()
        
        result['warning_3_days'] = users_3_days
        result['warning_1_day'] = users_1_day
        
    except Exception as e:
        logger.error(f"Failed to get users needing warnings: {e}")
    finally:
        close_session(session)
    
    return result

def check_and_update_expired_trials() -> int:
    """
    Check for expired trials and update database
    
    Returns:
        Number of users whose trials were marked as expired
    """
    session = get_session()
    expired_count = 0
    
    try:
        now = datetime.now()
        
        # Find users with expired trials that haven't been marked as expired yet
        expired_users = session.query(User).filter(
            User.trial_end_date.isnot(None),
            User.trial_end_date < now,
            User.is_premium == False,
            User.trial_expired == False,
            User.registration_complete == True
        ).all()
        
        for user in expired_users:
            user.trial_expired = True
            expired_count += 1
            logger.info(f"Marked trial as expired for user {user.telegram_id}")
        
        if expired_count > 0:
            session.commit()
            logger.info(f"Updated {expired_count} expired trials")
            
    except Exception as e:
        logger.error(f"Failed to update expired trials: {e}")
        session.rollback()
    finally:
        close_session(session)
    
    return expired_count 