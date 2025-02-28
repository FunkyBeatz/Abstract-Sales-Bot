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


class PingCommand(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="ping",
                          description="Check if the bot is online")
    @app_commands.checks.cooldown(1, 1.0)  # 1 use every second
    async def ping(self, interaction: discord.Interaction):
        """Sends a ping response with bot latency and status."""
        try:
            # Check if interaction is still valid
            if not hasattr(interaction,
                           'response') or interaction.response.is_done():
                logger.warning(
                    "Interaction expired or invalid for ping command")
                return

            await interaction.response.defer(ephemeral=True)

            # Get and round latency to milliseconds
            latency = round(self.bot.latency *
                            1000) if self.bot.latency is not None else -1
            if latency < 0:
                status = "🔴"
                latency_message = "Unknown (bot latency unavailable)"
            else:
                status = "🟢" if latency < 1000 else "🟡" if latency < 3000 else "🔴"
                latency_message = f"`{latency}ms`"

            # Send response with status and latency
            await interaction.followup.send(
                f"{status} Pong! Bot latency: {latency_message}",
                ephemeral=True)
            logger.info(
                f"Ping command used by {interaction.user} (ID: {interaction.user.id}) - Latency: {latency_message}"
            )
        except discord.errors.InteractionResponded:
            logger.warning("Interaction already responded for ping command")
        except Exception as e:
            logger.error(f"Error in ping command: {str(e)}")
            try:
                if not interaction.response.is_done():
                    await interaction.response.send_message(
                        "An error occurred while processing the command.",
                        ephemeral=True)
                else:
                    await interaction.followup.send(
                        "An error occurred while processing the command.",
                        ephemeral=True)
            except Exception as follow_up_error:
                logger.error(
                    f"Failed to send error message: {str(follow_up_error)}")


async def setup(bot):
    await bot.add_cog(PingCommand(bot))
