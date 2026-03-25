# vllm_lora_api.py
from vllm import LLM, SamplingParams
from flask import Flask, request, jsonify

app = Flask(__name__)

# vLLM model yükle
llm = LLM(
    model="Qwen/Qwen2.5-14B-Instruct",
    enable_lora=True,
    max_lora_rank=64,
    gpu_memory_utilization=0.9,
    dtype="bfloat16"
)

# LoRA adapter ekle
llm.load_lora_adapter("/mnt/backupdrive/qwen2.5_lora/checkpoint-5000", "custom-lora")

@app.route('/generate', methods=['POST'])
def generate():
    data = request.json
    prompt = data.get('prompt', '')
    
    sampling_params = SamplingParams(
        temperature=0.7,
        top_p=0.9,
        max_tokens=200
    )
    
    outputs = llm.generate([prompt], sampling_params, lora_request="custom-lora")
    
    return jsonify({
        "response": outputs[0].outputs[0].text,
        "response_time": outputs[0].metrics.total_time_ms
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5005)