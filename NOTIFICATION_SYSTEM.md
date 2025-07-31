# PsyBot Notification System

## Overview

The PsyBot notification system sends automated reminders to users based on their preferences stored in the database. The system includes emotion diary reminders and weekly motivational messages.

## Features

### 🔔 Emotion Diary Notifications
- **Frequency Options**: 1, 2, 4, or 6 times per day
- **Personalized Messages**: Time-based greetings (morning, afternoon, evening)
- **Smart Scheduling**: Prevents duplicate notifications on the same day
- **User Control**: Users can enable/disable notifications anytime

### 🌟 Weekly Motivational Messages
- **Schedule**: Every Sunday at 10:00 AM
- **Content**: Rotating motivational messages about emotional awareness
- **Personalized**: Uses user's name and encouraging language

### ⚙️ User Preferences
- **Database Storage**: Notification preferences stored in user profile
- **Easy Management**: `/notify` command for changing settings
- **Instant Updates**: Changes take effect immediately

## Notification Schedule

### Daily Emotion Diary Reminders

| Frequency | Times |
|-----------|-------|
| 1x per day | 12:00 |
| 2x per day | 10:00, 18:00 |
| 4x per day | 09:00, 13:00, 17:00, 21:00 |
| 6x per day | 08:00, 11:00, 14:00, 17:00, 20:00, 22:00 |

### Weekly Motivational Messages
- **Day**: Sunday
- **Time**: 10:00 AM
- **Recipients**: All users with notifications enabled

## User Commands

### `/notify` - Manage Notification Settings
Users can:
- Set notification frequency (1, 2, 4, or 6 times per day)
- Disable notifications completely
- View current settings
- Return to main menu

## Technical Implementation

### Architecture
```
main.py
├── Bot Polling (main thread)
└── NotificationScheduler (background task)
    ├── Emotion Diary Reminders
    ├── Weekly Motivational Messages
    └── Duplicate Prevention System
```

### Database Integration
- **User Model**: `notification_frequency` field stores user preferences
- **Query Optimization**: Only queries users with notifications enabled
- **Session Management**: Proper database session handling

### Error Handling
- **Graceful Failures**: Individual notification failures don't stop the system
- **Logging**: Comprehensive logging for monitoring and debugging
- **Rate Limiting**: Delays between messages to avoid Telegram limits

## Running the System

### Option 1: Integrated with Bot (Recommended)
```bash
python run_bot.py
```
This starts both the bot and notification scheduler together.

### Option 2: Standalone Scheduler
```bash
cd src
python notification_scheduler.py
```
This runs only the notification scheduler (for testing).

### Option 3: Testing
```bash
python test_notifications.py
```
This runs the test suite for the notification system.

## Configuration

### Environment Variables
- `TELEGRAM_BOT_TOKEN`: Required for sending notifications
- `DATABASE_URL`: Database connection string

### Notification Times
Modify `notification_times` in `NotificationScheduler` class to change schedule:

```python
self.notification_times = {
    1: ["12:00"],  # 1 time per day
    2: ["10:00", "18:00"],  # 2 times per day
    # ... etc
}
```

## Monitoring

### Logs
- **Location**: `psybot.log` (when using `run_bot.py`)
- **Level**: INFO level includes notification sending events
- **Format**: Timestamp, logger name, level, message

### Key Log Messages
- `🚀 Notification Scheduler started`
- `Notification sent to {user} (ID: {id})`
- `Sent {count} notifications at {time}`
- `Weekly motivation sent to {user}`

## User Experience

### Registration Flow
1. User completes registration with `/start`
2. System asks for notification frequency preference
3. User selects desired frequency (1, 2, 4, or 6 times per day)
4. Notifications begin at next scheduled time

### Notification Management
1. User sends `/notify` command
2. System shows current settings and options
3. User selects new frequency or disables notifications
4. System confirms changes and updates schedule

### Message Examples

#### Emotion Diary Reminder (Morning)
```
Доброе утро, Анна! 🌟

Время для дневника эмоций. Как начался твой день?

Используй кнопку 'Дневник эмоций' в главном меню чтобы зафиксировать свое состояние.

💡 Помни: отслеживание эмоций помогает лучше понимать себя!
```

#### Weekly Motivation
```
Привет, Анна! 🌈

Прошла неделя с тех пор, как ты используешь дневник эмоций. Помни: каждый шаг к пониманию себя — это большое достижение! 💪
```

## Troubleshooting

### Common Issues

1. **Notifications not sending**
   - Check bot token is valid
   - Verify user has notifications enabled (`notification_frequency > 0`)
   - Check logs for error messages

2. **Duplicate notifications**
   - System prevents duplicates automatically
   - Check `sent_today` tracking in logs

3. **Wrong timing**
   - Verify server timezone
   - Check `notification_times` configuration

### Debug Commands
```bash
# Test notification system
python test_notifications.py

# Check user settings
python -c "
import sys; sys.path.append('src')
from database.session import get_session
from database.models import User
session = get_session()
users = session.query(User).filter(User.notification_frequency.isnot(None)).all()
for u in users: print(f'{u.full_name}: {u.notification_frequency}x/day')
"
```

## Future Enhancements

### Potential Features
- **Custom Timing**: Allow users to set custom notification times
- **Timezone Support**: Handle different user timezones
- **Notification Types**: Add different types of reminders (breathing exercises, etc.)
- **Analytics**: Track notification engagement and effectiveness
- **Smart Scheduling**: AI-powered optimal timing based on user activity

### Database Extensions
```sql
-- Potential future columns
ALTER TABLE users ADD COLUMN timezone VARCHAR(50);
ALTER TABLE users ADD COLUMN custom_notification_times TEXT;
ALTER TABLE users ADD COLUMN last_notification_interaction DATETIME;
``` 