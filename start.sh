#!/bin/bash
echo "🚀 Starting Vinted Discord Bot..."

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "❌ Virtual environment not found. Run setup.sh first."
    exit 1
fi

# Activate virtual environment
source venv/bin/activate

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "❌ .env file not found. Please create it with your configuration."
    exit 1
fi

# Check if bot is already running
if pgrep -f "python.*main.py" > /dev/null; then
    echo "⚠️ Bot is already running!"
    echo "PID: $(pgrep -f 'python.*main.py')"
    exit 1
fi

# Start the bot
echo "▶️ Starting bot process..."
nohup python main.py > vinted_bot.log 2>&1 &
BOT_PID=$!

# Wait a moment to check if it started successfully
sleep 3

if ps -p $BOT_PID > /dev/null; then
    echo "✅ Vinted Bot started successfully!"
    echo "PID: $BOT_PID"
    echo "📋 Use './status.sh' to check status"
    echo "📋 Use './stop.sh' to stop the bot"
    echo "📋 Use 'tail -f vinted_bot.log' to view logs"
else
    echo "❌ Failed to start bot. Check vinted_bot.log for errors."
    exit 1
fi