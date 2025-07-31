# PsyBot - Telegram Psychological Support Bot

A Telegram bot designed to provide psychological support and guidance to users.

## Setup Instructions

1. **Create a Telegram Bot**:
   - Open Telegram and search for BotFather (@BotFather)
   - Send the command `/newbot`
   - Follow the instructions to create a new bot
   - BotFather will provide you with a token - save this for later

2. **Environment Setup**:
   - Clone this repository
   - Create a virtual environment: `python -m venv venv`
   - Activate the virtual environment:
     - Windows: `venv\Scripts\activate`
     - macOS/Linux: `source venv/bin/activate`
   - Install dependencies: `pip install -r requirements.txt`
   - Copy `.env.example` to `.env` and add your Telegram bot token

3. **Optional: Voice Message Support**:
   - Add Google GenAI API key to `.env` for voice transcription: `GOOGLE_GENAI_API_KEY=your_key`
   - Add voice proxy URL: `VOICE_API_URL=your_voice_proxy_url`
   - See `VOICE_TRANSCRIPTION_SETUP.md` for detailed setup

4. **Database Setup**:
   - Initialize the database: `python src/database/init_db.py`

5. **Run the Bot**:
   - Start both the bot and admin panel: `python run_bot.py`
   - The bot will be available on Telegram
   - The admin panel will be available at `http://localhost:8012`
   - Default admin credentials are in your `.env` file

## Features

- **Telegram Bot**: Emotion diary, thought diary, therapy themes management
- **🎤 Voice Messages**: AI-powered voice transcription using GPT-4o transcription model (optional)
- **Admin Panel**: User management, analytics, system monitoring (http://localhost:8012)
- **Notification System**: Automated emotion diary reminders
- **Therapy Integration**: Session reflections and therapy themes tracking
- **AI Support**: Emotion analysis and therapy recommendations
- **User Management**: Profile creation, timezone handling, preference settings

## License

This project is licensed under the MIT License - see the LICENSE file for details.