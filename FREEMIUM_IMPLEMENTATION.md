# PsyBot Freemium Implementation

## Overview

PsyBot now includes a freemium model where newly registered users receive a **2-week trial period** with full access to all features. After the trial expires, users need to upgrade to premium to continue using the bot.

## Features

### Trial Period
- **Duration**: 14 days (configurable via `TRIAL_DURATION_DAYS` environment variable)
- **Start**: Automatically begins when user completes registration
- **Full Access**: During trial, users have access to all bot features
- **Warnings**: Users receive notifications 3 days and 1 day before expiry
- **Expiry**: After trial expires, bot functionality is blocked

### User Status Types
1. **Trial Active**: User is within their 14-day trial period
2. **Trial Expired**: User's trial has ended, access is blocked
3. **Premium**: User has been upgraded to premium access (unlimited)

### Access Control
- All main bot features check trial status before allowing access
- Expired users receive a premium upgrade message when trying to use features
- Notifications are disabled for users with expired trials
- Admin panel shows trial status and allows manual upgrades

## Configuration

### Environment Variables
```bash
# Trial duration in days (default: 14)
TRIAL_DURATION_DAYS=14
```

### Freemium Settings
File: `src/freemium_config.py`
- Trial duration configuration
- Feature access permissions
- Expiry warning messages
- Premium upgrade messages

## Database Schema

### New User Fields
```sql
-- When user's trial started
trial_start_date DATETIME

-- When user's trial expires  
trial_end_date DATETIME

-- Whether user has premium access
is_premium BOOLEAN DEFAULT FALSE

-- Whether trial has expired and user is blocked
trial_expired BOOLEAN DEFAULT FALSE
```

## Implementation Details

### Registration Process
1. User completes standard registration flow
2. `start_trial_period()` is called automatically
3. Trial start/end dates are set
4. User receives welcome message mentioning 2-week trial

### Access Control Flow
1. Each feature handler checks `has_feature_access(user, feature)`
2. Trial manager checks user's trial status
3. If access denied, user sees premium upgrade message
4. Premium users and active trial users get full access

### Trial Status Checking
```python
from trial_manager import check_trial_status

status, days_remaining = check_trial_status(user)
# status: 'premium', 'trial_active', 'trial_expired', 'no_trial'
# days_remaining: number of days left (if applicable)
```

### Feature Access Checking
```python
from trial_manager import has_feature_access

if has_feature_access(user, 'emotion_diary'):
    # Allow access to emotion diary
else:
    # Show upgrade message
```

## Admin Panel Features

### User Management
- **Trial Status Column**: Shows current trial status with visual indicators
- **Premium Upgrade**: One-click upgrade to premium for any user
- **Premium Revoke**: Remove premium access (reverts to trial status)
- **Visual Indicators**:
  - 🏆 Premium users
  - ⏰ Active trial (with days remaining)
  - ⚠️ Trial ending soon (≤3 days)
  - 🚫 Expired trial

### API Endpoints
```
POST /api/user/{user_id}/upgrade-premium
POST /api/user/{user_id}/revoke-premium
```

## Notification System Updates

### Trial Management
- Notification scheduler checks and updates expired trials
- Expired trial users are excluded from notifications
- Trial warning notifications sent automatically

### Warning Schedule
- **3 days before expiry**: Warning message about upcoming expiry
- **1 day before expiry**: Final warning message
- **On expiry**: Access is blocked, upgrade message shown

## Migration

### For Existing Installations
1. Run the migration script:
   ```bash
   python migrate_trial_fields.py
   ```
2. This adds trial fields to existing users
3. Existing registered users get 14-day trials from their registration date
4. Restart the bot to activate freemium features

### What the Migration Does
- Adds 4 new columns to users table
- Sets up trial periods for existing registered users
- Marks trials as expired if registration was >14 days ago
- Preserves all existing user data

## User Experience

### New User Journey
1. **Registration**: Standard flow with trial period notification
2. **Usage**: Full access to all features for 14 days
3. **Warnings**: Automatic notifications at 3 days and 1 day remaining
4. **Expiry**: Bot shows upgrade message and blocks feature access
5. **Upgrade**: Contact admin for premium access

### Trial Status Visibility
- Main menu shows trial status: "🎯 Пробный период: осталось X дней"
- Premium users see: "⭐ Премиум-доступ активен"
- Registration message mentions 2-week trial period

### Blocked Feature Experience
When trial expires, users see:
```
🔒 Пробный период завершен

Ваш 2-недельный пробный период использования PsyBot истек.

Чтобы продолжить использование всех функций бота, 
необходимо оформить подписку.

🌟 Что включает премиум-доступ:
• Безлимитный доступ к дневнику эмоций
• Развернутая аналитика настроения  
• Персональные рекомендации
• Неограниченное количество тем для терапии
• Все техники релаксации
• Приоритетная поддержка

📞 Для оформления подписки свяжитесь с нами: @support_username
```

## Code Structure

### Core Files
- `src/freemium_config.py` - Configuration and messages
- `src/trial_manager.py` - Trial management utilities
- `src/database/models.py` - Updated User model with trial fields
- `src/handlers/main_menu.py` - Updated with access control
- `migrate_trial_fields.py` - Database migration script

### Key Functions
- `start_trial_period(user)` - Initialize trial for new user
- `check_trial_status(user)` - Get current trial status
- `has_feature_access(user, feature)` - Check feature access
- `upgrade_to_premium(telegram_id)` - Admin upgrade function
- `check_and_update_expired_trials()` - Batch trial expiry check

## Testing

### Manual Testing Checklist
- [ ] New user registration creates trial period
- [ ] Trial countdown shows in main menu
- [ ] Feature access works during trial
- [ ] Feature access blocked after trial expiry
- [ ] Admin panel shows correct trial status
- [ ] Premium upgrade works via admin panel
- [ ] Trial warning notifications sent correctly
- [ ] Expired users excluded from regular notifications

### Database Verification
```sql
-- Check trial setup
SELECT telegram_id, full_name, trial_start_date, trial_end_date, 
       is_premium, trial_expired, registration_complete
FROM users 
WHERE registration_complete = 1;

-- Check trial status distribution
SELECT 
  COUNT(*) as total,
  SUM(CASE WHEN is_premium = 1 THEN 1 ELSE 0 END) as premium,
  SUM(CASE WHEN trial_expired = 1 THEN 1 ELSE 0 END) as expired,
  SUM(CASE WHEN trial_expired = 0 AND is_premium = 0 AND trial_end_date > datetime('now') THEN 1 ELSE 0 END) as active_trial
FROM users 
WHERE registration_complete = 1;
```

## Troubleshooting

### Common Issues

**Users not getting trials**
- Check if migration was run
- Verify `start_trial_period()` is called in registration
- Check database for trial_start_date values

**Access control not working**
- Verify imports of trial_manager in handlers
- Check trial_expired field updates
- Ensure feature names match freemium_config.py

**Admin panel not showing trial status**
- Check if trial fields exist in database
- Verify template has trial status column
- Check for JavaScript errors in browser console

**Notifications still being sent to expired users**
- Check notification scheduler filter query
- Verify trial_expired field is being updated
- Check scheduler logs for expired trial updates

### Logs to Monitor
```
# Trial period starts
"Started trial period for user {telegram_id}: {start} - {end}"

# Trial expires
"Marked trial as expired for user {telegram_id}"

# Access denied
"Feature access denied for expired user {telegram_id}"

# Premium upgrade
"Upgraded user {telegram_id} to premium"
```

## Future Enhancements

### Potential Features
- **Payment Integration**: Automatic premium upgrades via payment
- **Trial Extensions**: Admin ability to extend trial periods
- **Usage Analytics**: Track feature usage during trials
- **A/B Testing**: Different trial lengths for optimization
- **Referral System**: Trial extensions for referrals
- **Grace Period**: Limited access for few days after expiry

### Configuration Improvements
- Trial duration per user type
- Feature-specific trial periods
- Graduated access reduction
- Custom trial messages per user

## Support

For issues with the freemium implementation:
1. Check the troubleshooting section above
2. Review logs for error messages
3. Verify database migration completed successfully
4. Test with a fresh user registration
5. Check admin panel functionality

The freemium model is designed to be non-disruptive to existing users while providing a clear upgrade path for continued access to PsyBot's features. 