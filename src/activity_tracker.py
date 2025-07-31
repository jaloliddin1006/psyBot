#!/usr/bin/env python3
"""
Activity Tracker for PsyBot
Tracks user interactions to prevent notifications during active sessions
"""

import logging
from datetime import datetime, timedelta
from typing import Union
from aiogram import types
from database.models import User
from database.session import get_session, close_session

logger = logging.getLogger(__name__)

# Time threshold for considering a user as "actively interacting"
ACTIVE_INTERACTION_THRESHOLD = timedelta(minutes=15)  # 15 minutes

def update_user_activity(user_id: int) -> None:
    """
    Update the last activity timestamp for a user
    
    Args:
        user_id: Telegram user ID
    """
    session = get_session()
    try:
        db_user = session.query(User).filter(User.telegram_id == user_id).first()
        if db_user:
            db_user.last_activity = datetime.now()
            session.commit()
            logger.debug(f"Updated last activity for user {user_id}")
    except Exception as e:
        logger.error(f"Failed to update activity for user {user_id}: {e}")
        session.rollback()
    finally:
        close_session(session)

def is_user_actively_interacting(user: User) -> bool:
    """
    Check if a user is currently actively interacting with the bot
    
    Args:
        user: User object to check
        
    Returns:
        True if user has interacted within the threshold, False otherwise
    """
    if not user.last_activity:
        return False
    
    time_since_activity = datetime.now() - user.last_activity
    return time_since_activity <= ACTIVE_INTERACTION_THRESHOLD

def activity_middleware(handler):
    """
    Middleware decorator to automatically track user activity
    
    Args:
        handler: The handler function to wrap
        
    Returns:
        Wrapped handler that tracks activity
    """
    async def wrapper(update: Union[types.Message, types.CallbackQuery], *args, **kwargs):
        # Extract user ID from either message or callback query
        if isinstance(update, types.Message):
            user_id = update.from_user.id
        elif isinstance(update, types.CallbackQuery):
            user_id = update.from_user.id
        else:
            # If it's some other type, just run the handler
            return await handler(update, *args, **kwargs)
        
        # Update activity before processing
        update_user_activity(user_id)
        
        # Call the original handler
        return await handler(update, *args, **kwargs)
    
    return wrapper 