
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
logging.basicConfig(
    filename='./data/logs/bot.log',
    level=logging.INFO,
    format='%(asctime)s %(levelname)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Configure discord.py logging to show purple messages in console
discord_logger = logging.getLogger('discord')
discord_logger.setLevel(logging.INFO)
discord_handler = logging.StreamHandler()
discord_handler.setFormatter(logging.Formatter('%(asctime)s %(name)s: %(message)s', datefmt='%Y-%m-%d %H:%M:%S', style='%'))
discord_logger.addHandler(discord_handler)

# Add console handler for custom logs with the same format
console_handler = logging.StreamHandler()
console_handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s: %(message)s', datefmt='%Y-%m-%d %H:%M:%S', style='%'))
logger.addHandler(console_handler)

# Enable bot with all necessary intents
intents = discord.Intents.all()
intents.message_content = True
intents.guilds = True
intents.guild_messages = True

# Ensure application_id is set and valid
if not config.APPLICATION_ID or config.APPLICATION_ID == 0:
    raise ValueError("APPLICATION_ID is missing or invalid in Replit Secrets or config.py")

try:
    application_id = int(config.APPLICATION_ID)  # Ensure it's an integer
    logger.debug(f"Initializing bot with APPLICATION_ID: {application_id}")
    logger.debug(f"BOT_TOKEN is set: {bool(config.BOT_TOKEN)}")
    logger.debug(f"Config values: BOT_TOKEN={config.BOT_TOKEN}, APPLICATION_ID={config.APPLICATION_ID}, GUILD_ID={config.GUILD_ID}")
    bot = commands.Bot(command_prefix='!', intents=intents, application_id=application_id)
except ValueError as e:
    logger.error(f"Invalid APPLICATION_ID: {str(e)}")
    raise ValueError("APPLICATION_ID must be a valid integer") from e

# Load all commands from /commands folder, handling renamed tracked_collectionsout.py
async def load_commands():
    for filename in os.listdir("./commands"):
        if filename.endswith(".py") and filename not in ["tracked_collections.py", "tracked_collectionsout.py"]:
            try:
                await bot.load_extension(f"commands.{filename[:-3]}")
                logger.info(f"Loaded {filename}")
            except Exception as e:
                logger.error(f"Failed to load {filename}: {str(e)}")
        elif filename == "tracked_collectionsout.py":
            try:
                await bot.load_extension(f"commands.{filename[:-3]}")
                logger.info(f"Loaded {filename} (renamed tracked_collections)")
            except Exception as e:
                logger.error(f"Failed to load {filename}: {str(e)}")

async def check_discord_api_status():
    """Check Discord API status to debug potential issues."""
    async with aiohttp.ClientSession() as session:
        try:
            # Check basic API connectivity
            async with session.get('https://discord.com/api/v10') as response:
                if response.status == 200:
                    logger.info("Discord API is reachable")
                else:
                    logger.error(f"Discord API status: {response.status}")

            # Check application commands endpoint with the bot token
            headers = {'Authorization': f'Bot {config.BOT_TOKEN}'}
            async with session.get(f'https://discord.com/api/v10/applications/{config.APPLICATION_ID}/commands', headers=headers) as response:
                if response.status == 200:
                    commands = await response.json()
                    logger.info(f"Bot has {len(commands)} global commands registered")
                    print(f"\n✅ Bot has {len(commands)} global commands registered on Discord's servers")
                    if len(commands) > 0:
                        print("Global commands found:")
                        for cmd in commands:
                            print(f" - /{cmd['name']}")
                    else:
                        print("No global commands found. Command sync may be failing or permissions/scopes are incorrect.")
                else:
                    logger.error(f"Commands API status: {response.status}")
                    print(f"\n❌ Failed to check global commands: HTTP {response.status}")
        except Exception as e:
            logger.error(f"Failed to check Discord API status: {str(e)}")
            print(f"\n❌ API connection error: {str(e)}")

async def manually_register_commands():
    """Manually register commands via Discord API as a fallback if sync fails."""
    async with aiohttp.ClientSession() as session:
        headers = {'Authorization': f'Bot {config.BOT_TOKEN}', 'Content-Type': 'application/json'}
        commands_data = [
            {
                "name": "ping",
                "description": "Check if the bot is online",
                "type": 1  # CHAT_INPUT
            },
            {
                "name": "start_track",
                "description": "Start tracking NFT sales for an Abstract collection",
                "type": 1,  # CHAT_INPUT
                "options": [
                    {
                        "name": "collection_address",
                        "description": "The address of the Abstract NFT collection",
                        "type": 3,  # STRING
                        "required": True
                    },
                    {
                        "name": "channel",
                        "description": "The Discord channel for sale notifications",
                        "type": 7,  # CHANNEL
                        "required": True
                    },
                    {
                        "name": "sales_threshold",
                        "description": "Minimum sales required to trigger notifications (default: 1)",
                        "type": 4,  # INTEGER
                        "required": False
                    }
                ]
            },
            {
                "name": "stop_track",
                "description": "Stop tracking NFT sales for an Abstract collection",
                "type": 1,  # CHAT_INPUT
                "options": [
                    {
                        "name": "collection_address",
                        "description": "The address of the Abstract NFT collection",
                        "type": 3,  # STRING
                        "required": True
                    }
                ]
            },
            {
                "name": "tracked_collectionsout",
                "description": "Show all currently tracked Abstract NFT collections",
                "type": 1  # CHAT_INPUT
            }
        ]
        url = f'https://discord.com/api/v10/applications/{config.APPLICATION_ID}/commands'

        for cmd_data in commands_data:
            try:
                async with session.post(url, headers=headers, json=cmd_data) as response:
                    if response.status in (200, 201):
                        result = await response.json()
                        logger.info(f"Manually registered command /{result['name']}")
                        print(f"✅ Successfully registered /{result['name']} manually!")
                    else:
                        error_text = await response.text()
                        logger.error(f"Manual command registration failed for /{cmd_data['name']}: {response.status} - {error_text}")
                        print(f"❌ Manual registration failed for /{cmd_data['name']}: HTTP {response.status}")
                        print(f"   Error: {error_text}")
            except Exception as e:
                logger.error(f"Failed manual command registration for /{cmd_data['name']}: {str(e)}")
                print(f"❌ Error during manual registration for /{cmd_data['name']}: {str(e)}")

@bot.event
async def on_ready():
    try:
        # Debug: Check if bot.tree is initialized
        if bot.tree is None:
            logger.error(f"ApplicationCommandTree is None; APPLICATION_ID={config.APPLICATION_ID}, BOT_TOKEN is set: {bool(config.BOT_TOKEN)}, bot.tree={bot.tree}")
            logger.debug(f"Bot object: {bot}")
            logger.debug(f"Bot intents: {bot.intents}")
            logger.debug(f"Bot application_id: {bot.application_id}")
            logger.debug(f"Bot user: {bot.user}")
            logger.debug(f"Config values in on_ready: BOT_TOKEN={config.BOT_TOKEN}, APPLICATION_ID={config.APPLICATION_ID}, GUILD_ID={config.GUILD_ID}")
            raise ValueError("Bot command tree is not initialized; check APPLICATION_ID and BOT_TOKEN")

        logger.info(f"Bot tree initialized: {bot.tree}")

        # Check Discord API status before syncing
        await check_discord_api_status()

        # Attempt to sync commands with extended retry logic, 403 handling, and manual fallback
        max_retries = 10  # Increased retries for cache refresh and stability
        retry_delay = 60  # Increased delay to 60 seconds for cache refresh and rate limits
        sync_succeeded = False
        for attempt in range(max_retries):
            try:
                logger.debug(f"Attempting to clear global commands (attempt {attempt + 1}/{max_retries})")
                await bot.tree.clear_commands(guild=None)
                logger.debug(f"Attempting to sync commands globally (attempt {attempt + 1}/{max_retries})")
                synced = await bot.tree.sync()
                if synced is None:
                    logger.warning(f"Command sync returned None (attempt {attempt + 1}/{max_retries}); attempting manual registration")
                    print(f"\n⚠️ Command sync returned None (attempt {attempt + 1}/{max_retries})")
                else:
                    logger.info(f"Synced {len(synced)} command(s) globally!")
                    print(f"\n✅ Successfully synced {len(synced)} command(s) globally!")
                    sync_succeeded = True
                    break
            except discord.errors.HTTPException as e:
                if e.status == 403:
                    logger.error(f"Discord HTTP 403 Forbidden during sync (attempt {attempt + 1}/{max_retries}): Bot lacks 'applications.commands' scope or permissions. Check OAuth2 invite, server permissions, and wait for cache refresh (up to 1 hour).")
                    print(f"\n❌ HTTP 403 Forbidden: Bot lacks 'applications.commands' scope or permissions (attempt {attempt + 1}/{max_retries}).")
                    print("Please verify the OAuth2 invite includes 'applications.commands' and the bot has 'Use Application Commands' permission.")
                elif e.status == 401:
                    logger.error(f"Discord HTTP 401 Unauthorized during sync (attempt {attempt + 1}/{max_retries}): Invalid BOT_TOKEN. Check Replit Secrets.")
                    print(f"\n❌ HTTP 401 Unauthorized: Invalid BOT_TOKEN (attempt {attempt + 1}/{max_retries}). Check Replit Secrets.")
                elif e.status == 429:
                    logger.error(f"Discord HTTP 429 Too Many Requests during sync (attempt {attempt + 1}/{max_retries}): Rate limited. Retrying after delay...")
                    print(f"\n⚠️ HTTP 429 Too Many Requests: Rate limited (attempt {attempt + 1}/{max_retries}). Retrying...")
                else:
                    logger.error(f"Discord HTTP error during sync (attempt {attempt + 1}/{max_retries}): {str(e)}")
                    print(f"\n❌ HTTP Error during sync (attempt {attempt + 1}/{max_retries}): {str(e)}")
                if attempt < max_retries - 1:
                    logger.info(f"Retrying command sync in {retry_delay} seconds (waiting for cache refresh or rate limit reset)...")
                    print(f"Retrying command sync in {retry_delay} seconds...")
                    await asyncio.sleep(retry_delay)
                else:
                    raise
            except TypeError as e:
                if "NoneType" in str(e):
                    logger.error(f"Sync failed due to NoneType (attempt {attempt + 1}/{max_retries}): {str(e)}")
                    print(f"\n⚠️ Sync failed due to NoneType (attempt {attempt + 1}/{max_retries}): {str(e)}")
                else:
                    logger.error(f"Sync failed (attempt {attempt + 1}/{max_retries}): {str(e)}")
                    print(f"\n⚠️ Sync failed (attempt {attempt + 1}/{max_retries}): {str(e)}")
                if attempt < max_retries - 1:
                    logger.info(f"Retrying command sync in {retry_delay} seconds (waiting for cache refresh or rate limit reset)...")
                    print(f"Retrying command sync in {retry_delay} seconds...")
                    await asyncio.sleep(retry_delay)
                else:
                    logger.warning("Max retries reached for command sync; attempting manual registration as fallback")
                    print("\n⚠️ Max retries reached for command sync; attempting manual registration as fallback...")
                    await manually_register_commands()
            except Exception as e:
                logger.error(f"Unexpected error during sync (attempt {attempt + 1}/{max_retries}): {str(e)}")
                print(f"\n❌ Unexpected error during sync (attempt {attempt + 1}/{max_retries}): {str(e)}")
                if attempt < max_retries - 1:
                    logger.info(f"Retrying command sync in {retry_delay} seconds (waiting for cache refresh or rate limit reset)...")
                    print(f"Retrying command sync in {retry_delay} seconds...")
                    await asyncio.sleep(retry_delay)
                else:
                    logger.warning("Max retries reached for command sync; attempting manual registration as fallback")
                    print("\n⚠️ Max retries reached for command sync; attempting manual registration as fallback...")
                    await manually_register_commands()

        if not sync_succeeded:
            logger.warning("Command sync failed after all retries; manual registration attempted but commands may not work until permissions/scopes are corrected.")
            print("\n⚠️ Command sync failed after all retries; manual registration attempted but commands may not work until permissions/scopes are corrected.")

        logger.info(f"Logged in as {bot.user.name}#{bot.user.discriminator} | Connected to Discord!" if bot.user else "Bot is not logged in | Connected to Discord!")

        # Only log available commands if bot.tree exists
        if bot.tree is not None:
            logger.info("Available commands:")
            for command in bot.tree.get_commands():
                logger.info(f"  /{command.name}")
        else:
            logger.warning("Cannot list available commands: bot.tree is None")

        # Start sales monitoring
        logger.info("Starting sales monitoring for Abstract collections")
        bot.loop.create_task(monitor_sales(bot))
    except Exception as e:
        logger.error(f"Failed to sync commands: {str(e)}")
        logger.warning("Bot will continue to run, but slash commands may not work.")

@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    error_message = "An error occurred while processing the command."

    try:
        if isinstance(error, app_commands.CommandOnCooldown):
            error_message = f"Command is on cooldown! Try again in {error.retry_after:.2f} seconds."

        logger.error(f"Command error: {str(error)}")

        try:
            if hasattr(interaction, 'response'):
                if not interaction.response.is_done():
                    await interaction.response.send_message(error_message, ephemeral=True)
                else:
                    await interaction.followup.send(error_message, ephemeral=True)
        except (discord.errors.InteractionNotFound, discord.errors.NotFound, discord.errors.HTTPException):
            logger.warning("Interaction expired or not found")
        except Exception as e:
            logger.error(f"Failed to send error message: {str(e)}")
    except Exception as e:
        logger.critical(f"Critical error in error handler: {str(e)}")

# Run the bot
async def main():
    max_retries = 5
    retry_delay = 5  # seconds

    # Validate token first
    if not config.BOT_TOKEN:
        logger.critical("BOT_TOKEN is missing. Please add it to your Replit Secrets.")
        print("\n⚠️ ERROR: BOT_TOKEN is missing! Please add your Discord bot token to Replit Secrets.\n")
        return

    # Print important bot info on startup
    print("\n====== DISCORD BOT CONFIGURATION ======")
    print(f"APPLICATION_ID: {config.APPLICATION_ID}")
    print(f"GUILD_ID: {config.GUILD_ID or 'Not set (using global commands)'}")
    print(f"BOT_TOKEN: {'✓ Set (hidden for security)' if config.BOT_TOKEN else '✗ Missing'}")
    print("======================================\n")

    # Check if token looks valid (basic format check)
    if len(config.BOT_TOKEN) < 50 or "." not in config.BOT_TOKEN:
        logger.critical("BOT_TOKEN appears to be invalid (wrong format).")
        print("\n⚠️ ERROR: BOT_TOKEN appears to be invalid. Token should be longer and contain periods.\n")
        print("Please check your Discord Developer Portal and ensure you've copied the entire token correctly.")
        return

    for attempt in range(max_retries):
        try:
            async with bot:
                await load_commands()
                logger.info(f"Connecting to Discord... (Attempt {attempt + 1}/{max_retries})")
                print(f"\nAttempting to connect to Discord... (Attempt {attempt + 1}/{max_retries})")
                await bot.start(config.BOT_TOKEN)
        except discord.errors.LoginFailure as e:
            logger.critical(f"Authentication failed: {str(e)}")
            print(f"\n❌ AUTHENTICATION FAILED: {str(e)}")
            print("Your bot token is invalid. Please generate a new token in the Discord Developer Portal.")
            print("Then update it in your Replit Secrets with the key 'DISCORD_BOT_TOKEN'")
            return  # Stop retrying on auth failure
        except discord.errors.HTTPException as e:
            logger.error(f"Discord HTTP Error: {str(e)}")
            print(f"\n⚠️ Discord API Error: {str(e)}")
            if attempt < max_retries - 1:
                logger.info(f"Retrying in {retry_delay} seconds...")
                print(f"Retrying in {retry_delay} seconds...")
                await asyncio.sleep(retry_delay)
            continue
        except KeyboardInterrupt:
            logger.info("Shutting down...")
            print("Shutting down...")
        except Exception as e:
            logger.error(f"Fatal error: {str(e)}")
            print(f"\n❌ Fatal error: {str(e)}")
        finally:
            if bot.is_ready():
                await bot.close()
                logger.info("Discord connection closed")
        break

if __name__ == "__main__":
    asyncio.run(main())
