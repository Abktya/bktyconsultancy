import random
from datasets import load_dataset
import re
import json

def clean_text(text):
    text = re.sub(r"\{\{.*?\}\}", "", text)
    text = re.sub(r"<ref.*?>.*?</ref>", "", text)
    text = re.sub(r"\[.*?\]", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text

def make_qa(example):
    text = example["clean_text"]
    if not text or len(text.split()) < 30:
        return {"instruction": None, "input": None, "output": None}

    tasks = [
        ("Bu yazıyı özetle.", text, text[:400]),
        (
            "Bu metne göre bir soru sor ve cevapla.",
            text,
            f"Soru: {text.split('.')[0]}?\nCevap: {text.split('.')[1] if len(text.split('.')) > 1 else text[:200]}"
        )
    ]
    instruction, input_text, output = random.choice(tasks)
    return {"instruction": instruction, "input": input_text, "output": output}

def save_jsonl(dataset, path):
    with open(path, "w", encoding="utf-8") as f:
        for ex in dataset:
            if ex["instruction"] and ex["output"]:
                f.write(json.dumps({
                    "instruction": ex["instruction"],
                    "input": ex["input"],
                    "output": ex["output"]
                }, ensure_ascii=False) + "\n")
    print(f"✅ Dataset kaydedildi: {path}")

if __name__ == "__main__":
    # --- İngilizce ---
    ds_en = load_dataset("wikimedia/wikipedia", "20231101.en", split="train")
    ds_en = ds_en.map(lambda x: {"clean_text": clean_text(x["text"])})
    qa_en = ds_en.map(make_qa).filter(lambda x: x["instruction"] is not None)
    save_jsonl(qa_en, "en_wiki_qa.jsonl")
