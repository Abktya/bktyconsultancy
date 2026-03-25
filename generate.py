import torch
from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig
from peft import PeftModel

BASE_MODEL = "Qwen/Qwen2.5-14B-Instruct"
LORA_PATH = "/mnt/backupdrive/qwen2.5_lora/checkpoint-5000"

# 4-bit yükleme
bnb_config = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_quant_type="nf4",
    bnb_4bit_compute_dtype=torch.bfloat16,
    bnb_4bit_use_double_quant=True,
)

print("📥 Base model yükleniyor...")
base_model = AutoModelForCausalLM.from_pretrained(
    BASE_MODEL,
    quantization_config=bnb_config,
    device_map="auto",
    trust_remote_code=True,
)

print("📥 Tokenizer yükleniyor...")
tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL, trust_remote_code=True)

print("📥 LoRA ağırlıkları yükleniyor...")
model = PeftModel.from_pretrained(base_model, LORA_PATH)
model.eval()

def chat(prompt, max_new_tokens=256):
    inputs = tokenizer(prompt, return_tensors="pt").to(model.device)
    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_new_tokens=max_new_tokens,
            temperature=0.7,
            top_p=0.9,
        )
    return tokenizer.decode(outputs[0], skip_special_tokens=True)

# Örnek testler
print("=== Türkçe Test ===")
print(chat("Adana nedir?"))

print("\n=== İngilizce Test ===")
print(chat("Summarize the importance of Newton's laws of motion."))


