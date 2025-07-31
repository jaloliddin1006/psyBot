# How to Create a Telegram Bot

This guide will walk you through the process of creating a Telegram bot using BotFather.

## Step 1: Open Telegram and Search for BotFather

1. Open the Telegram app on your device
2. In the search bar, type "@BotFather" and select the verified BotFather account

## Step 2: Start a Chat with BotFather

1. Click on the "Start" button to begin a conversation with BotFather

## Step 3: Create a New Bot

1. Send the command `/newbot` to BotFather
2. BotFather will ask you to choose a name for your bot. This is the display name that will appear in contacts and conversations
3. After setting the name, BotFather will ask you to choose a username for your bot. The username must end with "bot" (e.g., PsyHelperBot, PsychologicalSupportBot)

## Step 4: Get Your Bot Token

1. If everything goes well, BotFather will provide you with a token for your new bot
2. The token will look something like this: `123456789:ABCdefGhIJKlmNoPQRsTUVwxyZ`
3. This token is used to authenticate your bot and is required to run the PsyBot application

## Step 5: Configure Your Bot (Optional)

You can customize your bot further with these commands:
- `/setdescription` - Change the bot's description
- `/setabouttext` - Change the bot's about info
- `/setprofilepic` - Change the bot's profile photo
- `/setcommands` - Change the list of commands

## Step 6: Add Your Token to the PsyBot Application

1. Copy the token provided by BotFather
2. Open the `.env` file in the PsyBot application directory
3. Paste your token after `TELEGRAM_BOT_TOKEN=`
4. Save the file

## Step 7: Start Your Bot

1. Run the PsyBot application using the instructions in the main README
2. Your bot should now be operational

## Important Notes

- Keep your token secure. Anyone with your token can control your bot
- If your token is compromised, you can use the `/revoke` command with BotFather to revoke the token and generate a new one
- Telegram bots cannot initiate conversations with users. Users must either add them to a group or send them a message first 

cp psybot.service /etc/systemd/system/ && systemctl daemon-reload