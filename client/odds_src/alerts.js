const ALERT_DURATION = 1000;

export function showAlert(message) {
    const wrapper = document.getElementById("alerts-wrapper");
    if (!wrapper) return;

    const alert = document.createElement("div");
    alert.className = "alert-notification";
    // alert.textContent = message;

    // click to dismiss early
    alert.addEventListener("click", () => {
        removeAlert(alert);
    });

    const alertIcon = document.createElement("div");
    alertIcon.className = "alert-notification-icon";

    const alertText = document.createElement("div");
    alertText.className = "alert-notification-text";
    alertText.textContent = message;

    alert.appendChild(alertIcon);
    alert.appendChild(alertText);

    wrapper.appendChild(alert);

    // trigger animation
    requestAnimationFrame(() => {
        alert.classList.add("show");
    });

    // auto-remove
    setTimeout(() => {
        removeAlert(alert);
    }, ALERT_DURATION);
}

function removeAlert(alert) {
    if (!alert) return;

    alert.classList.remove("show");

    // wait for fade-out before removing
    alert.addEventListener(
        "transitionend",
        () => alert.remove(),
        { once: true }
    );
}