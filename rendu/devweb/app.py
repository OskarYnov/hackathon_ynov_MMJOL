#!/usr/bin/env python3
"""TechCorp Financial Assistant - Dev Web interface (stub backend).

Ce backend est un STUB : il simule les reponses en attendant que l'equipe
INFRA fournisse l'URL reelle du serveur d'inference (Ollama/Triton/maison).
Remplacer la logique de /api/chat par un appel a cette API une fois prete.
"""

import random
import time

from flask import Flask, jsonify, render_template, request

app = Flask(__name__)

STUB_REPLIES = [
    "D'apres les donnees disponibles, concernant '{q}' il faudrait une analyse plus approfondie des indicateurs de marche.",
    "Bonne question sur '{q}'. En general, il est recommande de diversifier son portefeuille avant de se positionner.",
    "A propos de '{q}', les tendances actuelles montrent une certaine volatilite a surveiller de pres.",
    "Le backend d'inference n'est pas encore branche, mais voici une reponse simulee a propos de '{q}'.",
    "Interessant. Sur '{q}', je recommanderais de consulter les derniers rapports trimestriels avant toute decision.",
]


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/status")
def status():
    # TODO: remplacer par un vrai ping vers le serveur d'inference (INFRA)
    return jsonify({"connected": True, "backend": "stub"})


@app.route("/api/chat", methods=["POST"])
def chat():
    data = request.get_json(force=True, silent=True) or {}
    message = (data.get("message") or "").strip()

    if not message:
        return jsonify({"error": "empty message"}), 400

    # Simule le temps de reponse d'un modele
    time.sleep(random.uniform(0.5, 1.3))

    reply = random.choice(STUB_REPLIES).format(q=message[:80])
    return jsonify({"reply": reply, "connected": True})


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
