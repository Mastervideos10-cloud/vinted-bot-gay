#!/bin/bash
echo "⏹️ Stopping Vinted Discord Bot..."

# Find and kill the bot process
BOT_PID=$(pgrep -f "python.*main.py")

if [ -z "$BOT_PID" ]; then
    echo "❌ Bot is not running"
    exit 1
fi

echo "🔄 Killing process PID: $BOT_PID"
kill $BOT_PID

# Wait for graceful shutdown
sleep 5

# Force kill if still running
if ps -p $BOT_PID > /dev/null 2>&1; then
    echo "⚠️ Forcing shutdown..."
    kill -9 $BOT_PID
    sleep 2
fi

# Verify it's stopped
if ! ps -p $BOT_PID > /dev/null 2>&1; then
    echo "✅ Vinted Bot stopped successfully"
else
    echo "❌ Failed to stop bot"
    exit 1
fi