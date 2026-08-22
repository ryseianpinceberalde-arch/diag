const BLOCKED_KEY_COMBOS = new Set(["F12", "I", "J", "C", "U"]);

export function installBrowserGuards() {
  if (import.meta.env.DEV) {
    return;
  }

  window.addEventListener("contextmenu", (event) => {
    event.preventDefault();
  });

  window.addEventListener("keydown", (event) => {
    const key = event.key.toUpperCase();
    const isBlockedShortcut =
      event.key === "F12" ||
      (event.ctrlKey && event.shiftKey && BLOCKED_KEY_COMBOS.has(key)) ||
      (event.ctrlKey && key === "U");

    if (isBlockedShortcut) {
      event.preventDefault();
      event.stopPropagation();
    }
  });
}
