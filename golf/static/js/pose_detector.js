/**
 * PoseDetector — wraps MediaPipe PoseLandmarker (LITE model).
 *
 * Each video panel gets its own frame-loop driven by
 * requestVideoFrameCallback. Landmarks are drawn onto the panel's
 * canvas overlay.
 */

const MEDIAPIPE_CDN =
  "https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@0.10.14/vision_bundle.js";

const MODEL_URL =
  "https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_lite/float16/1/pose_landmarker_lite.task";

// MediaPipe skeleton connections (landmark index pairs)
const CONNECTIONS = [
  [0, 1], [1, 2], [2, 3], [3, 7],
  [0, 4], [4, 5], [5, 6], [6, 8],
  [9, 10],
  [11, 12],
  [11, 13], [13, 15], [15, 17], [15, 19], [15, 21], [17, 19],
  [12, 14], [14, 16], [16, 18], [16, 20], [16, 22], [18, 20],
  [11, 23], [12, 24], [23, 24],
  [23, 25], [25, 27], [27, 29], [27, 31], [29, 31],
  [24, 26], [26, 28], [28, 30], [28, 32], [30, 32],
];

const DOT_RADIUS  = 5;
const DOT_COLOR   = "#4ade80";
const LINE_COLOR  = "rgba(74, 222, 128, 0.7)";
const LINE_WIDTH  = 2;

export class PoseDetector {
  constructor() {
    this._landmarker = null;      // PoseLandmarker instance (shared)
    this._panels     = new Map(); // panelId → { videoEl, canvasEl, rafHandle, visible }
    this._globalVisible = true;
    this._ready      = false;
    this._loadPromise = this._load();
  }

  /** Returns a Promise that resolves when the model is ready. */
  ready() { return this._loadPromise; }

  /**
   * Register a video+canvas pair. Starts running pose detection on every
   * rendered video frame once the model is loaded.
   */
  async registerPanel(panelId, videoEl, canvasEl) {
    await this._loadPromise;
    const entry = { videoEl, canvasEl, rafHandle: null, visible: true };
    this._panels.set(panelId, entry);
    this._startLoop(panelId, entry);
  }

  /** Stop detection and remove the panel. */
  unregisterPanel(panelId) {
    const entry = this._panels.get(panelId);
    if (!entry) return;
    if (entry.rafHandle !== null) {
      entry.videoEl.cancelVideoFrameCallback(entry.rafHandle);
    }
    this._panels.delete(panelId);
  }

  /** Show/hide the canvas overlay for a single panel. */
  togglePanel(panelId, visible) {
    const entry = this._panels.get(panelId);
    if (!entry) return;
    entry.visible = visible;
    entry.canvasEl.classList.toggle("hidden", !visible);
  }

  /** Show/hide all canvas overlays. */
  toggleGlobal(visible) {
    this._globalVisible = visible;
    this._panels.forEach((entry) => {
      const show = visible && entry.visible;
      entry.canvasEl.classList.toggle("hidden", !show);
    });
  }

  get globalVisible() { return this._globalVisible; }

  // ── private ────────────────────────────────────────────────────────

  async _load() {
    const { PoseLandmarker, FilesetResolver } = await this._importMediaPipe();

    const vision = await FilesetResolver.forVisionTasks(
      "https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@0.10.14/wasm"
    );

    this._landmarker = await PoseLandmarker.createFromOptions(vision, {
      baseOptions: {
        modelAssetPath: MODEL_URL,
        delegate: "GPU",
      },
      runningMode: "VIDEO",
      numPoses: 1,
    });

    this._ready = true;
  }

  _importMediaPipe() {
    return new Promise((resolve, reject) => {
      if (window.__mediapipeTasks) { resolve(window.__mediapipeTasks); return; }
      const script = document.createElement("script");
      script.src = MEDIAPIPE_CDN;
      script.onload = () => {
        // The bundle exports onto globalThis
        const { PoseLandmarker, FilesetResolver } = window;
        if (!PoseLandmarker) { reject(new Error("MediaPipe PoseLandmarker not found")); return; }
        window.__mediapipeTasks = { PoseLandmarker, FilesetResolver };
        resolve(window.__mediapipeTasks);
      };
      script.onerror = () => reject(new Error("Failed to load MediaPipe CDN script"));
      document.head.appendChild(script);
    });
  }

  _startLoop(panelId, entry) {
    const { videoEl, canvasEl } = entry;

    const tick = (now, _meta) => {
      if (!this._panels.has(panelId)) return; // was unregistered

      if (!videoEl.paused && !videoEl.ended && this._ready) {
        try {
          const results = this._landmarker.detectForVideo(videoEl, now);
          this._draw(canvasEl, videoEl, results.landmarks);
        } catch (_) {
          // detectForVideo can throw if video dimensions aren't ready yet
        }
      }

      entry.rafHandle = videoEl.requestVideoFrameCallback(tick);
    };

    entry.rafHandle = videoEl.requestVideoFrameCallback(tick);
  }

  _draw(canvas, video, landmarkGroups) {
    const ctx = canvas.getContext("2d");

    // Keep canvas sized to video's rendered resolution
    if (canvas.width !== video.videoWidth || canvas.height !== video.videoHeight) {
      canvas.width  = video.videoWidth  || canvas.offsetWidth;
      canvas.height = video.videoHeight || canvas.offsetHeight;
    }

    ctx.clearRect(0, 0, canvas.width, canvas.height);

    if (!landmarkGroups || landmarkGroups.length === 0) return;

    const lm = landmarkGroups[0];
    const w  = canvas.width;
    const h  = canvas.height;

    // Skeleton lines
    ctx.strokeStyle = LINE_COLOR;
    ctx.lineWidth   = LINE_WIDTH;
    for (const [a, b] of CONNECTIONS) {
      if (!lm[a] || !lm[b]) continue;
      ctx.beginPath();
      ctx.moveTo(lm[a].x * w, lm[a].y * h);
      ctx.lineTo(lm[b].x * w, lm[b].y * h);
      ctx.stroke();
    }

    // Landmark dots
    ctx.fillStyle = DOT_COLOR;
    for (const point of lm) {
      ctx.beginPath();
      ctx.arc(point.x * w, point.y * h, DOT_RADIUS, 0, Math.PI * 2);
      ctx.fill();
    }
  }
}
