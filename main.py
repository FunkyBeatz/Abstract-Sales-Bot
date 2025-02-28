import discord
from discord import app_commands
from discord.ext import commands
import config
import os
import asyncio
from utils.sales_posting import monitor_sales
import logging

# Set up logging to both file and console with a clean format
logging.basicConfig(filename='./data/logs/bot.log',
                    level=logging.INFO,
                    format='%(asctime)s %(levelname)s: %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S')
logger = logging.getLogger(__name__)

# Configure discord.py logging to show purple messages in console
discord_logger = logging.getLogger('discord')
discord_logger.setLevel(logging.INFO)
discord_handler = logging.StreamHandler()
discord_handler.setFormatter(
    logging.Formatter('%(asctime)s %(name)s: %(message)s',
                      datefmt='%Y-%m-%d %H:%M:%S',
                      style='%'))
discord_logger.addHandler(discord_handler)

# Add console handler for custom logs with the same format
console_handler = logging.StreamHandler()
console_handler.setFormatter(
    logging.Formatter('%(asctime)s %(levelname)s: %(message)s',
                      datefmt='%Y-%m-%d %H:%M:%S',
                      style='%'))
logger.addHandler(console_handler)

# Enable bot with all necessary intents
intents = discord.Intents.all()
intents.message_content = True
intents.guilds = True
intents.guild_messages = True

# Initialize bot with application_id if available
if config.APPLICATION_ID:
    bot = commands.Bot(command_prefix='!',
                       intents=intents,
                       application_id=config.APPLICATION_ID)
else:
    logger.warning("APPLICATION_ID is not set. Some features may not work properly.")
    bot = commands.Bot(command_prefix='!',
                       intents=intents)


# Load all commands from /commands folder
async def load_commands():
    for filename in os.listdir("./commands"):
        if filename.endswith(".py"):
            try:
                await bot.load_extension(f"commands.{filename[:-3]}")
                logger.info(f"Loaded {filename}")
            except Exception as e:
                logger.error(f"Failed to load {filename}: {str(e)}")


@bot.event
async def on_ready():
    try:
        logger.info(
            f"Logged in as {bot.user.name}#{bot.user.discriminator} | Connected to Discord!"
        )
        
        # Check if APPLICATION_ID is properly set
        if not config.APPLICATION_ID:
            logger.warning("APPLICATION_ID is not set or invalid. Command syncing will not work.")
            logger.warning("Please set a valid APPLICATION_ID in your Replit Secrets.")
        else:
            # Debug: Check if bot.tree is initialized
            if bot.tree is None:
                logger.error(
                    "ApplicationCommandTree is None; check APPLICATION_ID and BOT_TOKEN"
                )
                raise ValueError("Bot command tree is not initialized")

            # Clear global commands before syncing
            await bot.tree.clear_commands(guild=None)
            # Sync commands globally
            synced = await bot.tree.sync()
            logger.info(f"Synced {len(synced)} command(s) globally!")

            logger.info("Available commands:")
            for command in bot.tree.get_commands():
                logger.info(f"  /{command.name}")

        # Start sales monitoring - continue regardless of command syncing
        bot.loop.create_task(monitor_sales(bot))
    except Exception as e:
        logger.error(f"Failed to sync commands: {str(e)}")


@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction,
                               error: app_commands.AppCommandError):
    error_message = "An error occurred while processing the command."

    try:
        if isinstance(error, app_commands.CommandOnCooldown):
            error_message = f"Command is on cooldown! Try again in {error.retry_after:.2f} seconds."

        logger.error(f"Command error: {str(error)}")

        try:
            if hasattr(interaction, 'response'):
                if not interaction.response.is_done():
                    await interaction.response.send_message(error_message,
                                                            ephemeral=True)
                else:
                    await interaction.followup.send(error_message,
                                                    ephemeral=True)
        except (discord.errors.InteractionNotFound, discord.errors.NotFound):
            logger.warning("Interaction expired or not found")
        except Exception as e:
            logger.error(f"Failed to send error message: {str(e)}")
    except Exception as e:
        logger.critical(f"Critical error in error handler: {str(e)}")


# Run the bot
async def main():
    max_retries = 5
    retry_delay = 5  # seconds

    for attempt in range(max_retries):
        try:
            async with bot:
                await load_commands()
                logger.info(
                    f"Connecting to Discord... (Attempt {attempt + 1}/{max_retries})"
                )
                await bot.start(config.BOT_TOKEN)
        except discord.errors.HTTPException as e:
            logger.error(f"Discord HTTP Error: {str(e)}")
            if attempt < max_retries - 1:
                logger.info(f"Retrying in {retry_delay} seconds...")
                await asyncio.sleep(retry_delay)
            continue
        except KeyboardInterrupt:
            logger.info("Shutting down...")
        except Exception as e:
            logger.error(f"Fatal error: {str(e)}")
        finally:
            if bot.is_ready():
                await bot.close()
                logger.info("Discord connection closed")
        break


if __name__ == "__main__":
    asyncio.run(main())
