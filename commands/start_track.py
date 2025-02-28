import discord
from discord import app_commands
from discord.ext import commands
import json
import os
import asyncio

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
        """Command to start tracking NFT sales for an Abstract collection"""
        try:
            await interaction.response.defer(ephemeral=True)

            # Validate collection address (simplified; add more robust validation)
            if not self.is_valid_address(collection_address):
                await interaction.followup.send(
                    "❌ Invalid collection address format.", ephemeral=True)
                return

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

                # Check if collection is already being tracked
                collection_address = collection_address.lower()
                if "abstract" in tracked_collections and collection_address in tracked_collections[
                        "abstract"]:
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

            await interaction.followup.send(
                f"✅ Now tracking **{collection_address}** on Abstract in {channel.mention}!"
            )
        except Exception as e:
            print(f"Error in start_track: {e}")
            await interaction.followup.send(
                "❌ An error occurred while processing the command.",
                ephemeral=True)

    def is_valid_address(self, address):
        # Simplified validation for Ethereum-style addresses (0x...) or Abstract-specific format
        return isinstance(address, str) and (address.lower().startswith("0x")
                                             or address.isalnum())


async def setup(bot):
    await bot.add_cog(StartSale(bot))
