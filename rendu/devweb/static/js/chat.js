const chatScroll = document.getElementById("chat-scroll");
const messagesEl = document.getElementById("messages");
const chatForm = document.getElementById("chat-form");
const chatInput = document.getElementById("chat-input");
const sendBtn = document.getElementById("send-btn");
const statusDot = document.getElementById("status-dot");
const statusText = document.getElementById("status-text");
const targetsList = document.getElementById("targets-list");
const testBtn = document.getElementById("test-btn");
const testResult = document.getElementById("test-result");

const history = [];
let currentTarget = null;
let isSending = false;

function scrollToBottom() {
  chatScroll.scrollTop = chatScroll.scrollHeight;
}

function renderMessage(role, text) {
  const wrapper = document.createElement("div");
  wrapper.className = `flex ${role === "user" ? "justify-end" : "justify-start"} bubble-in`;

  const bubble = document.createElement("div");
  bubble.className =
    role === "user"
      ? "max-w-[75%] bg-ios-blue text-white text-[15px] leading-snug px-4 py-2 rounded-2xl rounded-br-md shadow-sm"
      : "max-w-[75%] bg-ios-gray text-neutral-900 text-[15px] leading-snug px-4 py-2 rounded-2xl rounded-bl-md shadow-sm";
  bubble.textContent = text;

  wrapper.appendChild(bubble);
  messagesEl.appendChild(wrapper);
  scrollToBottom();
  return wrapper;
}

function renderTyping() {
  const wrapper = document.createElement("div");
  wrapper.className = "flex justify-start bubble-in";
  wrapper.id = "typing-indicator";

  const bubble = document.createElement("div");
  bubble.className = "bg-ios-gray text-neutral-900 px-4 py-3 rounded-2xl rounded-bl-md shadow-sm flex items-center gap-1";
  bubble.innerHTML = `
    <span class="typing-dot w-1.5 h-1.5 rounded-full bg-neutral-500 inline-block"></span>
    <span class="typing-dot w-1.5 h-1.5 rounded-full bg-neutral-500 inline-block"></span>
    <span class="typing-dot w-1.5 h-1.5 rounded-full bg-neutral-500 inline-block"></span>
  `;

  wrapper.appendChild(bubble);
  messagesEl.appendChild(wrapper);
  scrollToBottom();
}

function removeTyping() {
  const el = document.getElementById("typing-indicator");
  if (el) el.remove();
}

function setStatus(connected) {
  if (connected) {
    statusDot.className = "w-2 h-2 rounded-full bg-green-500";
    statusText.textContent = "Connecte";
    statusText.className = "text-[11px] font-medium text-green-600";
    chatInput.disabled = false;
    sendBtn.disabled = false;
  } else {
    statusDot.className = "w-2 h-2 rounded-full bg-red-500";
    statusText.textContent = "Deconnecte";
    statusText.className = "text-[11px] font-medium text-red-500";
    chatInput.disabled = false;
    sendBtn.disabled = false;
  }
}

function renderTargets(config) {
  targetsList.innerHTML = "";
  currentTarget = config.current;

  Object.entries(config.targets).forEach(([key, t]) => {
    const active = key === config.current;

    const card = document.createElement("div");
    card.className = `rounded-lg border px-3 py-2.5 cursor-pointer transition ${
      active ? "border-ios-blue bg-blue-50" : "border-neutral-200 bg-white hover:bg-neutral-100"
    }`;
    card.dataset.target = key;

    card.innerHTML = `
      <div class="flex items-center gap-2">
        <span class="w-2.5 h-2.5 rounded-full shrink-0 ${active ? "bg-ios-blue" : "bg-neutral-300"}"></span>
        <span class="text-[13px] font-medium text-neutral-900">${t.label}</span>
      </div>
      <a href="${t.url}/api/tags" target="_blank" rel="noopener"
         class="block mt-1 text-[11px] text-neutral-500 hover:text-ios-blue truncate underline decoration-dotted">
        ${t.url}
      </a>
      <div class="text-[11px] text-neutral-400 mt-0.5">modele: ${t.model}</div>
    `;

    card.addEventListener("click", () => switchTarget(key));
    targetsList.appendChild(card);
  });
}

async function loadConfig() {
  try {
    const res = await fetch("/api/config");
    const data = await res.json();
    renderTargets(data);
  } catch (err) {
    targetsList.innerHTML = '<div class="text-[12px] text-red-500">Impossible de charger la config</div>';
  }
}

async function switchTarget(key) {
  if (key === currentTarget) return;
  try {
    const res = await fetch("/api/config", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ target: key }),
    });
    const data = await res.json();
    currentTarget = data.current;
    await loadConfig();
    await pollStatus();
    testResult.textContent = "";
  } catch (err) {
    testResult.textContent = "Erreur lors du changement de cible.";
    testResult.className = "text-[12px] leading-snug text-red-500";
  }
}

async function pollStatus() {
  if (isSending) return null;
  try {
    const res = await fetch("/api/status");
    const data = await res.json();
    setStatus(Boolean(data.connected));
    return data;
  } catch (err) {
    setStatus(false);
    return null;
  }
}

testBtn.addEventListener("click", async () => {
  testResult.textContent = "Test en cours...";
  testResult.className = "text-[12px] leading-snug text-neutral-400";
  const data = await pollStatus();
  if (!data) {
    testResult.textContent = "Impossible de contacter le backend Flask.";
    testResult.className = "text-[12px] leading-snug text-red-500";
    return;
  }
  if (data.connected) {
    testResult.textContent = `OK - ${data.label} repond, modele "${data.model}" pret.`;
    testResult.className = "text-[12px] leading-snug text-green-600";
  } else {
    testResult.textContent = data.error || "Serveur injoignable (raison inconnue).";
    testResult.className = "text-[12px] leading-snug text-red-500";
  }
});

async function sendMessage(message) {
  renderMessage("user", message);
  history.push({ role: "user", content: message });
  renderTyping();
  sendBtn.disabled = true;
  isSending = true;

  try {
    const res = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message, history }),
    });

    if (!res.ok) throw new Error("bad response");

    const data = await res.json();
    removeTyping();
    renderMessage("assistant", data.reply);
    history.push({ role: "assistant", content: data.reply });
    setStatus(Boolean(data.connected));
  } catch (err) {
    removeTyping();
    renderMessage("assistant", "Erreur de connexion au serveur d'inference.");
    setStatus(false);
  } finally {
    isSending = false;
    sendBtn.disabled = false;
  }
}

chatForm.addEventListener("submit", (e) => {
  e.preventDefault();
  const message = chatInput.value.trim();
  if (!message) return;
  chatInput.value = "";
  sendMessage(message);
});

// Message d'accueil
renderMessage("assistant", "Bonjour, je suis l'assistant financier TechCorp. Comment puis-je vous aider aujourd'hui ?");

loadConfig();
pollStatus();
setInterval(pollStatus, 5000);
