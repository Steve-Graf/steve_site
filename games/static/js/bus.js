(function () {
  // Sprite sheet: same layout as purple (14 cols × 4 rows)
  // Row 0=clubs, 1=diamonds, 2=hearts, 3=spades; back at row 0 col 13
  const CARD_W = 80;
  const CARD_H = 110;
  const SHEET_COLS = 14;
  const SHEET_ROWS = 4;

  const SUITS = [
    { name: 'clubs',    row: 0, color: 'black' },
    { name: 'diamonds', row: 1, color: 'red'   },
    { name: 'hearts',   row: 2, color: 'red'   },
    { name: 'spades',   row: 3, color: 'black' },
  ];
  const RANKS = ['A','2','3','4','5','6','7','8','9','10','J','Q','K'];

  let SPRITE;

  function buildDeck() {
    const deck = [];
    for (const suit of SUITS) {
      for (let i = 0; i < RANKS.length; i++) {
        deck.push({
          suit:      suit.name,
          rank:      RANKS[i],
          value:     i === 0 ? 14 : i + 1,
          color:     suit.color,
          spriteRow: suit.row,
          spriteCol: i,
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

  const SUIT_SVG = {
    clubs: `<svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
      <circle cx="12" cy="8.5" r="3.8"/>
      <circle cx="8" cy="13.5" r="3.8"/>
      <circle cx="16" cy="13.5" r="3.8"/>
      <path d="M10.5 17C10 20 9 21 7.5 21.5H16.5C15 21 14 20 13.5 17H10.5Z"/>
    </svg>`,
    diamonds: `<svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
      <path d="M12 2L22 12L12 22L2 12Z"/>
    </svg>`,
    hearts: `<svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
      <path d="M12 21C12 21 2.5 14.5 2.5 8.5C2.5 5.4 5 3 8 3C9.8 3 11.4 3.9 12 5.5C12.6 3.9 14.2 3 16 3C19 3 21.5 5.4 21.5 8.5C21.5 14.5 12 21 12 21Z"/>
    </svg>`,
    spades: `<svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
      <path d="M12 3C12 3 2.5 9 2.5 14C2.5 17 5 18.5 8 18.5C9.5 18.5 10.8 17.8 12 17C10.5 19.5 9 20.5 7.5 21H16.5C15 20.5 13.5 19.5 12 17C13.2 17.8 14.5 18.5 16 18.5C19 18.5 21.5 17 21.5 14C21.5 9 12 3 12 3Z"/>
    </svg>`,
  };

  const STAGE_QUESTIONS = [
    'Red or Black?',
    'Higher or Lower?',
    'In Between or Outside?',
    'Which Suit?',
  ];

  const STAGE_BUTTONS = [
    [
      { label: 'Red',   value: 'red',   cls: 'bus-btn--red'   },
      { label: 'Black', value: 'black', cls: 'bus-btn--black' },
    ],
    [
      { label: 'Higher', value: 'higher', cls: 'bus-btn--higher' },
      { label: 'Lower',  value: 'lower',  cls: 'bus-btn--lower'  },
      { label: 'Same',   value: 'same',   cls: 'bus-btn--same'   },
    ],
    [
      { label: 'In Between', value: 'in-between', cls: 'bus-btn--in'   },
      { label: 'Outside',    value: 'outside',    cls: 'bus-btn--out'  },
      { label: 'Edge',       value: 'edge',       cls: 'bus-btn--edge' },
    ],
    [
      { label: SUIT_SVG.clubs,    value: 'clubs',    cls: 'bus-btn--clubs    bus-btn--icon', aria: 'Clubs'    },
      { label: SUIT_SVG.diamonds, value: 'diamonds', cls: 'bus-btn--diamonds bus-btn--icon', aria: 'Diamonds' },
      { label: SUIT_SVG.spades,   value: 'spades',   cls: 'bus-btn--spades   bus-btn--icon', aria: 'Spades'   },
      { label: SUIT_SVG.hearts,   value: 'hearts',   cls: 'bus-btn--hearts   bus-btn--icon', aria: 'Hearts'   },
    ],
  ];

  let deck, hand, stage, roundsWon, phase;

  const $ = (id) => document.getElementById(id);

  function loadRoundsWon() {
    const match = document.cookie.match(/(?:^|;\s*)busRoundsWon=(\d+)/);
    return match ? parseInt(match[1], 10) : 0;
  }

  function saveRoundsWon(n) {
    const expires = new Date();
    expires.setFullYear(expires.getFullYear() + 1);
    document.cookie = `busRoundsWon=${n}; expires=${expires.toUTCString()}; path=/`;
  }

  function init() {
    deck      = shuffle(buildDeck());
    hand      = [];
    stage     = 0;
    roundsWon = loadRoundsWon();
    phase     = 'choose';
    renderAll();
  }

  function renderAll() {
    renderHand();
    renderProgress();
    $('question-label').textContent = STAGE_QUESTIONS[stage];
    renderCurrentCard();
    renderButtons();
    $('rounds').textContent = roundsWon;
    $('gameover').hidden  = true;
    $('play-area').hidden = false;
    setDisabled(false);
  }

  function renderProgress() {
    document.querySelectorAll('.progress-dot').forEach((dot, i) => {
      dot.classList.toggle('progress-dot--done',   i < stage);
      dot.classList.toggle('progress-dot--active', i === stage);
      dot.classList.toggle('progress-dot--empty',  i > stage);
    });
  }

  function renderHand() {
    const el = $('hand');
    el.innerHTML = '';
    if (hand.length === 0) {
      const hint = document.createElement('span');
      hint.className = 'hand-empty-hint';
      hint.textContent = 'No cards yet';
      el.appendChild(hint);
      return;
    }
    for (const card of hand) el.appendChild(makeFace(card));
  }

  function renderCurrentCard() {
    const zone = $('current-zone');
    zone.innerHTML = '';
    zone.appendChild(makeBack());
  }

  function renderButtons() {
    const container = $('buttons');
    container.innerHTML = '';
    for (const def of STAGE_BUTTONS[stage]) {
      const btn = document.createElement('button');
      btn.className = `bus-btn ${def.cls}`;
      btn.dataset.guess = def.value;
      btn.innerHTML = def.label;
      if (def.aria) btn.setAttribute('aria-label', def.aria);
      container.appendChild(btn);
    }
  }

  function setDisabled(disabled) {
    const container = $('buttons');
    if (disabled) {
      container.style.pointerEvents = 'none';
      container.querySelectorAll('button').forEach(b => (b.disabled = true));
    } else {
      // Defer re-enabling pointer events so the browser doesn't immediately
      // apply :hover to whatever button renders under the cursor
      setTimeout(() => { container.style.pointerEvents = ''; }, 80);
    }
  }

  function isCorrect(card, guess) {
    if (stage === 0) return card.color === guess;
    if (stage === 1) {
      if (guess === 'higher') return card.value > hand[0].value;
      if (guess === 'same')   return card.value === hand[0].value;
      if (guess === 'lower')  return card.value < hand[0].value;
    }
    if (stage === 2) {
      const lo = Math.min(hand[0].value, hand[1].value);
      const hi = Math.max(hand[0].value, hand[1].value);
      const between = card.value > lo && card.value < hi;
      const edge    = card.value === lo || card.value === hi;
      if (guess === 'in-between') return between;
      if (guess === 'edge')       return edge;
      if (guess === 'outside')    return !between && !edge;
    }
    if (stage === 3) return card.suit === guess;
    return false;
  }

  function handleGuess(guess) {
    if (phase !== 'choose') return;
    if (deck.length === 0) { endGame(); return; }

    phase = 'reveal';
    setDisabled(true);

    const card = deck.pop();
    const correct = isCorrect(card, guess);

    const zone = $('current-zone');
    zone.innerHTML = '';
    zone.appendChild(makeFace(card));

    if (correct && stage === 3) {
      hand.push(card);
      roundsWon++;
      saveRoundsWon(roundsWon);
      const roundsEl = $('rounds');
      roundsEl.textContent = roundsWon;
      roundsEl.classList.remove('pop');
      void roundsEl.offsetWidth;
      roundsEl.classList.add('pop');
      setTimeout(() => {
        hand  = [];
        stage = 0;
        phase = 'choose';
        renderAll();
      }, 1400);
    } else if (correct) {
      hand.push(card);
      stage++;
      renderProgress();
      renderHand();
      setTimeout(() => {
        phase = 'choose';
        $('question-label').textContent = STAGE_QUESTIONS[stage];
        renderCurrentCard();
        renderButtons();
        setDisabled(false);
      }, 1200);
    } else {
      setTimeout(() => {
        hand  = [];
        stage = 0;
        phase = 'choose';
        renderAll();
      }, 1200);
    }
  }

  function endGame() {
    $('play-area').hidden = true;
    $('gameover').hidden  = false;
    $('final-rounds').textContent = roundsWon;
  }

  document.addEventListener('DOMContentLoaded', () => {
    SPRITE = document.querySelector('.bus-game').dataset.sprite;

    $('buttons').addEventListener('click', (e) => {
      const btn = e.target.closest('[data-guess]');
      if (btn) handleGuess(btn.dataset.guess);
    });

    $('restart-btn').addEventListener('click', init);
    init();
  });
})();
