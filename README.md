# pump_fun_py

Python library to trade on pump.fun.

```
pip install solana==0.36.1 solders==0.23.0
```

Updated: 2/17/2025

# Instructions

1. Clone the repo, and add your Private Key (Base58 string) and RPC to the `config.py`.
2. Ensure you have sufficient SOL in your wallet to cover transaction fees and trades.
3. Install the required dependencies (see above).
4. Run the script via command line to perform buy or sell actions using the `pump_fun.py` script.

**Command Line Usage**:

The `pump_fun.py` script supports both buy and sell operations through the command line using flags. Use the following format:

```bash
python pump_fun.py -a <action> -m <mint> [-s <sol>] [-p <percentage>] [-l <slippage>]
```

or with long-form flags:

```bash
python pump_fun.py --action <action> --mint <mint> [--sol <sol>] [--percentage <percentage>] [--slippage <slippage>]
```

- `-a, --action`: Action to perform (`buy` or `sell`). Required.
- `-m, --mint`: Mint address of the token (e.g., `CFpucK7L7kk5hLqDRJdK5SWHrNw1dfGqC3nJJfwLpump`). Required.
- `-s, --sol`: Amount of SOL to spend for buy (e.g., `0.01`). Default: `0.1`. Used only for `buy`.
- `-p, --percentage`: Percentage of tokens to sell (1-100, e.g., `100`). Default: `100`. Used only for `sell`.
- `-l, --slippage`: Slippage percentage (e.g., `5`). Default: `5`.

**Examples**:

- Buy 0.01 SOL worth of tokens:

  ```bash
  python pump_fun.py -a buy -m CFpucK7L7kk5hLqDRJdK5SWHrNw1dfGqC3nJJfwLpump -s 0.01 -l 5
  ```

- Sell 100% of tokens:

  ```bash
  python pump_fun.py -a sell -m CFpucK7L7kk5hLqDRJdK5SWHrNw1dfGqC3nJJfwLpump -p 100 -l 5
  ```

- Buy with default slippage (5%):

  ```bash
  python pump_fun.py --action buy --mint CFpucK7L7kk5hLqDRJdK5SWHrNw1dfGqC3nJJfwLpump --sol 0.01
  ```

**Notes**:

- Ensure your token has not completed bonding (`coin_data.complete == False`), or trades will fail.
- Check your wallet balance before running commands (output will show `Wallet balance`).
- If transactions fail, verify your RPC endpoint, increase `UNIT_BUDGET`/`UNIT_PRICE` in `.env.example`, or check the transaction signature on Solana Explorer (e.g., solscan.io).

# Contact

My services are for **hire**. Contact me if you need help integrating the code into your own project.

- PF Token Launchers (Bundler or Self-Sniper)
- Bump Bot
- gRPC Detection (Mints, Buys, Migrations)
- Vanity Address Generator
- Rust implementations of PF code

# FAQ

**What format should my private key be in?**

The private key should be in the base58 string format, not bytes.

**Why are my transactions being dropped?**

You get what you pay for. Don't use the main-net RPC, just spend the money for Helius or Quick Node.

**How do I change the fee?**

Modify the `UNIT_BUDGET` and `UNIT_PRICE` in the `.env.example`.

**Does this code work on devnet?**

No.