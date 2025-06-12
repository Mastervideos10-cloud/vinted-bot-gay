"""
Database Management for Vinted Bot
Handles SQLite database operations for searches, filters, and configurations
"""

import aiosqlite
import logging
import json
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path

logger = logging.getLogger(__name__)

class Database:
    def __init__(self, db_path: str = "vinted_bot.db"):
        self.db_path = db_path
        self.db = None
    
    async def initialize(self):
        """Initialize database and create tables"""
        try:
            # Ensure database file exists
            Path(self.db_path).touch(exist_ok=True)
            
            async with aiosqlite.connect(self.db_path) as db:
                # Enable foreign keys
                await db.execute("PRAGMA foreign_keys = ON")
                
                # Create search_urls table
                await db.execute("""
                    CREATE TABLE IF NOT EXISTS search_urls (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        channel_id INTEGER NOT NULL,
                        search_url TEXT NOT NULL,
                        domain TEXT NOT NULL,
                        location TEXT NOT NULL,
                        added_by INTEGER NOT NULL,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        last_check DATETIME DEFAULT CURRENT_TIMESTAMP,
                        is_active BOOLEAN DEFAULT 1
                    )
                """)
                
                # Create filters table
                await db.execute("""
                    CREATE TABLE IF NOT EXISTS filters (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        channel_id INTEGER NOT NULL,
                        filter_type TEXT NOT NULL,
                        filter_value TEXT NOT NULL,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        is_active BOOLEAN DEFAULT 1
                    )
                """)
                
                # Create blacklist/whitelist table
                await db.execute("""
                    CREATE TABLE IF NOT EXISTS seller_lists (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        channel_id INTEGER NOT NULL,
                        seller_id TEXT NOT NULL,
                        seller_name TEXT,
                        list_type TEXT NOT NULL CHECK (list_type IN ('blacklist', 'whitelist')),
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        is_active BOOLEAN DEFAULT 1
                    )
                """)
                
                # Create listings table to track sent messages
                await db.execute("""
                    CREATE TABLE IF NOT EXISTS listings (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        listing_id TEXT NOT NULL,
                        channel_id INTEGER NOT NULL,
                        message_id INTEGER NOT NULL,
                        listing_data TEXT NOT NULL,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(listing_id, channel_id)
                    )
                """)
                
                # Create proxy table
                await db.execute("""
                    CREATE TABLE IF NOT EXISTS proxies (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        proxy_url TEXT NOT NULL UNIQUE,
                        proxy_type TEXT DEFAULT 'http',
                        is_active BOOLEAN DEFAULT 1,
                        last_used DATETIME,
                        success_count INTEGER DEFAULT 0,
                        failure_count INTEGER DEFAULT 0,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # Create indexes for better performance
                await db.execute("CREATE INDEX IF NOT EXISTS idx_search_urls_channel ON search_urls(channel_id)")
                await db.execute("CREATE INDEX IF NOT EXISTS idx_filters_channel ON filters(channel_id)")
                await db.execute("CREATE INDEX IF NOT EXISTS idx_listings_channel ON listings(channel_id)")
                await db.execute("CREATE INDEX IF NOT EXISTS idx_proxies_active ON proxies(is_active)")
                
                await db.commit()
                logger.info("Database initialized successfully")
                
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise
    
    async def add_search_url(self, channel_id: int, search_url: str, domain: str, location: str, added_by: int) -> int:
        """Add a new search URL to monitor"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute("""
                    INSERT INTO search_urls (channel_id, search_url, domain, location, added_by)
                    VALUES (?, ?, ?, ?, ?)
                """, (channel_id, search_url, domain, location, added_by))
                
                await db.commit()
                return cursor.lastrowid
                
        except Exception as e:
            logger.error(f"Error adding search URL: {e}")
            raise
    
    async def remove_search_url(self, search_id: int, channel_id: int) -> bool:
        """Remove a search URL by ID and channel"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute("""
                    UPDATE search_urls 
                    SET is_active = 0 
                    WHERE id = ? AND channel_id = ?
                """, (search_id, channel_id))
                
                await db.commit()
                return cursor.rowcount > 0
                
        except Exception as e:
            logger.error(f"Error removing search URL: {e}")
            return False
    
    async def get_channel_searches(self, channel_id: int) -> List[Dict]:
        """Get all active searches for a channel"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                
                cursor = await db.execute("""
                    SELECT id, search_url, domain, location, created_at, last_check
                    FROM search_urls 
                    WHERE channel_id = ? AND is_active = 1
                    ORDER BY created_at DESC
                """, (channel_id,))
                
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]
                
        except Exception as e:
            logger.error(f"Error getting channel searches: {e}")
            return []
    
    async def get_all_active_searches(self) -> List[Dict]:
        """Get all active searches across all channels"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                
                cursor = await db.execute("""
                    SELECT id, channel_id, search_url, domain, location, last_check
                    FROM search_urls 
                    WHERE is_active = 1
                    ORDER BY last_check ASC
                """)
                
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]
                
        except Exception as e:
            logger.error(f"Error getting all active searches: {e}")
            return []
    
    async def update_search_last_check(self, search_id: int):
        """Update the last check time for a search"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("""
                    UPDATE search_urls 
                    SET last_check = CURRENT_TIMESTAMP 
                    WHERE id = ?
                """, (search_id,))
                
                await db.commit()
                
        except Exception as e:
            logger.error(f"Error updating search last check: {e}")
    
    async def add_filter(self, channel_id: int, filter_type: str, filter_value: str) -> int:
        """Add a filter for a channel"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute("""
                    INSERT INTO filters (channel_id, filter_type, filter_value)
                    VALUES (?, ?, ?)
                """, (channel_id, filter_type, filter_value))
                
                await db.commit()
                return cursor.lastrowid
                
        except Exception as e:
            logger.error(f"Error adding filter: {e}")
            raise
    
    async def get_channel_filters(self, channel_id: int) -> List[Dict]:
        """Get all active filters for a channel"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                
                cursor = await db.execute("""
                    SELECT filter_type, filter_value
                    FROM filters 
                    WHERE channel_id = ? AND is_active = 1
                """, (channel_id,))
                
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]
                
        except Exception as e:
            logger.error(f"Error getting channel filters: {e}")
            return []
    
    async def add_seller_to_list(self, channel_id: int, seller_id: str, seller_name: str, list_type: str) -> int:
        """Add seller to blacklist or whitelist"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute("""
                    INSERT OR REPLACE INTO seller_lists (channel_id, seller_id, seller_name, list_type)
                    VALUES (?, ?, ?, ?)
                """, (channel_id, seller_id, seller_name, list_type))
                
                await db.commit()
                return cursor.lastrowid
                
        except Exception as e:
            logger.error(f"Error adding seller to list: {e}")
            raise
    
    async def get_seller_lists(self, channel_id: int) -> Dict[str, List[str]]:
        """Get blacklist and whitelist for a channel"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                
                cursor = await db.execute("""
                    SELECT seller_id, list_type
                    FROM seller_lists 
                    WHERE channel_id = ? AND is_active = 1
                """, (channel_id,))
                
                rows = await cursor.fetchall()
                
                lists = {'blacklist': [], 'whitelist': []}
                for row in rows:
                    lists[row['list_type']].append(row['seller_id'])
                
                return lists
                
        except Exception as e:
            logger.error(f"Error getting seller lists: {e}")
            return {'blacklist': [], 'whitelist': []}
    
    async def store_listing_message(self, listing_id: str, channel_id: int, message_id: int, listing_data: Dict):
        """Store a listing message for tracking"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("""
                    INSERT OR REPLACE INTO listings (listing_id, channel_id, message_id, listing_data)
                    VALUES (?, ?, ?, ?)
                """, (listing_id, channel_id, message_id, json.dumps(listing_data)))
                
                await db.commit()
                
        except Exception as e:
            logger.error(f"Error storing listing message: {e}")
    
    async def add_proxy(self, proxy_url: str, proxy_type: str = 'http') -> int:
        """Add a proxy to the database"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute("""
                    INSERT OR IGNORE INTO proxies (proxy_url, proxy_type)
                    VALUES (?, ?)
                """, (proxy_url, proxy_type))
                
                await db.commit()
                return cursor.lastrowid
                
        except Exception as e:
            logger.error(f"Error adding proxy: {e}")
            raise
    
    async def get_active_proxies(self) -> List[Dict]:
        """Get all active proxies"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                
                cursor = await db.execute("""
                    SELECT id, proxy_url, proxy_type, success_count, failure_count
                    FROM proxies 
                    WHERE is_active = 1
                    ORDER BY (success_count * 1.0 / NULLIF(success_count + failure_count, 0)) DESC
                """)
                
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]
                
        except Exception as e:
            logger.error(f"Error getting active proxies: {e}")
            return []
    
    async def update_proxy_stats(self, proxy_id: int, success: bool):
        """Update proxy success/failure statistics"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                if success:
                    await db.execute("""
                        UPDATE proxies 
                        SET success_count = success_count + 1, last_used = CURRENT_TIMESTAMP
                        WHERE id = ?
                    """, (proxy_id,))
                else:
                    await db.execute("""
                        UPDATE proxies 
                        SET failure_count = failure_count + 1
                        WHERE id = ?
                    """, (proxy_id,))
                
                await db.commit()
                
        except Exception as e:
            logger.error(f"Error updating proxy stats: {e}")
    
    async def cleanup_old_listings(self, days: int = 7):
        """Clean up old listing records"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("""
                    DELETE FROM listings 
                    WHERE created_at < datetime('now', '-{} days')
                """.format(days))
                
                await db.commit()
                logger.info(f"Cleaned up listings older than {days} days")
                
        except Exception as e:
            logger.error(f"Error cleaning up old listings: {e}")