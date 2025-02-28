import discord
import asyncio
from utils.api_handler import AbstractAPI
import json
import os
import logging

# Set up logging to match main.py
logging.basicConfig(filename='./data/logs/bot.log',
                    level=logging.INFO,
                    format='%(asctime)s %(levelname)s: %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S')
logger = logging.getLogger(__name__)

DATA_FILE = "./data/tracked_collections.json"


async def monitor_sales(bot):
    """Monitor NFT sales in real-time and post to Discord channels."""
    api = AbstractAPI()
    logger.info("Starting sales monitoring for Abstract collections")
    await api.listen_for_sales()  # Start real-time WebSocket monitoring

    while True:
        try:
            # Fallback polling (if WebSocket fails or for initial sync)
            await api.fallback_poll_sales()
            await asyncio.sleep(60)  # Less frequent polling as backup
        except Exception as e:
            logger.error(f"Error in monitor_sales: {str(e)}")
            await asyncio.sleep(10)  # Wait before retrying


async def post_sale_to_discord(collection, token_id, price, buyer, seller,
                               tx_hash, channel_id):
    """Post a sale to the specified Discord channel with a rich embed."""
    channel = bot.get_channel(channel_id)
    if not channel:
        logger.error(f"Channel {channel_id} not found")
        return

    embed = discord.Embed(title="🎉 Abstract NFT Sale Detected!",
                          color=discord.Color.green(),
                          timestamp=discord.utils.utcnow())

    # Add collection name (fetch from RPC if possible) or use address
    collection_name = await fetch_collection_name(
        collection) or f"{collection[:6]}...{collection[-4:]}"
    embed.add_field(name="Collection",
                    value=f"`{collection_name}`",
                    inline=True)

    # Add NFT image (fallback if unavailable)
    image_url = f"https://abs-api.abstract.io/nft/{collection}/{token_id}/image"
    try:
        embed.set_image(url=image_url)
    except:
        pass  # Skip if image fails

    embed.add_field(name="Token ID", value=f"#{token_id}", inline=True)
    embed.add_field(name="Price",
                    value=f"{price} ABS" if price else "N/A",
                    inline=True)
    embed.add_field(name="Buyer",
                    value=f"`{buyer[:6]}...{buyer[-4:]}`",
                    inline=True)
    embed.add_field(name="Seller",
                    value=f"`{seller[:6]}...{seller[-4:]}`",
                    inline=True)
    embed.add_field(
        name="Transaction",
        value=f"[View on AbstractScan](https://abscan.org/tx/{tx_hash})",
        inline=False)
    embed.set_footer(text=f"Tracked by {bot.user.name}",
                     icon_url=bot.user.avatar.url if bot.user.avatar else None)

    await channel.send(embed=embed)
    logger.info(
        f"Sale notification sent to channel {channel_id} for collection {collection}, token {token_id}"
    )


async def fetch_collection_name(collection_address):
    # Implement RPC call to fetch collection name (check Abstract docs for endpoint)
    # Placeholder; update based on Abstract’s API
    return None
