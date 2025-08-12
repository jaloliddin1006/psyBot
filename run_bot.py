#!/usr/bin/env python3
"""
Startup script for PsyBot with integrated notification scheduler and admin panel
"""

import asyncio
import sys
import os
import signal
import logging
import threading
from pathlib import Path

# Add src directory to path
# sys.path.append('src')

from src.main import main

def setup_logging():
    """Setup logging configuration"""
    logging.basicConfig(
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        level=logging.INFO,
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('psybot.log', encoding='utf-8')
        ]
    )

def signal_handler(signum, frame):
    """Handle shutdown signals"""
    print(f"\n🛑 Received signal {signum}. Shutting down gracefully...")
    sys.exit(0)

def start_admin_panel():
    """Start the admin panel in a separate thread"""
    try:
        # Change to src directory for admin panel
        original_cwd = os.getcwd()
        src_dir = Path(__file__).parent / "src"
        os.chdir(src_dir)
        
        # Import admin panel
        from admin_panel import app, create_admin_user
        
        print("🌐 Starting Admin Panel...")
        create_admin_user()
        print("🌐 Admin panel will be available at: http://localhost:8012")
        print("🔐 Use your configured admin credentials to login")
        
        # Start Flask app
        app.run(host='0.0.0.0', port=8012, debug=False, use_reloader=False)
        
    except ImportError as e:
        print(f"❌ Admin panel import error: {e}")
        print("Make sure admin panel dependencies are installed")
    except Exception as e:
        print(f"❌ Error starting admin panel: {e}")
    finally:
        # Restore original working directory
        os.chdir(original_cwd)

if __name__ == "__main__":
    # Setup logging
    setup_logging()
    
    # Setup signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    print("🚀 Starting PsyBot with Admin Panel and Notification System...")
    print("=" * 60)
    print("Features enabled:")
    print("✅ Telegram Bot")
    print("✅ Admin Panel (http://localhost:8012)")
    print("✅ Emotion Diary Notifications")
    print("✅ Weekly Motivational Messages")
    print("✅ User Preference Management")
    print("✅ Therapy Themes Management")
    print("=" * 60)
    print("Press Ctrl+C to stop both services")
    print()
    
    try:
        # Start admin panel in a separate thread
        admin_thread = threading.Thread(target=start_admin_panel, daemon=True)
        admin_thread.start()
        
        # Give admin panel a moment to start
        import time
        time.sleep(2)
        
        # Run the main bot function which includes the notification scheduler
        asyncio.run(main())
        
    except KeyboardInterrupt:
        print("\n🛑 Services stopped by user")
    except Exception as e:
        print(f"❌ Error running services: {e}")
        logging.error(f"Error running services: {e}")
        sys.exit(1) 