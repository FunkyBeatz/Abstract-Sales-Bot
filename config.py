import os

# Load sensitive data from Replit Secrets
BOT_TOKEN = os.getenv('DISCORD_BOT_TOKEN')
APPLICATION_ID = int(os.getenv('APPLICATION_ID', '0'))
GUILD_ID = int(os.getenv(
    'GUILD_ID',
    '0')) if os.getenv('GUILD_ID') else None  # Optional for global sync
ABSTRACT_WS_RPC = os.getenv('ABSTRACT_WS_RPC', 'wss://api.mainnet.abs.xyz/ws')
ABSTRACT_HTTP_RPC = os.getenv('ABSTRACT_HTTP_RPC',
                              'https://abstract.rpc.thirdweb.com')
