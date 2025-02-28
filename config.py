import os

# Load sensitive data from Replit Secrets
BOT_TOKEN = os.getenv('DISCORD_BOT_TOKEN')

# Ensure APPLICATION_ID is properly validated
app_id = os.getenv('APPLICATION_ID')
APPLICATION_ID = int(app_id) if app_id and app_id.isdigit() and app_id != '0' else None

# Handle GUILD_ID
guild_id = os.getenv('GUILD_ID')
GUILD_ID = int(guild_id) if guild_id and guild_id.isdigit() and guild_id != '0' else None  # Optional for global sync
ABSTRACT_WS_RPC = os.getenv('ABSTRACT_WS_RPC', 'wss://api.mainnet.abs.xyz/ws')
ABSTRACT_HTTP_RPC = os.getenv('ABSTRACT_HTTP_RPC',
                              'https://abstract.rpc.thirdweb.com')
