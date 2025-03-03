
import discord
from discord import app_commands
from discord.ext import commands
import logging
import aiohttp
import config

# Set up logging
logging.basicConfig(filename='./data/logs/bot.log',
                    level=logging.INFO,
                    format='%(asctime)s %(levelname)s: %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S')
logger = logging.getLogger(__name__)

class Sync(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        
    @commands.command(name="forcesync")
    @commands.is_owner()
    async def force_sync(self, ctx):
        """Force syncs commands (prefix command)"""
        try:
            await ctx.send("Attempting to force sync commands...")
            
            # Clear and sync commands
            await self.bot.tree.clear_commands(guild=None)
            
            try:
                synced = await self.bot.tree.sync()
                
                if synced:
                    await ctx.send(f"✅ Successfully synced {len(synced)} commands globally!")
                    logger.info(f"Force synced {len(synced)} commands")
                else:
                    await ctx.send("⚠️ Sync completed but returned empty results.")
                    logger.warning("Force sync returned empty results")
            except TypeError as e:
                if "NoneType" in str(e):
                    await ctx.send("⚠️ Sync returned None. Attempting manual registration...")
                    logger.warning("Force sync returned None")
                    
                    # Manual registration fallback
                    try:
                        async with aiohttp.ClientSession() as session:
                            headers = {'Authorization': f'Bot {config.BOT_TOKEN}', 'Content-Type': 'application/json'}
                            command_data = {"name": "ping", "description": "Check if the bot is responsive", "type": 1}
                            url = f'https://discord.com/api/v10/applications/{config.APPLICATION_ID}/commands'
                            
                            async with session.post(url, headers=headers, json=command_data) as response:
                                if response.status == 200 or response.status == 201:
                                    await ctx.send("✅ Manually registered ping command!")
                                else:
                                    error_text = await response.text()
                                    await ctx.send(f"❌ Manual registration failed: HTTP {response.status}\n```{error_text}```")
                    except Exception as manual_error:
                        await ctx.send(f"❌ Manual registration error: {str(manual_error)}")
                
            # Check API for commands
            async with aiohttp.ClientSession() as session:
                headers = {'Authorization': f'Bot {config.BOT_TOKEN}'}
                async with session.get(f'https://discord.com/api/v10/applications/{config.APPLICATION_ID}/commands', headers=headers) as response:
                    if response.status == 200:
                        commands = await response.json()
                        await ctx.send(f"🔍 Discord API shows {len(commands)} global commands registered")
                    else:
                        await ctx.send(f"❌ Failed to check global commands: HTTP {response.status}")
                        
        except Exception as e:
            logger.error(f"Error in forcesync: {str(e)}")
            await ctx.send(f"❌ Error: {str(e)}")

async def setup(bot: commands.Bot):
    await bot.add_cog(Sync(bot))
    logger.info("Sync command loaded")
