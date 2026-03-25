import torch
from datasets import load_dataset
from transformers import (
    AutoModelForCausalLM, 
    AutoTokenizer, 
    TrainingArguments, 
    Trainer,
    BitsAndBytesConfig,
    DataCollatorForLanguageModeling
)
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
import os

# Cache ve output yönlendirme
os.environ["HF_HOME"] = "/mnt/backupdrive/huggingface_cache"
os.environ["TRANSFORMERS_CACHE"] = "/mnt/backupdrive/huggingface_cache"

MODEL_NAME = "Qwen/Qwen2.5-14B-Instruct"

print("Model yukleniyor:", MODEL_NAME)

# 4-bit quantization
bnb_config = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_quant_type="nf4",
    bnb_4bit_compute_dtype=torch.bfloat16,
    bnb_4bit_use_double_quant=True,
)

model = AutoModelForCausalLM.from_pretrained(
    MODEL_NAME,
    quantization_config=bnb_config,
    device_map="auto",
    trust_remote_code=True,
    torch_dtype=torch.bfloat16,
    # Flash Attention 2 yok ise yoruma al
    # attn_implementation="flash_attention_2"
)

tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME, trust_remote_code=True)
tokenizer.pad_token = tokenizer.eos_token
tokenizer.padding_side = "right"

# Dataset
train_dataset = load_dataset("json", data_files={
    "train": ["tr_wiki_qa.jsonl", "en_wiki_qa.jsonl"]
})["train"]

def format_example(example):
    instruction = example["instruction"]
    context = example["input"]
    answer = example["output"]
    
    if context:
        prompt = f"Instruction: {instruction}\nInput: {context}\nAnswer:"
    else:
        prompt = f"Instruction: {instruction}\nAnswer:"
    
    full_text = prompt + " " + answer + tokenizer.eos_token
    
    tokenized = tokenizer(
        full_text, 
        truncation=True, 
        max_length=512,
        padding=False,
        return_tensors=None
    )
    
    prompt_len = len(tokenizer(prompt, truncation=True, max_length=512, add_special_tokens=False)["input_ids"])
    labels = tokenized["input_ids"].copy()
    labels[:prompt_len] = [-100] * prompt_len
    
    return {
        "input_ids": tokenized["input_ids"],
        "attention_mask": tokenized["attention_mask"],
        "labels": labels
    }

print("Dataset isleniyor...")
train_dataset = train_dataset.map(
    format_example, 
    remove_columns=train_dataset.column_names,
    num_proc=4
)

# LoRA
peft_config = LoraConfig(
    r=16,
    lora_alpha=32,
    lora_dropout=0.05,
    bias="none",
    task_type="CAUSAL_LM",
    target_modules=["q_proj", "v_proj"]
)

model = prepare_model_for_kbit_training(model)
model = get_peft_model(model, peft_config)
model.config.use_cache = False
model.gradient_checkpointing_enable()

print("Trainable parameters:")
model.print_trainable_parameters()

# Training args
training_args = TrainingArguments(
    output_dir="/mnt/backupdrive/qwen2.5_lora",
    per_device_train_batch_size=1,
    gradient_accumulation_steps=16,
    max_steps=5000,
    learning_rate=2e-4,
    warmup_steps=500,
    logging_steps=50,
    save_steps=500,
    save_total_limit=2,
    bf16=True,
    optim="paged_adamw_8bit",
    gradient_checkpointing=True,
    dataloader_num_workers=2,
    report_to="none",
    logging_first_step=True,
    max_grad_norm=0.3,
    dataloader_pin_memory=False,
)

data_collator = DataCollatorForLanguageModeling(
    tokenizer=tokenizer,
    mlm=False,
    pad_to_multiple_of=8
)

trainer = Trainer(
    model=model,
    train_dataset=train_dataset,
    args=training_args,
    data_collator=data_collator,
)

print("Egitim basliyor...")
trainer.train()

# Final model'i backupdrive'a kaydet
model.save_pretrained("/mnt/backupdrive/qwen2.5_lora_final")
tokenizer.save_pretrained("/mnt/backupdrive/qwen2.5_lora_final")
print("Egitim tamamlandi!")
print("Model: /mnt/backupdrive/qwen2.5_lora_final")