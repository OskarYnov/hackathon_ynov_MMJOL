const chatScroll = document.getElementById("chat-scroll");
const messagesEl = document.getElementById("messages");
const chatForm = document.getElementById("chat-form");
const chatInput = document.getElementById("chat-input");
const sendBtn = document.getElementById("send-btn");
const statusDot = document.getElementById("status-dot");
const statusText = document.getElementById("status-text");

const history = [];

function scrollToBottom() {
  chatScroll.scrollTop = chatScroll.scrollHeight;
}

function timeNow() {
  return new Date().toLocaleTimeString("fr-FR", { hour: "2-digit", minute: "2-digit" });
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
    chatInput.disabled = true;
    sendBtn.disabled = true;
  }
}

async function pollStatus() {
  try {
    const res = await fetch("/api/status");
    const data = await res.json();
    setStatus(Boolean(data.connected));
  } catch (err) {
    setStatus(false);
  }
}

async function sendMessage(message) {
  renderMessage("user", message);
  history.push({ role: "user", content: message });
  renderTyping();
  sendBtn.disabled = true;

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
  } catch (err) {
    removeTyping();
    renderMessage("assistant", "Erreur de connexion au serveur d'inference.");
    setStatus(false);
  } finally {
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

pollStatus();
setInterval(pollStatus, 5000);
