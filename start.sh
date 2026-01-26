#!/bin/bash
set -e

echo "Initializing database..."
python -m backend.init_db
echo "Database initialized successfully"

echo "Starting Telegram bot..."
python telegram-bot.py &
BOT_PID=$!

echo "Starting Telegram channel bot..."
python telegram-channel-bot.py &
CHANNEL_BOT_PID=$!

echo "All services started successfully"
echo "Telegram Bot PID: $BOT_PID"
echo "Channel Bot PID: $CHANNEL_BOT_PID"

# Wait for both processes to keep container alive
wait -n

# If one process exits, kill the other and exit
kill $BOT_PID $CHANNEL_BOT_PID 2>/dev/null
exit 1
