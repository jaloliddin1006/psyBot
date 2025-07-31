# Running PsyBot in the Background

This guide provides multiple methods to run your PsyBot in the background, ensuring it continues running even when you close your terminal or IDE.

## Prerequisites

1. Ensure you have a `.env` file with all required environment variables
2. Make sure all dependencies are installed: `pip install -r requirements.txt`
3. Verify FFmpeg is installed: `ffmpeg -version`

## Method 1: Using the Background Script (Recommended for Development)

The simplest way to run the bot in the background:

```bash
# Start the bot
./start_background.sh start

# Check status
./start_background.sh status

# View logs
./start_background.sh logs

# Stop the bot
./start_background.sh stop

# Restart the bot
./start_background.sh restart
```

### Features:
- ✅ Easy to use
- ✅ Automatic PID management
- ✅ Log file management
- ✅ Status checking
- ✅ Graceful start/stop

## Method 2: Using systemd (Recommended for Production)

For production deployments, use systemd to manage the bot as a system service:

```bash
# Install the service
sudo cp psybot.service /etc/systemd/system/
sudo systemctl daemon-reload

# Enable auto-start on boot
sudo systemctl enable psybot

# Start the service
sudo systemctl start psybot

# Check status
sudo systemctl status psybot

# View logs
sudo journalctl -u psybot -f

# Stop the service
sudo systemctl stop psybot

# Restart the service
sudo systemctl restart psybot
```

### Features:
- ✅ Automatic restart on failure
- ✅ Starts automatically on system boot
- ✅ Integrated with system logging
- ✅ Process monitoring
- ✅ Resource management

## Method 3: Using Docker (Recommended for Containerized Deployment)

For containerized deployment with Docker:

```bash
# Build and start with docker-compose
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f psybot

# Stop the container
docker-compose down

# Restart the container
docker-compose restart psybot

# Update and restart
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

### Features:
- ✅ Isolated environment
- ✅ Easy deployment
- ✅ Automatic restart
- ✅ Health checks
- ✅ Port management for admin panel

## Method 4: Using screen/tmux (Alternative)

If you prefer using screen or tmux:

### Using screen:
```bash
# Start a new screen session
screen -S psybot

# Inside the screen session, activate venv and run bot
source venv/bin/activate
python run_bot.py

# Detach from screen: Ctrl+A, then D
# Reattach to screen: screen -r psybot
# Kill screen session: screen -X -S psybot quit
```

### Using tmux:
```bash
# Start a new tmux session
tmux new-session -d -s psybot

# Run the bot in the session
tmux send-keys -t psybot "cd /home/psyBot && source venv/bin/activate && python run_bot.py" Enter

# Attach to session: tmux attach-session -t psybot
# Detach from session: Ctrl+B, then D
# Kill session: tmux kill-session -t psybot
```

## Monitoring and Troubleshooting

### Check if the bot is running:
```bash
# Using the background script
./start_background.sh status

# Using systemd
sudo systemctl status psybot

# Using Docker
docker-compose ps

# Manual check
ps aux | grep python | grep run_bot
```

### View logs:
```bash
# Background script logs
tail -f psybot.log

# systemd logs
sudo journalctl -u psybot -f

# Docker logs
docker-compose logs -f psybot
```

### Common Issues:

1. **Missing environment variables**: Ensure `.env` file exists and contains all required variables
2. **Permission issues**: Make sure the user has proper permissions to the bot directory
3. **Port conflicts**: Ensure port 8012 (admin panel) is not in use by another service
4. **Database issues**: Check if the database file is accessible and not corrupted

### Environment Variables Required:

Create a `.env` file with:
```env
TELEGRAM_BOT_TOKEN=your_bot_token_here
GOOGLE_GENAI_API_KEY=your_google_ai_key_here
API_URL=your_api_url_here
ADMIN_USERNAME=admin
ADMIN_PASSWORD=your_secure_password
```

## Choosing the Right Method

- **Development**: Use the background script (`./start_background.sh start`)
- **Production Server**: Use systemd service
- **Containerized Environment**: Use Docker
- **Temporary Testing**: Use screen/tmux

## Auto-restart on System Reboot

### For systemd:
```bash
sudo systemctl enable psybot
```

### For Docker:
The `restart: unless-stopped` policy in docker-compose.yml handles this automatically.

### For background script:
Add to crontab:
```bash
crontab -e
# Add this line:
@reboot /home/psyBot/start_background.sh start
```

## Security Considerations

1. **Environment Variables**: Never commit `.env` file to version control
2. **File Permissions**: Ensure proper file permissions for the bot directory
3. **Network Security**: Configure firewall rules if needed
4. **Admin Panel**: Use strong passwords for the admin panel
5. **Log Rotation**: Set up log rotation to prevent disk space issues

## Performance Monitoring

Monitor your bot's performance:

```bash
# CPU and memory usage
top -p $(cat psybot.pid)

# Disk usage
du -sh /home/psyBot/

# Network connections
netstat -tulpn | grep python
```

## Backup Strategy

Regular backups of important files:
```bash
# Backup database and logs
tar -czf psybot_backup_$(date +%Y%m%d).tar.gz database/ psybot.log .env

# Automated backup script (add to crontab)
0 2 * * * /home/psyBot/backup_bot.sh
``` 