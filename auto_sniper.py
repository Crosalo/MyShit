import time
from dex_client import get_new_listings
from wallet import buy_token, sell_token, w3
from config import config


def monitor_and_trade():
    seen = set()
    while True:
        try:
            tokens = get_new_listings()
            for token in tokens:
                if token in seen:
                    continue
                seen.add(token)
                print(time.strftime('%Y-%m-%d %H:%M:%S'), 'Buying', token)
                amount = w3.to_wei(config.TRADE_AMOUNT_ETH, 'ether')
                tx_buy = buy_token(token, amount)
                print(time.strftime('%Y-%m-%d %H:%M:%S'), 'Buy tx:', tx_buy)
                time.sleep(config.HOLD_SECONDS)
                tx_sell = sell_token(token, amount)
                print(time.strftime('%Y-%m-%d %H:%M:%S'), 'Sell tx:', tx_sell)
        except Exception as err:
            print('Error:', err)
        time.sleep(10)


if __name__ == '__main__':
    monitor_and_trade()
