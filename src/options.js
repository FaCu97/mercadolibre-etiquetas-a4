import "./style.css";
const inputs = [...document.querySelectorAll('input[name="auxiliary-mode"]')];
const status = document.querySelector("#status");
const stored = await chrome.storage.local.get({ auxiliaryMode: "discard" });
inputs.find((input) => input.value === stored.auxiliaryMode).checked = true;
inputs.forEach((input) => input.addEventListener("change", async () => { await chrome.storage.local.set({ auxiliaryMode: input.value }); status.textContent = "Configuración guardada."; }));
