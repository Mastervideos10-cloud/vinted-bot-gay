"""
Discord Bot Implementation for Vinted Monitoring
Handles Discord interactions, commands, and monitoring tasks
"""

import asyncio
import logging
import discord
from discord.ext import commands, tasks
from typing import Dict, List, Optional
import json
import re
from datetime import datetime, timedelta

from vinted_scraper import VintedScraper
from database import Database
from config import Config
from utils import format_price, get_flag_emoji, create_embed

logger = logging.getLogger(__name__)

class VintedBot:
    def __init__(self, config: Config, database: Database):
        self.config = config
        self.db = database
        self.scraper = VintedScraper(config)
        
        # Configure Discord intents
        intents = discord.Intents.default()
        intents.message_content = True
        intents.guilds = True
        intents.guild_messages = True
        intents.members = False  # Disable privileged intents
        intents.presences = False  # Disable privileged intents
        
        # Initialize bot
        self.bot = commands.Bot(
            command_prefix='!',
            intents=intents,
            help_command=None
        )
        
        # Track monitored channels and their last check times
        self.monitored_channels: Dict[int, Dict] = {}
        self.setup_events()
        self.setup_commands()
    
    def setup_events(self):
        """Setup Discord bot events"""
        
        @self.bot.event
        async def on_ready():
            logger.info(f'{self.bot.user} has connected to Discord!')
            logger.info(f'Bot is in {len(self.bot.guilds)} guilds')
            
            # Start monitoring task
            if not self.monitor_vinted.is_running():
                self.monitor_vinted.start()
        
        @self.bot.event
        async def on_error(event, *args, **kwargs):
            logger.error(f'Discord error in {event}: {args}, {kwargs}')
    
    def setup_commands(self):
        """Setup Discord bot commands"""
        
        @self.bot.command(name='add_search')
        async def add_search(ctx, *, search_url: str):
            """Add a Vinted search URL to monitor in this channel"""
            if not await self.check_permissions(ctx):
                return
            
            try:
                # Validate Vinted URL
                if not self.is_valid_vinted_url(search_url):
                    await ctx.send("❌ Invalid Vinted URL. Please provide a valid Vinted search link.")
                    return
                
                # Extract domain and location
                domain = self.extract_domain(search_url)
                location = domain.split('.')[-1] if '.' in domain else 'com'
                
                # Save to database
                await self.db.add_search_url(
                    channel_id=ctx.channel.id,
                    search_url=search_url,
                    domain=domain,
                    location=location,
                    added_by=ctx.author.id
                )
                
                flag = get_flag_emoji(location)
                embed = discord.Embed(
                    title="✅ Search Added Successfully",
                    description=f"Now monitoring Vinted listings from {flag} {domain}",
                    color=0x00ff00
                )
                embed.add_field(name="Search URL", value=f"[View Search]({search_url})", inline=False)
                embed.add_field(name="Channel", value=ctx.channel.mention, inline=True)
                embed.add_field(name="Added by", value=ctx.author.mention, inline=True)
                
                await ctx.send(embed=embed)
                
                # Add channel to monitoring if not already present
                if ctx.channel.id not in self.monitored_channels:
                    self.monitored_channels[ctx.channel.id] = {
                        'last_check': datetime.utcnow(),
                        'search_urls': []
                    }
                
            except Exception as e:
                logger.error(f"Error adding search URL: {e}")
                await ctx.send("❌ Failed to add search URL. Please try again.")
        
        @self.bot.command(name='remove_search')
        async def remove_search(ctx, search_id: int):
            """Remove a search URL by ID"""
            if not await self.check_permissions(ctx):
                return
            
            try:
                success = await self.db.remove_search_url(search_id, ctx.channel.id)
                if success:
                    embed = discord.Embed(
                        title="✅ Search Removed",
                        description=f"Search ID {search_id} has been removed from monitoring.",
                        color=0xff9900
                    )
                else:
                    embed = discord.Embed(
                        title="❌ Search Not Found",
                        description=f"No search found with ID {search_id} in this channel.",
                        color=0xff0000
                    )
                
                await ctx.send(embed=embed)
                
            except Exception as e:
                logger.error(f"Error removing search URL: {e}")
                await ctx.send("❌ Failed to remove search URL. Please try again.")
        
        @self.bot.command(name='list_searches')
        async def list_searches(ctx):
            """List all active searches in this channel"""
            try:
                searches = await self.db.get_channel_searches(ctx.channel.id)
                
                if not searches:
                    embed = discord.Embed(
                        title="📋 No Active Searches",
                        description="No Vinted searches are currently active in this channel.\nUse `!add_search <url>` to add one.",
                        color=0x999999
                    )
                else:
                    embed = discord.Embed(
                        title="📋 Active Searches",
                        description=f"Found {len(searches)} active search(es) in this channel:",
                        color=0x0099ff
                    )
                    
                    for search in searches[:10]:  # Limit to 10 to avoid embed size limits
                        flag = get_flag_emoji(search['location'])
                        embed.add_field(
                            name=f"{flag} Search ID: {search['id']}",
                            value=f"[View Search]({search['search_url']})\nAdded: {search['created_at'][:10]}",
                            inline=False
                        )
                
                await ctx.send(embed=embed)
                
            except Exception as e:
                logger.error(f"Error listing searches: {e}")
                await ctx.send("❌ Failed to retrieve search list. Please try again.")
        
        @self.bot.command(name='add_filter')
        async def add_filter(ctx, filter_type: str, *, filter_value: str):
            """Add a filter for this channel (price_min, price_max, brand, size, condition)"""
            if not await self.check_permissions(ctx):
                return
            
            valid_filters = ['price_min', 'price_max', 'brand', 'size', 'condition']
            if filter_type not in valid_filters:
                await ctx.send(f"❌ Invalid filter type. Valid types: {', '.join(valid_filters)}")
                return
            
            try:
                await self.db.add_filter(ctx.channel.id, filter_type, filter_value)
                
                embed = discord.Embed(
                    title="✅ Filter Added",
                    description=f"Added {filter_type} filter: **{filter_value}**",
                    color=0x00ff00
                )
                embed.add_field(name="Channel", value=ctx.channel.mention, inline=True)
                embed.add_field(name="Added by", value=ctx.author.mention, inline=True)
                
                await ctx.send(embed=embed)
                
            except Exception as e:
                logger.error(f"Error adding filter: {e}")
                await ctx.send("❌ Failed to add filter. Please try again.")
        
        @self.bot.command(name='help')
        async def help_command(ctx):
            """Show help information"""
            embed = discord.Embed(
                title="🤖 Vinted Bot Commands",
                description="Monitor Vinted listings with advanced filtering and instant notifications",
                color=0x0099ff
            )
            
            commands_info = [
                ("!add_search <url>", "Add a Vinted search URL to monitor"),
                ("!remove_search <id>", "Remove a search by ID"),
                ("!list_searches", "List all active searches in this channel"),
                ("!add_filter <type> <value>", "Add filter (price_min/max, brand, size, condition)"),
                ("!help", "Show this help message")
            ]
            
            for cmd, desc in commands_info:
                embed.add_field(name=cmd, value=desc, inline=False)
            
            embed.add_field(
                name="📡 Features",
                value="• Real-time monitoring\n• Multi-proxy support\n• Interactive buttons\n• Advanced filtering\n• Multi-domain support",
                inline=False
            )
            
            await ctx.send(embed=embed)
    
    async def check_permissions(self, ctx) -> bool:
        """Check if user has permissions to use bot commands"""
        # Check if user has admin role or is in allowed channel
        if self.config.DISCORD_ROLE_ADMIN_ID:
            admin_role = discord.utils.get(ctx.guild.roles, id=int(self.config.DISCORD_ROLE_ADMIN_ID))
            if admin_role in ctx.author.roles:
                return True
        
        # Check if in command channel
        if self.config.DISCORD_COMMAND_CHANNEL_ID:
            if ctx.channel.id == int(self.config.DISCORD_COMMAND_CHANNEL_ID):
                return True
        
        # Allow in thread channels created from the main thread channel
        if self.config.DISCORD_THREAD_CHANNEL_ID:
            if (hasattr(ctx.channel, 'parent') and 
                ctx.channel.parent and 
                ctx.channel.parent.id == int(self.config.DISCORD_THREAD_CHANNEL_ID)):
                return True
        
        await ctx.send("❌ You don't have permission to use this command in this channel.")
        return False
    
    def is_valid_vinted_url(self, url: str) -> bool:
        """Validate if URL is a valid Vinted search URL"""
        vinted_pattern = r'https?://www\.vinted\.[a-z]{2,3}/catalog\?'
        return bool(re.match(vinted_pattern, url))
    
    def extract_domain(self, url: str) -> str:
        """Extract domain from Vinted URL"""
        match = re.search(r'https?://([^/]+)', url)
        return match.group(1) if match else 'www.vinted.com'
    
    @tasks.loop(seconds=30)  # Check every 30 seconds
    async def monitor_vinted(self):
        """Main monitoring loop for Vinted listings"""
        try:
            # Get all active searches from database
            searches = await self.db.get_all_active_searches()
            
            for search in searches:
                try:
                    channel = self.bot.get_channel(search['channel_id'])
                    if not channel:
                        continue
                    
                    # Get new listings
                    listings = await self.scraper.get_new_listings(
                        search['search_url'],
                        last_check=search.get('last_check')
                    )
                    
                    # Apply filters
                    filtered_listings = await self.apply_filters(
                        listings, 
                        search['channel_id']
                    )
                    
                    # Send new listings to Discord
                    for listing in filtered_listings:
                        await self.send_listing_embed(channel, listing, search)
                    
                    # Update last check time
                    await self.db.update_search_last_check(search['id'])
                    
                except Exception as e:
                    logger.error(f"Error monitoring search {search['id']}: {e}")
                    continue
            
        except Exception as e:
            logger.error(f"Error in monitoring loop: {e}")
    
    async def apply_filters(self, listings: List[Dict], channel_id: int) -> List[Dict]:
        """Apply channel-specific filters to listings"""
        try:
            filters = await self.db.get_channel_filters(channel_id)
            if not filters:
                return listings
            
            filtered_listings = []
            
            for listing in listings:
                should_include = True
                
                for filter_item in filters:
                    filter_type = filter_item['filter_type']
                    filter_value = filter_item['filter_value']
                    
                    if filter_type == 'price_min':
                        if listing.get('price', 0) < float(filter_value):
                            should_include = False
                            break
                    elif filter_type == 'price_max':
                        if listing.get('price', 0) > float(filter_value):
                            should_include = False
                            break
                    elif filter_type == 'brand':
                        if filter_value.lower() not in listing.get('brand', '').lower():
                            should_include = False
                            break
                    elif filter_type == 'size':
                        if filter_value.lower() != listing.get('size', '').lower():
                            should_include = False
                            break
                    elif filter_type == 'condition':
                        if filter_value.lower() not in listing.get('condition', '').lower():
                            should_include = False
                            break
                
                if should_include:
                    filtered_listings.append(listing)
            
            return filtered_listings
            
        except Exception as e:
            logger.error(f"Error applying filters: {e}")
            return listings
    
    async def send_listing_embed(self, channel, listing: Dict, search: Dict):
        """Send a rich embed for a new Vinted listing"""
        try:
            embed = create_embed(listing, search)
            
            # Create interactive buttons
            view = VintedListingView(listing, self.config)
            
            message = await channel.send(embed=embed, view=view)
            
            # Store message for potential updates
            await self.db.store_listing_message(
                listing['id'],
                channel.id,
                message.id,
                listing
            )
            
        except Exception as e:
            logger.error(f"Error sending listing embed: {e}")
    
    async def start(self):
        """Start the Discord bot"""
        try:
            await self.bot.start(self.config.DISCORD_TOKEN)
        except discord.LoginFailure:
            logger.error("Invalid Discord token provided")
            raise
        except Exception as e:
            logger.error(f"Failed to start bot: {e}")
            raise

class VintedListingView(discord.ui.View):
    """Interactive view with buttons for Vinted listings"""
    
    def __init__(self, listing: Dict, config: Config):
        super().__init__(timeout=3600)  # 1 hour timeout
        self.listing = listing
        self.config = config
    
    @discord.ui.button(label='🛒 Autobuy', style=discord.ButtonStyle.success)
    async def autobuy(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Handle autobuy button click"""
        await interaction.response.send_message(
            f"🛒 Autobuy feature is being developed. Item: {self.listing.get('title', 'Unknown')}", 
            ephemeral=True
        )
    
    @discord.ui.button(label='🎯 Smart Offer', style=discord.ButtonStyle.primary)
    async def smart_offer(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Handle smart offer button click"""
        await interaction.response.send_message(
            f"🎯 Smart offer feature is being developed. Item: {self.listing.get('title', 'Unknown')}", 
            ephemeral=True
        )
    
    @discord.ui.button(label='💬 Message', style=discord.ButtonStyle.secondary)
    async def message_seller(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Handle message seller button click"""
        await interaction.response.send_message(
            f"💬 Messaging feature is being developed. Seller: {self.listing.get('seller', 'Unknown')}", 
            ephemeral=True
        )
    
    @discord.ui.button(label='🛍️ Buy', style=discord.ButtonStyle.danger)
    async def buy_direct(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Handle direct buy button click"""
        item_url = self.listing.get('url', '#')
        await interaction.response.send_message(
            f"🛍️ [Click here to buy on Vinted]({item_url})", 
            ephemeral=True
        )