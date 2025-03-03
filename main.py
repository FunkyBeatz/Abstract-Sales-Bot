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


# Load all commands from /commands folder, skipping tracked_collections.py
async def load_commands():
    for filename in os.listdir("./commands"):
        if filename.endswith(".py") and filename != "tracked_collections.py":
            try:
                await bot.load_extension(f"commands.{filename[:-3]}")
                logger.info(f"Loaded {filename}")
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
                        print("No global commands found. Command sync may be failing.")
                else:
                    logger.error(f"Commands API status: {response.status}")
                    print(f"\n❌ Failed to check global commands: HTTP {response.status}")
        except Exception as e:
            logger.error(f"Failed to check Discord API status: {str(e)}")
            print(f"\n❌ API connection error: {str(e)}")


@bot.event
async def on_ready():
    try:
        # Debug: Check if bot.tree is initialized
        # Check if bot.application_id is None and handle or raise an error if necessary
        if bot.application_id is None:
            raise ValueError("Bot application_id is None, please ensure it is set correctly.")

        # Generate proper invite link with needed scopes
        invite_url = discord.utils.oauth_url(
            client_id=bot.application_id,  # Ensured to not be None
            permissions=discord.Permissions(
                send_messages=True,
                read_messages=True,
                embed_links=True,
                attach_files=True,
                read_message_history=True,
                use_application_commands=True
            ),
            scopes=["bot", "applications.commands"]
        )
        print(f"\n✅ Bot is ready! Connected as {bot.user.name}#{bot.user.discriminator}")
        print(f"\n⚠️ If slash commands aren't working, try reinviting the bot with this URL:")
        print(f"\n{invite_url}\n")
        print(f"This URL includes the 'applications.commands' scope which is required for slash commands.")
        
        # Check Discord API status before syncing
        await check_discord_api_status()

        # Attempt to sync commands with extended retry logic and 403 handling
        max_retries = 5  # Increased retries
        retry_delay = 10  # Increased delay for stability
        for attempt in range(max_retries):
            try:
                logger.debug(
                    f"Attempting to clear global commands (attempt {attempt + 1}/{max_retries})"
                )
                await bot.tree.clear_commands(guild=None) if bot.tree else None  # type: ignore
                logger.debug(
                    f"Attempting to sync commands globally (attempt {attempt + 1}/{max_retries})"
                )
                try:
                    synced = await bot.tree.sync()
                    
                    if not synced:
                        logger.warning("Command sync returned empty results; attempting manual command registration")
                        print("\n⚠️ Command syncing through discord.py returned empty results")
                        print("Attempting manual command registration as fallback...")
                except TypeError as e:
                    if "NoneType" in str(e):
                        logger.warning("Command sync returned None; attempting manual command registration")
                        print("\n⚠️ Command sync through discord.py returned None")
                        print("Attempting manual command registration as fallback...")
                        # Set synced to empty list to continue with manual registration
                        synced = []
                    
                    # Try to manually register the ping command via the API
                    try:
                        async with aiohttp.ClientSession() as session:
                            headers = {
                                'Authorization': f'Bot {config.BOT_TOKEN}',
                                'Content-Type': 'application/json'
                            }
                            command_data = {
                                "name": "ping",
                                "description": "Check if the bot is responsive",
                                "type": 1  # CHAT_INPUT
                            }
                            url = f'https://discord.com/api/v10/applications/{config.APPLICATION_ID}/commands'
                            
                            print(f"Manually registering command via API to: {url}")
                            print(f"Using command data: {command_data}")
                            
                            async with session.post(url, headers=headers, json=command_data) as response:
                                if response.status == 200 or response.status == 201:
                                    result = await response.json()
                                    logger.info(f"Manually registered ping command: {result['name']}")
                                    print(f"✅ Successfully registered ping command manually!")
                                else:
                                    error_text = await response.text()
                                    logger.error(f"Manual command registration failed: {response.status} - {error_text}")
                                    print(f"❌ Manual registration failed: HTTP {response.status}")
                                    print(f"   Error: {error_text}")
                    except Exception as e:
                        logger.error(f"Failed manual command registration: {str(e)}")
                        print(f"❌ Error during manual registration: {str(e)}")
                else:
                    logger.info(f"Synced {len(synced)} command(s) globally!")
                    print(f"\n✅ Successfully synced {len(synced)} command(s) globally!")
                break
            except discord.errors.HTTPException as e:
                if e.status == 403:
                    logger.error(
                        f"Discord HTTP 403 Forbidden during sync (attempt {attempt + 1}/{max_retries}): Bot lacks 'applications.commands' scope or permissions. Check OAuth2 invite and server permissions."
                    )
                elif e.status == 401:
                    logger.error(
                        f"Discord HTTP 401 Unauthorized during sync (attempt {attempt + 1}/{max_retries}): Invalid BOT_TOKEN. Check Replit Secrets."
                    )
                elif e.status == 429:
                    logger.error(
                        f"Discord HTTP 429 Too Many Requests during sync (attempt {attempt + 1}/{max_retries}): Rate limited. Retrying..."
                    )
                else:
                    logger.error(
                        f"Discord HTTP error during sync (attempt {attempt + 1}/{max_retries}): {str(e)}"
                    )
                if attempt < max_retries - 1:
                    logger.info(
                        f"Retrying command sync in {retry_delay} seconds...")
                    await asyncio.sleep(retry_delay)
                else:
                    raise
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
            f"Logged in as {bot.user.name}#{bot.user.discriminator} | Connected to Discord!" if bot.user else "Bot is not logged in | Connected to Discord!"
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
                logger.info(
                    f"Connecting to Discord... (Attempt {attempt + 1}/{max_retries})"
                )
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
