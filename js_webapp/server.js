import express from 'express';
import session from 'express-session';
import bodyParser from 'body-parser';
import bcryptjs from 'bcryptjs';
import { spawn } from 'child_process';
import fs from 'fs';

const app = express();
const PORT = process.env.PORT || 3000;

const DB_FILE = './users.json';
let botProcess = null;

app.set('view engine', 'ejs');
app.set('views', './views');
app.use(express.static('public'));
app.use(bodyParser.urlencoded({ extended: false }));
app.use(session({
  secret: process.env.SESSION_SECRET || 'change-me',
  resave: false,
  saveUninitialized: false,
}));

function loadUsers() {
  if (!fs.existsSync(DB_FILE)) return [];
  const text = fs.readFileSync(DB_FILE, 'utf8');
  if (!text.trim()) return [];
  return JSON.parse(text);
}

function saveUsers(users) {
  fs.writeFileSync(DB_FILE, JSON.stringify(users, null, 2));
}

function findUser(username) {
  return loadUsers().find(u => u.username === username);
}

app.get('/', (req, res) => {
  if (!req.session.user) return res.redirect('/login');
  const profits = req.session.user.profits || [];
  const running = botProcess && botProcess.exitCode === null;
  res.render('index', { running, profits });
});

app.get('/register', (req, res) => {
  res.render('register');
});

app.post('/register', async (req, res) => {
  const { username, password } = req.body;
  const users = loadUsers();
  if (findUser(username)) {
    return res.status(400).send('Username taken');
  }
  const hash = await bcryptjs.hash(password, 10);
  const user = { username, password: hash, provider: '', privateKey: '', profits: [] };
  users.push(user);
  saveUsers(users);
  req.session.user = user;
  res.redirect('/settings');
});

app.get('/login', (req, res) => {
  res.render('login');
});

app.post('/login', async (req, res) => {
  const { username, password } = req.body;
  const user = findUser(username);
  if (!user) return res.status(400).send('Invalid credentials');
  if (!(await bcryptjs.compare(password, user.password))) {
    return res.status(400).send('Invalid credentials');
  }
  req.session.user = user;
  res.redirect('/');
});

app.get('/logout', (req, res) => {
  req.session.destroy(() => {
    res.redirect('/login');
  });
});

app.get('/settings', (req, res) => {
  if (!req.session.user) return res.redirect('/login');
  res.render('settings', { user: req.session.user });
});

app.post('/settings', (req, res) => {
  if (!req.session.user) return res.redirect('/login');
  const { provider, privateKey } = req.body;
  const users = loadUsers();
  const user = users.find(u => u.username === req.session.user.username);
  if (user) {
    user.provider = provider;
    user.privateKey = privateKey;
    saveUsers(users);
    req.session.user = user;
  }
  res.redirect('/');
});

app.get('/start', (req, res) => {
  if (!req.session.user) return res.redirect('/login');
  if (!botProcess) {
    const env = { ...process.env };
    if (req.session.user.provider) env.WEB3_PROVIDER = req.session.user.provider;
    if (req.session.user.privateKey) env.PRIVATE_KEY = req.session.user.privateKey;
    const log = fs.openSync('../bot.log', 'a');
    botProcess = spawn(process.execPath, ['../auto_sniper.py'], {
      env,
      stdio: ['ignore', log, log]
    });
    fs.closeSync(log);
  }
  res.redirect('/');
});

app.get('/stop', (req, res) => {
  if (botProcess) {
    botProcess.kill();
    botProcess = null;
  }
  res.redirect('/');
});

app.get('/logs', (req, res) => {
  const path = '../bot.log';
  if (!fs.existsSync(path)) return res.type('text/plain').send('No logs yet');
  const lines = fs.readFileSync(path, 'utf8').trim().split('\n').slice(-50);
  res.type('text/plain').send(lines.join('\n'));
});

app.listen(PORT, () => {
  console.log(`Server running on http://localhost:${PORT}`);
});
