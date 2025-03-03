
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
            synced = await self.bot.tree.sync()
            
            if synced:
                await ctx.send(f"✅ Successfully synced {len(synced)} commands globally!")
                logger.info(f"Force synced {len(synced)} commands")
            else:
                await ctx.send("⚠️ Sync completed but returned empty results.")
                logger.warning("Force sync returned empty results")
                
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
