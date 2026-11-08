(() => {
  const section = document.querySelector("#repbook-install");
  if (!window.isSecureContext || navigator.standalone ||
      window.matchMedia("(display-mode: standalone)").matches) return;

  const button = document.querySelector("#repbook-install-button");
  const help = document.querySelector("#repbook-install-help");
  const appleMobile = /iPhone|iPad|iPod/.test(navigator.userAgent) ||
    (navigator.platform === "MacIntel" && navigator.maxTouchPoints > 1);
  let installPrompt;

  section.hidden = false;
  window.addEventListener("beforeinstallprompt", (event) => {
    event.preventDefault();
    installPrompt = event;
    help.hidden = true;
    button.setAttribute("aria-expanded", "false");
  });
  window.addEventListener("appinstalled", () => {
    section.hidden = true;
    installPrompt = undefined;
  });

  function showHelp() {
    help.textContent = appleMobile
      ? "Open this page in Safari. Tap Share, then Add to Home Screen. Turn on Open as Web App if shown, then tap Add."
      : "Open your browser menu and choose Install app or Add to Home screen. If you opened this link inside another app, open it in Chrome or Edge first.";
    help.hidden = false;
    button.setAttribute("aria-expanded", "true");
  }

  button.addEventListener("click", async () => {
    if (!installPrompt) {
      showHelp();
      return;
    }
    const prompt = installPrompt;
    installPrompt = undefined;
    button.disabled = true;
    try {
      const { outcome } = await prompt.prompt();
      if (outcome === "accepted") section.hidden = true;
    } catch {
      showHelp();
    } finally {
      button.disabled = false;
    }
  });
})();
