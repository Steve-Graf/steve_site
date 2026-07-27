(function () {
  // Sprite sheet layout (1009×385, 14 cols × 4 rows)
  // Row 0: [A♣] [2♣] ... [K♣] [back]   (clubs,    cols 0-12; back at col 13)
  // Row 1: [A♦] [2♦] ... [K♦]          (diamonds, cols 0-12)
  // Row 2: [A♥] [2♥] ... [K♥]          (hearts,   cols 0-12)
  // Row 3: [A♠] [2♠] ... [K♠]          (spades,   cols 0-12)

  const CARD_W = 80;
  const CARD_H = 110;
  const SHEET_COLS = 14;
  const SHEET_ROWS = 4;

  const SUITS = [
    { name: 'clubs',    row: 0, colStart: 0, color: 'black' },
    { name: 'diamonds', row: 1, colStart: 0, color: 'red'   },
    { name: 'hearts',   row: 2, colStart: 0, color: 'red'   },
    { name: 'spades',   row: 3, colStart: 0, color: 'black' },
  ];
  const RANKS = ['A','2','3','4','5','6','7','8','9','10','J','Q','K'];

  let SPRITE;

  // ── Deck helpers ────────────────────────────────

  function buildDeck() {
    const deck = [];
    for (const suit of SUITS) {
      for (let i = 0; i < RANKS.length; i++) {
        deck.push({
          suit: suit.name,
          rank: RANKS[i],
          color: suit.color,
          spriteRow: suit.row,
          spriteCol: suit.colStart + i,
        });
      }
    }
    return deck;
  }

  function shuffle(arr) {
    for (let i = arr.length - 1; i > 0; i--) {
      const j = Math.floor(Math.random() * (i + 1));
      [arr[i], arr[j]] = [arr[j], arr[i]];
    }
    return arr;
  }

  // ── Card element factory ─────────────────────────

  function makeCardEl(spriteRow, spriteCol) {
    const el = document.createElement('div');
    el.className = 'card-sprite';
    el.style.cssText = [
      `width:${CARD_W}px`,
      `height:${CARD_H}px`,
      `background-image:url('${SPRITE}')`,
      `background-size:${CARD_W * SHEET_COLS}px ${CARD_H * SHEET_ROWS}px`,
      `background-position:${-spriteCol * CARD_W}px ${-spriteRow * CARD_H}px`,
      'background-repeat:no-repeat',
      'flex-shrink:0',
    ].join(';');
    return el;
  }

  const makeBack = () => makeCardEl(0, 13);
  const makeFace = (card) => makeCardEl(card.spriteRow, card.spriteCol);

  // ── Game state ───────────────────────────────────

  let deck, won, score, highScore, phase;

  const $ = (id) => document.getElementById(id);

  function loadHighScore() {
    const match = document.cookie.match(/(?:^|;\s*)purpleHighScore=(\d+)/);
    return match ? parseInt(match[1], 10) : 0;
  }

  function saveHighScore(n) {
    const expires = new Date();
    expires.setFullYear(expires.getFullYear() + 1);
    document.cookie = `purpleHighScore=${n}; expires=${expires.toUTCString()}; path=/`;
  }

  function init() {
    deck      = shuffle(buildDeck());
    won       = [];
    score     = 0;
    highScore = loadHighScore();
    phase     = 'choose';
    $('high-score').textContent = highScore;
    showChoose();
  }

  // ── Render helpers ───────────────────────────────

  function renderStack() {
    const el = $('stack');
    el.innerHTML = '';
    if (won.length === 0) {
      const hint = document.createElement('span');
      hint.className = 'stack-empty-hint';
      hint.textContent = 'No cards yet';
      el.appendChild(hint);
      return;
    }
    for (const card of won) {
      el.appendChild(makeFace(card));
    }
  }

  function showChoose() {
    $('score').textContent = score;
    renderStack();

    $('current-zone').innerHTML = '';
    $('current-zone').appendChild(makeBack());

    $('buttons').hidden = false;
    setDisabled(false);
    $('gameover').hidden = true;
    phase = 'choose';
  }

  function setDisabled(disabled) {
    $('buttons').querySelectorAll('button').forEach((b) => (b.disabled = disabled));
  }

  // ── Guess handler ────────────────────────────────

  function handleGuess(guess) {
    if (phase !== 'choose') return;
    phase = 'reveal';
    setDisabled(true);

    let cards, correct;

    if (guess === 'purple') {
      if (deck.length < 2) { endGame(); return; }
      cards = [deck.pop(), deck.pop()];
      correct = cards.some((c) => c.color === 'red') && cards.some((c) => c.color === 'black');
    } else {
      if (deck.length < 1) { endGame(); return; }
      cards = [deck.pop()];
      correct = cards[0].color === guess;
    }

    const zone = $('current-zone');
    zone.innerHTML = '';
    const row = document.createElement('div');
    row.className = 'reveal-row';
    for (const card of cards) row.appendChild(makeFace(card));
    zone.appendChild(row);

    if (correct) {
      score += cards.length;
      won.push(...cards);
      $('score').textContent = score;
      setTimeout(showChoose, 1200);
    } else {
      phase = 'gameover';
      setTimeout(endGame, 700);
    }
  }

  function endGame() {
    if (score > highScore) {
      highScore = score;
      saveHighScore(highScore);
      $('high-score').textContent = highScore;
    }
    $('buttons').hidden = true;
    $('gameover').hidden = false;
    phase = 'gameover';
  }

  // ── Boot ─────────────────────────────────────────

  document.addEventListener('DOMContentLoaded', () => {
    SPRITE = document.querySelector('.purple-game').dataset.sprite;

    $('buttons').addEventListener('click', (e) => {
      const btn = e.target.closest('[data-guess]');
      if (btn) handleGuess(btn.dataset.guess);
    });
    $('restart-btn').addEventListener('click', init);
    init();
  });
})();
