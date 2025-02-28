from web3 import Web3
import json
import asyncio
import os
from web3.providers.websocket import WebsocketProvider  # Correct for web3==6.13.0
import logging

# Set up logging to match main.py
logging.basicConfig(filename='./data/logs/bot.log',
                    level=logging.INFO,
                    format='%(asctime)s %(levelname)s: %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S')
logger = logging.getLogger(__name__)

ABSTRACT_WS_RPC = os.getenv('ABSTRACT_WS_RPC', 'wss://api.mainnet.abs.xyz/ws')
ABSTRACT_HTTP_RPC = os.getenv('ABSTRACT_HTTP_RPC',
                              'https://abstract.rpc.thirdweb.com')

# ERC721 ABI for Transfer events (simplified; update if Abstract uses custom ABI)
ERC721_ABI = json.loads(
    '[{"anonymous":false,"inputs":[{"indexed":true,"name":"from","type":"address"},{"indexed":true,"name":"to","type":"address"},{"indexed":true,"name":"tokenId","type":"uint256"}],"name":"Transfer","type":"event"}]'
)


class AbstractAPI:
    """Handles connections to the Abstract blockchain for NFT sales tracking."""

    def __init__(self):
        self.w3_ws = None
        self.w3_http = Web3(Web3.HTTPProvider(ABSTRACT_HTTP_RPC))
        self.tracked_collections = self.load_tracked_collections()
        self.processed_sales = set()
        self.connect_to_ws()

    def load_tracked_collections(self):
        """Load tracked collections from JSON file."""
        DATA_FILE = "./data/tracked_collections.json"
        os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
        try:
            if os.path.exists(DATA_FILE):
                with open(DATA_FILE, "r") as f:
                    return json.load(f)
            return {"abstract": {}, "ABS": {}}
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in {DATA_FILE}: {e}")
            return {"abstract": {}, "ABS": {}}

    def connect_to_ws(self):
        """Establish WebSocket connection to Abstract."""
        try:
            self.w3_ws = Web3(WebsocketProvider(ABSTRACT_WS_RPC))
            if self.w3_ws.is_connected():
                logger.info("Connected to Abstract WebSocket")
            else:
                logger.warning(
                    "WebSocket connection failed; falling back to HTTP")
                self.w3_ws = None
        except Exception as e:
            logger.error(f"WebSocket connection error: {str(e)}")
            self.w3_ws = None

    async def listen_for_sales(self):
        """Listen for NFT sales in real-time via WebSocket."""
        try:
            if not self.w3_ws:
                logger.warning("No WebSocket connection; using HTTP polling")
                await self.fallback_poll_sales()
                return

            # Subscribe to Transfer events for all tracked collections
            for blockchain in ["abstract"]:  # Focus only on Abstract
                for collection, data in self.tracked_collections.get(
                        blockchain, {}).items():
                    contract_address = Web3.to_checksum_address(collection)
                    contract = self.w3_ws.eth.contract(
                        address=contract_address, abi=ERC721_ABI)
                    event_filter = contract.events.Transfer.create_filter(
                        fromBlock="latest")

                    while True:
                        for event in event_filter.get_new_entries():
                            await self.handle_sale_event(
                                event, contract_address, data)
                        await asyncio.sleep(
                            1)  # Small delay to prevent overwhelming
        except Exception as e:
            logger.error(f"WebSocket error: {str(e)}")
            await self.fallback_poll_sales()  # Fall back to HTTP polling

    async def fallback_poll_sales(self):
        """Poll for sales via HTTP if WebSocket fails, with exponential backoff."""
        max_retries = 5
        delay = 2
        for attempt in range(max_retries):
            try:
                latest_block = self.w3_http.eth.block_number
                from_block = max(0, latest_block - 10)
                for blockchain in ["abstract"]:  # Focus only on Abstract
                    for collection, data in self.tracked_collections.get(
                            blockchain, {}).items():
                        contract_address = Web3.to_checksum_address(collection)
                        events = self.w3_http.eth.get_logs({
                            'fromBlock':
                            from_block,
                            'toBlock':
                            latest_block,
                            'address':
                            contract_address,
                            'topics': [
                                self.w3_http.keccak(
                                    text="Transfer(address,address,uint256)").
                                hex()
                            ]
                        })
                        for event in events:
                            await self.handle_sale_event(
                                event, contract_address, data)
                break
            except Exception as e:
                logger.error(
                    f"HTTP polling attempt {attempt + 1} failed: {str(e)}")
                await asyncio.sleep(delay)
                delay *= 2  # Exponential backoff

    async def handle_sale_event(self, event, collection_address, data):
        """Process a sale event and post to Discord if it's a valid sale."""
        sale_id = f"{collection_address}_{event['transactionHash'].hex()}"
        if sale_id in self.processed_sales:
            return

        try:
            # Extract sale details (simplified; adjust based on Abstract’s event structure)
            token_id = int(event["topics"][3].hex(), 16) if len(
                event["topics"]) > 3 else None
            from_addr = "0x" + event["topics"][1].hex()[-40:]
            to_addr = "0x" + event["topics"][2].hex()[-40:]
            tx_hash = event["transactionHash"].hex()

            # Check if this is a sale (e.g., value > 0 or marketplace event)
            tx = self.w3_http.eth.get_transaction(tx_hash)
            price = Web3.from_wei(tx['value'], 'ether') if tx and tx.get(
                'value', 0) > 0 else None

            logger.info(
                f"Detected potential sale for collection {collection_address}, token {token_id}, price {price}"
            )
            if price or self.is_marketplace_sale(
                    event):  # Add logic for marketplace sales
                await self.post_sale_to_discord(collection_address, token_id,
                                                price, from_addr, to_addr,
                                                tx_hash, data['channel_id'])
                self.processed_sales.add(sale_id)
                logger.info(
                    f"Processed sale for collection {collection_address}, token {token_id}"
                )
                if len(self.processed_sales) > 1000:
                    self.processed_sales.clear()  # Manage memory
        except Exception as e:
            logger.error(f"Error processing sale: {str(e)}")

    def is_marketplace_sale(self, event):
        # Add logic to detect if this is a marketplace sale (e.g., specific event signature or contract)
        # Check Abstract docs for marketplace contracts or events
        return False  # Placeholder; implement based on Abstract’s structure

    async def post_sale_to_discord(self, collection, token_id, price, buyer,
                                   seller, tx_hash, channel_id):
        # Post to Discord (implemented in sales_posting.py)
        from utils.sales_posting import post_sale_to_discord
        await post_sale_to_discord(collection, token_id, price, buyer, seller,
                                   tx_hash, channel_id)
