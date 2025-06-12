"""Telegram interface for the sniping bot."""
import logging
from typing import Any

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

from .config import load_config, CONFIG
from .dex import search_token
from .trading import Trader
from .copytrading import CopyTradingManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

copy_manager = CopyTradingManager()


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("Welcome to the Sniper Bot!")


async def search(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args:
        await update.message.reply_text("Usage: /search <token>")
        return
    query = " ".join(context.args)
    results = search_token(query)
    if not results:
        await update.message.reply_text("No results.")
    else:
        lines = [f"{r['pairAddress']} - {r['baseToken']['symbol']}" for r in results]
        await update.message.reply_text("\n".join(lines))


async def buy(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if len(context.args) < 2:
        await update.message.reply_text("Usage: /buy <token_address> <amount_eth>")
        return
    token, amount = context.args[0], float(context.args[1])
    trader = Trader()
    tx = trader.buy_token(token, amount)
    await update.message.reply_text(f"Buy order submitted: {tx}")


async def sell(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if len(context.args) < 2:
        await update.message.reply_text("Usage: /sell <token_address> <amount>")
        return
    token, amount = context.args[0], int(context.args[1])
    trader = Trader()
    tx = trader.sell_token(token, amount)
    await update.message.reply_text(f"Sell order submitted: {tx}")


async def copy(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args:
        await update.message.reply_text("Usage: /copy <trader_address>")
        return
    trader = context.args[0]
    copy_manager.start_copy(update.effective_user.id, trader)
    await update.message.reply_text(f"Copying trades from {trader}")


async def stopcopy(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    copy_manager.stop_copy(update.effective_user.id)
    await update.message.reply_text("Stopped copy trading.")


def main() -> None:
    import os
    token = os.environ.get("TELEGRAM_TOKEN")
    priv = os.environ.get("PRIVATE_KEY")
    addr = os.environ.get("WALLET_ADDRESS")
    if not (token and priv and addr):
        raise RuntimeError("TELEGRAM_TOKEN, PRIVATE_KEY and WALLET_ADDRESS must be set")
    load_config(token, priv, addr)

    application = Application.builder().token(CONFIG.telegram_token).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("search", search))
    application.add_handler(CommandHandler("buy", buy))
    application.add_handler(CommandHandler("sell", sell))
    application.add_handler(CommandHandler("copy", copy))
    application.add_handler(CommandHandler("stopcopy", stopcopy))

    application.run_polling()


if __name__ == "__main__":
    main()
