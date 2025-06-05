from flask import Flask, request, redirect, render_template, session, url_for
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import subprocess

DB_PATH = 'app.db'
app = Flask(__name__)
app.secret_key = 'change-me'


def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT,
            provider TEXT,
            private_key TEXT
        )''')
        c.execute('''CREATE TABLE IF NOT EXISTS trades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            profit REAL,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )''')
        conn.commit()


init_db()

bot_process = None


def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


@app.route('/')
def index():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    conn = get_db_connection()
    trades = conn.execute('SELECT profit FROM trades WHERE user_id=?', (session['user_id'],)).fetchall()
    conn.close()
    profits = [t['profit'] for t in trades]
    return render_template('index.html', profits=profits, running=bot_process is not None)


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = generate_password_hash(request.form['password'])
        conn = get_db_connection()
        try:
            conn.execute('INSERT INTO users (username, password) VALUES (?, ?)',
                         (username, password))
            conn.commit()
        except sqlite3.IntegrityError:
            conn.close()
            return 'Username already taken', 400
        user_id = conn.execute('SELECT id FROM users WHERE username=?', (username,)).fetchone()['id']
        session['user_id'] = user_id
        conn.close()
        return redirect(url_for('settings'))
    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE username=?', (username,)).fetchone()
        conn.close()
        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            return redirect(url_for('index'))
        return 'Invalid credentials', 400
    return render_template('login.html')


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


@app.route('/settings', methods=['GET', 'POST'])
def settings():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    conn = get_db_connection()
    if request.method == 'POST':
        provider = request.form['provider']
        private_key = request.form['private_key']
        conn.execute('UPDATE users SET provider=?, private_key=? WHERE id=?',
                     (provider, private_key, session['user_id']))
        conn.commit()
    user = conn.execute('SELECT provider, private_key FROM users WHERE id=?',
                        (session['user_id'],)).fetchone()
    conn.close()
    return render_template('settings.html', provider=user['provider'],
                           private_key=user['private_key'])


@app.route('/start')
def start_bot():
    global bot_process
    if bot_process is None:
        bot_process = subprocess.Popen(['python', 'auto_sniper.py'])
    return redirect(url_for('index'))


@app.route('/stop')
def stop_bot():
    global bot_process
    if bot_process is not None:
        bot_process.terminate()
        bot_process = None
    return redirect(url_for('index'))


if __name__ == '__main__':
    app.run(debug=True)
