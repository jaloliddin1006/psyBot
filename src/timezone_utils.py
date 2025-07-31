#!/usr/bin/env python3
"""
Timezone utility functions for PsyBot
"""

import logging
from typing import Tuple, Optional

logger = logging.getLogger(__name__)

# Server timezone configuration
SERVER_UTC_OFFSET = 3  # Server is in UTC+3

def calculate_timezone_offset(user_time_str: str, server_time_str: str, server_utc_offset: int = SERVER_UTC_OFFSET) -> Tuple[Optional[int], Optional[str], Optional[str]]:
    """
    Calculate timezone offset based on user's local time and server time.
    
    Args:
        user_time_str: User's local time in HH:MM format
        server_time_str: Server time in HH:MM format
        server_utc_offset: Server's UTC offset in hours (default: SERVER_UTC_OFFSET)
    
    Returns:
        Tuple of (timezone_offset, user_timezone_string, error_message)
        If successful: (offset_hours, "UTC+X", None)
        If error: (None, None, error_message)
    """
    try:
        # Parse user's time
        user_hour, user_minute = map(int, user_time_str.split(':'))
        
        # Validate time format
        if not (0 <= user_hour <= 23 and 0 <= user_minute <= 59):
            return None, None, "Неверный формат времени! Часы должны быть от 0 до 23, минуты от 0 до 59."
        
        # Parse server time
        server_hour, server_minute = map(int, server_time_str.split(':'))
        
        # Calculate timezone offset
        user_total_minutes = user_hour * 60 + user_minute
        server_total_minutes = server_hour * 60 + server_minute
        
        # Calculate difference in minutes
        diff_minutes = user_total_minutes - server_total_minutes
        
        # Handle day boundary crossings
        if diff_minutes > 12 * 60:  # More than 12 hours ahead
            diff_minutes -= 24 * 60  # User is actually behind (previous day)
        elif diff_minutes < -12 * 60:  # More than 12 hours behind
            diff_minutes += 24 * 60  # User is actually ahead (next day)
        
        # Convert to hours and round
        raw_offset = round(diff_minutes / 60)
        
        # Adjust for server's UTC offset to get user's actual UTC offset
        timezone_offset = raw_offset + server_utc_offset
        
        # Clamp to valid timezone range (-12 to +14)
        timezone_offset = max(-12, min(14, timezone_offset))
        
        # Create user-friendly timezone string
        if timezone_offset >= 0:
            user_timezone = f"UTC+{timezone_offset}"
        else:
            user_timezone = f"UTC{timezone_offset}"  # Already has minus sign
        
        logger.info(f"Calculated timezone: user_time={user_time_str}, server_time={server_time_str}, server_utc_offset={server_utc_offset}, raw_offset={raw_offset}, final_offset={timezone_offset}, timezone={user_timezone}")
        
        return timezone_offset, user_timezone, None
        
    except (ValueError, IndexError) as e:
        error_msg = "Неверный формат времени! Пожалуйста, введите время в формате ЧЧ:ММ (например: 16:54, 09:30, 23:15)"
        logger.error(f"Error calculating timezone offset: user_time={user_time_str}, server_time={server_time_str}, error={e}")
        return None, None, error_msg

def validate_time_format(time_str: str) -> bool:
    """
    Validate if time string is in correct HH:MM format.
    
    Args:
        time_str: Time string to validate
    
    Returns:
        True if valid, False otherwise
    """
    try:
        if ':' not in time_str:
            return False
        
        parts = time_str.split(':')
        if len(parts) != 2:
            return False
        
        hour, minute = map(int, parts)
        return 0 <= hour <= 23 and 0 <= minute <= 59
        
    except (ValueError, IndexError):
        return False

def format_timezone_display(timezone_offset: int) -> str:
    """
    Format timezone offset as user-friendly string.
    
    Args:
        timezone_offset: Offset in hours from UTC
    
    Returns:
        Formatted timezone string (e.g., "UTC+3", "UTC-5")
    """
    if timezone_offset >= 0:
        return f"UTC+{timezone_offset}"
    else:
        return f"UTC{timezone_offset}"  # Already has minus sign 