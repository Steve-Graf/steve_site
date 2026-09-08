(function () {
  const STORAGE_KEY = "bingo-ios-install-banner-dismissed";
  const banner = document.getElementById("ios-install-banner");
  if (!banner) return;

  const ua = window.navigator.userAgent;
  const isIOS =
    /iPad|iPhone|iPod/.test(ua) ||
    (navigator.platform === "MacIntel" && navigator.maxTouchPoints > 1);
  const isSafari = /^((?!chrome|crios|fxios|edgios|android).)*safari/i.test(ua);
  const isStandalone =
    window.navigator.standalone === true ||
    window.matchMedia("(display-mode: standalone)").matches;
  const dismissed = localStorage.getItem(STORAGE_KEY) === "1";

  if (!isIOS || !isSafari || isStandalone || dismissed) return;

  banner.hidden = false;

  const dismissBtn = banner.querySelector(".ios-install-banner__dismiss");
  if (dismissBtn) {
    dismissBtn.addEventListener("click", () => {
      banner.hidden = true;
      localStorage.setItem(STORAGE_KEY, "1");
    });
  }
})();
