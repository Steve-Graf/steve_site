const COLORS = [
  { id: 'red',    hex: '#e53935', label: 'Red'    },
  { id: 'orange', hex: '#fb8c00', label: 'Orange' },
  { id: 'gold',   hex: '#f9a825', label: 'Gold'   },
  { id: 'green',  hex: '#43a047', label: 'Green'  },
  { id: 'teal',   hex: '#00897b', label: 'Teal'   },
  { id: 'blue',   hex: '#1e88e5', label: 'Blue'   },
  { id: 'indigo', hex: '#3949ab', label: 'Indigo' },
  { id: 'purple', hex: '#8e24aa', label: 'Purple' },
  { id: 'pink',   hex: '#d81b60', label: 'Pink'   },
  { id: 'brown',  hex: '#6d4c41', label: 'Brown'  },
];

const TOKEN_SIZE = 38;

const HORSE_NAMES = [
  'Secretariat', 'Seabiscuit', 'Black Beauty', "Man o' War", 'Phar Lap',
  'Shadowfax', 'Silver', 'Trigger', 'Mr. Ed', 'Spirit',
];

let horses = [];
let raceActive = false;
let frameId = null;
let placeCounter = 0;

// ── Setup ────────────────────────────────────────────

function addHorse() {
  if (horses.length >= COLORS.length) return;

  const usedIds = new Set(horses.map(h => h.colorId));
  const color = COLORS.find(c => !usedIds.has(c.id));

  horses.push({
    id: Date.now(),
    name: HORSE_NAMES[horses.length] ?? `Horse ${horses.length + 1}`,
    colorId: color.id,
    colorHex: color.hex,
    progress: 0,
    speed: 0,
    finished: false,
    place: null,
    trackEl: null,
    horseEl: null,
  });

  renderSetup();
}

function removeHorse(id) {
  horses = horses.filter(h => h.id !== id);
  renderSetup();
}

function renderSetup() {
  const list = document.getElementById('horse-list');
  list.innerHTML = '';

  horses.forEach(horse => {
    const row = document.createElement('div');
    row.className = 'horse-row';

    const swatches = document.createElement('div');
    swatches.className = 'color-swatches';
    COLORS.forEach(c => {
      const btn = document.createElement('button');
      btn.className = 'swatch' + (horse.colorId === c.id ? ' swatch--active' : '');
      btn.style.background = c.hex;
      btn.title = c.label;
      btn.type = 'button';
      btn.addEventListener('click', () => {
        horse.colorId = c.id;
        horse.colorHex = c.hex;
        renderSetup();
      });
      swatches.appendChild(btn);
    });

    const input = document.createElement('input');
    input.className = 'horse-name-input';
    input.type = 'text';
    input.value = horse.name;
    input.maxLength = 20;
    input.placeholder = 'Horse name…';
    input.addEventListener('input', () => {
      horse.name = input.value || 'Horse';
    });

    const removeBtn = document.createElement('button');
    removeBtn.className = 'remove-btn';
    removeBtn.type = 'button';
    removeBtn.textContent = '✕';
    removeBtn.addEventListener('click', () => removeHorse(horse.id));

    row.append(swatches, input, removeBtn);
    list.appendChild(row);
  });

  document.getElementById('add-horse-btn').disabled = horses.length >= COLORS.length;
  document.getElementById('start-race-btn').disabled = horses.length < 2;
}

// ── Race ─────────────────────────────────────────────

function buildTrack() {
  const container = document.getElementById('track-container');
  container.innerHTML = '';

  horses.forEach(horse => {
    horse.progress = 0;
    horse.speed = 0.03 + Math.random() * 0.015;
    horse.targetSpeed = horse.speed;
    horse.burstTimer = Math.floor(Math.random() * 60); // stagger first bursts
    horse.finished = false;
    horse.place = null;

    const lane = document.createElement('div');
    lane.className = 'lane';

    const label = document.createElement('div');
    label.className = 'lane__label';
    label.textContent = horse.name;
    label.style.color = horse.colorHex;

    const track = document.createElement('div');
    track.className = 'lane__track';

    const token = document.createElement('div');
    token.className = 'horse-token';
    token.style.background = horse.colorHex;
    token.textContent = '🏇';

    track.appendChild(token);

    const finishFlag = document.createElement('div');
    finishFlag.className = 'lane__finish';
    finishFlag.textContent = '🏁';

    lane.append(label, track, finishFlag);
    container.appendChild(lane);

    horse.trackEl = track;
    horse.horseEl = token;
  });
}

function startRace() {
  if (frameId) cancelAnimationFrame(frameId);
  placeCounter = 0;
  buildTrack();

  document.getElementById('setup-screen').hidden = true;
  document.getElementById('race-screen').hidden = false;
  document.getElementById('race-result').hidden = true;

  raceActive = true;
  frameId = requestAnimationFrame(tick);
}

function tick() {
  if (!raceActive) return;

  let winner = null;

  horses.forEach(horse => {
    if (horse.finished) return;

    // Periodically pick a new target speed (cruise / sprint / reverse)
    if (--horse.burstTimer <= 0) {
      const r = Math.random();
      if (r < 0.22) {
        horse.targetSpeed = 0.10 + Math.random() * 0.08;          // sprint
        horse.burstTimer = 40 + Math.floor(Math.random() * 35);
      } else if (r < 0.42) {
        horse.targetSpeed = -(0.02 + Math.random() * 0.04);       // reverse
        horse.burstTimer = 35 + Math.floor(Math.random() * 30);
      } else {
        horse.targetSpeed = 0.02 + Math.random() * 0.025;         // cruise
        horse.burstTimer = 70 + Math.floor(Math.random() * 70);
      }
    }

    horse.speed += (horse.targetSpeed - horse.speed) * 0.15;
    horse.progress = Math.max(0, horse.progress + horse.speed);

    if (horse.progress >= 100) {
      horse.progress = 100;
      horse.finished = true;
      horse.place = ++placeCounter;
      if (horse.place === 1) winner = horse;
    }

    const maxX = horse.trackEl.clientWidth - TOKEN_SIZE;
    const x = (horse.progress / 100) * maxX;
    const facing = horse.speed < -0.005 ? 1 : -1;
    horse.horseEl.style.transform = `translateX(${x}px) scaleX(${facing})`;
  });

  if (winner) {
    raceActive = false;
    winner.horseEl.classList.add('horse-token--winner');

    const winnerText = document.getElementById('winner-text');
    winnerText.textContent = `${winner.name} wins!`;
    winnerText.style.color = winner.colorHex;
    document.getElementById('race-result').hidden = false;
    return;
  }

  frameId = requestAnimationFrame(tick);
}

function raceAgain() {
  if (frameId) cancelAnimationFrame(frameId);
  raceActive = false;
  startRace();
}

function editHorses() {
  if (frameId) cancelAnimationFrame(frameId);
  raceActive = false;
  document.getElementById('race-screen').hidden = true;
  document.getElementById('setup-screen').hidden = false;
  renderSetup();
}

// ── Init ─────────────────────────────────────────────

document.getElementById('add-horse-btn').addEventListener('click', addHorse);
document.getElementById('start-race-btn').addEventListener('click', startRace);
document.getElementById('race-again-btn').addEventListener('click', raceAgain);
document.getElementById('edit-horses-btn').addEventListener('click', editHorses);

for (let i = 0; i < 6; i++) addHorse();
