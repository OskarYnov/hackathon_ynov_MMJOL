from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import PeftModel
import torch
import os

base_model_name = "microsoft/Phi-3-mini-4k-instruct"
adapter_path = "models/phi3_financial"
output_path = "models/phi3_financial_merged"

try:
    print("Téléchargement du modèle de base...")
    base_model = AutoModelForCausalLM.from_pretrained(
    base_model_name,
    torch_dtype=torch.float16,
    device_map="cpu",
    low_cpu_mem_usage=True
)
    print("Modèle de base chargé OK.")

    tokenizer = AutoTokenizer.from_pretrained(base_model_name)
    print("Tokenizer chargé OK.")

    print("Chargement du LoRA...")
    model = PeftModel.from_pretrained(base_model, adapter_path)
    print("LoRA chargé OK.")

    print("Fusion...")
    merged_model = model.merge_and_unload()
    print("Fusion OK.")

    os.makedirs(output_path, exist_ok=True)
    print(f"Sauvegarde dans {os.path.abspath(output_path)}...")
    merged_model.save_pretrained(output_path)
    tokenizer.save_pretrained(output_path)
    print("Terminé !")

except Exception as e:
    print(f"ERREUR : {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()