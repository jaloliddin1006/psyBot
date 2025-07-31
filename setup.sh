#!/bin/bash

# Create virtual environment
echo "Creating virtual environment..."
python3 -m venv venv

# Activate virtual environment
if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
    source venv/Scripts/activate
else
    source venv/bin/activate
fi

# Install dependencies
echo "Installing dependencies..."
pip3 install -r requirements.txt

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    echo "Creating .env file..."
    cp .env.example .env
    echo "Please edit .env file and add your Telegram bot token."
fi

# Create database directory if it doesn't exist
if [ ! -d database ]; then
    echo "Creating database directory..."
    mkdir -p database
fi

# Initialize database
echo "Initializing database..."
python3 src/database/init_db.py

echo "Setup complete! You can now run the bot with: python3 src/main.py"
echo "Don't forget to set your Telegram bot token in the .env file."