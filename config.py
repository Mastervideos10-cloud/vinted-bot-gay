"""
Configuration Management
Handles environment variables and bot configuration
"""

import os
from typing import Optional
import logging

logger = logging.getLogger(__name__)

class Config:
    """Configuration class for Vinted Discord Bot"""
    
    def __init__(self):
        # Load environment variables
        self.load_environment()
        
        # Validate required configuration
        self.validate_config()
    
    def load_environment(self):
        """Load configuration from environment variables"""
        
        # Load .env file
        from dotenv import load_dotenv
        load_dotenv()
        
        # Discord Configuration
        self.DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
        self.DISCORD_CLIENT_ID = os.getenv("DISCORD_CLIENT_ID")
        self.DISCORD_GUILD_ID = os.getenv("DISCORD_GUILD_ID")
        self.DISCORD_ROLE_ADMIN_ID = os.getenv("DISCORD_ROLE_ADMIN_ID")
        self.DISCORD_THREAD_CHANNEL_ID = os.getenv("DISCORD_THREAD_CHANNEL_ID")
        self.DISCORD_COMMAND_CHANNEL_ID = os.getenv("DISCORD_COMMAND_CHANNEL_ID")
        
        # Proxy Configuration
        self.PROXY_LIST = os.getenv("PROXY_LIST", "")  # Comma-separated list of proxy URLs
        self.USE_PROXIES = os.getenv("USE_PROXIES", "true").lower() == "true"
        
        # Scraping Configuration
        self.SCRAPING_DELAY_MIN = int(os.getenv("SCRAPING_DELAY_MIN", "2"))  # Minimum delay between requests
        self.SCRAPING_DELAY_MAX = int(os.getenv("SCRAPING_DELAY_MAX", "5"))  # Maximum delay between requests
        self.MONITOR_INTERVAL = int(os.getenv("MONITOR_INTERVAL", "30"))  # Monitoring interval in seconds
        self.MAX_CONCURRENT_REQUESTS = int(os.getenv("MAX_CONCURRENT_REQUESTS", "5"))
        
        # Database Configuration
        self.DATABASE_PATH = os.getenv("DATABASE_PATH", "vinted_bot.db")
        
        # Logging Configuration
        self.LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
        self.LOG_FILE = os.getenv("LOG_FILE", "vinted_bot.log")
        
        # Feature Flags
        self.ENABLE_AUTOBUY = os.getenv("ENABLE_AUTOBUY", "false").lower() == "true"
        self.ENABLE_AUTO_OFFERS = os.getenv("ENABLE_AUTO_OFFERS", "false").lower() == "true"
        self.ENABLE_AUTO_MESSAGES = os.getenv("ENABLE_AUTO_MESSAGES", "false").lower() == "true"
        
        # Rate Limiting
        self.REQUESTS_PER_MINUTE = int(os.getenv("REQUESTS_PER_MINUTE", "30"))
        self.REQUESTS_PER_HOUR = int(os.getenv("REQUESTS_PER_HOUR", "500"))
        
        # Vinted Configuration
        self.DEFAULT_VINTED_DOMAIN = os.getenv("DEFAULT_VINTED_DOMAIN", "www.vinted.com")
        self.SUPPORTED_DOMAINS = [
            "www.vinted.com",
            "www.vinted.de",
            "www.vinted.fr",
            "www.vinted.es",
            "www.vinted.it",
            "www.vinted.be",
            "www.vinted.nl",
            "www.vinted.at",
            "www.vinted.cz",
            "www.vinted.pl"
        ]
        
        # Image and Media Configuration
        self.MAX_IMAGES_PER_LISTING = int(os.getenv("MAX_IMAGES_PER_LISTING", "4"))
        self.IMAGE_PROXY_ENABLED = os.getenv("IMAGE_PROXY_ENABLED", "false").lower() == "true"
        
        # Notification Configuration
        self.NOTIFICATION_COOLDOWN = int(os.getenv("NOTIFICATION_COOLDOWN", "300"))  # 5 minutes
        self.MAX_NOTIFICATIONS_PER_HOUR = int(os.getenv("MAX_NOTIFICATIONS_PER_HOUR", "50"))
        
        # Performance Configuration
        self.ENABLE_CACHING = os.getenv("ENABLE_CACHING", "true").lower() == "true"
        self.CACHE_TTL = int(os.getenv("CACHE_TTL", "300"))  # 5 minutes
        
        # Development Configuration
        self.DEBUG_MODE = os.getenv("DEBUG_MODE", "false").lower() == "true"
        self.DRY_RUN = os.getenv("DRY_RUN", "false").lower() == "true"
        
        logger.info("Configuration loaded successfully")
    
    def validate_config(self):
        """Validate required configuration values"""
        required_vars = [
            ("DISCORD_TOKEN", self.DISCORD_TOKEN),
            ("DISCORD_CLIENT_ID", self.DISCORD_CLIENT_ID),
            ("DISCORD_GUILD_ID", self.DISCORD_GUILD_ID)
        ]
        
        missing_vars = []
        for var_name, var_value in required_vars:
            if not var_value:
                missing_vars.append(var_name)
        
        if missing_vars:
            error_msg = f"Missing required environment variables: {', '.join(missing_vars)}"
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        # Validate proxy format if provided
        if self.PROXY_LIST:
            self.validate_proxy_list()
        
        logger.info("Configuration validation passed")
    
    def validate_proxy_list(self):
        """Validate proxy list format"""
        try:
            proxies = [p.strip() for p in self.PROXY_LIST.split(',') if p.strip()]
            
            for proxy in proxies:
                if not any(proxy.startswith(prefix) for prefix in ['http://', 'https://', 'socks4://', 'socks5://']):
                    logger.warning(f"Proxy URL may be invalid format: {proxy}")
            
            logger.info(f"Found {len(proxies)} proxies in configuration")
            
        except Exception as e:
            logger.warning(f"Error validating proxy list: {e}")
    
    def get_discord_config(self) -> dict:
        """Get Discord-specific configuration"""
        return {
            'token': self.DISCORD_TOKEN,
            'client_id': self.DISCORD_CLIENT_ID,
            'guild_id': int(self.DISCORD_GUILD_ID),
            'admin_role_id': int(self.DISCORD_ROLE_ADMIN_ID) if self.DISCORD_ROLE_ADMIN_ID else None,
            'thread_channel_id': int(self.DISCORD_THREAD_CHANNEL_ID) if self.DISCORD_THREAD_CHANNEL_ID else None,
            'command_channel_id': int(self.DISCORD_COMMAND_CHANNEL_ID) if self.DISCORD_COMMAND_CHANNEL_ID else None
        }
    
    def get_scraping_config(self) -> dict:
        """Get scraping-specific configuration"""
        return {
            'delay_min': self.SCRAPING_DELAY_MIN,
            'delay_max': self.SCRAPING_DELAY_MAX,
            'monitor_interval': self.MONITOR_INTERVAL,
            'max_concurrent_requests': self.MAX_CONCURRENT_REQUESTS,
            'requests_per_minute': self.REQUESTS_PER_MINUTE,
            'requests_per_hour': self.REQUESTS_PER_HOUR
        }
    
    def get_proxy_config(self) -> dict:
        """Get proxy-specific configuration"""
        return {
            'enabled': self.USE_PROXIES,
            'proxy_list': [p.strip() for p in self.PROXY_LIST.split(',') if p.strip()] if self.PROXY_LIST else [],
            'rotation_enabled': True
        }
    
    def is_development_mode(self) -> bool:
        """Check if running in development mode"""
        return self.DEBUG_MODE or self.DRY_RUN
    
    def get_supported_vinted_domains(self) -> list:
        """Get list of supported Vinted domains"""
        return self.SUPPORTED_DOMAINS.copy()
    
    def __str__(self) -> str:
        """String representation of config (without sensitive data)"""
        safe_config = {
            'discord_guild_id': self.DISCORD_GUILD_ID,
            'proxy_count': len([p.strip() for p in self.PROXY_LIST.split(',') if p.strip()]) if self.PROXY_LIST else 0,
            'monitor_interval': self.MONITOR_INTERVAL,
            'debug_mode': self.DEBUG_MODE,
            'supported_domains': len(self.SUPPORTED_DOMAINS)
        }
        return f"VintedBotConfig({safe_config})"