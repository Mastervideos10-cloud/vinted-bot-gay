"""
Proxy Management System
Handles proxy rotation, health checking, and load balancing
"""

import asyncio
import aiohttp
import logging
import random
from typing import List, Dict, Optional
from datetime import datetime, timedelta

from config import Config

logger = logging.getLogger(__name__)

class ProxyManager:
    def __init__(self, config: Config):
        self.config = config
        self.proxies = []
        self.current_proxy_index = 0
        self.proxy_health = {}
        self.last_health_check = None
        self.health_check_interval = timedelta(minutes=10)
        
        # Load proxies from config
        self.load_proxies_from_config()
    
    def load_proxies_from_config(self):
        """Load proxies from configuration"""
        try:
            # Load from environment variable (comma-separated)
            if self.config.PROXY_LIST:
                proxy_urls = [p.strip() for p in self.config.PROXY_LIST.split(',') if p.strip()]
                for proxy_url in proxy_urls:
                    self.add_proxy(proxy_url)
            
            logger.info(f"Loaded {len(self.proxies)} proxies from configuration")
            
        except Exception as e:
            logger.error(f"Error loading proxies from config: {e}")
    
    def add_proxy(self, proxy_url: str, proxy_type: str = 'http'):
        """Add a proxy to the manager"""
        try:
            # Validate proxy URL format
            if not self.is_valid_proxy_url(proxy_url):
                logger.warning(f"Invalid proxy URL format: {proxy_url}")
                return False
            
            proxy_info = {
                'url': proxy_url,
                'type': proxy_type,
                'success_count': 0,
                'failure_count': 0,
                'last_used': None,
                'last_success': None,
                'is_healthy': True,
                'response_time': None
            }
            
            self.proxies.append(proxy_info)
            self.proxy_health[proxy_url] = proxy_info
            
            logger.info(f"Added proxy: {proxy_url}")
            return True
            
        except Exception as e:
            logger.error(f"Error adding proxy {proxy_url}: {e}")
            return False
    
    def is_valid_proxy_url(self, proxy_url: str) -> bool:
        """Validate proxy URL format"""
        try:
            # Basic validation for common proxy formats
            valid_prefixes = ['http://', 'https://', 'socks4://', 'socks5://']
            return any(proxy_url.startswith(prefix) for prefix in valid_prefixes)
        except:
            return False
    
    async def get_proxy(self) -> Optional[str]:
        """Get the next available proxy"""
        try:
            # Check if health check is needed
            await self.check_proxy_health_if_needed()
            
            # Filter healthy proxies
            healthy_proxies = [p for p in self.proxies if p['is_healthy']]
            
            if not healthy_proxies:
                logger.warning("No healthy proxies available")
                return None
            
            # Use round-robin with preference for better performing proxies
            proxy_info = self.select_best_proxy(healthy_proxies)
            
            if proxy_info:
                proxy_info['last_used'] = datetime.utcnow()
                return proxy_info['url']
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting proxy: {e}")
            return None
    
    def select_best_proxy(self, healthy_proxies: List[Dict]) -> Optional[Dict]:
        """Select the best proxy based on performance metrics"""
        try:
            if not healthy_proxies:
                return None
            
            # Sort by success rate and response time
            def proxy_score(proxy):
                total_requests = proxy['success_count'] + proxy['failure_count']
                if total_requests == 0:
                    success_rate = 1.0  # New proxy gets benefit of doubt
                else:
                    success_rate = proxy['success_count'] / total_requests
                
                # Factor in response time (lower is better)
                response_time_factor = 1.0
                if proxy['response_time']:
                    response_time_factor = max(0.1, 1.0 / (1.0 + proxy['response_time']))
                
                return success_rate * response_time_factor
            
            # Sort by score (descending) and add some randomness
            sorted_proxies = sorted(healthy_proxies, key=proxy_score, reverse=True)
            
            # Select from top 3 proxies with weighted randomness
            top_proxies = sorted_proxies[:min(3, len(sorted_proxies))]
            weights = [3, 2, 1][:len(top_proxies)]
            
            return random.choices(top_proxies, weights=weights)[0]
            
        except Exception as e:
            logger.error(f"Error selecting best proxy: {e}")
            return random.choice(healthy_proxies) if healthy_proxies else None
    
    async def check_proxy_health_if_needed(self):
        """Check proxy health if enough time has passed"""
        try:
            now = datetime.utcnow()
            
            if (not self.last_health_check or 
                now - self.last_health_check > self.health_check_interval):
                
                logger.info("Starting proxy health check...")
                await self.check_all_proxies_health()
                self.last_health_check = now
                
        except Exception as e:
            logger.error(f"Error in health check scheduling: {e}")
    
    async def check_all_proxies_health(self):
        """Check health of all proxies"""
        try:
            # Create tasks for parallel health checks
            tasks = []
            for proxy_info in self.proxies:
                task = asyncio.create_task(self.check_single_proxy_health(proxy_info))
                tasks.append(task)
            
            # Wait for all health checks to complete
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)
            
            healthy_count = sum(1 for p in self.proxies if p['is_healthy'])
            logger.info(f"Health check complete: {healthy_count}/{len(self.proxies)} proxies healthy")
            
        except Exception as e:
            logger.error(f"Error checking all proxies health: {e}")
    
    async def check_single_proxy_health(self, proxy_info: Dict):
        """Check health of a single proxy"""
        try:
            start_time = datetime.utcnow()
            
            # Test URL - use a simple, fast endpoint
            test_url = "http://httpbin.org/ip"
            timeout = aiohttp.ClientTimeout(total=10, connect=5)
            
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(
                    test_url,
                    proxy=proxy_info['url'],
                    ssl=False
                ) as response:
                    
                    if response.status == 200:
                        # Proxy is healthy
                        response_time = (datetime.utcnow() - start_time).total_seconds()
                        proxy_info['is_healthy'] = True
                        proxy_info['last_success'] = datetime.utcnow()
                        proxy_info['response_time'] = response_time
                        proxy_info['success_count'] += 1
                        
                        logger.debug(f"Proxy {proxy_info['url']} is healthy (response time: {response_time:.2f}s)")
                    else:
                        # Proxy returned non-200 status
                        proxy_info['is_healthy'] = False
                        proxy_info['failure_count'] += 1
                        logger.warning(f"Proxy {proxy_info['url']} returned status {response.status}")
                        
        except Exception as e:
            # Proxy is unhealthy
            proxy_info['is_healthy'] = False
            proxy_info['failure_count'] += 1
            logger.debug(f"Proxy {proxy_info['url']} failed health check: {e}")
    
    async def report_proxy_result(self, proxy_url: str, success: bool, response_time: Optional[float] = None):
        """Report the result of using a proxy"""
        try:
            if proxy_url in self.proxy_health:
                proxy_info = self.proxy_health[proxy_url]
                
                if success:
                    proxy_info['success_count'] += 1
                    proxy_info['last_success'] = datetime.utcnow()
                    proxy_info['is_healthy'] = True
                    
                    if response_time:
                        # Update rolling average response time
                        if proxy_info['response_time']:
                            proxy_info['response_time'] = (proxy_info['response_time'] + response_time) / 2
                        else:
                            proxy_info['response_time'] = response_time
                else:
                    proxy_info['failure_count'] += 1
                    
                    # Mark as unhealthy after consecutive failures
                    if proxy_info['failure_count'] > proxy_info['success_count'] + 3:
                        proxy_info['is_healthy'] = False
                
        except Exception as e:
            logger.error(f"Error reporting proxy result: {e}")
    
    def get_proxy_stats(self) -> Dict:
        """Get statistics about proxy usage"""
        try:
            stats = {
                'total_proxies': len(self.proxies),
                'healthy_proxies': sum(1 for p in self.proxies if p['is_healthy']),
                'total_successes': sum(p['success_count'] for p in self.proxies),
                'total_failures': sum(p['failure_count'] for p in self.proxies),
                'last_health_check': self.last_health_check.isoformat() if self.last_health_check else None
            }
            
            if stats['total_successes'] + stats['total_failures'] > 0:
                stats['overall_success_rate'] = stats['total_successes'] / (stats['total_successes'] + stats['total_failures'])
            else:
                stats['overall_success_rate'] = 0.0
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting proxy stats: {e}")
            return {}
    
    def remove_proxy(self, proxy_url: str) -> bool:
        """Remove a proxy from the manager"""
        try:
            # Remove from proxies list
            self.proxies = [p for p in self.proxies if p['url'] != proxy_url]
            
            # Remove from health tracking
            if proxy_url in self.proxy_health:
                del self.proxy_health[proxy_url]
            
            logger.info(f"Removed proxy: {proxy_url}")
            return True
            
        except Exception as e:
            logger.error(f"Error removing proxy {proxy_url}: {e}")
            return False