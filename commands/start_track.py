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


class StartSale(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(
        name="start_track",
        description="Start tracking NFT sales for an Abstract collection")
    @app_commands.checks.cooldown(1, 2.0)  # 1 use every 2 seconds
    async def start_track(self,
                          interaction: discord.Interaction,
                          collection_address: str,
                          channel: discord.TextChannel,
                          sales_threshold: int = 1):
        """Command to start tracking NFT sales for an Abstract collection.

        Args:
            interaction: The Discord interaction triggering the command.
            collection_address: The address of the Abstract NFT collection to track (e.g., '0x...').
            channel: The Discord channel where sales notifications will be posted.
            sales_threshold: The minimum number of sales required to trigger notifications (default: 1).
        """
        try:
            await interaction.response.defer(ephemeral=True)

            # Validate collection address (simplified; add more robust validation)
            if not self.is_valid_address(collection_address):
                logger.warning(
                    f"Failed to track collection {collection_address}: Invalid address format"
                )
                await interaction.followup.send(
                    "❌ Invalid collection address format.", ephemeral=True)
                return

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

                # Check if collection is already being tracked
                collection_address = collection_address.lower()
                logger.debug(
                    f"Checking for duplicate collection: {collection_address} in {tracked_collections}"
                )
                if "abstract" in tracked_collections and collection_address in tracked_collections[
                        "abstract"]:
                    logger.warning(
                        f"Failed to track collection {collection_address}: Already tracked in {channel.mention}"
                    )
                    await interaction.followup.send(
                        f"❌ This collection is already being tracked in {channel.mention}!",
                        ephemeral=True)
                    return

                # Ensure 'abstract' exists in the JSON
                if "abstract" not in tracked_collections:
                    tracked_collections["abstract"] = {}

                # Add the new collection tracking
                tracked_collections["abstract"][collection_address] = {
                    "CA_or_ME": collection_address,  # Collection address
                    "channel_id": channel.id,
                    "sales_threshold": sales_threshold
                }

                # Save updated data safely
                with open(DATA_FILE, "w") as file:
                    json.dump(tracked_collections, file, indent=4)
                logger.info(
                    f"Successfully tracked collection {collection_address} on Abstract in channel {channel.id}"
                )

            await interaction.followup.send(
                f"✅ Now tracking **{collection_address}** on Abstract in {channel.mention}!"
            )
        except Exception as e:
            logger.error(f"Error in start_track: {str(e)}")
            await interaction.followup.send(
                "❌ An error occurred while processing the command.",
                ephemeral=True)

    def is_valid_address(self, address):
        """Validate if the address is a valid Ethereum-style or Abstract-specific address.

        Args:
            address: The string to validate (e.g., '0x...' or alphanumeric).

        Returns:
            bool: True if valid, False otherwise.
        """
        is_valid = isinstance(address,
                              str) and (address.lower().startswith("0x")
                                        or address.isalnum())
        if not is_valid:
            logger.debug(f"Invalid address format: {address}")
        return is_valid


async def setup(bot):
    await bot.add_cog(StartSale(bot))
