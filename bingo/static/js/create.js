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
    road_trip: {
      title: "Road Trip Bingo",
      tiles: [
        "Someone needs to pee within the first hour",
        "GPS takes a weird route",
        "Aux cord argument",
        "Someone falls asleep immediately",
        "Wrong turn taken",
        "Rest stop snack debate",
        '"How much longer?" asked',
        "Car karaoke happens",
        "Speed trap spotted",
        "Someone misses an exit",
        "Fast food consensus fails",
        "State line photo taken",
        "Radio station war",
        "Gas station bathroom reviewed",
        "Someone's phone mount falls",
        "Snack bag opened too early",
        "Driver refuses to ask for directions",
        "Seat recline conflict",
        "Someone's playlist gets skipped",
        "Service goes out at a critical moment",
      ],
    },
    wedding: {
      title: "Wedding Reception Bingo",
      tiles: [
        "Vows make someone cry",
        "Drunk uncle spotted",
        "Best man speech goes too long",
        "Open bar rush",
        "Photo booth line forms",
        "Couple that probably shouldn't be together",
        "Dance floor clears for a slow song",
        "Someone catches the bouquet dramatically",
        "Kids running wild",
        "DJ plays a bad request",
        "Dessert table stampede",
        "Seating chart confusion",
        "Someone gives unsolicited marriage advice",
        "Toast goes off-script",
        "Newlyweds sneak off early",
        "Flower girl or ring bearer meltdown",
        "Table runs out of wine",
        "Someone hits the dance floor too hard",
        "Wedding hashtag announced",
        "Couple's first dance stumbles",
      ],
    },
    office_happy_hour: {
      title: "Office Happy Hour Bingo",
      tiles: [
        "Manager overshares",
        "Someone checks Slack at the bar",
        "Work gossip spills",
        "Tab mishap",
        "Two people leave suspiciously together",
        "Round ordered for wrong number of people",
        "Someone gets drunker than expected",
        "Early departure with a lame excuse",
        "Inside joke no one gets",
        "Person pretends to know wine",
        '"This is off the record" moment',
        "Someone complains about a coworker",
        "HR joke made nervously",
        "Work story repeats from last time",
        "Someone brings up the annual review",
        "Team-building activity mentioned",
        "Someone orders water nervously",
        "Expense report joke",
        "Promotion rumor circulates",
        "Someone's partner texts them to leave",
      ],
    },
    trivia_night: {
      title: "Bar Trivia Night Bingo",
      tiles: [
        "Team argues over an answer",
        "Wrong answer submitted confidently",
        '"Should\'ve gone with our first answer"',
        "Someone Googles under the table",
        "Tie-breaker round happens",
        "Official answer gets protested",
        "Picture round panic",
        "Wildly wrong guess accepted by the team",
        "Someone zones out on their phone",
        "Name dispute with the host",
        "Someone leaves before final scores",
        "Team name regretted",
        "Bonus round catches everyone off guard",
        "Rivalry with another table forms",
        "One person carries the whole team",
        "Audio round causes chaos",
        "Sports category saves or sinks the team",
        "Prize revealed to be disappointing",
        "Someone demands a recount",
        "Last-second answer change backfires",
      ],
    },
    concert: {
      title: "Concert Bingo",
      tiles: [
        "Phone flashlight forest during a ballad",
        "Person in front of you is 6'5\"",
        "Merch line longer than the food line",
        "Surprise guest announced",
        "Crowd sings louder than the artist",
        "Someone spills a drink on you",
        "Setlist debate before the show",
        '"This is their best album" argument',
        "Sound check takes forever",
        "Fan knows every single word",
        "Bathroom run during an unfamiliar song",
        "Mosh pit forms unexpectedly",
        "Someone crowd surfs",
        "Opening act gets booed",
        "Someone cries during a song",
        "Encore chant starts",
        "Security interaction",
        '"I saw them before they were famous"',
        "Phone dies before the main set",
        "Ears still ringing after",
      ],
    },
    camping: {
      title: "Camping Trip Bingo",
      tiles: [
        "Tent assembly argument",
        "Forgot something essential",
        "Someone scared of a bug",
        "Fire won't start",
        "S'mores ratio argument",
        "Wildlife sighting causes panic",
        "Late night flashlight bathroom trip",
        "Someone sleeps through the sunrise hike",
        "Camp food disaster",
        "Unexpected rain",
        "Raccoon visits camp",
        "Hiking trail disagreement",
        '"Roughing it" said unironically',
        "Bug spray crisis",
        "Someone's air mattress deflates overnight",
        "Bear box argument",
        "Campfire smoke follows you everywhere",
        "Forgotten firewood run",
        "Campfire story gets too scary",
        "Sunrise actually worth it",
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
