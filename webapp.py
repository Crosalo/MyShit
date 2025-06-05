import os
import sqlite3
import subprocess
from flask import Flask

app = Flask(__name__)

bot_process = None

def get_current_user():
    """Load the first user from app.db."""
    if not os.path.exists('app.db'):
        return None
    conn = sqlite3.connect('app.db')
    try:
        row = conn.execute('SELECT provider, private_key FROM users LIMIT 1').fetchone()
    finally:
        conn.close()
    if row:
        return {'provider': row[0], 'private_key': row[1]}
    return None

def start_bot():
    global bot_process
    user = get_current_user()
    env = os.environ.copy()
    if user:
        env['WEB3_PROVIDER'] = user['provider']
        env['PRIVATE_KEY'] = user['private_key']
    bot_process = subprocess.Popen(['python', 'auto_sniper.py'], env=env)

@app.route('/')
def index():
    running = bot_process is not None and bot_process.poll() is None
    return f"Bot running: {running}"

if __name__ == '__main__':
    app.run()
