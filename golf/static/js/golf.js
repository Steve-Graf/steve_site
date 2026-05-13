import { VideoSyncManager } from "./video_sync.js";
import { PoseDetector }     from "./pose_detector.js";

const MAX_DURATION_S = 30;
const ANGLES         = ["DTL", "FO"];

// ── State ─────────────────────────────────────────────────────────────
let nextId     = 1;
const gallery  = [];  // [{ id, name, angle, duration, blobUrl }]
const panels   = [];  // [{ id, galleryId, panelEl, videoEl }]

const sync   = new VideoSyncManager();
const poser  = new PoseDetector();

// ── DOM refs ───────────────────────────────────────────────────────────
const videoGrid         = document.getElementById("video-grid");
const emptyState        = document.getElementById("empty-state");
const galleryStrip      = document.getElementById("gallery-strip");
const uploadInput       = document.getElementById("upload-input");
const uploadError       = document.getElementById("upload-error");
const masterPlayBtn     = document.getElementById("btn-master-play");
const stepFwdBtn        = document.getElementById("btn-step-fwd");
const stepBackBtn       = document.getElementById("btn-step-back");
const masterScrubber    = document.getElementById("master-scrubber");
const speedBtns         = document.querySelectorAll(".btn-speed");
const wireframeToggleBtn= document.getElementById("btn-toggle-wireframes");

const panelTpl   = document.getElementById("panel-template");
const cardTpl    = document.getElementById("gallery-card-template");

// ── Upload ─────────────────────────────────────────────────────────────
uploadInput.addEventListener("change", (e) => {
  Array.from(e.target.files).forEach(handleFile);
  uploadInput.value = "";
});

function handleFile(file) {
  const blobUrl = URL.createObjectURL(file);
  const probe   = document.createElement("video");
  probe.preload = "metadata";
  probe.src     = blobUrl;

  probe.addEventListener("loadedmetadata", () => {
    if (probe.duration > MAX_DURATION_S) {
      URL.revokeObjectURL(blobUrl);
      showUploadError(`"${file.name}" is ${Math.round(probe.duration)}s — max 30s.`);
      return;
    }
    hideUploadError();
    const entry = {
      id:       nextId++,
      name:     file.name.replace(/\.[^.]+$/, ""),
      angle:    "DTL",
      duration: probe.duration,
      blobUrl,
    };
    gallery.push(entry);
    renderGallery();
  });

  probe.addEventListener("error", () => {
    URL.revokeObjectURL(blobUrl);
    showUploadError(`Could not read "${file.name}".`);
  });
}

function showUploadError(msg) {
  uploadError.textContent = msg;
  uploadError.hidden = false;
  setTimeout(() => { uploadError.hidden = true; }, 5000);
}

function hideUploadError() {
  uploadError.hidden = true;
}

// ── Gallery ────────────────────────────────────────────────────────────
function renderGallery() {
  galleryStrip.innerHTML = "";

  if (gallery.length === 0) {
    galleryStrip.innerHTML =
      '<p class="gallery-empty">No videos uploaded yet. Upload a swing (max 30s) to get started.</p>';
    return;
  }

  for (const entry of gallery) {
    const card = cardTpl.content.cloneNode(true).firstElementChild;
    const thumb     = card.querySelector(".card-thumb");
    const nameEl    = card.querySelector(".card-name");
    const durEl     = card.querySelector(".card-duration");
    const angleBadge= card.querySelector(".card-angle-badge");
    const addBtn    = card.querySelector(".btn-card-add");
    const delBtn    = card.querySelector(".btn-card-delete");

    thumb.src       = entry.blobUrl;
    thumb.currentTime = Math.min(1, entry.duration * 0.1); // thumbnail seek
    nameEl.textContent  = entry.name;
    durEl.textContent   = formatDuration(entry.duration);
    angleBadge.textContent = entry.angle;

    nameEl.addEventListener("blur", () => { entry.name = nameEl.textContent.trim() || entry.name; });

    angleBadge.addEventListener("click", () => {
      const idx = ANGLES.indexOf(entry.angle);
      entry.angle = ANGLES[(idx + 1) % ANGLES.length];
      angleBadge.textContent = entry.angle;
      // Update any active panel showing this entry
      const active = panels.find(p => p.galleryId === entry.id);
      if (active) {
        active.panelEl.querySelector(".panel-angle-badge").textContent = entry.angle;
      }
    });

    addBtn.addEventListener("click", () => addToView(entry));
    delBtn.addEventListener("click", () => deleteFromGallery(entry.id));

    galleryStrip.appendChild(card);
  }
}

function deleteFromGallery(id) {
  const idx = gallery.findIndex(e => e.id === id);
  if (idx === -1) return;
  const entry = gallery[idx];

  // Remove from view first if active
  const panel = panels.find(p => p.galleryId === id);
  if (panel) removeFromView(panel.id);

  URL.revokeObjectURL(entry.blobUrl);
  gallery.splice(idx, 1);
  renderGallery();
}

// ── Panels ─────────────────────────────────────────────────────────────
function addToView(entry) {
  const panelId   = nextId++;
  const fragment  = panelTpl.content.cloneNode(true);
  const panelEl   = fragment.firstElementChild;
  const videoEl   = panelEl.querySelector(".panel-video");
  const canvasEl  = panelEl.querySelector(".panel-canvas");
  const labelEl   = panelEl.querySelector(".panel-label");
  const angleBadge= panelEl.querySelector(".panel-angle-badge");
  const removeBtn = panelEl.querySelector(".btn-panel-remove");
  const playBtn   = panelEl.querySelector(".btn-panel-play");
  const wfBtn     = panelEl.querySelector(".btn-panel-wireframe");

  panelEl.dataset.panelId = panelId;
  labelEl.textContent     = entry.name;
  angleBadge.textContent  = entry.angle;
  videoEl.src             = entry.blobUrl;
  videoEl.muted           = true;

  // Register with sync manager once metadata is ready
  videoEl.addEventListener("loadedmetadata", () => {
    sync.register(videoEl);
    updateScrubberMax();
  }, { once: true });

  // Register pose detection
  poser.registerPanel(panelId, videoEl, canvasEl);

  // Per-panel controls
  removeBtn.addEventListener("click", () => removeFromView(panelId));

  playBtn.addEventListener("click", () => {
    if (videoEl.paused) {
      videoEl.play().catch(() => {});
      playBtn.textContent = "⏸ Pause";
    } else {
      videoEl.pause();
      playBtn.textContent = "▶ Play";
    }
  });

  // Re-sync the panel's play button when master play/pause fires
  videoEl.addEventListener("play",  () => { playBtn.textContent = "⏸ Pause"; });
  videoEl.addEventListener("pause", () => { playBtn.textContent = "▶ Play"; });

  let panelWireframe = true;
  wfBtn.addEventListener("click", () => {
    panelWireframe = !panelWireframe;
    poser.togglePanel(panelId, panelWireframe);
    wfBtn.textContent = panelWireframe ? "Wireframe: On" : "Wireframe: Off";
    wfBtn.style.opacity = panelWireframe ? "1" : "0.6";
  });

  // Remove empty state if present
  emptyState.remove?.();
  emptyState.style?.setProperty("display", "none"); // fallback

  videoGrid.appendChild(panelEl);
  panels.push({ id: panelId, galleryId: entry.id, panelEl, videoEl });
  updateEmptyState();
}

function removeFromView(panelId) {
  const idx = panels.findIndex(p => p.id === panelId);
  if (idx === -1) return;
  const { videoEl, panelEl } = panels[idx];

  poser.unregisterPanel(panelId);
  sync.unregister(videoEl);
  panelEl.remove();
  panels.splice(idx, 1);
  updateEmptyState();
  updateScrubberMax();
}

function updateEmptyState() {
  if (panels.length === 0) {
    if (!videoGrid.contains(emptyState)) {
      videoGrid.appendChild(emptyState);
    }
    emptyState.style.display = "";
  } else {
    emptyState.style.display = "none";
  }
}

function updateScrubberMax() {
  const dur = sync.duration;
  masterScrubber.max = dur > 0 ? dur : 1;
}

// ── Master Controls ────────────────────────────────────────────────────
masterPlayBtn.addEventListener("click", () => {
  sync.toggle();
  masterPlayBtn.textContent = sync.isPlaying ? "⏸" : "▶";
});

stepFwdBtn.addEventListener("click",  () => sync.stepFrame(1));
stepBackBtn.addEventListener("click", () => sync.stepFrame(-1));

// Scrubber: user drag
masterScrubber.addEventListener("input", () => {
  sync.seek(parseFloat(masterScrubber.value));
});

// Keep scrubber in sync while playing
sync.onTimeUpdate = (currentTime, duration) => {
  if (!masterScrubber.matches(":active")) {
    masterScrubber.max   = duration || 1;
    masterScrubber.value = currentTime;
  }
  // Auto-pause master play button when videos end
  if (currentTime >= duration && duration > 0) {
    masterPlayBtn.textContent = "▶";
  }
};

// Speed buttons
speedBtns.forEach(btn => {
  btn.addEventListener("click", () => {
    speedBtns.forEach(b => b.classList.remove("btn-speed--active"));
    btn.classList.add("btn-speed--active");
    sync.setSpeed(parseFloat(btn.dataset.rate));
  });
});

// ── Global Wireframe Toggle ────────────────────────────────────────────
wireframeToggleBtn.addEventListener("click", () => {
  const newState = !poser.globalVisible;
  poser.toggleGlobal(newState);
  wireframeToggleBtn.textContent = `Wireframes: ${newState ? "On" : "Off"}`;
});

// ── Utilities ──────────────────────────────────────────────────────────
function formatDuration(seconds) {
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60).toString().padStart(2, "0");
  return `${m}:${s}`;
}

// ── Init ───────────────────────────────────────────────────────────────
updateEmptyState();
renderGallery();
