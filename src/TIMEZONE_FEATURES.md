# Timezone Features Documentation

## Overview

The PsyBot now supports user-specific timezones for personalized notification scheduling. Users can set their timezone during registration and change it later through notification settings.

## Features Added

### 1. Database Changes
- Added `timezone_offset` field (INTEGER) - stores offset from server time in hours
- Added `user_timezone` field (STRING) - stores user-friendly timezone string (e.g., "UTC+3", "UTC-5")

### 2. Registration Flow
- After age input, users are asked for their current local time
- Bot automatically calculates timezone offset based on server time vs user time
- User's timezone is stored and used for all future notifications

### 3. Notification Scheduler Updates
- Notifications are now sent based on user's local time, not server time
- Each user receives notifications at the correct time for their timezone
- Weekly motivational messages are also timezone-aware

### 4. Notification Settings
- Users can change their timezone through `/notify` command
- New "🌍 Изменить часовой пояс" button in notification settings
- Users enter their current time, bot calculates new timezone automatically
- Timezone information is displayed in notification settings

## Technical Implementation

### Timezone Calculation
```python
# Calculate user's local time
timezone_offset = getattr(user, 'timezone_offset', 0) or 0
user_local_time = server_time + timedelta(hours=timezone_offset)

# Server timezone configuration (UTC+3)
from timezone_utils import calculate_timezone_offset
offset, tz_string, error = calculate_timezone_offset(user_time, server_time)
```

### Notification Scheduling
- Server checks all users every minute
- For each user, calculates their local time
- Sends notification if user's local time matches scheduled notification times
- Tracks sent notifications per user per day in their timezone

### Database Migration
Run the migration script to add timezone fields to existing databases:
```bash
python src/database/migrate_add_timezone.py
```

## User Experience

### Registration Flow
1. User enters age
2. **NEW**: User enters their current local time (HH:MM format)
3. Bot calculates timezone offset automatically
4. User selects notification frequency
5. Registration completes

### Notification Settings
- `/notify` command shows current timezone and frequency
- Users can change timezone by entering their current time
- Bot automatically calculates new timezone offset
- Confirmation message shows new timezone

### Notifications
- Emotion diary reminders arrive at user's local time
- Greeting messages are personalized based on user's local time of day
- Weekly motivational messages on Sundays at 10:00 AM user's local time

## Testing

Use the test script to verify timezone functionality:
```bash
python src/test_timezone.py
```

This will test:
- Timezone offset calculations
- Notification scheduler logic
- Database timezone field access

## Configuration

### Server Timezone
- Server is configured for UTC+3 timezone
- This is set in `src/timezone_utils.py` as `SERVER_UTC_OFFSET = 3`
- Change this value if your server is in a different timezone

## Migration Notes

- Existing users will have `timezone_offset = 0` and `user_timezone = None`
- They can update their timezone through `/notify` command
- No data loss occurs during migration
- Backward compatibility maintained 