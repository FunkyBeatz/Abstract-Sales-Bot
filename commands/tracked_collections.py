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
        description="Show all currently tracked Abstract NFT collections")
    @app_commands.checks.cooldown(1, 5.0)  # 1 use every 5 seconds
    async def tracked_collections(self, interaction: discord.Interaction):
        """Show a list of all tracked Abstract NFT collections with basic stats.

        Displays an embed with each tracked collection's address, channel, sales threshold, and placeholder data for floor price, volume, sales, etc. Note: Some metrics (e.g., floor price, volume) are placeholders and require a data source (e.g., Magic Eden API) for real values.

        Args:
            interaction: The Discord interaction triggering the command.
        """
        try:
            await interaction.response.defer(ephemeral=True)

            async with lock:  # Use lock for thread-safe JSON access
                # Load tracked_collections
                tracked_collections = {}
                if os.path.exists(DATA_FILE):
                    try:
                        with open(DATA_FILE, "r") as file:
                            content = file.read().strip()
                            if content:
                                tracked_collections = json.load(file)
                                logger.info(
                                    f"Loaded tracked_collections.json for /tracked_collections: {tracked_collections}"
                                )
                            else:
                                tracked_collections = {"abstract": {}}
                                logger.warning(
                                    f"tracked_collections.json is empty for /tracked_collections"
                                )
                    except json.JSONDecodeError as e:
                        logger.error(
                            f"Invalid JSON in {DATA_FILE} for /tracked_collections: {e}"
                        )
                        tracked_collections = {"abstract": {}}
                else:
                    tracked_collections = {"abstract": {}}
                    logger.warning(
                        f"tracked_collections.json does not exist for /tracked_collections"
                    )

                # Get Abstract collections
                abstract_collections = tracked_collections.get("abstract", {})
                if not abstract_collections:
                    await interaction.followup.send(
                        "❌ No collections are currently being tracked on Abstract.",
                        ephemeral=True)
                    logger.warning(
                        "No collections tracked on Abstract for /tracked_collections"
                    )
                    return

                # Build embed with tracked collections and placeholder data
                embed = discord.Embed(title="Tracked Abstract NFT Collections",
                                      color=discord.Color.blue(),
                                      timestamp=discord.utils.utcnow())
                embed.set_footer(
                    text=
                    f"Tracked by {self.bot.user.name} | *Metrics are placeholders; real data pending API.*",
                    icon_url=self.bot.user.avatar.url
                    if self.bot.user.avatar else None)

                for collection_address, data in abstract_collections.items():
                    channel = self.bot.get_channel(data["channel_id"])
                    channel_mention = channel.mention if channel else f"Channel ID {data['channel_id']} (not found)"

                    # Placeholder data (replace with real data if available later)
                    embed.add_field(
                        name=
                        f"Collection: {collection_address[:6]}...{collection_address[-4:]}",
                        value=f"""
                        **Channel**: {channel_mention}
                        **Sales Threshold**: {data['sales_threshold']}
                        **Floor Price**: Not available (e.g., 1.5 ABS, +2%)
                        **24h Volume**: Not available (e.g., 10 ABS)
                        **24h Sales**: Not available (e.g., 5 sales)
                        **1h Sales**: Not available (e.g., 1 sale)
                        **Avg Sale**: Not available (e.g., 2 ABS)
                        **Listed/Supply**: Not available (e.g., 100/1000)
                        **Listed %**: Not available (e.g., 10%)
                        **Owners %**: Not available (e.g., 80%)
                        """,
                        inline=False)

                await interaction.followup.send(embed=embed)
                logger.info(
                    f"Displayed tracked collections for /tracked_collections: {list(abstract_collections.keys())}"
                )

        except Exception as e:
            logger.error(f"Error in tracked_collections command: {str(e)}")
            await interaction.followup.send(
                "❌ An error occurred while processing the command.",
                ephemeral=True)


async def setup(bot):
    await bot.add_cog(TrackedCollections(bot))
