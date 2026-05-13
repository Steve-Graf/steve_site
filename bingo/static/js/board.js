(function () {
  const grid = document.getElementById("bingo-grid");
  if (!grid) return;

  const boardId = grid.dataset.boardId;
  const bingoBanner = document.getElementById("bingo-banner");

  const modal = document.getElementById("tile-modal");
  const modalLabel = document.getElementById("tile-modal-label");
  const modalToggleBtn = document.getElementById("tile-modal-toggle");
  const modalBackdrop = document.getElementById("tile-modal-backdrop");

  const isMobile = () => window.matchMedia("(max-width: 600px)").matches;

  async function toggleTile(tile) {
    const row = parseInt(tile.dataset.row, 10);
    const col = parseInt(tile.dataset.col, 10);
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
        tile.classList.toggle("tile--completed");
        tile.setAttribute("aria-pressed", String(wasCompleted));
        return;
      }

      const data = await res.json();
      if (data.has_bingo && bingoBanner) {
        bingoBanner.hidden = false;
      }
    } catch {
      tile.classList.toggle("tile--completed");
      tile.setAttribute("aria-pressed", String(wasCompleted));
    }
  }

  function openModal(tile) {
    modal.dataset.activeTile = `${tile.dataset.row},${tile.dataset.col}`;
    modalLabel.textContent = tile.querySelector(".tile__label").textContent.trim();
    const isCompleted = tile.classList.contains("tile--completed");
    modalToggleBtn.textContent = isCompleted ? "Unmark" : "Mark as Done";
    modalToggleBtn.classList.toggle("btn-primary", !isCompleted);
    modalToggleBtn.classList.toggle("btn-secondary", isCompleted);
    modal.classList.add("tile-modal--open");
    modalBackdrop.classList.add("tile-modal-backdrop--open");
  }

  function closeModal() {
    modal.classList.remove("tile-modal--open");
    modalBackdrop.classList.remove("tile-modal-backdrop--open");
  }

  grid.addEventListener("click", async (e) => {
    const tile = e.target.closest(".tile");
    if (!tile) return;

    if (isMobile() && modal) {
      openModal(tile);
    } else {
      await toggleTile(tile);
    }
  });

  if (modalToggleBtn) {
    modalToggleBtn.addEventListener("click", async () => {
      const [row, col] = modal.dataset.activeTile.split(",");
      const tile = grid.querySelector(`[data-row="${row}"][data-col="${col}"]`);
      await toggleTile(tile);
      const isCompleted = tile.classList.contains("tile--completed");
      modalToggleBtn.textContent = isCompleted ? "Unmark" : "Mark as Done";
      modalToggleBtn.classList.toggle("btn-primary", !isCompleted);
      modalToggleBtn.classList.toggle("btn-secondary", isCompleted);
      closeModal();
    });
  }

  if (modalBackdrop) {
    modalBackdrop.addEventListener("click", closeModal);
  }
})();
