#!/usr/bin/env python3
"""TechCorp Financial Assistant - Dev Web interface.

Parle a un vrai serveur Ollama en local (http://localhost:11434 par defaut).
Si Ollama n'est pas joignable, bascule automatiquement sur des reponses
stub pour ne jamais casser la demo.
"""

import os
import random
import time

import requests
from flask import Flask, jsonify, render_template, request

app = Flask(__name__)

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "techcorp-financial")
OLLAMA_TIMEOUT = 30

STUB_REPLIES = [
    "D'apres les donnees disponibles, concernant '{q}' il faudrait une analyse plus approfondie des indicateurs de marche.",
    "Bonne question sur '{q}'. En general, il est recommande de diversifier son portefeuille avant de se positionner.",
    "A propos de '{q}', les tendances actuelles montrent une certaine volatilite a surveiller de pres.",
    "Le backend d'inference n'est pas encore branche, mais voici une reponse simulee a propos de '{q}'.",
    "Interessant. Sur '{q}', je recommanderais de consulter les derniers rapports trimestriels avant toute decision.",
]


def ping_ollama():
    """Verifie que le serveur Ollama repond et que le modele est disponible."""
    try:
        res = requests.get(f"{OLLAMA_URL}/api/tags", timeout=3)
        res.raise_for_status()
        models = [m["name"] for m in res.json().get("models", [])]
        model_ready = any(m.split(":")[0] == OLLAMA_MODEL.split(":")[0] for m in models)
        return True, model_ready
    except requests.RequestException:
        return False, False


def stub_reply(message):
    time.sleep(random.uniform(0.5, 1.3))
    return random.choice(STUB_REPLIES).format(q=message[:80])


def ollama_reply(history):
    """Appelle l'API /api/chat d'Ollama avec l'historique de conversation."""
    payload = {
        "model": OLLAMA_MODEL,
        "messages": history,
        "stream": False,
    }
    res = requests.post(f"{OLLAMA_URL}/api/chat", json=payload, timeout=OLLAMA_TIMEOUT)
    res.raise_for_status()
    return res.json()["message"]["content"].strip()


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/status")
def status():
    server_up, model_ready = ping_ollama()
    return jsonify({
        "connected": server_up and model_ready,
        "backend": "ollama" if server_up else "stub",
        "model": OLLAMA_MODEL,
        "model_ready": model_ready,
    })


@app.route("/api/chat", methods=["POST"])
def chat():
    data = request.get_json(force=True, silent=True) or {}
    message = (data.get("message") or "").strip()
    history = data.get("history") or []

    if not message:
        return jsonify({"error": "empty message"}), 400

    server_up, model_ready = ping_ollama()

    if server_up and model_ready:
        try:
            messages = [{"role": h["role"], "content": h["content"]} for h in history]
            messages.append({"role": "user", "content": message})
            reply = ollama_reply(messages)
            return jsonify({"reply": reply, "connected": True, "backend": "ollama"})
        except requests.RequestException:
            pass

    # Fallback stub si Ollama n'est pas joignable ou en erreur
    reply = stub_reply(message)
    return jsonify({"reply": reply, "connected": server_up and model_ready, "backend": "stub"})


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
