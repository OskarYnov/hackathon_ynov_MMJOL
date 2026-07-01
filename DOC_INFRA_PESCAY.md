# Documentation Technique — Déploiement Infra
## Projet TechCorp AI Chat — Modèle Phi-3.5-Financial

**Auteur :** Maxime (rôle INFRA)
**Équipe :** Oskar (chef de projet) et al.
**Date :** 01/07/2026

---

## 1. Choix technique

**Solution retenue : Ollama**

| Critère | Ollama | Triton Inference Server | Serveur maison |
|---|---|---|---|
| Temps de mise en place | Très rapide (installeur graphique) | Long (configuration protobuf, backend TensorRT/Python complexe) | Moyen à long (dev API complet) |
| Besoin GPU dédié | Non (tourne bien sur CPU pour un modèle "mini") | Recommandé fortement | Dépend de l'implémentation |
| API prête à l'emploi | Oui (REST native + endpoint compatible OpenAI) | Oui mais plus complexe à intégrer | À développer |
| Adapté à un hackathon de 7h | Oui | Non | Non |

Ollama a été choisi pour sa simplicité de déploiement, l'absence de dépendance à un GPU puissant, et une API REST immédiatement exploitable par l'équipe DEV WEB, ce qui correspondait aux contraintes de temps du hackathon.

---

## 2. Contexte : état du modèle hérité

Le dossier `models/phi3_financial/` fourni par l'équipe précédente ne contenait **pas** un modèle complet, mais uniquement un **adaptateur LoRA** (fine-tuning léger) :

- `adapter_config.json`
- `adapter_model.safetensors` (~30 Mo)
- fichiers de tokenizer

Le fichier `adapter_config.json` a permis d'identifier le modèle de base utilisé pour l'entraînement :

```json
"base_model_name_or_path": "microsoft/Phi-3-mini-4k-instruct"
```

Il a donc fallu reconstituer le modèle complet en fusionnant ce LoRA avec le modèle de base public, avant de pouvoir le déployer.

---

## 3. Pipeline de déploiement — étapes détaillées

### 3.1 Installation d'Ollama

Téléchargement et installation via l'installeur Windows officiel : https://ollama.com/download

Vérification :
```powershell
ollama --version
```

### 3.2 Récupération des fichiers du modèle (Git LFS)

Les fichiers volumineux (`adapter_model.safetensors`) sont versionnés via **Git LFS**. Deux points de blocage rencontrés et résolus :

1. **Remote configuré en SSH sans clé configurée** → bascule du remote en HTTPS :
   ```powershell
   git remote set-url origin https://github.com/OskarYnov/hackathon_ynov_MMJOL.git
   ```
2. **Conflit avec OneDrive** : le dossier de travail était synchronisé par OneDrive, ce qui provoquait des erreurs d'écriture pendant `git lfs pull` (`cannot add to the index`). Résolution : déplacement du repo hors de tout dossier synchronisé (`C:\Users\<user>\Documents\` en local, hors OneDrive).

```powershell
git lfs install
git lfs pull
```

### 3.3 Fusion du LoRA avec le modèle de base

**Environnement Python (venv) :**
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install torch transformers peft accelerate huggingface_hub
```

**Script de fusion (`merge_lora.py`) :**
```python
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import PeftModel
import torch
import os

base_model_name = "microsoft/Phi-3-mini-4k-instruct"
adapter_path = "models/phi3_financial"
output_path = "models/phi3_financial_merged"

base_model = AutoModelForCausalLM.from_pretrained(
    base_model_name,
    torch_dtype=torch.float16,
    device_map="cpu",
    low_cpu_mem_usage=True
)
tokenizer = AutoTokenizer.from_pretrained(base_model_name)

model = PeftModel.from_pretrained(base_model, adapter_path)
merged_model = model.merge_and_unload()

os.makedirs(output_path, exist_ok=True)
merged_model.save_pretrained(output_path)
tokenizer.save_pretrained(output_path)
```

**Points techniques rencontrés :**
- `trust_remote_code=True` provoquait une erreur (`KeyError: 'type'` sur `rope_scaling`) à cause d'une incompatibilité entre le code distant du repo HuggingFace et la version récente de `transformers`. Résolu en utilisant l'implémentation Phi-3 **native** de `transformers` (retrait du paramètre).
- Crash silencieux au chargement du modèle de base, dû à une saturation RAM (16 Go dispo, ~9 Go libres). Résolu avec `low_cpu_mem_usage=True` et `device_map="cpu"`, qui charge les poids de façon plus économe en mémoire.

Résultat : modèle fusionné (~7.6 Go en `model.safetensors`) dans `models/phi3_financial_merged/`.

### 3.4 Conversion au format GGUF (compatible Ollama)

Outil utilisé : [llama.cpp](https://github.com/ggerganov/llama.cpp) (cloné en dehors du repo projet).

```powershell
git clone https://github.com/ggerganov/llama.cpp.git
cd llama.cpp
pip install -r requirements.txt
python convert_hf_to_gguf.py <chemin_modele_fusionné> --outfile <chemin_sortie>.gguf --outtype f16
```

**Point technique rencontré :** le convertisseur exige un fichier `tokenizer.model` (format SentencePiece brut), absent après un `save_pretrained()` classique (qui ne sauvegarde que le tokenizer "fast" au format `tokenizer.json`). Le fichier a été récupéré depuis le cache local HuggingFace du modèle de base (`~/.cache/huggingface/hub/models--microsoft--Phi-3-mini-4k-instruct/snapshots/<hash>/tokenizer.model`) et copié manuellement dans le dossier du modèle fusionné.

Résultat : `phi3-financial-f16.gguf` (~7.6 Go, format f16 non quantisé).

> **Note d'optimisation non réalisée par manque de temps :** une quantization en Q4_K_M (via `llama-quantize`) permettrait de réduire la taille à ~2.2 Go et d'accélérer l'inférence sur CPU, au prix d'une perte de qualité marginale. Nécessite la compilation de `llama.cpp` (CMake + Visual Studio Build Tools), non réalisée dans le temps imparti du hackathon.

### 3.5 Création du modèle dans Ollama

**Modelfile :**
```
FROM ./models/phi3-financial-f16.gguf

TEMPLATE """<|user|>
{{ .Prompt }}<|end|>
<|assistant|>
{{ .Response }}<|end|>
"""

PARAMETER stop "<|end|>"
PARAMETER stop "<|user|>"
PARAMETER stop "<|assistant|>"
```

Le template reprend le format de chat natif de Phi-3 (balises `<|user|>` / `<|assistant|>` / `<|end|>`).

```powershell
ollama create phi3-financial -f Modelfile
```

### 3.6 Exposition réseau du serveur

Par défaut, Ollama n'écoute qu'en local (`127.0.0.1:11434`). Pour rendre le serveur accessible aux autres membres de l'équipe (DEV WEB) sur le réseau local :

```powershell
$env:OLLAMA_HOST="0.0.0.0:11434"
ollama serve
```

Règle de pare-feu Windows ajoutée pour autoriser le trafic entrant sur le port :
```powershell
New-NetFirewallRule -DisplayName "Ollama" -Direction Inbound -LocalPort 11434 -Protocol TCP -Action Allow
```

---

## 4. Évolution : passage sur Google Colab + ngrok

Le déploiement initial (Ollama en local sur Windows, exposé sur le réseau via IP locale) fonctionnait uniquement si toute l'équipe était connectée au **même réseau physique** (hotspot mobile). L'équipe travaillant en partie à distance, cette solution ne convenait pas pour l'équipe DEV WEB.

**Solution retenue : ré-héberger le pipeline complet sur Google Colab (GPU gratuit), exposé via un tunnel ngrok public.**

### 4.1 Pipeline reconstruit sur Colab

Toutes les étapes précédentes (clone du repo, fusion LoRA, conversion GGUF, création Ollama) ont été rejouées directement dans un notebook Colab, avec les avantages suivants :
- GPU disponible → fusion du LoRA nettement plus rapide qu'en local (~30s pour le chargement des poids vs plusieurs minutes en CPU)
- Pas de limite de stockage local (contrairement au Drive personnel, insuffisant pour héberger le modèle de 7.6 Go)

**Étapes clés (notebook Colab, GPU T4 activé) :**

```python
# 1. Clone du repo (avec token GitHub pour l'accès privé)
!git clone https://<TOKEN>@github.com/OskarYnov/hackathon_ynov_MMJOL.git
%cd hackathon_ynov_MMJOL
!git lfs install
!git lfs pull

# 2. Dépendances
!pip install torch transformers peft accelerate -q
!pip install -U torchao -q   # nécessaire : version par défaut de Colab incompatible avec peft

# 3. Fusion LoRA (identique à la section 3.3, avec device_map="cuda")
# 4. Récupération du tokenizer.model (identique à la section 3.3)

# 5. Conversion GGUF (identique à la section 3.4)
!apt-get install -y zstd -q   # requis par l'installeur Ollama, absent par défaut sur Colab

# 6. Installation et lancement d'Ollama
!curl -fsSL https://ollama.com/install.sh | sh
import subprocess, time
subprocess.Popen(["ollama", "serve"])
time.sleep(5)

# 7. Création du modèle (Modelfile identique à la section 3.5)

# 8. Exposition publique via ngrok
!pip install pyngrok -q
from pyngrok import ngrok
ngrok.set_auth_token("<TON_TOKEN_NGROK>")  # token personnel, récupéré sur dashboard.ngrok.com — ne jamais committer en clair
public_url = ngrok.connect(11434)
print(f"URL publique : {public_url}")
```

**Points techniques rencontrés :**
- `torchao` préinstallé sur Colab en version trop ancienne pour `peft` → mise à jour forcée (`pip install -U torchao`) puis simple relance de la cellule (pas de redémarrage de session nécessaire dans ce cas précis).
- L'installeur Ollama nécessite `zstd`, absent par défaut sur l'image Colab → installation via `apt-get`.
- Le token ngrok doit être un vrai token personnel récupéré sur le dashboard (`dashboard.ngrok.com/get-started/your-authtoken`), pas une valeur placeholder.

### 4.2 Contraintes de cette solution

⚠️ **Session Colab non permanente** : la session se coupe après une période d'inactivité ou au bout de 12h (compte gratuit). L'onglet du notebook doit rester ouvert pendant toute la durée du hackathon. En cas de coupure, il faut relancer au minimum les cellules `ollama serve` + `ngrok.connect` (le modèle GGUF déjà généré reste sur le disque tant que la VM Colab n'est pas recyclée).

⚠️ **URL ngrok non fixe** : à chaque redémarrage du tunnel (compte gratuit), une nouvelle URL est générée — à recommuniquer à l'équipe DEV WEB si la session redémarre.

## 5. Accès pour l'équipe DEV WEB

**URL du serveur d'inférence (tunnel ngrok, accessible depuis n'importe quel réseau) :**
```
https://<sous-domaine-généré>.ngrok-free.app
```
*(URL communiquée séparément à l'équipe, car régénérée à chaque redémarrage de session Colab)*

**Endpoint de génération :**
```
POST /api/generate
Content-Type: application/json

{
  "model": "phi3-financial",
  "prompt": "Votre question ici",
  "stream": false
}
```

**Exemple de test réussi :**
```powershell
curl http://172.20.10.2:11434/api/generate -Method Post -Body '{"model":"phi3-financial","prompt":"Quel est le role dun CFO ?","stream":false}' -ContentType "application/json"
```
→ Réponse HTTP 200, modèle opérationnel et cohérent sur des questions financières.

Ollama expose également un endpoint compatible OpenAI (`/v1/chat/completions`) si l'équipe DEV WEB préfère ce format standard plutôt que le format natif Ollama.

---

## 5. Récapitulatif des livrables INFRA

- ✅ Serveur d'inférence Ollama opérationnel avec le modèle `phi3-financial`
- ✅ Modèle reconstitué à partir du LoRA hérité + modèle de base public
- ✅ API accessible sur le réseau local, testée et validée
- ✅ Documentation du déploiement (ce document)

## 6. Pistes d'amélioration (si temps restant)

- Quantization Q4_K_M pour réduire la taille et accélérer l'inférence
- Ajustement des paramètres d'inférence (température, top_p, num_ctx) selon les retours de l'équipe IA sur la qualité des réponses
- Passage à un hébergement plus stable qu'un hotspot mobile si la démo doit durer