(function () {
  const grid = document.getElementById("bingo-grid");
  if (!grid) return;

  const boardId = grid.dataset.boardId;
  const bingoBanner = document.getElementById("bingo-banner");

  grid.addEventListener("click", async (e) => {
    const tile = e.target.closest(".tile");
    if (!tile) return;

    const row = parseInt(tile.dataset.row, 10);
    const col = parseInt(tile.dataset.col, 10);

    // Optimistic toggle
    const wasCompleted = tile.classList.contains("tile--completed");
    tile.classList.toggle("tile--completed");
    tile.setAttribute("aria-pressed", String(!wasCompleted));

    try {
      const res = await fetch(`/bingo/api/player-boards/${boardId}/toggle`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ row, col }),
      });

      if (!res.ok) {
        // Revert optimistic update on failure
        tile.classList.toggle("tile--completed");
        tile.setAttribute("aria-pressed", String(wasCompleted));
        return;
      }

      const data = await res.json();

      if (data.has_bingo && bingoBanner) {
        bingoBanner.hidden = false;
      }
    } catch {
      // Revert on network failure
      tile.classList.toggle("tile--completed");
      tile.setAttribute("aria-pressed", String(wasCompleted));
    }
  });
})();
