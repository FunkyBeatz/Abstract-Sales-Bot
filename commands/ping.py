import discord
from discord import app_commands
from discord.ext import commands
import logging

# Set up logging to match main.py
logging.basicConfig(filename='./data/logs/bot.log',
                    level=logging.INFO,
                    format='%(asctime)s %(levelname)s: %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S')
logger = logging.getLogger(__name__)

class Ping(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="ping", description="Check if the bot is responsive")
    async def ping(self, interaction: discord.Interaction):
        """Simple ping command to check bot responsiveness"""
        try:
            # Calculate bot latency
            latency = round(self.bot.latency * 1000)
            logger.info(f"Ping command used by {interaction.user} with latency {latency}ms")

            await interaction.response.send_message(
                f"🏓 Pong! Bot latency is {latency}ms", 
                ephemeral=True
            )
        except Exception as e:
            logger.error(f"Error in ping command: {str(e)}")
            await interaction.response.send_message(
                "❌ Something went wrong processing your request.", 
                ephemeral=True
            )

async def setup(bot: commands.Bot):
    await bot.add_cog(Ping(bot))
    logger.info("Ping command loaded")