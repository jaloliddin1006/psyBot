#!/usr/bin/env python3
"""
Test script for PsyBot notification system
"""

import asyncio
import sys
import os
from datetime import datetime

# Add src directory to path
sys.path.append('src')

from src.notification_scheduler import NotificationScheduler
from src.database.session import get_session, close_session
from src.database.models import User

async def test_notification_system():
    """Test the notification system"""
    print("🧪 Testing PsyBot Notification System")
    print("=" * 50)
    
    # Initialize scheduler
    scheduler = NotificationScheduler()
    
    # Show current notification schedule
    print("\n📅 Notification Schedule:")
    for frequency, times in scheduler.notification_times.items():
        print(f"  {frequency}x per day: {', '.join(times)}")
    
    current_time = datetime.now().strftime("%H:%M")
    current_day = datetime.now().strftime("%A")
    print(f"\n🕐 Current time: {current_time} ({current_day})")
    
    # Check which frequencies would trigger now
    active_frequencies = []
    for frequency, times in scheduler.notification_times.items():
        if current_time in times:
            active_frequencies.append(frequency)
    
    if active_frequencies:
        print(f"🔔 Notifications would be sent now for frequencies: {active_frequencies}")
    else:
        print("🔕 No notifications scheduled for current time")
    
    # Check database for users
    session = get_session()
    try:
        total_users = session.query(User).count()
        registered_users = session.query(User).filter(
            User.registration_complete == True,
            User.full_name.isnot(None)
        ).count()
        
        users_with_notifications = session.query(User).filter(
            User.registration_complete == True,
            User.full_name.isnot(None),
            User.notification_frequency.isnot(None),
            User.notification_frequency > 0
        ).count()
        
        print(f"\n👥 Database Statistics:")
        print(f"  Total users: {total_users}")
        print(f"  Registered users: {registered_users}")
        print(f"  Users with notifications enabled: {users_with_notifications}")
        
        # Show notification frequency distribution
        if users_with_notifications > 0:
            print(f"\n📊 Notification Frequency Distribution:")
            for freq in [1, 2, 4, 6]:
                count = session.query(User).filter(
                    User.registration_complete == True,
                    User.notification_frequency == freq
                ).count()
                if count > 0:
                    print(f"  {freq}x per day: {count} users")
            
            disabled_count = session.query(User).filter(
                User.registration_complete == True,
                User.notification_frequency == 0
            ).count()
            if disabled_count > 0:
                print(f"  Disabled: {disabled_count} users")
    
    finally:
        close_session(session)
    
    print(f"\n🔧 Test Options:")
    print("1. Run single notification check")
    print("2. Show detailed user list")
    print("3. Send example notification to user")
    print("4. Exit")
    
    while True:
        choice = input("\nEnter your choice (1-4): ").strip()
        
        if choice == "1":
            print("\n🔄 Running notification check...")
            await scheduler.check_and_send_notifications()
            print("✅ Check completed!")
            
        elif choice == "2":
            session = get_session()
            try:
                users = session.query(User).filter(
                    User.registration_complete == True,
                    User.full_name.isnot(None)
                ).all()
                
                if users:
                    print(f"\n👤 Registered Users:")
                    for user in users:
                        freq = user.notification_frequency or 0
                        status = "enabled" if freq > 0 else "disabled"
                        print(f"  {user.full_name} (ID: {user.telegram_id}) - {freq}x/day ({status})")
                else:
                    print("\n❌ No registered users found")
            finally:
                close_session(session)
                
        elif choice == "3":
            # Send example notification to a specific user
            session = get_session()
            try:
                users = session.query(User).filter(
                    User.registration_complete == True,
                    User.full_name.isnot(None)
                ).all()
                
                if not users:
                    print("\n❌ No registered users found")
                    continue
                
                print(f"\n👤 Available Users:")
                for i, user in enumerate(users, 1):
                    freq = user.notification_frequency or 0
                    status = "enabled" if freq > 0 else "disabled"
                    print(f"  {i}. {user.full_name} (ID: {user.telegram_id}) - {freq}x/day ({status})")
                
                try:
                    user_choice = input(f"\nSelect user (1-{len(users)}) or 'b' to go back: ").strip()
                    
                    if user_choice.lower() == 'b':
                        continue
                    
                    user_index = int(user_choice) - 1
                    if 0 <= user_index < len(users):
                        selected_user = users[user_index]
                        
                        print(f"\n📨 Notification Options for {selected_user.full_name}:")
                        print("1. Emotion diary reminder")
                        print("2. Weekly motivational message")
                        print("3. Both")
                        
                        notif_choice = input("Select notification type (1-3): ").strip()
                        
                        if notif_choice == "1":
                            print(f"\n📤 Sending emotion diary reminder to {selected_user.full_name}...")
                            success = await scheduler.send_emotion_diary_reminder(selected_user)
                            if success:
                                print("✅ Emotion diary reminder sent successfully!")
                            else:
                                print("❌ Failed to send emotion diary reminder")
                                
                        elif notif_choice == "2":
                            print(f"\n📤 Sending weekly motivation to {selected_user.full_name}...")
                            success = await scheduler.send_weekly_motivation(selected_user)
                            if success:
                                print("✅ Weekly motivation sent successfully!")
                            else:
                                print("❌ Failed to send weekly motivation")
                                
                        elif notif_choice == "3":
                            print(f"\n📤 Sending both notifications to {selected_user.full_name}...")
                            
                            # Send emotion diary reminder
                            success1 = await scheduler.send_emotion_diary_reminder(selected_user)
                            await asyncio.sleep(1)  # Small delay between messages
                            
                            # Send weekly motivation
                            success2 = await scheduler.send_weekly_motivation(selected_user)
                            
                            if success1 and success2:
                                print("✅ Both notifications sent successfully!")
                            elif success1:
                                print("⚠️ Emotion diary reminder sent, but weekly motivation failed")
                            elif success2:
                                print("⚠️ Weekly motivation sent, but emotion diary reminder failed")
                            else:
                                print("❌ Both notifications failed")
                        else:
                            print("❌ Invalid choice")
                    else:
                        print("❌ Invalid user selection")
                        
                except ValueError:
                    print("❌ Invalid input. Please enter a number.")
                    
            finally:
                close_session(session)
                
        elif choice == "4":
            print("👋 Goodbye!")
            break
        else:
            print("❌ Invalid choice. Please try again.")

if __name__ == "__main__":
    try:
        asyncio.run(test_notification_system())
    except KeyboardInterrupt:
        print("\n\n👋 Test interrupted by user") 