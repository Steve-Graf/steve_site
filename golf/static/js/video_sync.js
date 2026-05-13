/**
 * VideoSyncManager — keeps an arbitrary number of video elements in sync.
 *
 * Each video is registered with an optional time offset so swings can be
 * aligned at their address position rather than at t=0.
 *
 * Drift correction runs via requestAnimationFrame: the first registered video
 * is the reference; all others are nudged if they drift >50ms from it.
 */
export class VideoSyncManager {
  constructor() {
    this._entries = [];        // [{videoEl, offset}]
    this._playing = false;
    this._speed = 1;
    this._rafId = null;
    this._userScrubbing = false;
    this._onTimeUpdateCb = null;
  }

  /** Register a video element with this manager. */
  register(videoEl, offset = 0) {
    if (this._entries.find(e => e.videoEl === videoEl)) return;
    videoEl.playbackRate = this._speed;
    this._entries.push({ videoEl, offset });
  }

  /** Remove a video from sync management (call before removing from DOM). */
  unregister(videoEl) {
    this._entries = this._entries.filter(e => e.videoEl !== videoEl);
    if (this._entries.length === 0) {
      this._stopDriftLoop();
      this._playing = false;
    }
  }

  get isPlaying() { return this._playing; }

  /** Callback fired with (currentTime, duration) whenever reference video ticks. */
  set onTimeUpdate(fn) { this._onTimeUpdateCb = fn; }

  play() {
    if (this._entries.length === 0) return;
    this._playing = true;
    this._entries.forEach(({ videoEl }) => videoEl.play().catch(() => {}));
    this._startDriftLoop();
  }

  pause() {
    this._playing = false;
    this._entries.forEach(({ videoEl }) => videoEl.pause());
    this._stopDriftLoop();
    this._emitTime();
  }

  toggle() {
    this._playing ? this.pause() : this.play();
  }

  /**
   * Step all videos by `frames` frames (positive = forward, negative = back).
   * Pauses first.
   */
  stepFrame(frames = 1) {
    this.pause();
    const ref = this._entries[0];
    if (!ref) return;
    const newTime = Math.max(0, ref.videoEl.currentTime + (frames / 30));
    this._seekToRef(newTime);
  }

  /**
   * Seek the reference video to `masterTime`; all others follow their offset.
   */
  seek(masterTime) {
    const ref = this._entries[0];
    if (!ref) return;
    const clampedRef = Math.max(0, Math.min(masterTime, ref.videoEl.duration || 0));
    this._seekToRef(clampedRef);
    this._emitTime();
  }

  setSpeed(rate) {
    this._speed = rate;
    this._entries.forEach(({ videoEl }) => { videoEl.playbackRate = rate; });
  }

  /** Duration of the reference video (for scrubber max). */
  get duration() {
    return this._entries[0]?.videoEl.duration || 0;
  }

  /** Current time of the reference video. */
  get currentTime() {
    return this._entries[0]?.videoEl.currentTime || 0;
  }

  // ── private ────────────────────────────────────────────────────────

  _seekToRef(refTime) {
    this._entries.forEach(({ videoEl, offset }) => {
      videoEl.currentTime = Math.max(0, refTime + offset);
    });
  }

  _startDriftLoop() {
    this._stopDriftLoop();
    const loop = () => {
      this._correctDrift();
      this._emitTime();
      if (this._playing) this._rafId = requestAnimationFrame(loop);
    };
    this._rafId = requestAnimationFrame(loop);
  }

  _stopDriftLoop() {
    if (this._rafId !== null) {
      cancelAnimationFrame(this._rafId);
      this._rafId = null;
    }
  }

  _correctDrift() {
    const ref = this._entries[0];
    if (!ref || this._entries.length < 2) return;
    const refTime = ref.videoEl.currentTime;
    for (let i = 1; i < this._entries.length; i++) {
      const { videoEl, offset } = this._entries[i];
      const expected = refTime + offset;
      if (Math.abs(videoEl.currentTime - expected) > 0.05) {
        videoEl.currentTime = Math.max(0, expected);
      }
    }
  }

  _emitTime() {
    if (!this._onTimeUpdateCb || this._entries.length === 0) return;
    const ref = this._entries[0].videoEl;
    this._onTimeUpdateCb(ref.currentTime, ref.duration || 0);
  }
}
