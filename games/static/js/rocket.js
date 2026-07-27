// ── Constants ──────────────────────────────────────────────────────────────
const GROW          = 0.068;   // mult = e^(GROW * t); ~2x at 10 s, ~4x at 20 s
const COUNTDOWN_SEC = 3;
const POST_CRASH    = 3000;    // ms pause after crash before next round
const CURVE_STEPS   = 100;     // curve smoothness
const PAD           = { t: 20, r: 52, b: 32, l: 14 };

// ── State ──────────────────────────────────────────────────────────────────
let phase     = 'countdown';  // 'countdown' | 'flying' | 'bailed' | 'crashed'
let crashAt   = 2;
let mult      = 1.0;
let elapsed   = 0;
let bailedAt  = null;
let bailTime  = null;
let countdown = COUNTDOWN_SEC;
let countdownTimer = null;
let rafId     = null;
let lastTs    = null;
let canvasW   = 0;
let canvasH   = 0;

let personalBest = parseFloat(localStorage.getItem('rocket_pb') || '0');
let history = [];
try { history = JSON.parse(localStorage.getItem('rocket_history') || '[]'); } catch (_) {}

const STARS = Array.from({ length: 130 }, () => ({
  x: Math.random(), y: Math.random(),
  r: Math.random() * 1.4 + 0.3,
  a: Math.random() * 0.6 + 0.25,
}));

// ── DOM refs ───────────────────────────────────────────────────────────────
const canvas       = document.getElementById('rocket-canvas');
const ctx          = canvas.getContext('2d');
const multEl       = document.getElementById('rocket-mult');
const statusEl     = document.getElementById('rocket-status');
const bailBtn      = document.getElementById('bail-btn');
const historyEl    = document.getElementById('rocket-history');
const pbEl         = document.getElementById('rocket-pb-val');
const crashFlash   = document.getElementById('crash-flash');
const bailFlash    = document.getElementById('bail-flash');
const newBestBadge = document.getElementById('new-best-badge');

// ── Canvas sizing ──────────────────────────────────────────────────────────
const ro = new ResizeObserver(entries => {
  for (const entry of entries) {
    canvasW = entry.contentRect.width;
    canvasH = entry.contentRect.height;
    const dpr = window.devicePixelRatio || 1;
    canvas.width  = canvasW * dpr;
    canvas.height = canvasH * dpr;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    redraw();
  }
});
ro.observe(canvas);

// ── Crash distribution ─────────────────────────────────────────────────────
// Pareto: P(crash > x) = (1.26/x)^1.5
// ~50% before 2x, ~87% before 5x, ~95% before 10x, ~98.4% before 20x
function rollCrash() {
  return Math.min(200, 1.26 / Math.pow(1 - Math.random(), 2 / 3));
}

// ── Game flow ──────────────────────────────────────────────────────────────
function startCountdown() {
  phase     = 'countdown';
  mult      = 1.0;
  elapsed   = 0;
  bailedAt  = null;
  bailTime  = null;
  crashAt   = rollCrash();
  countdown = COUNTDOWN_SEC;

  newBestBadge.hidden = true;
  updateUI();
  redraw();

  countdownTimer = setInterval(() => {
    countdown--;
    updateUI();
    if (countdown <= 0) {
      clearInterval(countdownTimer);
      launch();
    }
  }, 1000);
}

function launch() {
  phase  = 'flying';
  lastTs = null;
  updateUI();
  rafId = requestAnimationFrame(tick);
}

function tick(ts) {
  if (!lastTs) lastTs = ts;
  const dt = Math.min((ts - lastTs) / 1000, 0.05);
  lastTs = ts;

  elapsed += dt;
  mult = Math.exp(GROW * elapsed);

  if (mult >= crashAt) {
    elapsed = Math.log(crashAt) / GROW;
    mult    = crashAt;
    doCrash();
    return;
  }

  multEl.textContent = mult.toFixed(2) + 'x';
  redraw();
  rafId = requestAnimationFrame(tick);
}

function bail() {
  if (phase !== 'flying') return;
  phase    = 'bailed';
  bailedAt = mult;
  bailTime = elapsed;

  triggerFlash(bailFlash, 'bail-flash--active');

  if (bailedAt > personalBest) {
    personalBest = bailedAt;
    localStorage.setItem('rocket_pb', personalBest.toFixed(2));
    updatePB();
    newBestBadge.hidden = false;
  }
  updateUI();
}

function doCrash() {
  phase = 'crashed';

  history.unshift({
    mult:   bailedAt !== null ? bailedAt.toFixed(2) : crashAt.toFixed(2),
    bailed: bailedAt !== null,
  });
  if (history.length > 20) history.pop();
  localStorage.setItem('rocket_history', JSON.stringify(history));

  triggerFlash(crashFlash, 'crash-flash--active');
  redraw();
  updateUI();
  updateHistory();
  setTimeout(startCountdown, POST_CRASH);
}

function triggerFlash(el, cls) {
  el.classList.remove(cls);
  void el.offsetWidth;
  el.classList.add(cls);
}

// ── Drawing ────────────────────────────────────────────────────────────────
function redraw() {
  if (!canvasW || !canvasH) return;
  const W = canvasW, H = canvasH;

  ctx.clearRect(0, 0, W, H);
  drawBackground(W, H);
  drawStars(W, H);

  if (phase === 'countdown') return;

  const mEnd = phase === 'crashed' ? crashAt : mult;
  const maxT = Math.max(elapsed, 0.1);
  const maxM = Math.max(mEnd * 1.25, 2);

  function px(t) { return PAD.l + (t / maxT) * (W - PAD.l - PAD.r); }
  function py(m) { return H - PAD.b - ((m - 1) / (maxM - 1)) * (H - PAD.t - PAD.b); }

  // Build full curve analytically from t=0 to now
  const curve = [];
  for (let i = 0; i <= CURVE_STEPS; i++) {
    const t = (i / CURVE_STEPS) * elapsed;
    const m = Math.exp(GROW * t);
    if (phase === 'crashed' && m >= crashAt) {
      curve.push({ t, m: crashAt });
      break;
    }
    curve.push({ t, m });
  }

  drawGrid(W, H, maxM, py);
  drawTrail(curve, px, py);

  if (bailedAt !== null && bailTime !== null) {
    drawBailMarker(bailTime, bailedAt, px, py, W);
  }

  drawRocket({ t: elapsed, m: mEnd }, curve, px, py);
}

function drawBackground(W, H) {
  const grad = ctx.createLinearGradient(0, 0, 0, H);
  grad.addColorStop(0, '#040812');
  grad.addColorStop(1, '#0b1225');
  ctx.fillStyle = grad;
  ctx.fillRect(0, 0, W, H);
}

function drawStars(W, H) {
  for (const s of STARS) {
    ctx.beginPath();
    ctx.arc(s.x * W, s.y * H, s.r, 0, Math.PI * 2);
    ctx.fillStyle = `rgba(255,255,255,${s.a})`;
    ctx.fill();
  }
}

function drawGrid(W, H, maxM, py) {
  const levels = gridLevels(maxM);
  ctx.font = '11px "Fredoka", sans-serif';
  ctx.textAlign = 'right';
  ctx.textBaseline = 'middle';

  for (const lv of levels) {
    if (lv < 1 || lv > maxM) continue;
    const y = py(lv);
    if (y < PAD.t - 8 || y > H - PAD.b + 8) continue;
    ctx.strokeStyle = 'rgba(255,255,255,0.055)';
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(PAD.l, y);
    ctx.lineTo(W - PAD.r + 6, y);
    ctx.stroke();
    ctx.fillStyle = 'rgba(255,255,255,0.32)';
    const label = lv % 1 === 0 ? `${lv}x` : `${lv.toFixed(1)}x`;
    ctx.fillText(label, W - 3, y);
  }
}

function gridLevels(maxM) {
  if (maxM <= 3)   return [1, 1.5, 2, 2.5, 3];
  if (maxM <= 6)   return [1, 2, 3, 4, 5, 6];
  if (maxM <= 15)  return [1, 2, 4, 6, 8, 10, 12, 15];
  if (maxM <= 30)  return [1, 5, 10, 15, 20, 25, 30];
  if (maxM <= 60)  return [1, 10, 20, 30, 40, 50, 60];
  return [1, 20, 50, 100, 150, 200].filter(v => v <= maxM);
}

function trailColor() {
  if (phase === 'crashed') return '#f87171';
  if (phase === 'bailed')  return '#4ade80';
  return '#60a5fa';
}

function drawTrail(curve, px, py) {
  if (curve.length < 2) return;
  const color = trailColor();

  ctx.beginPath();
  ctx.moveTo(px(curve[0].t), py(curve[0].m));
  for (let i = 1; i < curve.length; i++) ctx.lineTo(px(curve[i].t), py(curve[i].m));

  ctx.globalAlpha = 0.18;
  ctx.strokeStyle = color;
  ctx.lineWidth = 10;
  ctx.lineCap = 'round';
  ctx.lineJoin = 'round';
  ctx.stroke();

  ctx.globalAlpha = 1;
  ctx.lineWidth = 2.5;
  ctx.stroke();
}

function drawBailMarker(bt, bm, px, py, W) {
  const x = px(bt), y = py(bm);
  ctx.globalAlpha = 1;

  ctx.beginPath();
  ctx.arc(x, y, 5, 0, Math.PI * 2);
  ctx.fillStyle = '#4ade80';
  ctx.fill();
  ctx.strokeStyle = '#fff';
  ctx.lineWidth = 1.5;
  ctx.stroke();

  ctx.font = '11px "Fredoka", sans-serif';
  ctx.fillStyle = '#4ade80';
  ctx.textBaseline = 'bottom';
  if (x > W * 0.6) {
    ctx.textAlign = 'right';
    ctx.fillText(`${bm.toFixed(2)}x`, x - 8, y - 3);
  } else {
    ctx.textAlign = 'left';
    ctx.fillText(`${bm.toFixed(2)}x`, x + 8, y - 3);
  }
}

function drawRocket(pt, curve, px, py) {
  const x = px(pt.t), y = py(pt.m);
  ctx.globalAlpha = 1;
  ctx.textAlign = 'center';
  ctx.textBaseline = 'middle';
  ctx.font = '26px "Segoe UI Emoji","Apple Color Emoji","Noto Color Emoji",sans-serif';

  if (phase === 'crashed') {
    ctx.fillText('💥', x, y);
    return;
  }

  // Rotate emoji to face direction of travel
  const prev = curve.length > 1 ? curve[curve.length - 2] : curve[0];
  const dx = px(pt.t) - px(prev.t);
  const dy = py(pt.m) - py(prev.m);
  const angle = Math.atan2(dy, dx) + Math.PI / 4;

  ctx.save();
  ctx.translate(x, y);
  ctx.rotate(angle);
  ctx.fillText('🚀', 0, 0);
  ctx.restore();
}

// ── UI updates ─────────────────────────────────────────────────────────────
function updateUI() {
  updateMultDisplay();
  updateStatus();
  updateBailBtn();
}

function updateMultDisplay() {
  const shown = bailedAt ?? mult;
  multEl.textContent = shown.toFixed(2) + 'x';
  multEl.className = 'rocket-multiplier';
  if (phase === 'crashed') multEl.classList.add('rocket-multiplier--crashed');
  else if (phase === 'bailed') multEl.classList.add('rocket-multiplier--bailed');
}

function updateStatus() {
  if (phase === 'countdown') {
    statusEl.textContent = countdown > 0 ? `Launching in ${countdown}…` : 'Launching!';
  } else if (phase === 'flying') {
    statusEl.textContent = '';
  } else if (phase === 'bailed') {
    statusEl.textContent = `Bailed at ${bailedAt.toFixed(2)}x — watching the ride…`;
  } else {
    statusEl.textContent = bailedAt
      ? `Crashed at ${crashAt.toFixed(2)}x  ·  You bailed at ${bailedAt.toFixed(2)}x ✓`
      : `Crashed at ${crashAt.toFixed(2)}x`;
  }
}

function updateBailBtn() {
  if (phase === 'flying') {
    bailBtn.disabled = false;
    bailBtn.textContent = 'BAIL';
    bailBtn.className = 'bail-btn';
  } else if (phase === 'countdown') {
    bailBtn.disabled = true;
    bailBtn.textContent = 'BAIL';
    bailBtn.className = 'bail-btn bail-btn--waiting';
  } else if (phase === 'bailed') {
    bailBtn.disabled = true;
    bailBtn.textContent = `Bailed at ${bailedAt.toFixed(2)}x`;
    bailBtn.className = 'bail-btn bail-btn--success';
  } else {
    bailBtn.disabled = true;
    bailBtn.textContent = bailedAt ? `Bailed at ${bailedAt.toFixed(2)}x` : 'CRASHED';
    bailBtn.className = bailedAt ? 'bail-btn bail-btn--success' : 'bail-btn bail-btn--crashed';
  }
}

function updatePB() {
  pbEl.textContent = personalBest > 0 ? personalBest.toFixed(2) + 'x' : '—';
}

function updateHistory() {
  if (!history.length) {
    historyEl.innerHTML = '<p class="history-empty">No rounds played yet.</p>';
    return;
  }

  const rows = history.map(entry => {
    // handle legacy string entries from old localStorage format
    const bailed = typeof entry === 'object' ? entry.bailed : false;
    const mult   = typeof entry === 'object' ? entry.mult   : entry;
    const cls    = bailed ? 'bailed' : 'crashed';
    const label  = bailed ? 'Bailed' : 'Crashed';
    return `<div class="history-row">
      <span class="history-mult history-mult--${cls}">${mult}x</span>
      <span class="history-status history-status--${cls}">${label}</span>
    </div>`;
  }).join('');

  historyEl.innerHTML = `
    <div class="history-header">
      <span>Multiplier</span><span>Result</span>
    </div>
    ${rows}`;
}

// ── Boot ───────────────────────────────────────────────────────────────────
bailBtn.addEventListener('click', bail);
updatePB();
updateHistory();
startCountdown();
