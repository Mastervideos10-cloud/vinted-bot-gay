"""
Vinted Web Scraper
Handles scraping of Vinted listings with proxy support and rate limiting
"""

import asyncio
import aiohttp
import json
import logging
import re
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from urllib.parse import urlparse, parse_qs
import random
from bs4 import BeautifulSoup

from proxy_manager import ProxyManager
from config import Config

logger = logging.getLogger(__name__)

class VintedScraper:
    def __init__(self, config: Config):
        self.config = config
        self.proxy_manager = ProxyManager(config)
        self.session = None
        self.last_requests = {}  # Track last request times per domain
        self.min_delay = 2  # Minimum delay between requests in seconds
        
        # Common headers to mimic real browser
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Cache-Control': 'max-age=0'
        }
    
    async def initialize_session(self):
        """Initialize aiohttp session with proper configuration"""
        if not self.session:
            timeout = aiohttp.ClientTimeout(total=30, connect=10)
            connector = aiohttp.TCPConnector(limit=100, limit_per_host=10)
            self.session = aiohttp.ClientSession(
                headers=self.headers,
                timeout=timeout,
                connector=connector
            )
    
    async def close_session(self):
        """Close aiohttp session"""
        if self.session:
            await self.session.close()
            self.session = None
    
    async def get_new_listings(self, search_url: str, last_check: Optional[datetime] = None) -> List[Dict]:
        """Get new listings from a Vinted search URL"""
        try:
            await self.initialize_session()
            
            # Rate limiting per domain
            domain = self.extract_domain(search_url)
            await self.apply_rate_limit(domain)
            
            # Get proxy for this request
            proxy = await self.proxy_manager.get_proxy()
            
            # Make request to Vinted
            async with self.session.get(
                search_url,
                proxy=proxy,
                ssl=False
            ) as response:
                
                if response.status != 200:
                    logger.warning(f"Non-200 status {response.status} for {search_url}")
                    return []
                
                html_content = await response.text()
                
                # Parse listings from HTML
                listings = self.parse_vinted_listings(html_content, search_url)
                
                # Filter by last check time if provided
                if last_check:
                    listings = [
                        listing for listing in listings 
                        if listing.get('published_at', datetime.min) > last_check
                    ]
                
                logger.info(f"Found {len(listings)} new listings for {domain}")
                return listings
                
        except Exception as e:
            logger.error(f"Error scraping {search_url}: {e}")
            return []
    
    def parse_vinted_listings(self, html_content: str, search_url: str) -> List[Dict]:
        """Parse Vinted listings from HTML content"""
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            listings = []
            
            # Try to find the JSON data embedded in the page
            script_tags = soup.find_all('script')
            vinted_data = None
            
            for script in script_tags:
                if script.string and 'window.App' in script.string:
                    # Extract JSON data from window.App
                    match = re.search(r'window\.App\s*=\s*({.*?});', script.string, re.DOTALL)
                    if match:
                        try:
                            vinted_data = json.loads(match.group(1))
                            break
                        except json.JSONDecodeError:
                            continue
            
            if vinted_data and 'catalog' in vinted_data:
                # Parse from embedded JSON data (preferred method)
                catalog_data = vinted_data.get('catalog', {})
                items = catalog_data.get('items', [])
                
                for item in items:
                    listing = self.parse_item_data(item, search_url)
                    if listing:
                        listings.append(listing)
            
            else:
                # Fallback: Parse from HTML elements
                listings = self.parse_html_listings(soup, search_url)
            
            return listings
            
        except Exception as e:
            logger.error(f"Error parsing Vinted listings: {e}")
            return []
    
    def parse_item_data(self, item: Dict, search_url: str) -> Optional[Dict]:
        """Parse individual item data from Vinted JSON"""
        try:
            # Extract basic information
            listing = {
                'id': str(item.get('id', '')),
                'title': item.get('title', ''),
                'price': float(item.get('price', {}).get('amount', 0)),
                'currency': item.get('price', {}).get('currency_code', 'EUR'),
                'brand': item.get('brand_title', ''),
                'size': item.get('size_title', ''),
                'condition': self.get_condition_text(item.get('status', '')),
                'seller': item.get('user', {}).get('login', ''),
                'seller_id': item.get('user', {}).get('id', ''),
                'url': self.build_item_url(item, search_url),
                'published_at': self.parse_datetime(item.get('created_at_ts')),
                'updated_at': self.parse_datetime(item.get('updated_at_ts')),
                'images': [],
                'reviews_count': item.get('user', {}).get('positive_feedback_count', 0),
                'location': self.extract_location_from_url(search_url)
            }
            
            # Extract images
            photos = item.get('photos', [])
            for photo in photos[:4]:  # Limit to 4 images
                if 'full_size_url' in photo:
                    listing['images'].append(photo['full_size_url'])
                elif 'url' in photo:
                    listing['images'].append(photo['url'])
            
            # Additional details
            if 'brand_title' in item:
                listing['brand'] = item['brand_title']
            
            if 'size_title' in item:
                listing['size'] = item['size_title']
            
            return listing
            
        except Exception as e:
            logger.error(f"Error parsing item data: {e}")
            return None
    
    def parse_html_listings(self, soup: BeautifulSoup, search_url: str) -> List[Dict]:
        """Fallback method to parse listings from HTML elements"""
        try:
            listings = []
            
            # Find item containers (this may need adjustment based on Vinted's HTML structure)
            item_containers = soup.find_all(['div', 'article'], class_=re.compile(r'item|product|listing'))
            
            for container in item_containers[:20]:  # Limit to first 20 items
                try:
                    listing = {
                        'id': self.extract_id_from_html(container),
                        'title': self.extract_text(container, ['h3', 'h2', '.title']),
                        'price': self.extract_price_from_html(container),
                        'currency': 'EUR',  # Default
                        'brand': self.extract_text(container, ['.brand', '.brand-title']),
                        'size': self.extract_text(container, ['.size', '.size-title']),
                        'condition': self.extract_text(container, ['.condition', '.status']),
                        'seller': self.extract_text(container, ['.seller', '.user', '.username']),
                        'url': self.extract_url_from_html(container, search_url),
                        'published_at': datetime.utcnow(),  # Fallback to current time
                        'images': self.extract_images_from_html(container),
                        'location': self.extract_location_from_url(search_url)
                    }
                    
                    if listing['id'] and listing['title']:
                        listings.append(listing)
                        
                except Exception as e:
                    logger.debug(f"Error parsing HTML item: {e}")
                    continue
            
            return listings
            
        except Exception as e:
            logger.error(f"Error parsing HTML listings: {e}")
            return []
    
    def extract_text(self, container, selectors: List[str]) -> str:
        """Extract text from container using multiple selectors"""
        for selector in selectors:
            element = container.select_one(selector)
            if element:
                return element.get_text(strip=True)
        return ''
    
    def extract_price_from_html(self, container) -> float:
        """Extract price from HTML container"""
        price_selectors = ['.price', '.amount', '[data-price]']
        for selector in price_selectors:
            element = container.select_one(selector)
            if element:
                price_text = element.get_text(strip=True)
                # Extract numeric value
                price_match = re.search(r'(\d+[.,]\d+|\d+)', price_text.replace(',', '.'))
                if price_match:
                    return float(price_match.group(1))
        return 0.0
    
    def extract_id_from_html(self, container) -> str:
        """Extract item ID from HTML container"""
        # Try data attributes first
        for attr in ['data-id', 'data-item-id', 'id']:
            if container.get(attr):
                return str(container[attr])
        
        # Try to extract from links
        link = container.find('a', href=True)
        if link:
            href = link['href']
            id_match = re.search(r'/items/(\d+)', href)
            if id_match:
                return id_match.group(1)
        
        return f"html_{random.randint(1000000, 9999999)}"
    
    def extract_url_from_html(self, container, base_url: str) -> str:
        """Extract item URL from HTML container"""
        link = container.find('a', href=True)
        if link:
            href = link['href']
            if href.startswith('http'):
                return href
            elif href.startswith('/'):
                domain = self.extract_domain(base_url)
                return f"https://{domain}{href}"
        return ''
    
    def extract_images_from_html(self, container) -> List[str]:
        """Extract image URLs from HTML container"""
        images = []
        img_tags = container.find_all('img', src=True)
        
        for img in img_tags[:4]:  # Limit to 4 images
            src = img['src']
            if 'http' in src and 'vinted' in src:
                images.append(src)
        
        return images
    
    def build_item_url(self, item: Dict, search_url: str) -> str:
        """Build full item URL from item data"""
        try:
            domain = self.extract_domain(search_url)
            item_id = item.get('id', '')
            if item_id:
                return f"https://{domain}/items/{item_id}"
            return ''
        except:
            return ''
    
    def extract_domain(self, url: str) -> str:
        """Extract domain from URL"""
        try:
            parsed = urlparse(url)
            return parsed.netloc
        except:
            return 'www.vinted.com'
    
    def extract_location_from_url(self, url: str) -> str:
        """Extract country/location from Vinted URL"""
        try:
            domain = self.extract_domain(url)
            if '.de' in domain:
                return 'de'
            elif '.fr' in domain:
                return 'fr'
            elif '.es' in domain:
                return 'es'
            elif '.it' in domain:
                return 'it'
            elif '.be' in domain:
                return 'be'
            elif '.nl' in domain:
                return 'nl'
            else:
                return 'com'
        except:
            return 'com'
    
    def get_condition_text(self, status: str) -> str:
        """Convert status code to readable condition text"""
        conditions = {
            'very_good': 'Very Good',
            'good': 'Good',
            'satisfactory': 'Satisfactory',
            'new_with_tags': 'New with Tags',
            'new_without_tags': 'New without Tags'
        }
        return conditions.get(status, status.replace('_', ' ').title())
    
    def parse_datetime(self, timestamp) -> datetime:
        """Parse datetime from various formats"""
        try:
            if isinstance(timestamp, (int, float)):
                return datetime.fromtimestamp(timestamp)
            elif isinstance(timestamp, str):
                # Try ISO format
                return datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            else:
                return datetime.utcnow()
        except:
            return datetime.utcnow()
    
    async def apply_rate_limit(self, domain: str):
        """Apply rate limiting per domain"""
        now = datetime.utcnow()
        last_request = self.last_requests.get(domain)
        
        if last_request:
            time_since_last = (now - last_request).total_seconds()
            if time_since_last < self.min_delay:
                delay = self.min_delay - time_since_last
                logger.debug(f"Rate limiting: waiting {delay:.2f}s for {domain}")
                await asyncio.sleep(delay)
        
        self.last_requests[domain] = now