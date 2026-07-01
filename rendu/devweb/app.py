#!/usr/bin/env python3
"""TechCorp Financial Assistant - Dev Web interface.

Parle a un serveur Ollama, local ou distant (tunnel ngrok cote INFRA).
Si le serveur choisi n'est pas joignable, bascule automatiquement sur des
reponses stub pour ne jamais casser la demo, et remonte l'erreur reelle
pour pouvoir diagnostiquer.
"""

import os
import random
import time

import requests
from flask import Flask, jsonify, render_template, request

app = Flask(__name__)

TARGETS = {
    "local": {
        "label": "Local",
        "url": os.environ.get("OLLAMA_LOCAL_URL", "http://localhost:11434"),
        "model": os.environ.get("OLLAMA_LOCAL_MODEL", "techcorp-financial"),
    },
    "remote": {
        "label": "Distant (INFRA / ngrok)",
        "url": os.environ.get("OLLAMA_REMOTE_URL", "https://turbojet-deviant-reshape.ngrok-free.dev"),
        "model": os.environ.get("OLLAMA_REMOTE_MODEL", "phi3-financial"),
    },
}

# Cible active par defaut (modifiable en live depuis le panneau de gauche)
current_target = os.environ.get("OLLAMA_TARGET", "local")
if current_target not in TARGETS:
    current_target = "local"

OLLAMA_TIMEOUT = 30

STUB_REPLIES = [
    "D'apres les donnees disponibles, concernant '{q}' il faudrait une analyse plus approfondie des indicateurs de marche.",
    "Bonne question sur '{q}'. En general, il est recommande de diversifier son portefeuille avant de se positionner.",
    "A propos de '{q}', les tendances actuelles montrent une certaine volatilite a surveiller de pres.",
    "Le backend d'inference n'est pas encore branche, mais voici une reponse simulee a propos de '{q}'.",
    "Interessant. Sur '{q}', je recommanderais de consulter les derniers rapports trimestriels avant toute decision.",
]


def active():
    return TARGETS[current_target]


def ping_ollama():
    """Verifie que le serveur Ollama actif repond et que le modele est disponible.

    Retourne (server_up, model_ready, error_message).
    """
    target = active()
    try:
        res = requests.get(f"{target['url']}/api/tags", timeout=5)
        res.raise_for_status()
        models = [m["name"] for m in res.json().get("models", [])]
        model_ready = any(m.split(":")[0] == target["model"].split(":")[0] for m in models)
        error = None if model_ready else f"Modele '{target['model']}' introuvable sur ce serveur"
        return True, model_ready, error
    except requests.exceptions.Timeout:
        return False, False, "Timeout : le serveur ne repond pas"
    except requests.exceptions.ConnectionError as e:
        return False, False, f"Connexion impossible : {e}"
    except requests.exceptions.HTTPError as e:
        return False, False, f"Erreur HTTP {e.response.status_code} : {e.response.text[:200]}"
    except requests.RequestException as e:
        return False, False, str(e)


def stub_reply(message):
    time.sleep(random.uniform(0.5, 1.3))
    return random.choice(STUB_REPLIES).format(q=message[:80])


def ollama_reply(history):
    """Appelle l'API /api/chat d'Ollama avec l'historique de conversation."""
    target = active()
    payload = {
        "model": target["model"],
        "messages": history,
        "stream": False,
    }
    res = requests.post(f"{target['url']}/api/chat", json=payload, timeout=OLLAMA_TIMEOUT)
    res.raise_for_status()
    return res.json()["message"]["content"].strip()


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/config")
def get_config():
    return jsonify({
        "current": current_target,
        "targets": {
            key: {"label": t["label"], "url": t["url"], "model": t["model"]}
            for key, t in TARGETS.items()
        },
    })


@app.route("/api/config", methods=["POST"])
def set_config():
    global current_target
    data = request.get_json(force=True, silent=True) or {}
    target = data.get("target")
    if target not in TARGETS:
        return jsonify({"error": f"cible inconnue: {target}"}), 400
    current_target = target
    return jsonify({"current": current_target})


@app.route("/api/status")
def status():
    server_up, model_ready, error = ping_ollama()
    target = active()
    return jsonify({
        "connected": server_up and model_ready,
        "backend": "ollama" if server_up and model_ready else "stub",
        "target": current_target,
        "label": target["label"],
        "url": target["url"],
        "model": target["model"],
        "model_ready": model_ready,
        "error": error,
    })


@app.route("/api/chat", methods=["POST"])
def chat():
    data = request.get_json(force=True, silent=True) or {}
    message = (data.get("message") or "").strip()
    history = data.get("history") or []

    if not message:
        return jsonify({"error": "empty message"}), 400

    server_up, model_ready, error = ping_ollama()

    if server_up and model_ready:
        try:
            messages = [{"role": h["role"], "content": h["content"]} for h in history]
            messages.append({"role": "user", "content": message})
            reply = ollama_reply(messages)
            return jsonify({"reply": reply, "connected": True, "backend": "ollama"})
        except requests.RequestException as e:
            error = str(e)

    # Fallback stub si le serveur choisi n'est pas joignable ou en erreur
    reply = stub_reply(message)
    return jsonify({
        "reply": reply,
        "connected": False,
        "backend": "stub",
        "error": error,
    })


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
