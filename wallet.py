from web3 import Web3
from config import config


ROUTER_ABI = [
    {
        "name": "swapExactETHForTokens",
        "type": "function",
        "inputs": [
            {"name": "amountOutMin", "type": "uint256"},
            {"name": "path", "type": "address[]"},
            {"name": "to", "type": "address"},
            {"name": "deadline", "type": "uint256"},
        ],
        "outputs": [{"name": "amounts", "type": "uint256[]"}],
        "stateMutability": "payable",
    },
    {
        "name": "swapExactTokensForETH",
        "type": "function",
        "inputs": [
            {"name": "amountIn", "type": "uint256"},
            {"name": "amountOutMin", "type": "uint256"},
            {"name": "path", "type": "address[]"},
            {"name": "to", "type": "address"},
            {"name": "deadline", "type": "uint256"},
        ],
        "outputs": [{"name": "amounts", "type": "uint256[]"}],
        "stateMutability": "nonpayable",
    },
]

ERC20_ABI = [
    {
        "name": "approve",
        "type": "function",
        "inputs": [
            {"name": "spender", "type": "address"},
            {"name": "amount", "type": "uint256"},
        ],
        "outputs": [{"name": "", "type": "bool"}],
        "stateMutability": "nonpayable",
    }
]

w3 = Web3(Web3.HTTPProvider(config.WEB3_PROVIDER))


def buy_token(token_address: str, amount_wei: int):
    """Execute a buy transaction using the configured wallet."""
    router = w3.eth.contract(address=config.ROUTER_ADDRESS, abi=ROUTER_ABI)
    account = w3.eth.account.from_key(config.PRIVATE_KEY)
    path = [w3.to_checksum_address(config.WETH_ADDRESS), token_address]
    deadline = w3.eth.get_block('latest')['timestamp'] + 60

    nonce = w3.eth.get_transaction_count(account.address)
    txn = router.functions.swapExactETHForTokens(
        0,
        path,
        account.address,
        deadline,
    ).build_transaction({
        'from': account.address,
        'value': amount_wei,
        'gas': 300000,
        'gasPrice': w3.to_wei(config.GAS_PRICE_GWEI, 'gwei'),
        'nonce': nonce,
    })

    signed_txn = account.sign_transaction(txn)
    tx_hash = w3.eth.send_raw_transaction(signed_txn.rawTransaction)
    return tx_hash.hex()


def approve_token(token_address: str, spender: str, amount_wei: int):
    token = w3.eth.contract(address=token_address, abi=ERC20_ABI)
    account = w3.eth.account.from_key(config.PRIVATE_KEY)
    nonce = w3.eth.get_transaction_count(account.address)

    txn = token.functions.approve(spender, amount_wei).build_transaction({
        'from': account.address,
        'gas': 100000,
        'gasPrice': w3.to_wei(config.GAS_PRICE_GWEI, 'gwei'),
        'nonce': nonce,
    })
    signed_txn = account.sign_transaction(txn)
    tx_hash = w3.eth.send_raw_transaction(signed_txn.rawTransaction)
    w3.eth.wait_for_transaction_receipt(tx_hash)
    return tx_hash.hex()


def sell_token(token_address: str, amount_wei: int):
    router = w3.eth.contract(address=config.ROUTER_ADDRESS, abi=ROUTER_ABI)
    account = w3.eth.account.from_key(config.PRIVATE_KEY)
    path = [token_address, w3.to_checksum_address(config.WETH_ADDRESS)]
    deadline = w3.eth.get_block('latest')['timestamp'] + 60

    approve_token(token_address, config.ROUTER_ADDRESS, amount_wei)

    nonce = w3.eth.get_transaction_count(account.address)
    txn = router.functions.swapExactTokensForETH(
        amount_wei,
        0,
        path,
        account.address,
        deadline,
    ).build_transaction({
        'from': account.address,
        'gas': 300000,
        'gasPrice': w3.to_wei(config.GAS_PRICE_GWEI, 'gwei'),
        'nonce': nonce,
    })
    signed_txn = account.sign_transaction(txn)
    tx_hash = w3.eth.send_raw_transaction(signed_txn.rawTransaction)
    return tx_hash.hex()
