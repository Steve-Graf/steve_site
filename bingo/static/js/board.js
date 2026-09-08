(function () {
  const grid = document.getElementById("bingo-grid");
  if (!grid) return;

  const gameId = grid.dataset.gameId;
  const bingoBanner = document.getElementById("bingo-banner");

  const modal = document.getElementById("tile-modal");
  const modalLabel = document.getElementById("tile-modal-label");
  const modalPhotos = document.getElementById("tile-modal-photos");
  const modalPhotoImg = modalPhotos ? modalPhotos.querySelector(".filmstrip__hero") : null;
  const modalPhotoThumbs = document.getElementById("tile-modal-photo-thumbs");
  const modalPhotoDelete = document.getElementById("tile-modal-photo-delete");
  const modalToggleBtn = document.getElementById("tile-modal-toggle");
  const modalUploadBtn = document.getElementById("tile-modal-upload");
  const modalUploadStatus = document.getElementById("tile-modal-upload-status");
  const modalBackdrop = document.getElementById("tile-modal-backdrop");
  const photoInput = document.getElementById("tile-photo-input");

  if (modalPhotoImg) {
    modalPhotoImg.addEventListener("error", () => {
      modalPhotos.hidden = true;
    });
  }

  const CAMERA_ICON_SVG =
    '<svg viewBox="0 0 24 24" fill="currentColor"><path d="M9 3 7.17 5H4a2 2 0 0 0-2 2v11a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2V7a2 2 0 0 0-2-2h-3.17L15 3H9Zm3 15a5 5 0 1 1 0-10 5 5 0 0 1 0 10Zm0-2a3 3 0 1 0 0-6 3 3 0 0 0 0 6Z"/></svg>';

  let activeTile = null;
  let activePhotos = [];
  let activePhotoIndex = 0;
  let uploadStatusTimeout = null;
  let deleteArmed = false;
  let deleteArmTimeout = null;

  function applyBingo(hasBingo) {
    if (hasBingo && bingoBanner) {
      bingoBanner.hidden = false;
    }
  }

  function applyTileUpdate(tileEl, tile) {
    const photos = tile.photos || [];

    tileEl.classList.toggle("tile--completed", tile.completed);
    tileEl.setAttribute("aria-pressed", String(tile.completed));
    tileEl.dataset.completed = String(tile.completed);
    tileEl.dataset.photos = JSON.stringify(photos);

    let badge = tileEl.querySelector(".tile__photo-badge");
    if (photos.length && !badge) {
      badge = document.createElement("span");
      badge.className = "tile__photo-badge";
      badge.setAttribute("aria-hidden", "true");
      badge.innerHTML = CAMERA_ICON_SVG;
      tileEl.appendChild(badge);
    } else if (!photos.length && badge) {
      badge.remove();
    }
  }

  function setButtonBusy(btn, busy) {
    btn.disabled = busy;
  }

  function setUploadStatus(message, kind) {
    if (!modalUploadStatus) return;
    clearTimeout(uploadStatusTimeout);

    modalUploadStatus.textContent = message;
    modalUploadStatus.classList.remove(
      "tile-modal__upload-status--success",
      "tile-modal__upload-status--error"
    );
    if (kind) modalUploadStatus.classList.add(`tile-modal__upload-status--${kind}`);
    modalUploadStatus.hidden = !message;

    if (message && kind) {
      uploadStatusTimeout = setTimeout(() => setUploadStatus(""), 5000);
    }
  }

  async function toggleTile(tileEl) {
    const tileId = tileEl.dataset.tileId;
    setButtonBusy(modalToggleBtn, true);
    try {
      const res = await fetch(`/bingo/api/games/${gameId}/tiles/${tileId}/toggle`, {
        method: "PATCH",
      });
      if (!res.ok) return;

      const data = await res.json();
      applyTileUpdate(tileEl, data.tile);
      applyBingo(data.has_bingo);
      syncModalToTile(tileEl);
    } finally {
      setButtonBusy(modalToggleBtn, false);
    }
  }

  const MAX_UPLOAD_DIMENSION = 1920;
  const UPLOAD_JPEG_QUALITY = 0.85;

  async function resizeImageForUpload(file) {
    if (!file.type.startsWith("image/")) return file;

    let bitmap;
    try {
      bitmap = await createImageBitmap(file, { imageOrientation: "from-image" });
    } catch (err) {
      return file;
    }

    const scale = Math.min(1, MAX_UPLOAD_DIMENSION / Math.max(bitmap.width, bitmap.height));
    if (scale >= 1) {
      bitmap.close();
      return file;
    }

    const canvas = document.createElement("canvas");
    canvas.width = Math.round(bitmap.width * scale);
    canvas.height = Math.round(bitmap.height * scale);
    canvas.getContext("2d").drawImage(bitmap, 0, 0, canvas.width, canvas.height);
    bitmap.close();

    const blob = await new Promise((resolve) =>
      canvas.toBlob(resolve, "image/jpeg", UPLOAD_JPEG_QUALITY)
    );
    if (!blob) return file;

    const name = file.name.replace(/\.\w+$/, "") + ".jpg";
    return new File([blob], name, { type: "image/jpeg" });
  }

  async function uploadPhoto(tileEl, file) {
    const tileId = tileEl.dataset.tileId;

    setButtonBusy(modalUploadBtn, true);
    setUploadStatus("Uploading…");
    try {
      const resized = await resizeImageForUpload(file);
      const formData = new FormData();
      formData.append("photo", resized);

      const res = await fetch(`/bingo/api/games/${gameId}/tiles/${tileId}/photo`, {
        method: "POST",
        body: formData,
      });
      if (!res.ok) {
        setUploadStatus("Upload failed. Please try again.", "error");
        return;
      }

      const data = await res.json();
      applyTileUpdate(tileEl, data.tile);
      applyBingo(data.has_bingo);
      syncModalToTile(tileEl);
      setUploadStatus("Photo uploaded!", "success");
    } catch (err) {
      setUploadStatus("Upload failed. Please try again.", "error");
    } finally {
      setButtonBusy(modalUploadBtn, false);
    }
  }

  async function deleteActivePhoto() {
    if (!activeTile || !activePhotos.length) return;
    const tileId = activeTile.dataset.tileId;
    const filename = activePhotos[activePhotoIndex].filename;

    setButtonBusy(modalPhotoDelete, true);
    try {
      const res = await fetch(
        `/bingo/api/games/${gameId}/tiles/${tileId}/photos/${encodeURIComponent(filename)}`,
        { method: "DELETE" }
      );
      if (!res.ok) return;

      const data = await res.json();
      applyTileUpdate(activeTile, data.tile);
      applyBingo(data.has_bingo);
      syncModalToTile(activeTile);
    } finally {
      setButtonBusy(modalPhotoDelete, false);
    }
  }

  function renderToggleButton() {
    const isCompleted = activeTile.dataset.completed === "true";
    const hasPhotos = activePhotos.length > 0;

    if (isCompleted && hasPhotos && deleteArmed) {
      const noun = activePhotos.length > 1 ? "photos" : "photo";
      modalToggleBtn.textContent = `Delete ${noun} & unmark`;
      modalToggleBtn.classList.remove("btn-primary", "btn-secondary");
      modalToggleBtn.classList.add("btn-danger");
      return;
    }

    modalToggleBtn.textContent = isCompleted ? "Unmark" : "Mark as Done";
    modalToggleBtn.classList.remove("btn-danger");
    modalToggleBtn.classList.toggle("btn-primary", !isCompleted);
    modalToggleBtn.classList.toggle("btn-secondary", isCompleted);
  }

  function armDelete() {
    deleteArmed = true;
    renderToggleButton();
    clearTimeout(deleteArmTimeout);
    deleteArmTimeout = setTimeout(disarmDelete, 4000);
  }

  function disarmDelete() {
    deleteArmed = false;
    clearTimeout(deleteArmTimeout);
    deleteArmTimeout = null;
    if (activeTile) renderToggleButton();
  }

  function renderSlideshow() {
    if (!modalPhotos) return;

    if (!activePhotos.length) {
      modalPhotos.hidden = true;
      return;
    }

    modalPhotos.hidden = false;
    modalPhotoImg.src = activePhotos[activePhotoIndex].url;

    if (modalPhotoThumbs) {
      modalPhotoThumbs.hidden = activePhotos.length <= 1;
      modalPhotoThumbs.innerHTML = "";
      activePhotos.forEach((photo, i) => {
        const thumb = document.createElement("button");
        thumb.type = "button";
        thumb.className =
          "filmstrip__thumb" + (i === activePhotoIndex ? " filmstrip__thumb--active" : "");
        thumb.style.backgroundImage = `url('${photo.url}')`;
        thumb.setAttribute("aria-label", `View photo ${i + 1}`);
        thumb.addEventListener("click", () => {
          activePhotoIndex = i;
          renderSlideshow();
        });
        modalPhotoThumbs.appendChild(thumb);
      });
    }
  }

  function syncModalToTile(tileEl) {
    activePhotos = JSON.parse(tileEl.dataset.photos || "[]");
    activePhotoIndex = activePhotos.length - 1;

    disarmDelete();
    renderSlideshow();
  }

  function openModal(tileEl) {
    activeTile = tileEl;
    modalLabel.textContent = tileEl.querySelector(".tile__label").textContent.trim();
    syncModalToTile(tileEl);
    setUploadStatus("");
    modal.classList.add("tile-modal--open");
    modalBackdrop.classList.add("tile-modal-backdrop--open");
  }

  function closeModal() {
    modal.classList.remove("tile-modal--open");
    modalBackdrop.classList.remove("tile-modal-backdrop--open");
    clearTimeout(deleteArmTimeout);
    deleteArmTimeout = null;
    deleteArmed = false;
    activeTile = null;
  }

  grid.addEventListener("click", (e) => {
    const tile = e.target.closest(".tile");
    if (!tile) return;
    openModal(tile);
  });

  if (modalToggleBtn) {
    modalToggleBtn.addEventListener("click", () => {
      if (!activeTile) return;

      const isCompleted = activeTile.dataset.completed === "true";
      const hasPhotos = activePhotos.length > 0;

      if (isCompleted && hasPhotos && !deleteArmed) {
        armDelete();
        return;
      }

      disarmDelete();
      toggleTile(activeTile);
    });
  }

  if (modalUploadBtn && photoInput) {
    modalUploadBtn.addEventListener("click", () => photoInput.click());
  }

  if (modalPhotoDelete) {
    modalPhotoDelete.addEventListener("click", deleteActivePhoto);
  }

  function handleFileInputChange(input) {
    input.addEventListener("change", () => {
      const file = input.files[0];
      input.value = "";
      if (file && activeTile) uploadPhoto(activeTile, file);
    });
  }

  if (photoInput) handleFileInputChange(photoInput);

  if (modalBackdrop) {
    modalBackdrop.addEventListener("click", closeModal);
  }
})();
