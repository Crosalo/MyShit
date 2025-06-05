from dex_client import check_token
from wallet import buy_token, w3

if __name__ == '__main__':
    # Replace with the token address you want to monitor/buy
    sample_token = "0x0000000000000000000000000000000000000000"
    data = check_token(sample_token)
    print('Token data:', data)
    # Example buy call (using minimal value)
    # tx_hash = buy_token(sample_token, w3.to_wei(0.01, 'ether'))
    # print('Submitted transaction:', tx_hash)
