import discord
from discord import app_commands
from discord.ext import commands
import json
import os
import asyncio

DATA_FILE = "./data/tracked_collections.json"
lock = asyncio.Lock()  # Thread-safe file access


class StopSale(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(
        name="stop_track",
        description="Stop tracking NFT sales for a collection")
    @app_commands.checks.cooldown(1, 2.0)  # 1 use every 2 seconds
    async def stop_track(self, interaction: discord.Interaction,
                         blockchain: str, collection_address: str):
        """Command to stop tracking an NFT collection"""
        try:
            await interaction.response.defer(ephemeral=True)

            # Ensure Data directory exists
            os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)

            async with lock:  # Use lock for thread-safe JSON access
                # Load existing data
                tracked_collections = {}
                if os.path.exists(DATA_FILE):
                    with open(DATA_FILE, "r") as file:
                        tracked_collections = json.load(file)
                else:
                    await interaction.followup.send(
                        "❌ No tracked collections found.", ephemeral=True)
                    return

                # Check if the collection is being tracked
                blockchain = blockchain.lower()
                collection_address = collection_address.lower()
                if blockchain in tracked_collections and collection_address in tracked_collections[
                        blockchain]:
                    del tracked_collections[blockchain][collection_address]

                    # Save updated data
                    with open(DATA_FILE, "w") as file:
                        json.dump(tracked_collections, file, indent=4)

                    await interaction.followup.send(
                        f"✅ Stopped tracking **{collection_address}** on **{blockchain}**.",
                        ephemeral=True)
                else:
                    await interaction.followup.send(
                        f"❌ Could not find tracking for **{collection_address}** on **{blockchain}**.",
                        ephemeral=True)
        except Exception as e:
            print(f"Error in stop_track: {e}")
            await interaction.followup.send(
                "❌ An error occurred while processing the command.",
                ephemeral=True)


async def setup(bot):
    await bot.add_cog(StopSale(bot))
