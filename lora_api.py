# lora_api.py
# LoRA API Service (Bkty Consultancy) - GPU-friendly + ComfyUI-friendly
# ✅ Lazy-load model (import'ta GPU'yu kilitlemez)
# ✅ /generate ile istek gelince yükler
# ✅ /unload ile VRAM'i serbest bırakır (ComfyUI için)
# ✅ idle olunca otomatik unload (opsiyonel)
# ✅ basit concurrency kilidi

from flask import Flask, request, jsonify
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
from peft import PeftModel
import torch
import time
import os
import re
import threading
import gc
from datetime import datetime, timedelta

# -------------------------
# Flask
# -------------------------
app = Flask(__name__)

# -------------------------
# Config
# -------------------------
BASE_MODEL_NAME = os.getenv("LORA_BASE_MODEL", "Qwen/Qwen2.5-14B-Instruct")
LORA_PATH = os.getenv("LORA_PATH", "/mnt/backupdrive/qwen2.5_lora/checkpoint-5000")

# Idle olunca otomatik unload (saniye)
IDLE_UNLOAD_SECONDS = int(os.getenv("LORA_IDLE_UNLOAD_SECONDS", "180"))  # 3 dk default
# İstek bitince cache temizliği
ENABLE_PER_REQUEST_CUDA_CLEANUP = os.getenv("LORA_CUDA_CLEANUP", "1") == "1"

# -------------------------
# CUDA & Torch Safety
# -------------------------
os.environ["TOKENIZERS_PARALLELISM"] = "false"

torch.backends.cuda.matmul.allow_tf32 = True
torch.backends.cudnn.allow_tf32 = True

# -------------------------
# Globals (Lazy model)
# -------------------------
_model = None
_tokenizer = None
_model_lock = threading.Lock()
_last_used_utc = None
_is_loading = False


# -------------------------
# Helper: text cleaning / validation
# -------------------------
def clean_non_turkish_chars(text: str) -> str:
    """Çince/Japonca/Korece ve Arapça blokları temizle + whitespace normalize."""
    if not text:
        return ""

    # CJK (Chinese, Japanese, Korean) blokları kaldır
    text = re.sub(r'[\u4e00-\u9fff\u3400-\u4dbf\u3000-\u303f\u30a0-\u30ff\u3100-\u312f\uff00-\uffef]+', '', text)

    # Arapça blokları kaldır
    text = re.sub(r'[\u0600-\u06ff\u0750-\u077f]+', '', text)

    # Çoklu boşlukları tek boşluk yap
    text = re.sub(r'\s+', ' ', text)

    return text.strip()


def validate_turkish_or_english_response(text: str) -> bool:
    """Yanıtın Latin tabanlı (TR/EN) olduğuna dair basit kontrol."""
    if not text:
        return False

    # CJK varsa invalid
    if re.search(r'[\u4e00-\u9fff]+', text):
        return False

    # En az birkaç Latin/TR karakteri olsun
    latin_chars = re.findall(r'[a-zA-ZğüşıöçĞÜŞİÖÇ]', text)
    return len(latin_chars) >= 3


# -------------------------
# Model load/unload (Lazy)
# -------------------------
def _now_utc() -> datetime:
    return datetime.utcnow()


def _touch_last_used():
    global _last_used_utc
    _last_used_utc = _now_utc()


def load_model():
    """Modeli ilk istek geldiğinde yükler. Thread-safe."""
    global _model, _tokenizer, _is_loading

    # hızlı yol
    if _model is not None and _tokenizer is not None:
        _touch_last_used()
        return _model, _tokenizer

    with _model_lock:
        if _model is not None and _tokenizer is not None:
            _touch_last_used()
            return _model, _tokenizer

        if _is_loading:
            # başka thread yüklerken bekle
            # (çok nadir; 1 worker gunicorn ile genelde gerekmez ama güvenli)
            while _is_loading:
                time.sleep(0.05)

            if _model is not None and _tokenizer is not None:
                _touch_last_used()
                return _model, _tokenizer

        _is_loading = True

        try:
            print("🔄 LoRA model yükleniyor (lazy)...")

            # 4-bit Quant Config (STABLE)
            bnb_config = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_quant_type="nf4",
                bnb_4bit_compute_dtype=torch.float16,
                bnb_4bit_use_double_quant=True,
            )

            # Tokenizer
            tokenizer = AutoTokenizer.from_pretrained(
                BASE_MODEL_NAME,
                use_fast=True
            )
            tokenizer.pad_token = tokenizer.eos_token

            # Base Model
            base_model = AutoModelForCausalLM.from_pretrained(
                BASE_MODEL_NAME,
                quantization_config=bnb_config,
                device_map="cuda:0",
                torch_dtype=torch.float16,
            )

            # LoRA
            model = PeftModel.from_pretrained(
                base_model,
                LORA_PATH
            )

            model.eval()
            model.config.pad_token_id = tokenizer.eos_token_id

            # küçük bir mini-warmup (çok minimal)
            try:
                print("🔥 Mini warmup...")
                text = tokenizer.apply_chat_template(
                    [{"role": "user", "content": "Merhaba"}],
                    tokenize=False,
                    add_generation_prompt=True
                )
                inputs = tokenizer(text, return_tensors="pt").to("cuda")
                with torch.inference_mode():
                    model.generate(**inputs, max_new_tokens=1)
                print("✅ Mini warmup tamam")
            except Exception as e:
                print(f"⚠️ Warmup atlandı: {e}")

            _model = model
            _tokenizer = tokenizer
            _touch_last_used()

            print("✅ LoRA model hazır (lazy)")
            return _model, _tokenizer

        finally:
            _is_loading = False


def unload_model():
    """VRAM'i serbest bırakır (ComfyUI gibi servisler için)."""
    global _model, _tokenizer, _last_used_utc

    with _model_lock:
        if _model is None and _tokenizer is None:
            return

        print("🧹 LoRA model unload ediliyor...")
        try:
            # model içinde base_model referansı var; del yeterli
            del _model
            del _tokenizer
        except:
            pass

        _model = None
        _tokenizer = None
        _last_used_utc = None

        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            torch.cuda.ipc_collect()

        print("✅ LoRA unload tamamlandı, VRAM serbest.")


def maybe_unload_if_idle():
    """Model belirli süre idle kalınca unload eder."""
    global _last_used_utc
    if _last_used_utc is None:
        return

    if IDLE_UNLOAD_SECONDS <= 0:
        return

    if _now_utc() - _last_used_utc > timedelta(seconds=IDLE_UNLOAD_SECONDS):
        unload_model()


def post_request_cleanup():
    """Her istekten sonra hafif VRAM temizliği (opsiyonel)."""
    if not ENABLE_PER_REQUEST_CUDA_CLEANUP:
        return

    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()


# -------------------------
# Health / Admin endpoints
# -------------------------
@app.route("/health", methods=["GET"])
def health():
    loaded = (_model is not None and _tokenizer is not None)
    return jsonify({
        "status": "ok",
        "service": "lora_api",
        "model_loaded": loaded,
        "base_model": BASE_MODEL_NAME,
        "lora_path": LORA_PATH,
        "device": "cuda:0",
        "idle_unload_seconds": IDLE_UNLOAD_SECONDS,
        "per_request_cuda_cleanup": ENABLE_PER_REQUEST_CUDA_CLEANUP
    })


@app.route("/unload", methods=["POST"])
def unload():
    unload_model()
    return jsonify({"status": "ok", "message": "model unloaded"})


@app.route("/reload", methods=["POST"])
def reload():
    unload_model()
    model, tok = load_model()
    return jsonify({"status": "ok", "message": "model reloaded"})


@app.route("/status", methods=["GET"])
def status():
    loaded = (_model is not None and _tokenizer is not None)
    return jsonify({
        "model_loaded": loaded,
        "last_used_utc": _last_used_utc.isoformat() if _last_used_utc else None
    })


# -------------------------
# Generate Endpoint
# -------------------------
@app.route("/generate", methods=["POST"])
def generate():
    try:
        data = request.get_json(force=True) or {}

        prompt = (data.get("prompt") or "").strip()
        system = data.get("system") or "Sen yardımsever bir Türkçe AI asistanısın. SADECE Türkçe veya İngilizce yanıt ver. Başka dillerde asla yanıt verme."
        max_tokens = int(data.get("max_new_tokens", 128))

        temperature = float(data.get("temperature", 0.5))
        top_p = float(data.get("top_p", 0.85))
        top_k = int(data.get("top_k", 30))
        repetition_penalty = float(data.get("repetition_penalty", 1.1))

        if not prompt:
            return jsonify({"error": "prompt boş olamaz"}), 400

        # kısa prompt optimizasyonu
        if len(prompt) < 50:
            max_tokens = min(max_tokens, 64)

        enhanced_system = f"""{system}

KRITIK KURALLAR:
1. YALNIZCA Türkçe veya İngilizce yanıt verebilirsin
2. Çince, Japonca, Arapça veya başka dillerde ASLA yanıt verme
3. Eğer hava durumu soruluyorsa, sadece verilen güncel bilgileri kullan
4. Rugby bir spor dalıdır, şehir değildir
"""

        # Modeli lazy-load
        model, tokenizer = load_model()

        messages = [
            {"role": "system", "content": enhanced_system},
            {"role": "user", "content": prompt},
        ]

        text = tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True
        )

        inputs = tokenizer(
            text,
            return_tensors="pt",
            truncation=True,
            max_length=3072
        ).to("cuda")

        start = time.time()

        with torch.inference_mode():
            output = model.generate(
                **inputs,
                max_new_tokens=max_tokens,
                temperature=temperature,
                top_p=top_p,
                top_k=top_k,
                repetition_penalty=repetition_penalty,
                do_sample=True,
                use_cache=True,
                pad_token_id=tokenizer.pad_token_id,
                eos_token_id=tokenizer.eos_token_id,
            )

        gen_tokens = output[0][inputs["input_ids"].shape[1]:]
        response = tokenizer.decode(gen_tokens, skip_special_tokens=True)

        response = clean_non_turkish_chars(response)

        if not validate_turkish_or_english_response(response):
            print(f"⚠️ Geçersiz yanıt filtrelendi (ilk 120): {response[:120]}")
            response = "Üzgünüm, şu anda yanıt veremiyorum. Lütfen sorunuzu tekrar sorun."

        # idle timer touch
        _touch_last_used()

        # istek sonrası cleanup + idle unload kontrol
        post_request_cleanup()
        maybe_unload_if_idle()

        return jsonify({
            "response": response.strip(),
            "response_time_ms": round((time.time() - start) * 1000),
            "tokens_generated": int(len(gen_tokens)),
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        try:
            post_request_cleanup()
            maybe_unload_if_idle()
        except:
            pass
        return jsonify({"error": str(e)}), 500


# -------------------------
# Test Endpoint
# -------------------------
@app.route("/test", methods=["GET"])
def test():
    test_prompts = [
        "Merhaba, nasılsın?",
        "İstanbul'da hava nasıl?",
        "Rugby'de hava durumu nedir?"
    ]

    results = []
    for p in test_prompts:
        r = _generate_test(p)
        results.append({"prompt": p, "response": r})

    return jsonify(results)


def _generate_test(prompt: str) -> str:
    model, tokenizer = load_model()

    messages = [
        {"role": "system", "content": "Sen Türkçe konuşan bir AI asistanısın. SADECE Türkçe yanıt ver."},
        {"role": "user", "content": prompt},
    ]

    text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    inputs = tokenizer(text, return_tensors="pt", truncation=True).to("cuda")

    with torch.inference_mode():
        output = model.generate(
            **inputs,
            max_new_tokens=60,
            temperature=0.5,
            top_p=0.85,
            do_sample=True,
            pad_token_id=tokenizer.pad_token_id,
        )

    response = tokenizer.decode(output[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True)
    response = clean_non_turkish_chars(response).strip()

    _touch_last_used()
    post_request_cleanup()
    maybe_unload_if_idle()

    return response


# -------------------------
# Main (dev only)
# -------------------------
if __name__ == "__main__":
    # Dev modda direkt çalıştırmak için
    app.run(host="0.0.0.0", port=5005, debug=False)
