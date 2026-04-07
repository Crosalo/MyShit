import os

if __name__ == '__main__':
    provider = os.environ.get('WEB3_PROVIDER')
    key = os.environ.get('PRIVATE_KEY')
    print(f"auto_sniper started with provider={provider} and key={'***' if key else None}")
