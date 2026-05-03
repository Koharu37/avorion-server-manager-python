/* ═══════ Avorion Server Manager — Frontend (Python SocketIO) ═══════ */

// ─── State ────────────────────────────────────────────────────────────────────
let socket = null;
let settings = {};
let isRunning = false;

// ─── Init ─────────────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  initNav();
  connectSocketIO();
  loadSettings();
  loadGameConfig();
  pollStatus();
  setInterval(pollStatus, 3000);
});

// ─── Navigation ───────────────────────────────────────────────────────────────
function initNav() {
  document.querySelectorAll('.nav-btn').forEach((btn) => {
    btn.addEventListener('click', () => switchTab(btn.dataset.tab));
  });
}

function switchTab(tab) {
  document.querySelectorAll('.nav-btn').forEach((b) => b.classList.remove('active'));
  document.querySelector(`.nav-btn[data-tab="${tab}"]`).classList.add('active');
  document.querySelectorAll('.tab-panel').forEach((p) => p.classList.remove('active'));
  document.getElementById(`panel-${tab}`).classList.add('active');
}

// ─── Socket.IO ────────────────────────────────────────────────────────────────
function connectSocketIO() {
  socket = io();
  socket.on('log', (data) => appendLog(data));
  socket.on('serverStarted', () => pollStatus());
  socket.on('serverStopped', () => pollStatus());
  socket.on('installDone', () => {
    toast('서버 설치/업데이트 완료', 'success');
    document.getElementById('btn-install').disabled = false;
    document.getElementById('install-status').textContent = '';
  });
}

// ─── Console ──────────────────────────────────────────────────────────────────
function appendLog(entry) {
  const targets = ['console-output', 'console-mini'];
  targets.forEach((id) => {
    const el = document.getElementById(id);
    if (!el) return;
    const div = document.createElement('div');
    div.className = 'console-line';
    const time = new Date(entry.time).toLocaleTimeString('ko-KR');
    let cls = '';
    if (entry.text.startsWith('[ERR]') || entry.text.startsWith('[SteamCMD ERR]')) cls = 'err';
    else if (entry.text.startsWith('>')) cls = 'cmd';
    else if (entry.text.startsWith('===')) cls = 'sys';
    div.innerHTML = `<span class="time">${time}</span><span class="text ${cls}">${escHtml(entry.text)}</span>`;
    el.appendChild(div);
    if (id === 'console-output' && document.getElementById('auto-scroll').checked) {
      el.scrollTop = el.scrollHeight;
    }
    if (id === 'console-mini') el.scrollTop = el.scrollHeight;
    if (id === 'console-mini' && el.children.length > 30) el.removeChild(el.firstChild);
  });
}

function clearConsole() {
  document.getElementById('console-output').innerHTML = '';
}

function sendCommand() {
  const input = document.getElementById('console-input');
  const cmd = input.value.trim();
  if (!cmd) return;
  fetch('/api/command', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ command: cmd }),
  })
    .then((r) => r.json())
    .then((d) => { if (d.error) toast(d.error, 'error'); })
    .catch((e) => toast(e.message, 'error'));
  input.value = '';
  input.focus();
}

// ─── Status Polling ───────────────────────────────────────────────────────────
function pollStatus() {
  fetch('/api/status')
    .then((r) => r.json())
    .then((s) => {
      isRunning = s.running;
      updateStatusUI(s);
    })
    .catch(() => {});
}

function updateStatusUI(s) {
  const badge = document.getElementById('status-badge');
  const ring = document.getElementById('status-ring');
  const ringLabel = document.getElementById('ring-label');
  const btnStart = document.getElementById('btn-start');
  const btnStop = document.getElementById('btn-stop');
  const uptimeEl = document.getElementById('uptime-label');
  const pidEl = document.getElementById('info-pid');

  if (s.running) {
    badge.classList.add('online');
    badge.querySelector('.status-text').textContent = 'Online';
    ring.classList.add('online');
    ringLabel.textContent = 'ONLINE';
    btnStart.disabled = true;
    btnStop.disabled = false;
    uptimeEl.textContent = `업타임: ${formatUptime(s.uptime)}`;
    pidEl.textContent = s.pid || '-';
  } else {
    badge.classList.remove('online');
    badge.querySelector('.status-text').textContent = 'Offline';
    ring.classList.remove('online');
    ringLabel.textContent = 'OFFLINE';
    btnStart.disabled = false;
    btnStop.disabled = true;
    uptimeEl.textContent = '';
    pidEl.textContent = '-';
  }
}

function formatUptime(sec) {
  if (!sec) return '0초';
  const h = Math.floor(sec / 3600);
  const m = Math.floor((sec % 3600) / 60);
  const s = sec % 60;
  let out = '';
  if (h) out += `${h}시간 `;
  if (m) out += `${m}분 `;
  out += `${s}초`;
  return out;
}

// ─── Settings ─────────────────────────────────────────────────────────────────
function loadSettings() {
  fetch('/api/settings')
    .then((r) => r.json())
    .then((cfg) => {
      settings = cfg;
      populateSettingsForm(cfg);
      updateInfoCards(cfg);
    });
}

function populateSettingsForm(cfg) {
  const fields = ['steamcmdPath','serverPath','serverName','galaxyName','port','maxPlayers','saveInterval','adminSteamId','seed','webPort'];
  fields.forEach((f) => {
    const el = document.getElementById(`set-${f}`);
    if (el) el.value = cfg[f] ?? '';
  });
}

function updateInfoCards(cfg) {
  document.getElementById('info-name').textContent = cfg.serverName || '-';
  document.getElementById('info-galaxy').textContent = cfg.galaxyName || '-';
  document.getElementById('info-port').textContent = cfg.port || '-';
  document.getElementById('info-players').textContent = cfg.maxPlayers || '-';
  document.getElementById('info-save').textContent = cfg.saveInterval ? `${cfg.saveInterval}초` : '-';
}

function saveSettings(e) {
  e.preventDefault();
  const form = document.getElementById('settings-form');
  const data = {};
  new FormData(form).forEach((v, k) => {
    data[k] = ['port','maxPlayers','saveInterval','webPort'].includes(k) ? Number(v) : v;
  });
  fetch('/api/settings', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
    .then((r) => r.json())
    .then(() => {
      toast('설정이 저장되었습니다', 'success');
      loadSettings();
    })
    .catch((e) => toast(e.message, 'error'));
}

// ─── Game Config ──────────────────────────────────────────────────────────────
let gameConfigData = {};

function loadGameConfig() {
  fetch('/api/gameconfig')
    .then((r) => r.json())
    .then((res) => {
      if (res.exists) {
        gameConfigData = res.data;
        document.getElementById('gameconfig-placeholder').style.display = 'none';
        document.getElementById('gameconfig-form').style.display = 'block';
        populateGameConfig(res.data);
      }
    });
}

function populateGameConfig(data) {
  const game = data['Game'] || data['Game Options'] || {};
  const net = data['Networking'] || data['Network'] || {};
  const setVal = (id, val) => {
    const el = document.getElementById(id);
    if (el && val !== undefined) el.value = val;
  };
  setVal('gc-Difficulty', game.Difficulty);
  setVal('gc-HardcoreEnabled', game.HardcoreEnabled);
  setVal('gc-InfiniteResources', game.InfiniteResources);
  setVal('gc-CollisionDamage', game.CollisionDamage);
  setVal('gc-PlayerToPlayerDamage', game.PlayerToPlayerDamage);
  setVal('gc-LogoutInvincibility', game.LogoutInvincibility);
  setVal('gc-isPublic', net.isPublic);
  setVal('gc-isListed', net.isListed);
  setVal('gc-password', net.password);
  setVal('gc-motd', net.motd);
}

function saveGameConfig(e) {
  e.preventDefault();
  const form = document.getElementById('gameconfig-form');
  const fd = new FormData(form);
  const gameSection = gameConfigData['Game'] ? 'Game' : 'Game Options';
  const netSection = gameConfigData['Networking'] ? 'Networking' : 'Network';
  const data = JSON.parse(JSON.stringify(gameConfigData));
  if (!data[gameSection]) data[gameSection] = {};
  if (!data[netSection]) data[netSection] = {};
  ['Difficulty','HardcoreEnabled','InfiniteResources','CollisionDamage','PlayerToPlayerDamage','LogoutInvincibility'].forEach((k) => {
    data[gameSection][k] = fd.get(k);
  });
  ['isPublic','isListed','password','motd'].forEach((k) => {
    data[netSection][k] = fd.get(k);
  });
  fetch('/api/gameconfig', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
    .then((r) => r.json())
    .then(() => toast('게임 설정이 저장되었습니다', 'success'))
    .catch((e) => toast(e.message, 'error'));
}

// ─── Server Control ───────────────────────────────────────────────────────────
function startServer() {
  document.getElementById('btn-start').disabled = true;
  fetch('/api/start', { method: 'POST' })
    .then((r) => r.json())
    .then((d) => {
      if (d.error) { toast(d.error, 'error'); document.getElementById('btn-start').disabled = false; }
      else toast('서버 시작 중...', 'info');
    })
    .catch((e) => { toast(e.message, 'error'); document.getElementById('btn-start').disabled = false; });
}

function stopServer() {
  document.getElementById('btn-stop').disabled = true;
  fetch('/api/stop', { method: 'POST' })
    .then((r) => r.json())
    .then((d) => {
      if (d.error) { toast(d.error, 'error'); document.getElementById('btn-stop').disabled = false; }
      else toast('서버 중지 중...', 'info');
    })
    .catch((e) => { toast(e.message, 'error'); document.getElementById('btn-stop').disabled = false; });
}

// ─── SteamCMD ─────────────────────────────────────────────────────────────────
function installServer() {
  const btn = document.getElementById('btn-install');
  btn.disabled = true;
  document.getElementById('install-status').textContent = '설치 중... 콘솔 탭에서 진행 상황을 확인하세요.';
  fetch('/api/install', { method: 'POST' })
    .then((r) => r.json())
    .then((d) => {
      if (d.error) { toast(d.error, 'error'); btn.disabled = false; document.getElementById('install-status').textContent = ''; }
    })
    .catch((e) => { toast(e.message, 'error'); btn.disabled = false; });
}

// ─── Helpers ──────────────────────────────────────────────────────────────────
function escHtml(s) {
  const d = document.createElement('div');
  d.textContent = s;
  return d.innerHTML;
}

function toast(msg, type = 'info') {
  const container = document.getElementById('toast-container');
  const el = document.createElement('div');
  el.className = `toast toast--${type}`;
  el.textContent = msg;
  container.appendChild(el);
  setTimeout(() => { el.style.opacity = '0'; setTimeout(() => el.remove(), 300); }, 3500);
}
