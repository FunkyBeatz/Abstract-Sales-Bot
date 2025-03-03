# Abstract Sales Bot

## Overview

The **Abstract Sales Bot** is a Discord bot designed to monitor and track NFT sales on the Abstract blockchain in real-time. It posts sale notifications to specified Discord channels and provides slash commands to manage tracked collections, check bot status, and view tracked collections. Built with Python, `discord.py`, and `web3.py`, this bot integrates with the Abstract blockchain via WebSocket and HTTP RPC endpoints.

## Features

- **Real-time Tracking:** Monitor NFT sales on the Abstract blockchain.
- **Slash Commands:**
  - `/ping`: Check if the bot is online and its latency.
  - `/start_track`: Start tracking an Abstract NFT collection.
  - `/stop_track`: Stop tracking an Abstract NFT collection.
  - `/tracked_collections`: List all tracked Abstract NFT collections (with placeholder data for metrics like floor price, volume, etc.).
- **Thread-Safe Storage:** Uses JSON files for storing tracked collections.
- **Comprehensive Logging:** Logs activities to both console and files for easy debugging.
- **WebSocket & HTTP Fallback:** Automatically switches to HTTP polling if WebSocket connections fail.

## Prerequisites

| **Requirement**         | **Details**                                                                 |
|-------------------------|-----------------------------------------------------------------------------|
| **Python**              | Python 3.8+ installed on your system.                                       |
| **Discord Bot Token**   | Obtainable from the [Discord Developer Portal](https://discord.com/developers/applications). |
| **Abstract RPC Endpoints** | WebSocket and HTTP endpoints for the Abstract blockchain.                  |
| **Python Libraries**    | `discord.py`, `web3`, `aiohttp`, `python-dotenv`.                           |

## Installation

### 1. Clone or Download the Repository

Clone this repository to your local machine or download the ZIP file from GitHub:
```bash
git clone <repository-url>
cd abstract-sales-bot
```

### 2. Install Dependencies

Install the required Python libraries using pip:
```bash
pip install -r requirements.txt
```
Ensure your `requirements.txt` includes:
```text
discord.py>=2.3.2
web3==6.13.0
aiohttp
python-dotenv
```

### 3. Set Up Environment Variables

Create a `.env` file in your project root to store sensitive data:
```env
DISCORD_BOT_TOKEN=your_discord_bot_token_here
APPLICATION_ID=your_discord_application_id_here
ABSTRACT_WS_RPC=wss://api.mainnet.abs.xyz/ws
ABSTRACT_HTTP_RPC=https://abstract.rpc.thirdweb.com
```
Replace placeholders with your actual credentials and endpoints.

Update your `config.py` to load from `.env`:
```python
from dotenv import load_dotenv
import os

load_dotenv()

BOT_TOKEN = os.getenv('DISCORD_BOT_TOKEN')
APPLICATION_ID = int(os.getenv('APPLICATION_ID', '0'))
ABSTRACT_WS_RPC = os.getenv('ABSTRACT_WS_RPC', 'wss://api.mainnet.abs.xyz/ws')
ABSTRACT_HTTP_RPC = os.getenv('ABSTRACT_HTTP_RPC', 'https://abstract.rpc.thirdweb.com')
```

### 4. Run the Bot

To start the bot, use:
```bash
python main.py
```
The bot will log into Discord and sync its slash commands. Ensure your bot is invited to your Discord server with the appropriate permissions.

## Usage

| **Command**                  | **Description**                                      | **Example**                                                  |
|------------------------------|------------------------------------------------------|--------------------------------------------------------------|
| `/ping`                      | Check bot latency and status.                         | `Pong! Bot latency: 85ms`                                     |
| `/start_track`               | Start tracking an NFT collection.                     | `/start_track collection_address:0xe9c75... channel:#sales sales_threshold:1` |
| `/stop_track`                | Stop tracking an NFT collection.                      | `/stop_track collection_address:0xe9c75...`                   |
| `/tracked_collections`       | List all tracked collections with placeholder stats.  | _(Currently disabled, see commands/tracked_collections.py)_   |

### Example

Start tracking a collection:
```bash
/option collection_address:0xe9c75... channel:#sales sales_threshold:1
```

Stop tracking a collection:
```bash
/stop_track collection_address:0xe9c75...
```

## Configuration

- **Tracked Collections:** Stored in `./data/tracked_collections.json`.
- **Logs:** Written to `./data/logs/bot.log` and displayed in the console.

## Troubleshooting

| **Issue**                    | **Solution**                                                               |
|------------------------------|---------------------------------------------------------------------------|
| **No Slash Commands**        | Ensure the bot has the `applications.commands` scope and permissions.       |
| **Syncing Errors (HTTP 403)**| Check the OAuth2 invite and server permissions. Review logs in `bot.log`.  |
| **WebSocket Issues**         | Verify `web3==6.13.0` is installed and RPC endpoints are reachable.        |

## Contributing

Feel free to report issues. Contributions to enhance features, fix bugs, or add Abstract marketplace data scraping (e.g., Magic Eden) are welcome.

---

## Follow Me on Social Media

Stay connected and follow my work on social media:

- **Main 𝕏 Account:** [FunkyxBeatz](https://x.com/FunkyxBeatz)
- **Projects 𝕏 Account:** [WebFrens_](https://x.com/WebFrens_)
