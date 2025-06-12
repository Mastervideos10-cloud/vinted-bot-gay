#!/usr/bin/env python3
"""
Vinted Discord Bot - Main Entry Point
Monitors Vinted listings and provides Discord integration with interactive buttons
"""

import asyncio
import logging
import os
import sys
from pathlib import Path

# Add current directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

from bot import VintedBot
from config import Config
from database import Database

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('vinted_bot.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

async def main():
    """Main entry point for the Vinted Discord Bot"""
    try:
        # Load configuration
        config = Config()
        
        # Validate required environment variables
        if not all([
            config.DISCORD_TOKEN,
            config.DISCORD_CLIENT_ID,
            config.DISCORD_GUILD_ID
        ]):
            logger.error("Missing required environment variables. Check .env file.")
            sys.exit(1)
        
        # Initialize database
        db = Database()
        await db.initialize()
        
        # Create and start bot
        bot = VintedBot(config, db)
        
        logger.info("Starting Vinted Discord Bot...")
        await bot.start()
        
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    # Ensure event loop is available
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot shutdown complete")