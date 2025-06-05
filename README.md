# Meme Coin Sniping Bot

This repository contains a simple prototype of a meme coin sniping bot.
The bot monitors token listings through Dexscreener and can execute
buy transactions via MetaMask using a Web3 provider. Purchases and
sales are routed through the Uniswap V2 router by default.

The project is intended for educational purposes. Use at your own risk
and ensure compliance with local regulations.

## Setup

1. Install dependencies:
   ```bash
   pip install web3 requests
   ```
2. Configure a local JSON-RPC endpoint (e.g. through MetaMask or a self-hosted
   node) and set it in `config.py` or the `WEB3_PROVIDER` environment variable.
3. Set your private key in `config.py` or via the `PRIVATE_KEY` environment
   variable.
4. Optional: adjust `ROUTER_ADDRESS`, `TRADE_AMOUNT_ETH` and `HOLD_SECONDS` in
   `config.py` or via environment variables. The default router address
   points to the Uniswap V2 router on Ethereum mainnet.
5. Run `python sniper_bot.py` to query a token and optionally trigger a buy.
6. For automated buying and selling, run `python auto_sniper.py`.

## Repository Structure

- `config.py` – central configuration for provider URL and private key
- `dex_client.py` – helper for fetching token data from Dexscreener
- `wallet.py` – Web3 wallet integration and transaction helper
- `sniper_bot.py` – minimal entry point using the above modules
- `auto_sniper.py` – loop that discovers new tokens and performs automated trades

## Disclaimer

This example is simplified and provided for educational purposes. Always test
thoroughly before trading with real funds.

## Sniping Bot Outline

Below are core components to consider when building a more complete sniping bot:

1. **API access** – connect to exchanges or DeFi protocols via Web3 or HTTP APIs
2. **Monitoring new listings** – watch listing websites or blockchain events to
   detect new tokens early.
3. **Automated buying logic** – place buy transactions immediately once a token
   is found.
4. **Risk management** – limit trade sizes and set up stop-loss/take-profit rules.
5. **Technical implementation** – scripts in Python with libraries like `web3.py`
   or custom smart contracts.
6. **Security and testing** – keep private keys secure and test in testnets before
   trading.
7. **Compliance** – check local regulations regarding automated trading.

## Web Interface

A minimal Flask app in `webapp.py` provides a simple dashboard to control the bot:

1. Run `pip install flask werkzeug`
2. Start the server with `python webapp.py`
3. Create an account on the `/register` page and log in
4. In **Settings**, enter your RPC provider URL and private key
5. Use **Start** and **Stop** on the dashboard to launch or stop the trading loop
6. The dashboard displays a profit/loss graph from recorded trades

This interface stores data in `app.db` (SQLite). It is only a basic example and should
be secured and extended for production use.

### JavaScript Version

A lightweight Express-based version is provided in `js_webapp`. It implements the same dashboard using JavaScript and CSS.

1. Install dependencies with `npm install` inside `js_webapp`.
2. Start the server using `npm start`.
3. Navigate to `http://localhost:3000` and register or log in.
4. Enter your RPC provider and private key under **Settings**.
5. Use the dashboard to start or stop the Python trading loop.
