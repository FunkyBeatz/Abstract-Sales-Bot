import discord
from discord import app_commands
from discord.ext import commands
import json
import os
import asyncio
import logging

# Set up logging to match main.py
logging.basicConfig(filename='./data/logs/bot.log',
                    level=logging.INFO,
                    format='%(asctime)s %(levelname)s: %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S')
logger = logging.getLogger(__name__)

DATA_FILE = "./data/tracked_collections.json"
lock = asyncio.Lock()  # Thread-safe file access


class StopSale(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(
        name="stop_track",
        description="Stop tracking NFT sales for an Abstract collection")
    @app_commands.checks.cooldown(1, 2.0)  # 1 use every 2 seconds
    async def stop_track(self, interaction: discord.Interaction,
                         collection_address: str):
        """Command to stop tracking an Abstract NFT collection.

        Args:
            interaction: The Discord interaction triggering the command.
            collection_address: The address of the Abstract NFT collection to stop tracking (e.g., '0x...').
        """
        try:
            await interaction.response.defer(ephemeral=True)

            # Ensure Data directory exists
            os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)

            async with lock:  # Use lock for thread-safe JSON access
                # Load or initialize tracked_collections with debugging
                tracked_collections = {}
                if os.path.exists(DATA_FILE):
                    try:
                        with open(DATA_FILE, "r") as file:
                            content = file.read().strip()
                            if content:  # Check if file has content
                                tracked_collections = json.load(file)
                                logger.info(
                                    f"Loaded tracked_collections.json: {tracked_collections}"
                                )
                            else:
                                # File is empty, initialize with default structure
                                tracked_collections = {"abstract": {}}
                                logger.warning(
                                    f"tracked_collections.json is empty, initializing with default structure"
                                )
                    except json.JSONDecodeError as e:
                        logger.error(f"Invalid JSON in {DATA_FILE}: {e}")
                        # Initialize with default structure if JSON is corrupted
                        tracked_collections = {"abstract": {}}
                else:
                    # File doesn’t exist, initialize with default structure
                    tracked_collections = {"abstract": {}}
                    logger.warning(
                        f"tracked_collections.json does not exist, initializing with default structure"
                    )

                # Check if the collection is being tracked on Abstract (case-insensitive)
                collection_address = collection_address.lower()
                logger.debug(
                    f"Checking for collection: {collection_address} in tracked_collections: {tracked_collections}"
                )
                if "abstract" in tracked_collections and collection_address in tracked_collections[
                        "abstract"]:
                    del tracked_collections["abstract"][collection_address]

                    # Save updated data safely
                    with open(DATA_FILE, "w") as file:
                        json.dump(tracked_collections, file, indent=4)
                    logger.info(
                        f"Successfully stopped tracking collection {collection_address} on Abstract"
                    )

                    await interaction.followup.send(
                        f"✅ Stopped tracking **{collection_address}** on Abstract.",
                        ephemeral=True)
                else:
                    logger.warning(
                        f"Failed to stop tracking collection {collection_address}: Not found in tracked_collections: {tracked_collections}"
                    )
                    await interaction.followup.send(
                        f"❌ Could not find tracking for **{collection_address}** on Abstract.",
                        ephemeral=True)
        except Exception as e:
            logger.error(f"Error in stop_track: {str(e)}")
            await interaction.followup.send(
                "❌ An error occurred while processing the command.",
                ephemeral=True)


async def setup(bot):
    await bot.add_cog(StopSale(bot))
