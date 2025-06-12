# Telegram Sniping Bot

This project provides a basic framework for a Telegram-based sniping bot that searches for tokens on Dexscreener and performs buy/sell actions via Uniswap. It also includes a simple copy trading mechanism.

## Features

- **Token Search** using Dexscreener API
- **Buy/Sell** tokens via Uniswap
- **Copy Trading** to follow trades of another address

## Requirements

- Python 3.10+
- A running Ethereum node or Infura project
- Telegram bot token

Install dependencies:

```bash
pip install -r requirements.txt
```

## Running

Set the following environment variables:

- `TELEGRAM_TOKEN` – Telegram bot token
- `PRIVATE_KEY` – wallet private key
- `WALLET_ADDRESS` – wallet address

Then start the bot:

```bash
python -m sniper_bot.bot
```

## Disclaimer

This is an experimental project. Use at your own risk and be mindful of potential losses and transaction fees on Uniswap.
