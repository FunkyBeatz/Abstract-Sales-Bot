import discord
from discord import app_commands
from discord.ext import commands
import json
import os
import asyncio
import logging

DATA_FILE = "./data/tracked_collections.json"
lock = asyncio.Lock()  # Thread-safe file access

logger = logging.getLogger(__name__)


class StopSale(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(
        name="stop_track",
        description="Stop tracking NFT sales for an Abstract collection")
    @app_commands.checks.cooldown(1, 2.0)  # 1 use every 2 seconds
    async def stop_track(self, interaction: discord.Interaction,
                         collection_address: str):
        """Command to stop tracking an Abstract NFT collection"""
        try:
            await interaction.response.defer(ephemeral=True)

            # Ensure Data directory exists
            os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)

            async with lock:  # Use lock for thread-safe JSON access
                # Load or initialize tracked_collections
                tracked_collections = {}
                if os.path.exists(DATA_FILE):
                    try:
                        with open(DATA_FILE, "r") as file:
                            content = file.read().strip()
                            if content:  # Check if file has content
                                tracked_collections = json.load(file)
                            else:
                                # File is empty, initialize with default structure
                                tracked_collections = {"abstract": {}}
                    except json.JSONDecodeError as e:
                        logger.error(f"Invalid JSON in {DATA_FILE}: {e}")
                        # Initialize with default structure if JSON is corrupted
                        tracked_collections = {"abstract": {}}
                else:
                    # File doesn’t exist, initialize with default structure
                    tracked_collections = {"abstract": {}}

                # Check if the collection is being tracked on Abstract
                collection_address = collection_address.lower()
                if "abstract" in tracked_collections and collection_address in tracked_collections[
                        "abstract"]:
                    del tracked_collections["abstract"][collection_address]

                    # Save updated data
                    with open(DATA_FILE, "w") as file:
                        json.dump(tracked_collections, file, indent=4)

                    await interaction.followup.send(
                        f"✅ Stopped tracking **{collection_address}** on Abstract.",
                        ephemeral=True)
                else:
                    await interaction.followup.send(
                        f"❌ Could not find tracking for **{collection_address}** on Abstract.",
                        ephemeral=True)
        except Exception as e:
            print(f"Error in stop_track: {e}")
            await interaction.followup.send(
                "❌ An error occurred while processing the command.",
                ephemeral=True)


async def setup(bot):
    await bot.add_cog(StopSale(bot))
