(function () {
  const TEMPLATES = {
    golf_trip: {
      title: "Golf Trip Bingo",
      tiles: [
        "Breakfast ball taken",
        "Someone loses a ball in the woods",
        "Someone loses a ball in the water",
        "Sandtrap meltdown",
        "Someone blames the wind",
        "That's a gimme (not a gimme)",
        "Scorecard dispute",
        "Someone cheats on their handicap",
        "Chip-in happens",
        "Mid-swing interruption",
        "Post-round drinks",
        "Practice swing chunk",
      ],
    },
    football_game: {
      title: "Football Game Bingo",
      tiles: [
        "Ref makes a bad call",
        "Wave started in the stands",
        "Someone spills their beer",
        "Beer vendor walks by",
        "Argument with an opposing fan",
        "Fourth-quarter comeback",
        "Fumble on the field",
        "Someone leaves early",
        "Group photo in the stands",
        "Stadium prices shock",
        "Coin toss prediction correct",
        "Someone knows a guy on the team",
      ],
    },
    night_out: {
      title: "Night Out Bingo",
      tiles: [
        "Someone texts their ex",
        "Mystery round bought for the group",
        "Lost in the bathroom line",
        "Karaoke happens",
        "Group splits the check wrong",
        "Someone loses their card",
        "One more drink said three times",
        "Spontaneous dance floor",
        "Bouncer interaction",
        "Someone's phone dies",
        "Late night food run",
        "Uber pool chaos",
      ],
    },
  };

  const form = document.getElementById("create-form");
  const tileInput = document.getElementById("tile-input");
  const addBtn = document.getElementById("add-tile-btn");
  const tileList = document.getElementById("tile-list");
  const minTilesSpan = document.getElementById("min-tiles");
  const formError = document.getElementById("form-error");
  const submitBtn = document.getElementById("submit-btn");
  const templateSelect = document.getElementById("template-select");
  const loadTemplateBtn = document.getElementById("load-template-btn");

  const sizeRadios = document.querySelectorAll('input[name="board_size"]');

  let tiles = [];

  function getSelectedSize() {
    for (const r of sizeRadios) {
      if (r.checked) return parseInt(r.value, 10);
    }
    return 4;
  }

  function updateMinTilesHint() {
    const size = getSelectedSize();
    minTilesSpan.textContent = size * size;
  }

  function renderTiles() {
    tileList.innerHTML = "";
    tiles.forEach((label, idx) => {
      const li = document.createElement("li");
      li.className = "tile-list__item";
      li.textContent = label;

      const removeBtn = document.createElement("button");
      removeBtn.type = "button";
      removeBtn.className = "tile-list__remove";
      removeBtn.setAttribute("aria-label", `Remove ${label}`);
      removeBtn.textContent = "×";
      removeBtn.addEventListener("click", () => {
        tiles.splice(idx, 1);
        renderTiles();
      });

      li.appendChild(removeBtn);
      tileList.appendChild(li);
    });
  }

  function addTile() {
    const value = tileInput.value.trim();
    if (!value) return;
    if (tiles.includes(value)) {
      tileInput.value = "";
      return;
    }
    tiles.push(value);
    tileInput.value = "";
    setActive(addBtn, false);
    renderTiles();
  }

  addBtn.addEventListener("click", addTile);

  tileInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
      e.preventDefault();
      addTile();
    }
  });

  sizeRadios.forEach((r) => r.addEventListener("change", updateMinTilesHint));

  function setActive(btn, active) {
    btn.classList.toggle("btn-primary", active);
    btn.classList.toggle("btn-secondary", !active);
  }

  templateSelect.addEventListener("change", () => {
    setActive(loadTemplateBtn, !!templateSelect.value);
  });

  tileInput.addEventListener("input", () => {
    setActive(addBtn, !!tileInput.value.trim());
  });

  loadTemplateBtn.addEventListener("click", () => {
    const key = templateSelect.value;
    if (!key) return;
    const template = TEMPLATES[key];
    for (const tile of template.tiles) {
      if (!tiles.includes(tile)) tiles.push(tile);
    }
    renderTiles();
    const titleInput = document.getElementById("title");
    if (!titleInput.value.trim()) titleInput.value = template.title;
    templateSelect.value = "";
    setActive(loadTemplateBtn, false);
  });

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    formError.hidden = true;

    const title = document.getElementById("title").value.trim();
    const boardSize = getSelectedSize();
    const minTiles = boardSize * boardSize;

    if (!title) {
      formError.textContent = "Please enter a board title.";
      formError.hidden = false;
      return;
    }

    if (tiles.length < minTiles) {
      formError.textContent = `You need at least ${minTiles} tiles for a ${boardSize}×${boardSize} board. You have ${tiles.length}.`;
      formError.hidden = false;
      return;
    }

    submitBtn.disabled = true;
    submitBtn.textContent = "Creating…";

    try {
      const res = await fetch("/bingo/api/boards", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ title, board_size: boardSize, tile_pool: tiles }),
      });

      const data = await res.json();

      if (!res.ok) {
        formError.textContent = data.error || "Something went wrong.";
        formError.hidden = false;
        submitBtn.disabled = false;
        submitBtn.textContent = "Create Board";
        return;
      }

      // Join own board automatically then redirect to view it
      const joinRes = await fetch(`/bingo/api/boards/${data.id}/join`, { method: "POST" });
      const joinData = await joinRes.json();

      window.location.href = `/bingo/boards/${data.id}`;
    } catch {
      formError.textContent = "A network error occurred. Please try again.";
      formError.hidden = false;
      submitBtn.disabled = false;
      submitBtn.textContent = "Create Board";
    }
  });

  updateMinTilesHint();
})();
