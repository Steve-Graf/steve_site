export function isIOSDevice() {
  const ua = window.navigator.userAgent;
  return (
    /iPad|iPhone|iPod/.test(ua) ||
    (navigator.platform === "MacIntel" && navigator.maxTouchPoints > 1)
  );
}

export function isStandalonePWA() {
  return (
    window.navigator.standalone === true ||
    window.matchMedia("(display-mode: standalone)").matches
  );
}

(function () {
  const STORAGE_KEY = "odds-ios-install-banner-dismissed";
  const banner = document.getElementById("ios-install-banner");
  if (!banner) return;

  const ua = window.navigator.userAgent;
  const isSafari = /^((?!chrome|crios|fxios|edgios|android).)*safari/i.test(ua);
  const dismissed = localStorage.getItem(STORAGE_KEY) === "1";

  if (!isIOSDevice() || !isSafari || isStandalonePWA() || dismissed) return;

  banner.hidden = false;

  const autoCloseTimer = setTimeout(() => {
    banner.hidden = true;
  }, 10000);

  const dismissBtn = banner.querySelector(".ios-install-banner-dismiss");
  if (dismissBtn) {
    dismissBtn.addEventListener("click", () => {
      clearTimeout(autoCloseTimer);
      banner.hidden = true;
      localStorage.setItem(STORAGE_KEY, "1");
    });
  }
})();
