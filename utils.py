"""
Utility Functions
Common helper functions for the Vinted Discord Bot
"""

import discord
import re
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional, List, Any
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

def format_price(price: float, currency: str = "EUR") -> str:
    """Format price with currency symbol"""
    try:
        currency_symbols = {
            'EUR': '€',
            'USD': '$',
            'GBP': '£',
            'PLN': 'zł',
            'CZK': 'Kč'
        }
        
        symbol = currency_symbols.get(currency, currency)
        
        if currency in ['EUR', 'USD', 'GBP']:
            return f"{symbol}{price:.2f}"
        else:
            return f"{price:.2f} {symbol}"
            
    except Exception as e:
        logger.error(f"Error formatting price: {e}")
        return f"{price} {currency}"

def get_flag_emoji(location: str) -> str:
    """Get flag emoji for country code"""
    flags = {
        'de': '🇩🇪',
        'fr': '🇫🇷',
        'es': '🇪🇸',
        'it': '🇮🇹',
        'be': '🇧🇪',
        'nl': '🇳🇱',
        'at': '🇦🇹',
        'cz': '🇨🇿',
        'pl': '🇵🇱',
        'com': '🌍'
    }
    return flags.get(location.lower(), '🌍')

def get_condition_emoji(condition: str) -> str:
    """Get emoji for item condition"""
    condition_lower = condition.lower()
    
    if 'new' in condition_lower and 'tag' in condition_lower:
        return '🏷️'
    elif 'new' in condition_lower:
        return '✨'
    elif 'very good' in condition_lower or 'excellent' in condition_lower:
        return '⭐'
    elif 'good' in condition_lower:
        return '👍'
    elif 'satisfactory' in condition_lower or 'fair' in condition_lower:
        return '👌'
    else:
        return '📦'

def get_size_category_emoji(size: str) -> str:
    """Get emoji based on size category"""
    size_lower = size.lower()
    
    if any(s in size_lower for s in ['xs', 'xxs']):
        return '🤏'
    elif 's' in size_lower and 'xs' not in size_lower:
        return '👕'
    elif 'm' in size_lower:
        return '👔'
    elif 'l' in size_lower and 'xl' not in size_lower:
        return '🧥'
    elif any(s in size_lower for s in ['xl', 'xxl', 'xxxl']):
        return '🦺'
    else:
        return '📏'

def create_embed(listing: Dict, search: Dict) -> discord.Embed:
    """Create a rich embed for a Vinted listing"""
    try:
        # Create base embed
        title = listing.get('title', 'Unknown Item')[:256]  # Discord title limit
        url = listing.get('url', '')
        
        embed = discord.Embed(
            title=title,
            url=url,
            color=0x00D4AA,  # Vinted green color
            timestamp=datetime.utcnow()
        )
        
        # Add thumbnail image
        images = listing.get('images', [])
        if images:
            embed.set_thumbnail(url=images[0])
        
        # Price information
        price = listing.get('price', 0)
        currency = listing.get('currency', 'EUR')
        price_emoji = '💰'
        embed.add_field(
            name=f"{price_emoji} Price",
            value=format_price(price, currency),
            inline=True
        )
        
        # Brand information
        brand = listing.get('brand', 'Unknown')
        if brand and brand.lower() != 'unknown':
            embed.add_field(
                name="🏷️ Brand",
                value=brand,
                inline=True
            )
        
        # Size information
        size = listing.get('size', '')
        if size:
            size_emoji = get_size_category_emoji(size)
            embed.add_field(
                name=f"{size_emoji} Size",
                value=size,
                inline=True
            )
        
        # Condition information
        condition = listing.get('condition', 'Unknown')
        if condition and condition.lower() != 'unknown':
            condition_emoji = get_condition_emoji(condition)
            embed.add_field(
                name=f"{condition_emoji} Condition",
                value=condition,
                inline=True
            )
        
        # Seller information
        seller = listing.get('seller', 'Unknown')
        if seller and seller.lower() != 'unknown':
            embed.add_field(
                name="👤 Seller",
                value=seller,
                inline=True
            )
        
        # Reviews/Ratings
        reviews_count = listing.get('reviews_count', 0)
        if reviews_count > 0:
            stars = '⭐' * min(5, max(1, int(reviews_count / 20)))  # Rough rating approximation
            embed.add_field(
                name="⭐ Reviews",
                value=f"{stars} ({reviews_count})",
                inline=True
            )
        
        # Location/Country
        location = listing.get('location', search.get('location', 'unknown'))
        flag = get_flag_emoji(location)
        embed.add_field(
            name=f"{flag} Location",
            value=location.upper(),
            inline=True
        )
        
        # Published time
        published_at = listing.get('published_at')
        if published_at:
            if isinstance(published_at, datetime):
                time_ago = format_time_ago(published_at)
                embed.add_field(
                    name="🕒 Published",
                    value=time_ago,
                    inline=True
                )
        
        # Additional images in description
        if len(images) > 1:
            additional_images = len(images) - 1
            embed.add_field(
                name="📸 Images",
                value=f"1 + {additional_images} more",
                inline=True
            )
        
        # Footer information
        embed.set_footer(
            text=f"Vinted Bot • {search.get('domain', 'vinted.com')}",
            icon_url="https://cdn.discordapp.com/attachments/123/456/vinted-icon.png"
        )
        
        return embed
        
    except Exception as e:
        logger.error(f"Error creating embed: {e}")
        
        # Fallback embed
        embed = discord.Embed(
            title="New Vinted Listing",
            description="Error loading listing details",
            color=0xff0000
        )
        return embed

def format_time_ago(dt: datetime) -> str:
    """Format datetime as 'time ago' string"""
    try:
        now = datetime.utcnow()
        
        # Ensure dt is timezone-naive for comparison
        if dt.tzinfo is not None:
            dt = dt.replace(tzinfo=None)
        
        diff = now - dt
        
        if diff.days > 0:
            return f"{diff.days}d ago"
        elif diff.seconds >= 3600:
            hours = diff.seconds // 3600
            return f"{hours}h ago"
        elif diff.seconds >= 60:
            minutes = diff.seconds // 60
            return f"{minutes}m ago"
        else:
            return "Just now"
            
    except Exception as e:
        logger.error(f"Error formatting time ago: {e}")
        return "Unknown"

def extract_search_params(search_url: str) -> Dict[str, Any]:
    """Extract search parameters from Vinted URL"""
    try:
        parsed_url = urlparse(search_url)
        params = {}
        
        # Parse query parameters
        if parsed_url.query:
            for param in parsed_url.query.split('&'):
                if '=' in param:
                    key, value = param.split('=', 1)
                    params[key] = value
        
        return params
        
    except Exception as e:
        logger.error(f"Error extracting search params: {e}")
        return {}

def validate_vinted_url(url: str) -> bool:
    """Validate if URL is a proper Vinted search URL"""
    try:
        parsed = urlparse(url)
        
        # Check if it's a Vinted domain
        if 'vinted' not in parsed.netloc:
            return False
        
        # Check if it's a catalog/search URL
        if not parsed.path.startswith('/catalog'):
            return False
        
        return True
        
    except Exception as e:
        logger.error(f"Error validating Vinted URL: {e}")
        return False

def sanitize_filename(filename: str) -> str:
    """Sanitize filename for safe file system usage"""
    try:
        # Remove or replace invalid characters
        invalid_chars = r'[<>:"/\\|?*]'
        sanitized = re.sub(invalid_chars, '_', filename)
        
        # Limit length
        if len(sanitized) > 200:
            sanitized = sanitized[:200]
        
        return sanitized.strip()
        
    except Exception as e:
        logger.error(f"Error sanitizing filename: {e}")
        return "unknown_file"

def chunk_list(lst: List[Any], chunk_size: int) -> List[List[Any]]:
    """Split a list into chunks of specified size"""
    try:
        chunks = []
        for i in range(0, len(lst), chunk_size):
            chunks.append(lst[i:i + chunk_size])
        return chunks
        
    except Exception as e:
        logger.error(f"Error chunking list: {e}")
        return [lst]  # Return original list as single chunk

def format_number(number: int) -> str:
    """Format large numbers with K/M suffixes"""
    try:
        if number >= 1000000:
            return f"{number / 1000000:.1f}M"
        elif number >= 1000:
            return f"{number / 1000:.1f}K"
        else:
            return str(number)
            
    except Exception as e:
        logger.error(f"Error formatting number: {e}")
        return str(number)

def get_brand_emoji(brand: str) -> str:
    """Get emoji for popular brands"""
    brand_lower = brand.lower()
    
    brand_emojis = {
        'nike': '✔️',
        'adidas': '🦓',
        'zara': '⚫',
        'h&m': '🟢',
        'uniqlo': '🔴',
        'gucci': '💚',
        'prada': '🖤',
        'chanel': '💎',
        'louis vuitton': '🤎',
        'supreme': '🔴'
    }
    
    for brand_name, emoji in brand_emojis.items():
        if brand_name in brand_lower:
            return emoji
    
    return '🏷️'  # Default brand emoji

def calculate_deal_score(listing: Dict) -> float:
    """Calculate a deal score based on various factors"""
    try:
        score = 0.0
        
        # Price factor (lower price = higher score, but not too low to avoid scams)
        price = listing.get('price', 0)
        if 5 <= price <= 50:
            score += 3.0
        elif 50 < price <= 100:
            score += 2.0
        elif 100 < price <= 200:
            score += 1.0
        
        # Condition factor
        condition = listing.get('condition', '').lower()
        if 'new' in condition:
            score += 2.0
        elif 'very good' in condition or 'excellent' in condition:
            score += 1.5
        elif 'good' in condition:
            score += 1.0
        
        # Brand factor
        brand = listing.get('brand', '').lower()
        premium_brands = ['gucci', 'prada', 'chanel', 'louis vuitton', 'hermes', 'dior']
        popular_brands = ['nike', 'adidas', 'zara', 'h&m', 'uniqlo']
        
        if any(b in brand for b in premium_brands):
            score += 3.0
        elif any(b in brand for b in popular_brands):
            score += 1.0
        
        # Seller reputation (if available)
        reviews_count = listing.get('reviews_count', 0)
        if reviews_count > 100:
            score += 2.0
        elif reviews_count > 50:
            score += 1.0
        elif reviews_count > 10:
            score += 0.5
        
        # Recently listed (higher score for newer items)
        published_at = listing.get('published_at')
        if published_at and isinstance(published_at, datetime):
            hours_ago = (datetime.utcnow() - published_at).total_seconds() / 3600
            if hours_ago < 1:
                score += 2.0
            elif hours_ago < 6:
                score += 1.0
            elif hours_ago < 24:
                score += 0.5
        
        return min(score, 10.0)  # Cap at 10.0
        
    except Exception as e:
        logger.error(f"Error calculating deal score: {e}")
        return 0.0

def is_likely_fake(listing: Dict) -> bool:
    """Check if listing is likely fake/scam based on heuristics"""
    try:
        # Check for suspiciously low prices on premium brands
        price = listing.get('price', 0)
        brand = listing.get('brand', '').lower()
        
        premium_brands = ['gucci', 'prada', 'chanel', 'louis vuitton', 'hermes', 'dior']
        
        if any(b in brand for b in premium_brands) and price < 50:
            return True
        
        # Check for new sellers with premium items
        reviews_count = listing.get('reviews_count', 0)
        if reviews_count == 0 and price > 500:
            return True
        
        # Check title for common fake indicators
        title = listing.get('title', '').lower()
        fake_indicators = ['replica', 'copy', 'fake', 'mirror', '1:1', 'aaa quality']
        
        if any(indicator in title for indicator in fake_indicators):
            return True
        
        return False
        
    except Exception as e:
        logger.error(f"Error checking if listing is fake: {e}")
        return False

def truncate_text(text: str, max_length: int, suffix: str = "...") -> str:
    """Truncate text to specified length with suffix"""
    try:
        if len(text) <= max_length:
            return text
        
        return text[:max_length - len(suffix)] + suffix
        
    except Exception as e:
        logger.error(f"Error truncating text: {e}")
        return text[:max_length] if len(text) > max_length else text