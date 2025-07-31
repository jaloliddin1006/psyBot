#!/bin/bash

# PsyBot Background Starter Script
# This script starts the bot in the background and keeps it running

BOT_DIR="/home/psyBot"
VENV_PATH="$BOT_DIR/venv"
LOG_FILE="$BOT_DIR/psybot.log"
PID_FILE="$BOT_DIR/psybot.pid"

cd "$BOT_DIR"

# Function to start the bot
start_bot() {
    echo "Starting PsyBot..."
    
    # Check if bot is already running
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if ps -p "$PID" > /dev/null 2>&1; then
            echo "Bot is already running with PID $PID"
            return 1
        else
            echo "Removing stale PID file"
            rm -f "$PID_FILE"
        fi
    fi
    
    # Activate virtual environment and start bot
    source "$VENV_PATH/bin/activate"
    nohup python run_bot.py > "$LOG_FILE" 2>&1 &
    
    # Save PID
    echo $! > "$PID_FILE"
    echo "Bot started with PID $(cat $PID_FILE)"
    echo "Log file: $LOG_FILE"
    echo "To stop the bot, run: ./start_background.sh stop"
}

# Function to stop the bot
stop_bot() {
    echo "Stopping PsyBot..."
    
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if ps -p "$PID" > /dev/null 2>&1; then
            kill "$PID"
            echo "Bot stopped (PID $PID)"
            rm -f "$PID_FILE"
        else
            echo "Bot is not running"
            rm -f "$PID_FILE"
        fi
    else
        echo "PID file not found. Bot may not be running."
    fi
}

# Function to check bot status
status_bot() {
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if ps -p "$PID" > /dev/null 2>&1; then
            echo "Bot is running with PID $PID"
            echo "Log file: $LOG_FILE"
            echo "Last 10 lines of log:"
            tail -n 10 "$LOG_FILE"
        else
            echo "Bot is not running (stale PID file)"
            rm -f "$PID_FILE"
        fi
    else
        echo "Bot is not running"
    fi
}

# Function to restart the bot
restart_bot() {
    stop_bot
    sleep 2
    start_bot
}

# Function to show logs
show_logs() {
    if [ -f "$LOG_FILE" ]; then
        echo "Showing last 50 lines of log file:"
        tail -n 50 "$LOG_FILE"
        echo ""
        echo "To follow logs in real-time, run: tail -f $LOG_FILE"
    else
        echo "Log file not found"
    fi
}

# Main script logic
case "$1" in
    start)
        start_bot
        ;;
    stop)
        stop_bot
        ;;
    restart)
        restart_bot
        ;;
    status)
        status_bot
        ;;
    logs)
        show_logs
        ;;
    *)
        echo "Usage: $0 {start|stop|restart|status|logs}"
        echo ""
        echo "Commands:"
        echo "  start   - Start the bot in background"
        echo "  stop    - Stop the bot"
        echo "  restart - Restart the bot"
        echo "  status  - Check if bot is running"
        echo "  logs    - Show recent log entries"
        exit 1
        ;;
esac 