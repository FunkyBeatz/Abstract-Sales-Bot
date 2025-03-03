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

class TrackedCollections(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(
        name="tracked_collections",
        description="Shows all currently tracked Abstract NFT collections")
    async def tracked_collections(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        try:
            if not os.path.exists(DATA_FILE):
                await interaction.followup.send(
                    "No collections are currently being tracked.", ephemeral=True)
                return

            async with lock:
                with open(DATA_FILE, 'r') as f:
                    data = json.load(f)

            abstract_collections = data.get("abstract", {})

            if not abstract_collections:
                await interaction.followup.send(
                    "No Abstract collections are currently being tracked.", 
                    ephemeral=True)
                return

            try:
                embed = discord.Embed(title="Tracked Abstract NFT Collections",
                                      color=discord.Color.blue(),
                                      timestamp=discord.utils.utcnow())

                # Safe footer handling
                footer_text = "Tracked collections | *Metrics are placeholders; real data pending API.*"
                if self.bot and self.bot.user:
                    footer_text = f"Tracked by {self.bot.user.name} | {footer_text}"

                embed.set_footer(text=footer_text)

                for collection_address, data in abstract_collections.items():
                    channel_id = data.get("channel_id")
                    channel = None

                    if self.bot and channel_id:
                        channel = self.bot.get_channel(channel_id)

                    channel_mention = f"<#{channel_id}>" if channel_id else "No channel set"

                    # Collection data display
                    embed.add_field(
                        name=f"Collection: {data.get('name', 'Unknown')}",
                        value=f"• **Address**: `{collection_address}`\n"
                              f"• **Channel**: {channel_mention}\n"
                              f"• **Floor Price**: {data.get('floor_price', 'N/A')} ABS\n"
                              f"• **Last Sale**: {data.get('last_sale', 'N/A')} ABS\n"
                              f"• **Sales Today**: {data.get('sales_today', 0)}\n"
                              f"• **Volume Today**: {data.get('volume_today', 0)} ABS",
                        inline=False
                    )

                await interaction.followup.send(embed=embed, ephemeral=True)

            except Exception as e:
                logger.error(f"Error in tracked_collections command: {str(e)}")
                await interaction.followup.send(
                    "❌ An error occurred while processing the command.",
                    ephemeral=True)

        except Exception as e:
            logger.error(f"Error in tracked_collections command: {str(e)}")
            await interaction.followup.send(
                "❌ An error occurred while processing the command.",
                ephemeral=True)


async def setup(bot):
    await bot.add_cog(TrackedCollections(bot))