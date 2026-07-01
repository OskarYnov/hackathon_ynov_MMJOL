\# Documentation Technique — Déploiement Infra

\## Projet TechCorp AI Chat — Modèle Phi-3.5-Financial



\*\*Auteur :\*\* Maxime (rôle INFRA)

\*\*Équipe :\*\* Oskar (chef de projet) et al.

\*\*Date :\*\* 01/07/2026



\---



\## 1. Choix technique



\*\*Solution retenue : Ollama\*\*



| Critère | Ollama | Triton Inference Server | Serveur maison |

|---|---|---|---|

| Temps de mise en place | Très rapide (installeur graphique) | Long (configuration protobuf, backend TensorRT/Python complexe) | Moyen à long (dev API complet) |

| Besoin GPU dédié | Non (tourne bien sur CPU pour un modèle "mini") | Recommandé fortement | Dépend de l'implémentation |

| API prête à l'emploi | Oui (REST native + endpoint compatible OpenAI) | Oui mais plus complexe à intégrer | À développer |

| Adapté à un hackathon de 7h | Oui | Non | Non |



Ollama a été choisi pour sa simplicité de déploiement, l'absence de dépendance à un GPU puissant, et une API REST immédiatement exploitable par l'équipe DEV WEB, ce qui correspondait aux contraintes de temps du hackathon.



\---



\## 2. Contexte : état du modèle hérité



Le dossier `models/phi3\_financial/` fourni par l'équipe précédente ne contenait \*\*pas\*\* un modèle complet, mais uniquement un \*\*adaptateur LoRA\*\* (fine-tuning léger) :



\- `adapter\_config.json`

\- `adapter\_model.safetensors` (\~30 Mo)

\- fichiers de tokenizer



Le fichier `adapter\_config.json` a permis d'identifier le modèle de base utilisé pour l'entraînement :



```json

"base\_model\_name\_or\_path": "microsoft/Phi-3-mini-4k-instruct"

```



Il a donc fallu reconstituer le modèle complet en fusionnant ce LoRA avec le modèle de base public, avant de pouvoir le déployer.



\---



\## 3. Pipeline de déploiement, étapes détaillées



\### 3.1 Installation d'Ollama



Téléchargement et installation via l'installeur Windows officiel : https://ollama.com/download



Vérification :

```powershell

ollama --version

```



\### 3.2 Récupération des fichiers du modèle (Git LFS)



Les fichiers volumineux (`adapter\_model.safetensors`) sont versionnés via \*\*Git LFS\*\*. Deux points de blocage rencontrés et résolus :



1\. \*\*Remote configuré en SSH sans clé configurée\*\* → bascule du remote en HTTPS :

&#x20;  ```powershell

&#x20;  git remote set-url origin https://github.com/OskarYnov/hackathon\_ynov\_MMJOL.git

&#x20;  ```

2\. \*\*Conflit avec OneDrive\*\* : le dossier de travail était synchronisé par OneDrive, ce qui provoquait des erreurs d'écriture pendant `git lfs pull` (`cannot add to the index`). Résolution : déplacement du repo hors de tout dossier synchronisé (`C:\\Users\\<user>\\Documents\\` en local, hors OneDrive).



```powershell

git lfs install

git lfs pull

```



\### 3.3 Fusion du LoRA avec le modèle de base



\*\*Environnement Python (venv) :\*\*

```powershell

python -m venv venv

.\\venv\\Scripts\\Activate.ps1

pip install torch transformers peft accelerate huggingface\_hub

```



\*\*Script de fusion (`merge\_lora.py`) :\*\*

```python

from transformers import AutoModelForCausalLM, AutoTokenizer

from peft import PeftModel

import torch

import os



base\_model\_name = "microsoft/Phi-3-mini-4k-instruct"

adapter\_path = "models/phi3\_financial"

output\_path = "models/phi3\_financial\_merged"



base\_model = AutoModelForCausalLM.from\_pretrained(

&#x20;   base\_model\_name,

&#x20;   torch\_dtype=torch.float16,

&#x20;   device\_map="cpu",

&#x20;   low\_cpu\_mem\_usage=True

)

tokenizer = AutoTokenizer.from\_pretrained(base\_model\_name)



model = PeftModel.from\_pretrained(base\_model, adapter\_path)

merged\_model = model.merge\_and\_unload()



os.makedirs(output\_path, exist\_ok=True)

merged\_model.save\_pretrained(output\_path)

tokenizer.save\_pretrained(output\_path)

```



\*\*Points techniques rencontrés :\*\*

\- `trust\_remote\_code=True` provoquait une erreur (`KeyError: 'type'` sur `rope\_scaling`) à cause d'une incompatibilité entre le code distant du repo HuggingFace et la version récente de `transformers`. Résolu en utilisant l'implémentation Phi-3 \*\*native\*\* de `transformers` (retrait du paramètre).

\- Crash silencieux au chargement du modèle de base, dû à une saturation RAM (16 Go dispo, \~9 Go libres). Résolu avec `low\_cpu\_mem\_usage=True` et `device\_map="cpu"`, qui charge les poids de façon plus économe en mémoire.



Résultat : modèle fusionné (\~7.6 Go en `model.safetensors`) dans `models/phi3\_financial\_merged/`.



\### 3.4 Conversion au format GGUF (compatible Ollama)



Outil utilisé : \[llama.cpp](https://github.com/ggerganov/llama.cpp) (cloné en dehors du repo projet).



```powershell

git clone https://github.com/ggerganov/llama.cpp.git

cd llama.cpp

pip install -r requirements.txt

python convert\_hf\_to\_gguf.py <chemin\_modele\_fusionné> --outfile <chemin\_sortie>.gguf --outtype f16

```



\*\*Point technique rencontré :\*\* le convertisseur exige un fichier `tokenizer.model` (format SentencePiece brut), absent après un `save\_pretrained()` classique (qui ne sauvegarde que le tokenizer "fast" au format `tokenizer.json`). Le fichier a été récupéré depuis le cache local HuggingFace du modèle de base (`\~/.cache/huggingface/hub/models--microsoft--Phi-3-mini-4k-instruct/snapshots/<hash>/tokenizer.model`) et copié manuellement dans le dossier du modèle fusionné.



Résultat : `phi3-financial-f16.gguf` (\~7.6 Go, format f16 non quantisé).



> \*\*Note d'optimisation non réalisée par manque de temps :\*\* une quantization en Q4\_K\_M (via `llama-quantize`) permettrait de réduire la taille à \~2.2 Go et d'accélérer l'inférence sur CPU, au prix d'une perte de qualité marginale. Nécessite la compilation de `llama.cpp` (CMake + Visual Studio Build Tools), non réalisée dans le temps imparti du hackathon.



\### 3.5 Création du modèle dans Ollama



\*\*Modelfile :\*\*

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



\### 3.6 Exposition réseau du serveur



Par défaut, Ollama n'écoute qu'en local (`127.0.0.1:11434`). Pour rendre le serveur accessible aux autres membres de l'équipe (DEV WEB) sur le réseau local :



```powershell

$env:OLLAMA\_HOST="0.0.0.0:11434"

ollama serve

```



Règle de pare-feu Windows ajoutée pour autoriser le trafic entrant sur le port :

```powershell

New-NetFirewallRule -DisplayName "Ollama" -Direction Inbound -LocalPort 11434 -Protocol TCP -Action Allow

```



\---



\## 4. Accès pour l'équipe DEV WEB



\*\*URL du serveur d'inférence :\*\*

```

http://172.20.10.2:11434

```



⚠️ Toutes les machines de l'équipe doivent être connectées au \*\*même réseau\*\* (hotspot mobile utilisé pendant le hackathon) pour pouvoir joindre cette adresse.



\*\*Endpoint de génération :\*\*

```

POST /api/generate

Content-Type: application/json



{

&#x20; "model": "phi3-financial",

&#x20; "prompt": "Votre question ici",

&#x20; "stream": false

}

```



\*\*Exemple de test réussi :\*\*

```powershell

curl http://172.20.10.2:11434/api/generate -Method Post -Body '{"model":"phi3-financial","prompt":"Quel est le role dun CFO ?","stream":false}' -ContentType "application/json"

```

→ Réponse HTTP 200, modèle opérationnel et cohérent sur des questions financières.



Ollama expose également un endpoint compatible OpenAI (`/v1/chat/completions`) si l'équipe DEV WEB préfère ce format standard plutôt que le format natif Ollama.



\---



\## 5. Récapitulatif des livrables INFRA



\- ✅ Serveur d'inférence Ollama opérationnel avec le modèle `phi3-financial`

\- ✅ Modèle reconstitué à partir du LoRA hérité + modèle de base public

\- ✅ API accessible sur le réseau local, testée et validée

\- ✅ Documentation du déploiement (ce document)



\## 6. Pistes d'amélioration (si temps restant)



\- Quantization Q4\_K\_M pour réduire la taille et accélérer l'inférence

\- Ajustement des paramètres d'inférence (température, top\_p, num\_ctx) selon les retours de l'équipe IA sur la qualité des réponses

\- Passage à un hébergement plus stable qu'un hotspot mobile si la démo doit durer

