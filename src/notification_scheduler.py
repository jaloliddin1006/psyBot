#!/usr/bin/env python3
"""
Notification Scheduler for PsyBot
Sends emotion diary reminders based on user frequency preferences
"""

import os
import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Dict
from dotenv import load_dotenv
from aiogram import Bot
from src.database.session import get_session, close_session
from src.database.models import User, TherapySession
from timezone_utils import SERVER_UTC_OFFSET
from src.activity_tracker import is_user_actively_interacting

load_dotenv()

# Setup logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", 
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Initialize bot
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
bot = Bot(token=TELEGRAM_BOT_TOKEN)

class NotificationScheduler:
    def __init__(self):
        self.running = False
        self.notification_times = {
            1: ["16:00"],  # 1 time per day - noon
            2: ["12:00", "17:00"],  # 2 times per day - morning and evening
            4: ["12:00", "15:00", "17:00", "20:00"],  # 4 times per day
            6: ["11:00", "13:00", "15:00", "17:00", "19:00", "21:00"]  # 6 times per day
        }
        self.sent_today = {}  # Track sent notifications per user per day
    
    async def send_emotion_diary_reminder(self, user: User) -> bool:
        """Send emotion diary reminder to a specific user"""
        try:
            # Calculate user's local time for personalized messages
            timezone_offset = getattr(user, 'timezone_offset', 0) or 0
            server_time = datetime.now()
            server_utc_time = server_time - timedelta(hours=SERVER_UTC_OFFSET)  # Convert server time to UTC
            user_local_time = server_utc_time + timedelta(hours=timezone_offset)
            current_hour = user_local_time.hour
            
            if 6 <= current_hour < 12:
                greeting = "Доброе утро"
                time_context = "Как начался твой день?"
            elif 12 <= current_hour < 17:
                greeting = "Добрый день"
                time_context = "Как дела в середине дня?"
            elif 17 <= current_hour < 22:
                greeting = "Добрый вечер"
                time_context = "Как прошел твой день?"
            else:
                greeting = "Привет"
                time_context = "Как ты себя чувствуешь?"
            
            message_text = (
                f"{greeting}, {user.full_name}! 🌟\n\n"
                f"Время для дневника эмоций. {time_context}\n\n"
                f"Используй кнопку 'Дневник эмоций' в главном меню чтобы зафиксировать свое состояние.\n\n"
                f"💡 Помни: отслеживание эмоций помогает лучше понимать себя!"
            )
            
            await bot.send_message(
                chat_id=user.telegram_id,
                text=message_text
            )
            
            logger.info(f"Notification sent to {user.full_name} (ID: {user.telegram_id})")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send notification to {user.full_name} (ID: {user.telegram_id}): {e}")
            return False
    
    async def send_weekly_motivation(self, user: User) -> bool:
        """Send weekly motivational message to a specific user"""
        try:
            motivational_messages = [
                f"Привет, {user.full_name}! 🌈\n\nПрошла неделя с тех пор, как ты используешь дневник эмоций. Помни: каждый шаг к пониманию себя — это большое достижение! 💪",
                f"{user.full_name}, ты делаешь важную работу! 🌟\n\nОтслеживание эмоций — это навык, который поможет тебе лучше понимать себя и управлять своим состоянием.",
                f"Привет, {user.full_name}! 🦋\n\nИзменения происходят постепенно. Каждая запись в дневнике эмоций — это инвестиция в твое психологическое здоровье.",
                f"{user.full_name}, помни: нет 'правильных' или 'неправильных' эмоций! 💝\n\nВсе чувства важны и имеют право на существование. Продолжай наблюдать за собой с добротой.",
                f"Привет, {user.full_name}! 🌱\n\nТы растешь и развиваешься каждый день. Дневник эмоций помогает тебе видеть этот прогресс. Продолжай в том же духе!"
            ]
            
            import random
            message_text = random.choice(motivational_messages)
            
            await bot.send_message(
                chat_id=user.telegram_id,
                text=message_text
            )
            
            logger.info(f"Weekly motivation sent to {user.full_name} (ID: {user.telegram_id})")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send weekly motivation to {user.full_name} (ID: {user.telegram_id}): {e}")
            return False

    async def send_reflection_reminder(self, user: User, therapy_session: TherapySession) -> bool:
        """Send reflection reminder to a specific user after their therapy session"""
        try:
            # Session time is already stored in the correct timezone, no conversion needed
            session_formatted = therapy_session.session_datetime.strftime("%d.%m.%Y в %H:%M")
            
            message_text = (
                f"Привет, {user.full_name}! 🌟\n\n"
                f"Прошло 5 часов после твоей встречи с психологом ({session_formatted}). "
                f"Самое время провести рефлексию!\n\n"
                f"Используй команду /reflection или кнопку 'Рефлексия' в главном меню, "
                f"чтобы зафиксировать свои впечатления от сессии.\n\n"
                f"💡 Рефлексия поможет лучше усвоить полученные инсайты и подготовиться к следующей встрече."
            )
            
            await bot.send_message(
                chat_id=user.telegram_id,
                text=message_text
            )
            
            logger.info(f"Reflection reminder sent to {user.full_name} (ID: {user.telegram_id}) "
                       f"for session at {therapy_session.session_datetime}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send reflection reminder to {user.full_name} (ID: {user.telegram_id}): {e}")
            return False

    async def send_weekly_reflection_reminder(self, user: User) -> bool:
        """Send weekly reflection reminder to a specific user"""
        try:
            from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
            
            # Create keyboard with two buttons
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(text="Начать рефлексию", callback_data="weekly_start_reflection"),
                    InlineKeyboardButton(text="Отказаться", callback_data="weekly_decline_reflection")
                ]
            ])
            
            message_text = (
                f"Привет, {user.full_name}! 🌟\n\n"
                f"Воскресный вечер — идеальное время для еженедельной рефлексии!\n\n"
                f"Давайте вместе вспомним хорошие моменты этой недели и подумаем о том, "
                f"что принесло вам радость и благодарность."
            )
            
            await bot.send_message(
                chat_id=user.telegram_id,
                text=message_text,
                reply_markup=keyboard
            )
            
            logger.info(f"Weekly reflection reminder sent to {user.full_name} (ID: {user.telegram_id})")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send weekly reflection reminder to {user.full_name} (ID: {user.telegram_id}): {e}")
            return False
    
    def should_send_notification(self, user: User, server_time: datetime) -> bool:
        """Check if notification should be sent to user at current time"""
        frequency = user.notification_frequency
        
        # Don't send notifications if they are disabled (frequency = 0)
        if frequency == 0 or frequency not in self.notification_times:
            return False
        
        # Calculate user's local time based on their timezone offset
        # timezone_offset is stored as UTC offset, so we need to convert server time to UTC first
        timezone_offset = getattr(user, 'timezone_offset', 0) or 0
        server_utc_time = server_time - timedelta(hours=SERVER_UTC_OFFSET)  # Convert server time to UTC
        user_local_time = server_utc_time + timedelta(hours=timezone_offset)
        user_time_str = user_local_time.strftime("%H:%M")
        
        # Check if user's local time matches any notification time for this frequency
        times_for_frequency = self.notification_times[frequency]
        if user_time_str not in times_for_frequency:
            return False
        
        # Check if we already sent notification to this user today at this time (in user's timezone)
        user_today = user_local_time.strftime("%Y-%m-%d")
        user_key = f"{user.telegram_id}_{user_today}_{user_time_str}"
        
        if user_key in self.sent_today:
            return False
        
        return True
    
    def mark_notification_sent(self, user: User, server_time: datetime):
        """Mark notification as sent for this user today at this time"""
        timezone_offset = getattr(user, 'timezone_offset', 0) or 0
        server_utc_time = server_time - timedelta(hours=SERVER_UTC_OFFSET)  # Convert server time to UTC
        user_local_time = server_utc_time + timedelta(hours=timezone_offset)
        user_today = user_local_time.strftime("%Y-%m-%d")
        user_time_str = user_local_time.strftime("%H:%M")
        user_key = f"{user.telegram_id}_{user_today}_{user_time_str}"
        self.sent_today[user_key] = True
    
    def cleanup_old_tracking(self):
        """Remove tracking data older than 2 days"""
        cutoff_date = (datetime.now() - timedelta(days=2)).strftime("%Y-%m-%d")
        keys_to_remove = []
        
        for key in self.sent_today:
            if key.split("_")[1] < cutoff_date:
                keys_to_remove.append(key)
        
        for key in keys_to_remove:
            del self.sent_today[key]
    
    async def check_and_send_notifications(self):
        """Check all users and send notifications if needed"""
        server_time = datetime.now()
        current_time = server_time.strftime("%H:%M")
        current_day = server_time.strftime("%A")  # Get day of week
        logger.info(f"Checking notifications for server time: {current_time} on {current_day}")
        
        # Check and update expired trials
        from trial_manager import check_and_update_expired_trials
        expired_count = check_and_update_expired_trials()
        if expired_count > 0:
            logger.info(f"Updated {expired_count} expired trials")
        
        session = get_session()
        try:
            # Get all registered users with notifications enabled and valid access
            users = session.query(User).filter(
                User.registration_complete == True,
                User.full_name.isnot(None),
                User.notification_frequency.isnot(None),
                User.notification_frequency > 0,  # Only users with notifications enabled
                User.trial_expired == False  # Exclude users with expired trials
            ).all()
            
            notifications_sent = 0
            motivations_sent = 0
            reflections_sent = 0
            
            for user in users:
                # Calculate user's local time for logging
                timezone_offset = getattr(user, 'timezone_offset', 0) or 0
                server_utc_time = server_time - timedelta(hours=SERVER_UTC_OFFSET)  # Convert server time to UTC
                user_local_time = server_utc_time + timedelta(hours=timezone_offset)
                user_timezone = getattr(user, 'user_timezone', 'UTC+0') or 'UTC+0'
                
                # Check if user is actively interacting before sending emotion diary reminders
                if is_user_actively_interacting(user):
                    logger.debug(f"Skipping notification for {user.full_name} - user is actively interacting")
                    continue
                
                # Send regular emotion diary reminders
                if self.should_send_notification(user, server_time):
                    success = await self.send_emotion_diary_reminder(user)
                    if success:
                        self.mark_notification_sent(user, server_time)
                        notifications_sent += 1
                        logger.info(f"Sent notification to {user.full_name} (local time: {user_local_time.strftime('%H:%M')} {user_timezone})")
                    
                    # Small delay between messages to avoid rate limiting
                    await asyncio.sleep(0.5)
                
                # Send weekly motivational message on Sundays at 10:00 (user's local time)
                user_day = user_local_time.strftime("%A")
                user_time_str = user_local_time.strftime("%H:%M")
                
                if user_day == "Sunday" and user_time_str == "10:00":
                    user_today = user_local_time.strftime("%Y-%m-%d")
                    motivation_key = f"{user.telegram_id}_motivation_{user_today}"
                    
                    if motivation_key not in self.sent_today:
                        success = await self.send_weekly_motivation(user)
                        if success:
                            self.sent_today[motivation_key] = True
                            motivations_sent += 1
                            logger.info(f"Sent weekly motivation to {user.full_name} (local time: {user_local_time.strftime('%H:%M')} {user_timezone})")
                        
                        # Small delay between messages
                        await asyncio.sleep(0.5)
                
                # Send weekly reflection message on Sundays at 17:00 (user's local time)
                if user_day == "Sunday" and user_time_str == "17:00":
                    user_today = user_local_time.strftime("%Y-%m-%d")
                    reflection_key = f"{user.telegram_id}_weekly_reflection_{user_today}"
                    
                    if reflection_key not in self.sent_today:
                        success = await self.send_weekly_reflection_reminder(user)
                        if success:
                            self.sent_today[reflection_key] = True
                            reflections_sent += 1
                            logger.info(f"Sent weekly reflection reminder to {user.full_name} (local time: {user_local_time.strftime('%H:%M')} {user_timezone})")
                        
                        # Small delay between messages
                        await asyncio.sleep(0.5)
            
            # Check for reflection reminders (separate query for efficiency)
            # Look for therapy sessions where reflection_datetime has passed but reflection_sent is False
            pending_reflections = session.query(TherapySession).filter(
                TherapySession.reflection_datetime <= server_time,
                TherapySession.reflection_sent == False
            ).all()
            
            for therapy_session in pending_reflections:
                # Get the user for this session
                user = session.query(User).filter(User.id == therapy_session.user_id).first()
                if user and user.registration_complete:
                    success = await self.send_reflection_reminder(user, therapy_session)
                    if success:
                        # Mark reflection as sent
                        therapy_session.reflection_sent = True
                        session.commit()
                        reflections_sent += 1
                        logger.info(f"Sent reflection reminder to {user.full_name} for session at {therapy_session.session_datetime}")
                    
                    # Small delay between messages
                    await asyncio.sleep(0.5)
            
            if notifications_sent > 0:
                logger.info(f"Sent {notifications_sent} emotion diary notifications at server time {current_time}")
            
            if motivations_sent > 0:
                logger.info(f"Sent {motivations_sent} weekly motivational messages at server time {current_time}")
            
            if reflections_sent > 0:
                logger.info(f"Sent {reflections_sent} reflection reminders at server time {current_time}")
            
        except Exception as e:
            logger.error(f"Error in check_and_send_notifications: {e}")
        finally:
            close_session(session)
    
    async def run_scheduler(self):
        """Main scheduler loop"""
        logger.info("🚀 Notification Scheduler started")
        self.running = True
        
        while self.running:
            try:
                await self.check_and_send_notifications()
                
                # Cleanup old tracking data once per day at midnight
                if datetime.now().strftime("%H:%M") == "00:00":
                    self.cleanup_old_tracking()
                    logger.info("Cleaned up old notification tracking data")
                
                # Wait 1 minute before next check
                await asyncio.sleep(60)
                
            except KeyboardInterrupt:
                logger.info("Scheduler stopped by user")
                break
            except Exception as e:
                logger.error(f"Error in scheduler loop: {e}")
                await asyncio.sleep(60)  # Wait before retrying
    
    def stop(self):
        """Stop the scheduler"""
        self.running = False
        logger.info("Scheduler stop requested")

async def test_notification_times():
    """Test function to show when notifications would be sent"""
    print("📅 Notification Schedule:")
    print("=" * 50)
    
    scheduler = NotificationScheduler()
    
    for frequency, times in scheduler.notification_times.items():
        print(f"\n{frequency}x per day: {', '.join(times)}")
    
    print(f"\nCurrent time: {datetime.now().strftime('%H:%M')}")
    
    # Show which frequencies would trigger now
    current_time = datetime.now().strftime("%H:%M")
    active_frequencies = []
    
    for frequency, times in scheduler.notification_times.items():
        if current_time in times:
            active_frequencies.append(frequency)
    
    if active_frequencies:
        print(f"🔔 Notifications would be sent now for frequencies: {active_frequencies}")
    else:
        print("🔕 No notifications scheduled for current time")

async def main():
    """Main function with options"""
    print("🤖 Notification Scheduler")
    print("=" * 30)
    
    while True:
        print("\nOptions:")
        print("1. Show notification schedule")
        print("2. Run scheduler (continuous)")
        print("3. Test single notification check")
        print("4. Exit")
        
        choice = input("\nEnter your choice (1-4): ").strip()
        
        if choice == "1":
            await test_notification_times()
        elif choice == "2":
            scheduler = NotificationScheduler()
            try:
                await scheduler.run_scheduler()
            except KeyboardInterrupt:
                scheduler.stop()
                print("\nScheduler stopped.")
        elif choice == "3":
            scheduler = NotificationScheduler()
            await scheduler.check_and_send_notifications()
        elif choice == "4":
            print("Goodbye! 👋")
            break
        else:
            print("Invalid choice. Please try again.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nExiting... 👋") 