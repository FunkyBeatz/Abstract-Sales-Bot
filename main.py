import discord
from discord import app_commands
from discord.ext import commands
import config
import os
import asyncio
from utils.sales_posting import monitor_sales
import logging

# Set up logging
logging.basicConfig(filename='./data/logs/bot.log',
                    level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Enable bot with all necessary intents
intents = discord.Intents.all()
intents.message_content = True
intents.guilds = True
intents.guild_messages = True

bot = commands.Bot(command_prefix='!',
                   intents=intents,
                   application_id=config.APPLICATION_ID)


# Load all commands from /commands folder
async def load_commands():
    for filename in os.listdir("./commands"):
        if filename.endswith(".py"):
            try:
                await bot.load_extension(f"commands.{filename[:-3]}")
                logger.info(f"✅ Loaded {filename}")
            except Exception as e:
                logger.error(f"❌ Failed to load {filename}: {e}")


@bot.event
async def on_ready():
    try:
        if config.GUILD_ID:
            guild = discord.Object(id=config.GUILD_ID)
            # Clear existing guild commands before syncing new ones
            await bot.tree.clear_commands(guild=guild)
            bot.tree.copy_global_to(guild=guild)
            synced = await bot.tree.sync(guild=guild)
            logger.info(f"✅ Logged in as {bot.user}")
            logger.info(
                f"🔄 Synced {len(synced)} command(s) to guild {config.GUILD_ID}!"
            )
        else:
            # Clear global commands before syncing (optional, use cautiously)
            await bot.tree.clear_commands(guild=None)
            synced = await bot.tree.sync()
            logger.info(f"✅ Logged in as {bot.user}")
            logger.info(f"🔄 Synced {len(synced)} command(s) globally!")

        logger.info("📝 Available commands:")
        for command in bot.tree.get_commands():
            logger.info(f"  /{command.name}")

        # Start sales monitoring
        bot.loop.create_task(monitor_sales(bot))
    except Exception as e:
        logger.error(f"❌ Failed to sync commands: {e}")


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
            logger.error(f"Failed to send error message: {e}")
    except Exception as e:
        logger.critical(f"Critical error in error handler: {e}")


# Run the bot
async def main():
    max_retries = 5
    retry_delay = 5  # seconds

    for attempt in range(max_retries):
        try:
            async with bot:
                await load_commands()
                logger.info(
                    f"🔄 Connecting to Discord... (Attempt {attempt + 1}/{max_retries})"
                )
                await bot.start(config.BOT_TOKEN)
        except discord.errors.HTTPException as e:
            logger.error(f"Discord HTTP Error: {e}")
            if attempt < max_retries - 1:
                logger.info(f"Retrying in {retry_delay} seconds...")
                await asyncio.sleep(retry_delay)
            continue
        except KeyboardInterrupt:
            logger.info("Shutting down...")
        except Exception as e:
            logger.error(f"Fatal error: {e}")
        finally:
            if bot.is_ready():
                await bot.close()
                logger.info("Discord connection closed")
        break


if __name__ == "__main__":
    asyncio.run(main())
