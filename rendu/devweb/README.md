# DEV WEB — TechCorp Financial Assistant

Interface de chat web pour l'assistant financier TechCorp, branchee sur un
serveur Ollama local servant le modele `techcorp-financial` (base `phi3.5`
+ prompt systeme finance, voir `../../ollama_server/Modelfile`).

## Lancer le projet

Prerequis : Ollama installe et le modele cree.

```bash
# 1. Demarrer Ollama (si pas deja lance en service)
ollama serve

# 2. Creer le modele depuis le Modelfile (une seule fois)
ollama create techcorp-financial -f ../../ollama_server/Modelfile

# 3. Installer les dependances et lancer l'interface
cd rendu/devweb
pip install -r requirements.txt
python app.py
```

Puis ouvrir `http://localhost:5000` dans le navigateur.

## Configuration

Variables d'environnement optionnelles :
- `OLLAMA_URL` (defaut `http://localhost:11434`)
- `OLLAMA_MODEL` (defaut `techcorp-financial`)

Si Ollama n'est pas joignable ou que le modele n'est pas pret, le backend
bascule automatiquement sur des reponses simulees (stub) pour ne jamais
casser la demo, et l'indicateur de statut passe sur "Deconnecte".

## Architecture

- `app.py` — backend Flask, relaie les requetes vers l'API Ollama
  (`/api/chat`, `/api/tags`)
- `templates/index.html` — interface de chat (style iOS, Tailwind)
- `static/js/chat.js` — logique front (envoi de message, historique,
  indicateur de connexion)

## Remerciements

Merci à **Maxime Pescay** pour sa participation au groupe.

Les personnes suivantes, initialement assignées au groupe, n'ont jamais
participé au projet : Maxime Desportes, Léa Lemos Barrau, Julien Fromont.

Je n'ai pas fait l'IA moi même ni la data, j'ai pris un modèle de base qui me donne des infos sur des actions ou des entreprises. L'interface et fonctionnelle, le chat avec la réponse via le LLM aussi. J'estime avoir fait plus que demandé pour le devweb
