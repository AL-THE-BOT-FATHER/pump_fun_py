from solana.rpc.api import Client
from solders.keypair import Keypair  # type: ignore

from pump_fun import buy

# Configuration
priv_key = "base58_priv_str_here"
rpc = "rpc_url_here"
mint_str = "pump_token_address"
sol_in = 0.1
slippage = 5
unit_budget = 120_000
unit_price = 1_000_000

# Initialize client and keypair
client = Client(rpc)
payer_keypair = Keypair.from_base58_string(priv_key)

# Execute buy
buy(client, payer_keypair, mint_str, sol_in, slippage, unit_budget, unit_price)
