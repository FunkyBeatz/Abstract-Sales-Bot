import discord
from discord import app_commands
from discord.ext import commands
import config
import os
import asyncio
from utils.sales_posting import monitor_sales
import logging
import aiohttp  # For checking Discord API status

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

# Ensure application_id is set and valid
if not config.APPLICATION_ID or config.APPLICATION_ID == 0:
    raise ValueError(
        "APPLICATION_ID is missing or invalid in Replit Secrets or config.py")

try:
    application_id = int(config.APPLICATION_ID)  # Ensure it's an integer
    logger.debug(f"Initializing bot with APPLICATION_ID: {application_id}")
    logger.debug(f"BOT_TOKEN is set: {bool(config.BOT_TOKEN)}")
    logger.debug(
        f"Config values: BOT_TOKEN={config.BOT_TOKEN}, APPLICATION_ID={config.APPLICATION_ID}, GUILD_ID={config.GUILD_ID}"
    )
    bot = commands.Bot(command_prefix='!',
                       intents=intents,
                       application_id=application_id)
except ValueError as e:
    logger.error(f"Invalid APPLICATION_ID: {str(e)}")
    raise ValueError("APPLICATION_ID must be a valid integer") from e


# Load all commands from /commands folder
async def load_commands():
    for filename in os.listdir("./commands"):
        if filename.endswith(".py"):
            try:
                await bot.load_extension(f"commands.{filename[:-3]}")
                logger.info(f"Loaded {filename}")
            except Exception as e:
                logger.error(f"Failed to load {filename}: {str(e)}")


async def check_discord_api_status():
    """Check Discord API status to debug potential issues."""
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get('https://discord.com/api/v10') as response:
                if response.status == 200:
                    logger.info("Discord API is reachable")
                else:
                    logger.error(f"Discord API status: {response.status}")
        except Exception as e:
            logger.error(f"Failed to check Discord API status: {str(e)}")


@bot.event
async def on_ready():
    try:
        # Debug: Check if bot.tree is initialized
        if bot.tree is None:
            logger.error(
                f"ApplicationCommandTree is None; APPLICATION_ID={config.APPLICATION_ID}, BOT_TOKEN is set: {bool(config.BOT_TOKEN)}, bot.tree={bot.tree}"
            )
            logger.debug(f"Bot object: {bot}")
            logger.debug(f"Bot intents: {bot.intents}")
            logger.debug(f"Bot application_id: {bot.application_id}")
            logger.debug(f"Bot user: {bot.user}")
            logger.debug(
                f"Config values in on_ready: BOT_TOKEN={config.BOT_TOKEN}, APPLICATION_ID={config.APPLICATION_ID}, GUILD_ID={config.GUILD_ID}"
            )
            raise ValueError(
                "Bot command tree is not initialized; check APPLICATION_ID and BOT_TOKEN"
            )

        logger.info(f"Bot tree initialized: {bot.tree}")

        # Check Discord API status before syncing
        await check_discord_api_status()

        # Attempt to sync commands with extended retry logic
        max_retries = 5  # Increased retries
        retry_delay = 10  # Increased delay for stability
        for attempt in range(max_retries):
            try:
                logger.debug(
                    f"Attempting to clear global commands (attempt {attempt + 1}/{max_retries})"
                )
                await bot.tree.clear_commands(guild=None)
                logger.debug(
                    f"Attempting to sync commands globally (attempt {attempt + 1}/{max_retries})"
                )
                synced = await bot.tree.sync()
                logger.info(f"Synced {len(synced)} command(s) globally!")
                break
            except TypeError as e:
                if "NoneType" in str(e):
                    logger.error(
                        f"Sync failed due to NoneType (attempt {attempt + 1}/{max_retries}): {str(e)}"
                    )
                else:
                    logger.error(
                        f"Sync failed (attempt {attempt + 1}/{max_retries}): {str(e)}"
                    )
                if attempt < max_retries - 1:
                    logger.info(
                        f"Retrying command sync in {retry_delay} seconds...")
                    await asyncio.sleep(retry_delay)
                else:
                    raise
            except discord.errors.HTTPException as e:
                logger.error(
                    f"Discord HTTP error during sync (attempt {attempt + 1}/{max_retries}): {str(e)}"
                )
                if attempt < max_retries - 1:
                    logger.info(
                        f"Retrying command sync in {retry_delay} seconds...")
                    await asyncio.sleep(retry_delay)
                else:
                    raise
            except Exception as e:
                logger.error(
                    f"Unexpected error during sync (attempt {attempt + 1}/{max_retries}): {str(e)}"
                )
                if attempt < max_retries - 1:
                    logger.info(
                        f"Retrying command sync in {retry_delay} seconds...")
                    await asyncio.sleep(retry_delay)
                else:
                    raise

        logger.info(
            f"Logged in as {bot.user.name}#{bot.user.discriminator} | Connected to Discord!"
        )

        logger.info("Available commands:")
        for command in bot.tree.get_commands():
            logger.info(f"  /{command.name}")

        # Start sales monitoring
        logger.info("Starting sales monitoring for Abstract collections")
        bot.loop.create_task(monitor_sales(bot))
    except Exception as e:
        logger.error(f"Failed to sync commands: {str(e)}")
        logger.warning(
            "Bot will continue to run, but slash commands may not work.")


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
