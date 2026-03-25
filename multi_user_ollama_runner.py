# multi_user_ollama_runner.py - Asyncio düzeltilmiş versiyonu
import asyncio
import aiohttp
import requests
import json
import time
import threading
import uuid
import logging
import os
import re
import websocket
import urllib.request
import urllib.parse
import base64
from datetime import datetime, timedelta
from collections import defaultdict, deque
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Optional, Tuple, Any
import hashlib
import websocket as ws_lib
import websocket


# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(), logging.FileHandler('ollama_runner.log')]
)
logger = logging.getLogger(__name__)

# Model konfigürasyonları - güncellenmiş
OLLAMA_MODELS = {
    "qwen2.5:14b-instruct": "🚀 Qwen2.5 14B (Genel Kullanım & Türkçe)",
    "qwen2.5-lora": "🚀 Qwen2.5 14B + LoRA (Sohbet için)",
    "deepseek-coder-v2:16b": "💻 DeepSeek Coder V2 16B (Kod Uzmanı)",
    "bakllava:7b": "🥧 Bakllava 7B (Türkçe LLaMA türevi)",
    "llava:13b": "👁️ LLaVA 13B (Görüntü Analizi)",
    "stable-diffusion-v1.5": "🎨 Stable Diffusion v1.5 (Görüntü Üretimi)"
}

# GPU model routing
GPU_MODEL_ROUTING = {
    "primary": {
        "endpoint": "http://localhost:11434",
        "models": [m for m in OLLAMA_MODELS.keys() if "stable-diffusion" not in m],
        "max_concurrent": 6,
        "timeout": 10
    },
    "comfyui": {
        "endpoint": "http://localhost:8188",
        "models": ["stable-diffusion-v1.5"],
        "max_concurrent": 2,
        "timeout": 30
    }
}


class ComfyUIAPI:
    def __init__(self, server_address="127.0.0.1:8188"):
        self.server_address = server_address
        
    def queue_prompt(self, prompt):
        """Prompt'u ComfyUI queue'sine ekle"""
        try:
            p = {"prompt": prompt, "client_id": str(uuid.uuid4())}
            data = json.dumps(p).encode('utf-8')
            req = urllib.request.Request(f"http://{self.server_address}/prompt", data=data)
            req.add_header('Content-Type', 'application/json')
            
            response = urllib.request.urlopen(req, timeout=30)
            result = json.loads(response.read())
            print(f"📨 Queue prompt response: {result}")
            return result
        except Exception as e:
            print(f"❌ Queue prompt error: {e}")
            raise

    def get_image(self, filename, subfolder, folder_type):
        """Tek bir görüntüyü ComfyUI'den al"""
        try:
            data = {"filename": filename, "subfolder": subfolder, "type": folder_type}
            url_values = urllib.parse.urlencode(data)
            url = f"http://{self.server_address}/view?{url_values}"
            print(f"📷 Fetching image from: {url}")
            
            response = urllib.request.urlopen(url, timeout=30)
            image_data = response.read()
            print(f"📷 Downloaded image: {len(image_data)} bytes")
            return image_data
        except Exception as e:
            print(f"❌ Get image error: {e}")
            raise

    def get_history(self, prompt_id):
        """Belirli bir prompt_id için history al"""
        try:
            url = f"http://{self.server_address}/history/{prompt_id}"
            print(f"📚 Fetching history from: {url}")
            
            response = urllib.request.urlopen(url, timeout=30)
            result = json.loads(response.read())
            print(f"📚 History response: {len(result)} items")
            return result
        except Exception as e:
            print(f"❌ Get history error: {e}")
            raise

    def get_queue_status(self):
        """Queue durumunu kontrol et"""
        try:
            url = f"http://{self.server_address}/queue"
            response = urllib.request.urlopen(url, timeout=10)
            result = json.loads(response.read())
            return result
        except Exception as e:
            print(f"❌ Get queue status error: {e}")
            return {"queue_running": [], "queue_pending": []}

    def check_server_status(self):
        """Server durumunu kontrol et"""
        try:
            url = f"http://{self.server_address}/system_stats"
            response = urllib.request.urlopen(url, timeout=5)
            return response.getcode() == 200
        except:
            return False
            
class UserSession:
    """Kullanıcı session yönetimi"""
    
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.session_id = str(uuid.uuid4())
        self.created_at = time.time()
        self.last_activity = time.time()
        self.request_count = 0
        self.context_history = deque(maxlen=10)
        self.preferred_model = "auto"
        self.total_tokens = 0
        self.avg_response_time = 0.0
        self.error_count = 0
        
    def update_activity(self):
        self.last_activity = time.time()
        
    def add_context(self, user_message: str, bot_response: str, model_used: str):
        try:
            self.context_history.append({
                "timestamp": time.time(),
                "user": user_message[:500],
                "bot": bot_response[:500],
                "model": model_used
            })
        except Exception as e:
            logger.error(f"Context ekleme hatası: {e}")
        
    def is_active(self, timeout_minutes: int = 30) -> bool:
        return (time.time() - self.last_activity) < (timeout_minutes * 60)
        
    def get_context_string(self, max_messages: int = 5) -> str:
        recent_context = list(self.context_history)[-max_messages:]
        context_parts = []
        for ctx in recent_context:
            context_parts.extend([f"User: {ctx['user']}", f"Assistant: {ctx['bot']}"])
        return "\n".join(context_parts) if context_parts else ""

class RateLimiter:
    def __init__(self):
        self.user_requests = defaultdict(lambda: deque(maxlen=1000))
        self.limits = {
            "requests_per_minute": 20,
            "requests_per_hour": 200,
            "requests_per_day": 1000
        }
        
    def is_allowed(self, user_id: str) -> Tuple[bool, str]:
        now = time.time()
        user_history = self.user_requests[user_id]
        
        minute_requests = sum(1 for req_time in user_history if now - req_time < 60)
        if minute_requests >= self.limits["requests_per_minute"]:
            return False, f"Dakikada maksimum {self.limits['requests_per_minute']} istek yapabilirsiniz"
            
        hour_requests = sum(1 for req_time in user_history if now - req_time < 3600)
        if hour_requests >= self.limits["requests_per_hour"]:
            return False, f"Saatte maksimum {self.limits['requests_per_hour']} istek yapabilirsiniz"
            
        day_requests = len(user_history)
        if day_requests >= self.limits["requests_per_day"]:
            return False, f"Günde maksimum {self.limits['requests_per_day']} istek yapabilirsiniz"
            
        return True, ""
        
    def add_request(self, user_id: str):
        self.user_requests[user_id].append(time.time())

class LoadBalancer:
    def __init__(self):
        self.active_requests = defaultdict(int)
        self.model_gpu_map = self._build_model_gpu_map()
        
    def _build_model_gpu_map(self) -> Dict[str, str]:
        mapping = {}
        for gpu_type, config in GPU_MODEL_ROUTING.items():
            for model in config["models"]:
                mapping[model] = gpu_type
        return mapping
        
    def get_best_endpoint(self, model_name: str) -> str:
        gpu_type = self.model_gpu_map.get(model_name, "primary")
        return GPU_MODEL_ROUTING[gpu_type]["endpoint"]
        
    def can_process_request(self, model_name: str) -> bool:
        gpu_type = self.model_gpu_map.get(model_name, "primary")
        max_concurrent = GPU_MODEL_ROUTING[gpu_type]["max_concurrent"]
        current_load = self.active_requests[gpu_type]
        return current_load < max_concurrent
        
    def acquire_slot(self, model_name: str):
        gpu_type = self.model_gpu_map.get(model_name, "primary")
        self.active_requests[gpu_type] += 1
        
    def release_slot(self, model_name: str):
        gpu_type = self.model_gpu_map.get(model_name, "primary")
        self.active_requests[gpu_type] = max(0, self.active_requests[gpu_type] - 1)

class SmartModelSelector:
    def __init__(self):
        from collections import defaultdict
        self.model_performance = defaultdict(lambda: {"avg_time": 5.0, "success_rate": 0.95})

    def select_model(self, prompt: str, user_preference: str = "auto", context_length: int = 0) -> str:
        if user_preference != "auto" and user_preference in OLLAMA_MODELS:
            return user_preference

        prompt_lower = prompt.lower().strip()

        # 1. FUTBOL TAHMİNİ (En yüksek öncelik - özel işlem gerektirir)
        football_keywords = [
            'maç', 'match', 'tahmin', 'predict', 'analiz', 'analyze',
            'galatasaray', 'fenerbahçe', 'fenerbahce', 'beşiktaş', 'besiktas', 
            'trabzonspor', 'barcelona', 'real madrid', 'liverpool', 'manchester',
            'arsenal', 'chelsea', 'bayern', 'psg', 'juventus', 'milan'
        ]
        vs_pattern = r'\b(vs|versus|-|ile)\b'
        
        has_football_keyword = any(kw in prompt_lower for kw in football_keywords)
        has_vs_pattern = re.search(vs_pattern, prompt_lower)
        
        if has_football_keyword and has_vs_pattern:
            print("⚽ Futbol maç analizi algılandı -> FOOTBALL API")
            return "football-prediction"  # Özel marker

        # 2. SELAMLAMA
        casual_phrases = ["selam", "merhaba", "hi", "hello", "nasılsın", "naber", "teşekkür", "sağol"]
        if any(phrase == prompt_lower for phrase in casual_phrases):
            print("💬 Casual chat algılandı -> qwen2.5-lora")
            return "qwen2.5-lora"

        # 3. KOD YAZMA
        if re.search(r"\b(def |class |import |console\.log|function\s*\(|kod yaz|code|python|javascript)", prompt_lower):
            print("💻 Kod algılandı -> deepseek-coder")
            return "deepseek-coder-v2:16b"

        # 4. GÖRÜNTÜ ÜRETİMİ
        image_generation_keywords = [
            "resim çiz", "görsel oluştur", "çizim yap", "resim yap", "görsel yap",
            "resim yapar mısın", "resim yapabilir misin", "çizebilir misin", 
            "resim oluştur", "fotoğraf çek", "bir resim", "resim üret",
            "kedi resmi", "köpek resmi", "manzara resmi", "portre çiz",
            "draw image", "create picture", "generate image", "make image", 
            "paint", "sketch", "illustration", "artwork", "photo"
        ]
        
        for keyword in image_generation_keywords:
            if keyword in prompt_lower:
                print(f"🎨 Görüntü üretimi algılandı ('{keyword}') -> stable-diffusion")
                return "stable-diffusion-v1.5"

        # 5. GÖRÜNTÜ ANALİZİ
        analysis_keywords = [
            "görüntü analiz", "resmi analiz", "bu resimde", "resimde ne var",
            "image analyze", "what do you see", "describe image"
        ]
        for keyword in analysis_keywords:
            if keyword in prompt_lower:
                print("👁️ Görüntü analizi algılandı -> llava")
                return "llava:13b"

        # 6. DEFAULT: Genel sohbet
        return "qwen2.5-lora"
        
    def update_performance(self, model_name: str, response_time: float, success: bool):
        perf = self.model_performance[model_name]
        perf["avg_time"] = (perf["avg_time"] * 0.9) + (response_time * 0.1)
        perf["success_rate"] = (perf["success_rate"] * 0.95) + (0.05 if success else 0.0)



class CodeExecutionAgent:
    def __init__(self, config: Dict = None):
        self.config = config or {}
        self.stats = {
            "total_executions": 0,
            "successful_executions": 0,
            "failed_executions": 0,
            "avg_execution_time": 0.0
        }
        
    def execute_code(self, code: str, language: str = "python") -> Dict[str, Any]:
        start_time = time.time()
        self.stats["total_executions"] += 1
        
        unsafe_commands = ['os.system', 'subprocess', 'import os', 'import sys', 'eval(', 'exec(']
        if any(cmd in code.lower() for cmd in unsafe_commands):
            return {"success": False, "error": "Güvenlik nedeniyle bu kod çalıştırılamaz", "execution_time": 0.0}
        
        try:
            if language.lower() == "python":
                result = self._execute_python(code)
            elif language.lower() == "javascript":
                result = self._execute_javascript(code)
            else:
                return {"error": f"Desteklenmeyen dil: {language}", "success": False}
            
            execution_time = time.time() - start_time
            self.stats["avg_execution_time"] = (self.stats["avg_execution_time"] * 0.9) + (execution_time * 0.1)
            
            if result.get("success"):
                self.stats["successful_executions"] += 1
            else:
                self.stats["failed_executions"] += 1
                
            result["execution_time"] = execution_time
            return result
            
        except Exception as e:
            self.stats["failed_executions"] += 1
            return {
                "success": False,
                "error": str(e),
                "execution_time": time.time() - start_time
            }
    
    def _execute_python(self, code: str) -> Dict[str, Any]:
        import subprocess
        import tempfile
        
        try:
            result = subprocess.run(
                ['python', '-c', code],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            return {
                "success": result.returncode == 0,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "return_code": result.returncode
            }
        except subprocess.TimeoutExpired as e:
            return {"success": False, "error": "Kod çalıştırma zaman aşımı", "stderr": str(e)}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _execute_javascript(self, code: str) -> Dict[str, Any]:
        import subprocess
        import tempfile
        
        try:
            with tempfile.NamedTemporaryFile(mode='w', suffix='.js', delete=False) as f:
                f.write(code)
                f.flush()
                
                result = subprocess.run(
                    ['node', f.name],
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                os.unlink(f.name)
                
                return {
                    "success": result.returncode == 0,
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                    "return_code": result.returncode
                }
        except subprocess.TimeoutExpired as e:
            return {"success": False, "error": "Kod çalıştırma zaman aşımı", "stderr": str(e)}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def get_stats(self) -> Dict[str, Any]:
        success_rate = 0.0
        if self.stats["total_executions"] > 0:
            success_rate = self.stats["successful_executions"] / self.stats["total_executions"]
        return {**self.stats, "success_rate": success_rate}

class MultiUserOllamaRunner:
    def __init__(self):
        self.sessions: Dict[str, UserSession] = {}
        self.rate_limiter = RateLimiter()
        self.load_balancer = LoadBalancer()
        self.model_selector = SmartModelSelector()
        self.code_agent = CodeExecutionAgent()
        self.executor = ThreadPoolExecutor(max_workers=20)
        self.comfy_api = ComfyUIAPI()
        
        self.request_queue = asyncio.Queue(maxsize=500)
        self.processing_users = set()
        
        self.stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "avg_response_time": 0.0,
            "active_sessions": 0,
            "model_usage": defaultdict(int)
        }
        
        self._start_cleanup_thread()
        
    def _start_cleanup_thread(self):
        def cleanup_sessions():
            while True:
                try:
                    expired_sessions = [
                        session_id for session_id, session in self.sessions.items()
                        if not session.is_active(timeout_minutes=60)
                    ]
                    for session_id in expired_sessions:
                        del self.sessions[session_id]
                        logger.info(f"Session expired: {session_id}")
                    self.stats["active_sessions"] = len(self.sessions)
                    time.sleep(300)
                except Exception as e:
                    logger.error(f"Cleanup error: {e}")
                    time.sleep(60)
        cleanup_thread = threading.Thread(target=cleanup_sessions, daemon=True)
        cleanup_thread.start()
        
    def get_or_create_session(self, user_id: str) -> UserSession:
        if user_id not in self.sessions:
            self.sessions[user_id] = UserSession(user_id)
            logger.info(f"New session created: {user_id}")
        session = self.sessions[user_id]
        session.update_activity()
        return session
        
    def is_ollama_running(self, endpoint: str = "http://localhost:11434") -> bool:
        try:
            response = requests.get(f"{endpoint}/api/tags", timeout=5)
            return response.status_code == 200
        except requests.RequestException:
            return False
    
    def is_comfyui_running(self) -> bool:
        """ComfyUI servisinin çalışıp çalışmadığını kontrol et"""
        try:
            response = requests.get("http://localhost:8188/system_stats", timeout=5)
            return response.status_code == 200
        except requests.RequestException:
            return False
            
    def get_available_models(self, endpoint: str = "http://localhost:11434") -> List[str]:
        try:
            response = requests.get(f"{endpoint}/api/tags", timeout=10)
            if response.status_code == 200:
                try:
                    models = response.json().get('models', [])
                except ValueError:
                    logger.error(f"get_available_models JSON parse hatası: {response.text[:200]}")
                    return []
                return [model['name'] for model in models]
            return []
        except requests.RequestException as e:
            logger.error(f"Error getting models from {endpoint}: {e}")
            return []

    def create_basic_workflow(self, prompt_text: str, negative_prompt: str = "") -> dict:
        workflow = {
            "3": {
                "inputs": {
                    "seed": 42,
                    "steps": 20,
                    "cfg": 8.0,
                    "sampler_name": "euler",
                    "scheduler": "normal",
                    "denoise": 1,
                    "model": ["4", 0],
                    "positive": ["6", 0],
                    "negative": ["7", 0],
                    "latent_image": ["5", 0]
                },
                "class_type": "KSampler"
            },
            "4": {
                "inputs": {
                    "ckpt_name": "v1-5-pruned.safetensors"
                },
                "class_type": "CheckpointLoaderSimple"
            },
            "5": {
                "inputs": {
                    "width": 512,
                    "height": 512,
                    "batch_size": 1
                },
                "class_type": "EmptyLatentImage"
            },
            "6": {
                "inputs": {
                    "text": prompt_text,
                    "clip": ["4", 1]
                },
                "class_type": "CLIPTextEncode"
            },
            "7": {
                "inputs": {
                    "text": negative_prompt,
                    "clip": ["4", 1]
                },
                "class_type": "CLIPTextEncode"
            },
            "8": {
                "inputs": {
                    "samples": ["3", 0],
                    "vae": ["4", 2]
                },
                "class_type": "VAEDecode"
            },
            "9": {
                "inputs": {
                    "filename_prefix": "ComfyUI",
                    "images": ["8", 0]
                },
                "class_type": "SaveImage"
            }
        }
        return workflow



    def generate_image_with_comfyui_sync(self, prompt: str, user_id: str, negative_prompt: str = "") -> Dict[str, Any]:
        """Senkron ComfyUI görüntü üretimi - düzeltilmiş WebSocket handling"""
        session = self.get_or_create_session(user_id)
        request_id = f"{user_id}_{int(time.time())}_{hash(prompt[:50]) % 10000}"

        print(f"🎨 Starting image generation: {prompt}")
        
        allowed, limit_msg = self.rate_limiter.is_allowed(user_id)
        if not allowed:
            return {"error": f"Rate limit: {limit_msg}", "request_id": request_id, "success": False}

        if not self.is_comfyui_running():
            print("❌ ComfyUI not running")
            return {"error": "ComfyUI servisi çalışmıyor", "request_id": request_id, "success": False}

        print("✅ ComfyUI is running, starting generation...")
        start_time = time.time()

        try:
            print("🔧 Creating workflow...")
            workflow = self.create_basic_workflow(prompt, negative_prompt)
            print(f"📋 Workflow created: {len(workflow)} nodes")
            
            print("🎯 Starting image generation...")
            
            # Prompt gönder
            prompt_result = self.comfy_api.queue_prompt(workflow)
            prompt_id = prompt_result['prompt_id']
            print(f"📨 Prompt queued with ID: {prompt_id}")
            
            # WebSocket bağlantısı kur
            print("📡 Creating WebSocket connection...")
            client_id = str(uuid.uuid4())
            ws_url = f"ws://127.0.0.1:8188/ws?clientId={client_id}"
            
            ws = None
            generation_completed = False
            timeout_seconds = 240  # 4 dakika timeout
            polling_timeout = 120
            start_wait = time.time()
            last_progress_time = time.time()
            
            try:
                # WebSocket bağlantısı
                ws = websocket.create_connection(ws_url, timeout=15)
                print(f"✅ WebSocket connected with client_id: {client_id}")
                
                # İlk progress durumunu kontrol et
                progress_check_count = 0
                
                while not generation_completed:
                    current_time = time.time()
                    
                    # Global timeout kontrolü
                    if current_time - start_wait > timeout_seconds:
                        print(f"⏰ Global timeout after {timeout_seconds} seconds")
                        break
                    
                    # Progress timeout kontrolü (30 saniye progress yoksa)
                    if current_time - last_progress_time > 45:
                        print("⏰ No progress for 45 seconds, checking queue status...")
                        queue_status = self.comfy_api.get_queue_status()
                        print(f"📊 Queue status: {len(queue_status.get('queue_running', []))} running, {len(queue_status.get('queue_pending', []))} pending")
                        last_progress_time = current_time
                    
                    try:
                        # WebSocket mesajını al (kısa timeout)
                        ws.settimeout(2.0)
                        message = ws.recv()
                        
                        if isinstance(message, str):
                            try:
                                data = json.loads(message)
                                msg_type = data.get('type', 'unknown')
                                print(f"📨 Received: {msg_type}")
                                
                                # Progress güncellemesi
                                last_progress_time = current_time
                                
                                if msg_type == 'executing':
                                    node_info = data.get('data', {})
                                    current_node = node_info.get('node')
                                    msg_prompt_id = node_info.get('prompt_id')
                                    
                                    if current_node is None and msg_prompt_id == prompt_id:
                                        print("✅ Generation completed!")
                                        generation_completed = True
                                        break
                                    elif current_node:
                                        print(f"🔄 Processing node: {current_node}")
                                
                                elif msg_type == 'progress':
                                    progress_data = data.get('data', {})
                                    value = progress_data.get('value', 0)
                                    max_val = progress_data.get('max', 100)
                                    percentage = (value / max_val * 100) if max_val > 0 else 0
                                    print(f"📈 Progress: {percentage:.1f}% ({value}/{max_val})")
                                
                                elif msg_type == 'execution_error':
                                    print(f"❌ Execution error: {data}")
                                    return {"error": "ComfyUI execution error", "request_id": request_id, "success": False}
                                
                                elif msg_type == 'status':
                                    status_data = data.get('data', {})
                                    exec_info = status_data.get('status', {}).get('exec_info', {})
                                    queue_remaining = exec_info.get('queue_remaining', 0)
                                    if queue_remaining > 0:
                                        print(f"⏳ Queue position: {queue_remaining}")
                            
                            except json.JSONDecodeError:
                                print(f"⚠️ Invalid JSON message: {message[:100]}")
                                continue
                                
                    except websocket._exceptions.WebSocketTimeoutException:
                        # Timeout normal, döngüye devam et
                        progress_check_count += 1
                        if progress_check_count % 15 == 0:  # Her 30 saniyede bir
                            print(f"⏳ Still waiting... ({progress_check_count * 2}s)")
                        continue
                        
                    except Exception as ws_error:
                        print(f"❌ WebSocket error: {ws_error}")
                        # WebSocket hatası olursa polling ile devam et
                        break
                
            finally:
                if ws:
                    try:
                        ws.close()
                        print("📡 WebSocket connection closed")
                    except:
                        pass
            
            # Generation tamamlanmadıysa polling ile kontrol et
            if not generation_completed:
                print("🔄 WebSocket failed, switching to polling method...")
                polling_timeout = 60  # 1 dakika daha bekle
                polling_start = time.time()
                
                while time.time() - polling_start < polling_timeout:
                    try:
                        history = self.comfy_api.get_history(prompt_id)
                        if prompt_id in history:
                            print("✅ Generation found in history!")
                            generation_completed = True
                            break
                    except Exception as e:
                        print(f"⚠️ Polling error: {e}")
                    
                    time.sleep(3)  # 3 saniye bekle
                    print("🔄 Polling for completion...")
            
            if not generation_completed:
                print("❌ Generation timeout - could not complete")
                return {"error": "Görüntü üretimi tamamlanamadı", "request_id": request_id, "success": False}
            
            # History'den sonuçları al
            print(f"📚 Fetching results for prompt_id: {prompt_id}")
            history = self.comfy_api.get_history(prompt_id)
            
            if prompt_id not in history:
                print("❌ Prompt ID not found in history")
                return {"error": "Görüntü sonuçları bulunamadı", "request_id": request_id, "success": False}
            
            output_images = {}
            prompt_history = history[prompt_id]
            print(f"📋 History outputs: {list(prompt_history.get('outputs', {}).keys())}")
            
            for node_id in prompt_history['outputs']:
                node_output = prompt_history['outputs'][node_id]
                print(f"🔍 Checking node {node_id}: {list(node_output.keys())}")
                
                if 'images' in node_output:
                    images_output = []
                    for i, image in enumerate(node_output['images']):
                        print(f"📷 Fetching image {i+1}: {image['filename']}")
                        image_data = self.comfy_api.get_image(image['filename'], image['subfolder'], image['type'])
                        images_output.append(image_data)
                    output_images[node_id] = images_output
            
            print(f"📷 Received {len(output_images)} image sets")
            
            if not output_images:
                print("❌ No images in output")
                return {"error": "Görüntü üretilemedi", "request_id": request_id, "success": False}
            
            # İlk görüntüyü al
            image_data = list(output_images.values())[0][0]
            print(f"💾 Image data size: {len(image_data)} bytes")
            
            # Static dizin yolunu belirle
            try:
                from flask import current_app
                app_root = current_app.root_path
                static_dir = os.path.join(app_root, "static", "generated_images")
            except RuntimeError:
                current_dir = os.getcwd()
                static_dir = os.path.join(current_dir, "static", "generated_images")
            
            os.makedirs(static_dir, exist_ok=True)
            print(f"📁 Static directory: {static_dir}")
            
            # Dosya adı ve tam yolu
            filename = f"{request_id}.png"
            image_path = os.path.join(static_dir, filename)
            
            # Görüntüyü dosyaya kaydet
            with open(image_path, "wb") as f:
                f.write(image_data)
            print(f"💾 Image saved to: {image_path}")
            
            # URL oluştur
            image_url = f"/static/generated_images/{filename}"
            print(f"🔗 Image URL: {image_url}")
            
            # Dosya kontrolü
            if not os.path.exists(image_path):
                print(f"❌ File was not created: {image_path}")
                return {"error": "Görüntü dosyası kaydedilemedi", "request_id": request_id, "success": False}
                
            file_size = os.path.getsize(image_path)
            print(f"📏 File size on disk: {file_size} bytes")
            
            if file_size == 0:
                print("❌ Created file is empty")
                return {"error": "Boş görüntü dosyası oluşturuldu", "request_id": request_id, "success": False}
            
            # Base64 encode
            image_base64 = base64.b64encode(image_data).decode("utf-8")
            data_url = f"data:image/png;base64,{image_base64}"
            
            response_time = time.time() - start_time
            session.add_context(prompt, f"[Görüntü üretildi: {image_path}]", "stable-diffusion-v1.5")
            session.request_count += 1
            
            self.stats["total_requests"] += 1
            self.stats["successful_requests"] += 1
            self.stats["model_usage"]["stable-diffusion-v1.5"] += 1
            
            result = {
                "success": True,
                "image_path": image_path,
                "image_url": image_url,
                "image_base64": data_url,
                "model": "stable-diffusion-v1.5",
                "request_id": request_id,
                "response_time": response_time,
                "session_id": session.session_id,
                "prompt_used": prompt,
                "negative_prompt": negative_prompt,
                "file_size": file_size
            }
            
            print(f"✅ Image generation completed successfully in {response_time:.2f}s")
            print(f"📋 Result summary: {filename} ({file_size} bytes) -> {image_url}")
            return result

        except Exception as e:
            print(f"❌ Image generation error: {e}")
            import traceback
            traceback.print_exc()
            logger.error(f"ComfyUI image generation error: {e}", exc_info=True)
            return {"error": f"Görüntü üretimi hatası: {str(e)}", "request_id": request_id, "success": False}

    def chat_with_external_apis(self, model_name: str, prompt: str, user_id: str = "anonymous",
                                system_prompt: str = None, use_context: bool = True, 
                                auto_select_model: bool = False, enable_apis: bool = True) -> Dict[str, Any]:
        """
        External API desteği eklenmiş chat metodu
        
        Args:
            enable_apis: External API'leri kullan/kullanma
        """
        # API enhancement
        api_data = None
        final_prompt = prompt
        
        if enable_apis:
            from ai_external_api_agent import enhance_ai_prompt_with_apis
            api_enhancement = enhance_ai_prompt_with_apis(prompt)
            
            if api_enhancement.get('api_used'):
                final_prompt = api_enhancement.get('enhanced_prompt', prompt)
                api_data = api_enhancement
                logger.info(f"External API used: {api_enhancement['intent_data']['primary_intent']}")
        
        # Normal chat işlemi
        result = self.chat_with_model(
            model_name=model_name,
            prompt=final_prompt,
            user_id=user_id,
            system_prompt=system_prompt,
            use_context=use_context,
            auto_select_model=auto_select_model
        )
        
        # API metadata ekle
        if api_data:
            result['external_api'] = {
                'used': True,
                'type': api_data['intent_data']['primary_intent'],
                'success': api_data.get('api_success', False)
            }
        
        return result

    def _run_async_in_thread(self, coro):
        """Asyncio coroutine'ini thread'de çalıştır"""
        def thread_target():
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    return loop.run_until_complete(coro)
                finally:
                    loop.close()
            except Exception as e:
                logger.error(f"Async thread error: {e}")
                return {"error": f"Async execution error: {str(e)}"}

        future = self.executor.submit(thread_target)
        return future.result(timeout=300) 

    def _call_lora_api(self, prompt: str, user_id: str, system_prompt: str = None, use_context: bool = True):
        """LoRA API çağrısı"""
        try:
            session = self.get_or_create_session(user_id)
            
            if not system_prompt:
                system_prompt = "Sen Türkçe konuşan yardımsever bir asistansın."
            
            context_str = ""
            if use_context:
                context_str = session.get_context_string(max_messages=3)
            
            final_prompt = f"{context_str}\n\n{prompt}" if context_str else prompt
            
            payload = {
                "prompt": final_prompt,
                "system": system_prompt
            }
            
            start_time = time.time()
            
            # DEBUG: Log ekleyin
            print(f"🔗 Calling LoRA API: http://localhost:5005/generate")
            print(f"📝 Payload: {payload}")
            
            response = requests.post(
                "http://localhost:5005/generate",
                json=payload,
                timeout=300
            )
            
            print(f"📥 LoRA API response status: {response.status_code}")
            
            response_time = time.time() - start_time
            
            if response.status_code == 200:
                data = response.json()
                response_text = data.get("response", "")
                
                session.add_context(prompt, response_text, "qwen2.5-lora")
                session.request_count += 1
                
                self.stats["total_requests"] += 1
                self.stats["successful_requests"] += 1
                self.stats["model_usage"]["qwen2.5-lora"] += 1
                
                return {
                    "success": True,
                    "response": response_text,
                    "model": "qwen2.5-lora",
                    "request_id": f"lora_{int(time.time())}_{user_id[:8]}",
                    "response_time": response_time,
                    "session_id": session.session_id
                }
            else:
                error_text = response.text
                print(f"❌ LoRA API error: {error_text}")
                return {
                    "error": f"LoRA API hata: {response.status_code} - {error_text}",
                    "request_id": f"lora_err_{int(time.time())}"
                }
                
        except requests.exceptions.ConnectionError as e:
            print(f"❌ LoRA API connection error: {e}")
            return {"error": "LoRA API bağlanamadı - servis çalışıyor mu?", "request_id": "lora_conn_err"}
        except Exception as e:
            print(f"❌ LoRA API general error: {e}")
            return {"error": f"LoRA API hatası: {str(e)}", "request_id": "lora_err"}

    def chat_with_model(self, model_name: str, prompt: str, user_id: str = "anonymous",
                        system_prompt: str = None, use_context: bool = True, 
                        auto_select_model: bool = False) -> Dict[str, Any]:
        """Ana chat metodu - akıllı yönlendirme ile"""

        # Model seçimi
        if auto_select_model or model_name == "auto":
            session = self.get_or_create_session(user_id)
            context_length = len(session.get_context_string())
            selected_model = self.model_selector.select_model(prompt, session.preferred_model, context_length)
            
            # ⚽ FUTBOL TAHMİNİ SPESİFİK KONTROLÜ
            if selected_model == "football-prediction":
                print("🔀 Routing to football prediction system...")
                return self.predict_football_match(
                    team1=self._extract_team_names(prompt)[0],
                    team2=self._extract_team_names(prompt)[1],
                    user_id=user_id
                )
            
            model_name = selected_model
            print(f"🎯 Auto-selected model: {model_name}")

        # ✅ LoRA kontrolü
        if model_name == "qwen2.5-lora":
            print(f"🔗 Routing to LoRA API")
            return self._call_lora_api(prompt, user_id, system_prompt, use_context)
        
        # Stable Diffusion kontrolü
        if model_name == "stable-diffusion-v1.5":
            return self.generate_image_with_comfyui_sync(prompt, user_id)
        
        # Ollama modelleri için
        endpoint = self.load_balancer.get_best_endpoint(model_name)
        if not self.is_ollama_running(endpoint):
            return {"error": f"Ollama servisi çalışmıyor: {endpoint}"}
            
        available_models = self.get_available_models(endpoint)
        if model_name not in available_models:
            return {"error": f"Model '{model_name}' bulunamadı. Mevcut: {available_models}"}
        
        # Async chat'i thread'de çalıştır
        coro = self.async_chat_with_model(model_name, prompt, user_id, system_prompt, use_context)
        return self._run_async_in_thread(coro)

    def _extract_team_names(self, prompt: str) -> Tuple[str, str]:
        """Prompt'tan takım isimlerini çıkar"""
        vs_pattern = r'([\w\sığüşöçĞÜŞÖÇİ]+)\s+(?:vs|versus|-|ile)\s+([\w\sığüşöçĞÜŞÖÇİ]+)'
        match = re.search(vs_pattern, prompt, re.IGNORECASE)
        
        if match:
            team1 = match.group(1).strip()
            team2 = match.group(2).strip()
            # "maç", "analiz" gibi kelimeleri temizle
            team1 = re.sub(r'\b(maç|match|analiz|analyze|tahmin|predict)\b', '', team1, flags=re.IGNORECASE).strip()
            team2 = re.sub(r'\b(maç|match|analiz|analyze|tahmin|predict)\b', '', team2, flags=re.IGNORECASE).strip()
            return (team1, team2)
        
        return ("", "")


    def detect_user_language(self, prompt: str) -> str:
            """Kullanıcının prompt dilini algıla"""
            prompt_lower = prompt.lower()
            
            # Türkçe belirteçler
            turkish_chars = any(char in prompt for char in 'çğıöşüÇĞIÖŞÜ')
            turkish_words = any(word in prompt_lower for word in [
                'merhaba', 'selam', 'nasılsın', 'naber', 'teşekkür', 'lütfen',
                'bir', 'bu', 'şu', 'ile', 'için', 'değil', 'oldu', 'yapabilir',
                'nedir', 'nasıl', 'hangi', 'kimdir', 'nerede', 'ne zaman',
                'kodla', 'yap', 'oluştur', 'anlatır', 'misin', 'bilir'
            ])
            
            if turkish_chars or turkish_words:
                return 'tr'
            else:
                return 'en'

    def _is_chinese_response(self, text: str) -> bool:
        """Chinese/Vietnamese/Foreign language response detection - geliştirilmiş"""
        if not text or len(text) < 10:
            return False
        
        # Çince karakterler
        chinese_chars = sum(1 for char in text if '\u4e00' <= char <= '\u9fff')
        
        # Vietnamca özel karakterler  
        vietnamese_chars = sum(1 for char in text if char in 'ăâđêôơưàáạảãèéẹẻẽìíịỉĩòóọỏõùúụủũỳýỵỷỹ')
        
        total_chars = len(text)
        chinese_ratio = chinese_chars / total_chars if total_chars > 0 else 0
        vietnamese_ratio = vietnamese_chars / total_chars if total_chars > 0 else 0
        
        # Türkçe karakterleri kontrol et
        turkish_chars = sum(1 for char in text if char in 'çğıöşüÇĞIÖŞÜ')
        
        # Eğer Türkçe karakter varsa daha toleranslı ol
        if turkish_chars > 0:
            threshold = 0.15  # %15'e kadar izin ver
        else:
            threshold = 0.05  # %5'e kadar izin ver
        
        if chinese_ratio > threshold or vietnamese_ratio > threshold:
            logger.warning(f"Foreign characters detected: Chinese {chinese_ratio:.3f}, Vietnamese {vietnamese_ratio:.3f}")
            return True
        
        # Yasak yabancı kelimeler (aynı)
        forbidden_words = [
            'tương', 'tác', 'với', 'trong', 'nhiều', 'lĩnh', 'vực', 'khác', 'nhau', 
            'của', 'cho', 'và', 'một', 'các', 'này', 'đó', 'được', 'có', 'là', 'hỗ', 'trợ',
            '用户', '问题', '人类', '中国', '可以', '如果', '这个', '那个', '什么', '怎么',
            '我们', '他们', '什么', '怎么样', '非常', '很好', '谢谢', '不客气'
        ]
        
        text_lower = text.lower()
        for word in forbidden_words:
            if word in text_lower:
                logger.warning(f"Forbidden foreign word detected: {word}")
                return True
        
        return False

    async def async_chat_with_model(self, model_name: str, prompt: str, user_id: str, 
                                    system_prompt: str = None, use_context: bool = True) -> Dict[str, Any]:
        # 🔗 Eğer LoRA seçilmişse doğrudan API'ye yönlendir
        if model_name == "qwen2.5-lora":
            return self._call_lora_api(prompt, user_id, system_prompt, use_context)


        # 🎨 Stable Diffusion için ComfyUI'ye yönlendir
        if model_name == "stable-diffusion-v1.5":
            # async fonksiyondan sync fonksiyonu çağırmak için executor kullan
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(
                None, 
                self.generate_image_with_comfyui_sync,
                prompt, user_id, ""
            )

        session = self.get_or_create_session(user_id)
        request_id = f"{user_id}_{int(time.time())}_{hash(prompt[:50]) % 10000}"
        
        allowed, limit_msg = self.rate_limiter.is_allowed(user_id)
        if not allowed:
            return {"error": f"Rate limit: {limit_msg}", "request_id": request_id}
            
        if not self.load_balancer.can_process_request(model_name):
            return {"error": "Sistem yoğun, lütfen bekleyin", "request_id": request_id}
            
        endpoint = self.load_balancer.get_best_endpoint(model_name)
        
        # Kullanıcının dilini algıla
        user_language = self.detect_user_language(prompt)
        
        if not system_prompt:
            if user_language == 'tr':
                base_system = (
                    "Sen Türkçe konuşan bir asistansın. "
                    "Türkçe yanıt ver, sadece gerekli durumlarda teknik terimler veya özel isimler İngilizce olabilir. "
                    "Asla Çince, Vietnamca, Arapça gibi diğer dillerde yanıt verme. "
                    "Açık, net ve anlaşılır Türkçe kullan. "
                )
            else:
                base_system = (
                    "You are an English-speaking assistant. "
                    "ONLY respond in English, NEVER respond in any other language. "
                    "Even if asked in another language, respond in English. "
                    "Be clear, concise and direct in your responses. "
                )
            
            if "qwen" in model_name.lower():
                if user_language == 'tr':
                    system_prompt = base_system + (
                        "Konu dışına çıkma, gereksiz cümle kurma. "
                        "Markdown formatı kullanabilirsin. "
                        "İngilizce teknik terimler (Python, API, GitHub gibi) kullanabilirsin. "
                    )
                else:
                    system_prompt = base_system + (
                        "Stay on topic, don't add unnecessary sentences. "
                        "You can use Markdown format."
                    )
            elif "coder" in model_name.lower() or "deepseek" in model_name.lower():
                if user_language == 'tr':
                    system_prompt = (
                        "Sen Türkçe konuşan bir yazılım uzmanısın. "
                        "Açıklamaları Türkçe yap ama programlama dilleri, framework isimleri, "
                        "teknik terimler İngilizce olarak kullanılabilir (Python, JavaScript, API, etc.). "
                        "Kodları ``` blokları içinde yaz. "
                        "Çalışan örnekler ver. "
                        "Asla Çince, Vietnamca veya başka dillerde açıklama yapma. "
                    )
                else:
                    system_prompt = base_system + (
                        "You are a software and programming expert. "
                        "Always write code in ``` language blocks. "
                        "Provide working examples. "
                        "Explain in English, but keep code syntax correct."
                    )
            else:
                if user_language == 'tr':
                    system_prompt = base_system + (
                        "Yanıtlarını kısa, net ve konuya odaklı tut. "
                        "Gerektiğinde İngilizce teknik terimler kullanabilirsin. "
                    )
                else:
                    system_prompt = base_system + (
                        "Keep your responses short, clear and focused."
                    )

        context_str = session.get_context_string(max_messages=5) if use_context else ""
        enhanced_prompt = f"{context_str}\n\nYeni soru: {prompt}" if context_str else prompt
            
        model_options = {
            "temperature": 0.7,
            "top_p": 0.9,
            "repeat_penalty": 1.1,
            "num_predict": 600,
            "stop": ["<|im_end|>", "</s>", "<|end|>", "User:", "Human:", "用户:", "人类:"]
        }
        
        if "coder" in model_name.lower() or "deepseek" in model_name.lower():
            model_options.update({
                "temperature": 0.3,
                "top_p": 0.95,
                "num_predict": 1200
            })
            
        payload = {
            "model": model_name,
            "prompt": enhanced_prompt,
            "system": system_prompt,
            "stream": False,
            "options": model_options
        }
        
        start_time = time.time()
        
        try:
            self.load_balancer.acquire_slot(model_name)
            self.rate_limiter.add_request(user_id)
            
            async with aiohttp.ClientSession() as http_session:
                async with http_session.post(
                    f"{endpoint}/api/generate",
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=180)
                ) as response:
                    response_time = time.time() - start_time

                    response_text = await response.text()
                    content_type = response.headers.get("Content-Type", "")

                    if response.status == 200 and "application/json" in content_type:
                        try:
                            data = json.loads(response_text)
                        except json.JSONDecodeError as e:
                            logger.error(f"JSON parse hatası: {e}, Yanıt: {response_text[:200]}")
                            return {"error": "Ollama yanıtı JSON formatında değil", "request_id": request_id}

                        response_text_clean = data.get("response", "").strip()
                        if not response_text_clean:
                            return {"error": "Model boş yanıt döndürdü", "request_id": request_id}

                        # Çince karakterler varsa uyarı ver ve reddet
                        if self._is_chinese_response(response_text_clean):
                            logger.warning(f"Çince/Vietnamca yanıt algılandı ve reddedildi: {response_text_clean[:100]}")


                        # Session update + stats işlemleri
                        session.add_context(prompt, response_text_clean, model_name)
                        session.request_count += 1
                        session.avg_response_time = (session.avg_response_time * 0.8) + (response_time * 0.2)

                        self.stats["total_requests"] += 1
                        self.stats["successful_requests"] += 1
                        self.stats["model_usage"][model_name] += 1
                        self.stats["avg_response_time"] = (self.stats["avg_response_time"] * 0.9) + (response_time * 0.1)

                        self.model_selector.update_performance(model_name, response_time, True)

                        return {
                            "success": True,
                            "response": response_text_clean,
                            "model": model_name,
                            "request_id": request_id,
                            "response_time": response_time,
                            "total_duration": data.get("total_duration", 0),
                            "eval_count": data.get("eval_count", 0),
                            "session_id": session.session_id,
                            "detected_language": user_language
                        }

                    else:
                        logger.error(f"Ollama geçersiz içerik döndürdü ({content_type}): {response_text[:200]}")
                        return {"error": f"Ollama geçersiz içerik döndürdü: {response.status}", "request_id": request_id}

        except asyncio.TimeoutError:
            self.model_selector.update_performance(model_name, 90.0, False)
            return {"error": "İstek zaman aşımına uğradı", "request_id": request_id}
        except Exception as e:
            self.model_selector.update_performance(model_name, 0.0, False)
            logger.error(f"Chat error: {e}")
            return {"error": f"Beklenmeyen hata: {str(e)}", "request_id": request_id}
        finally:
            self.load_balancer.release_slot(model_name)



    def detect_task_request(self, prompt: str) -> bool:
        task_indicators = [
            'yap', 'oluştur', 'kodla', 'hesapla', 'analiz et', 'bul',
            'listele', 'kaydet', 'oku', 'indir', 'çek', 'parse et',
            'temizle', 'dönüştür', 'organize et', 'sırala', 'filtrele',
            'make', 'create', 'code', 'calculate', 'analyze', 'find',
            'list', 'save', 'read', 'download', 'scrape', 'parse',
            'clean', 'convert', 'organize', 'sort', 'filter'
        ]
        execution_indicators = [
            'çalıştır', 'execute', 'run', 'perform', 'do this',
            'bu kodu çalıştır', 'şunu yap', 'gerçekleştir'
        ]
        prompt_lower = prompt.lower()
        all_indicators = task_indicators + execution_indicators
        has_task_indicator = any(indicator in prompt_lower for indicator in all_indicators)
        has_code_block = '```' in prompt or 'def ' in prompt or 'function' in prompt
        return has_task_indicator or has_code_block

    def extract_code_from_response(self, response: str) -> List[Dict[str, str]]:
        codes = []
        pattern = r'```(\w+)?\n(.*?)```'
        matches = re.findall(pattern, response, re.DOTALL)
        for language, code in matches:
            codes.append({
                'language': language.lower() if language else 'python',
                'code': code.strip()
            })
        return codes

    def chat_with_code_execution(self, model_name: str, prompt: str, user_id: str = "anonymous",
                               system_prompt: str = None, use_context: bool = True,
                               auto_execute: bool = True) -> Dict[str, Any]:
        """Kod çalıştırma özellikli chat - thread safe"""
        chat_result = self.chat_with_model(model_name, prompt, user_id, system_prompt, use_context)
        if "error" in chat_result:
            return chat_result
        
        response_text = chat_result.get("response", "")
        if auto_execute and (self.detect_task_request(prompt) or '```' in response_text):
            extracted_codes = self.extract_code_from_response(response_text)
            if extracted_codes:
                execution_results = []
                for code_block in extracted_codes:
                    exec_result = self.code_agent.execute_code(code_block['code'], code_block['language'])
                    execution_results.append({
                        'language': code_block['language'],
                        'code': code_block['code'],
                        'result': exec_result
                    })
                chat_result['code_executions'] = execution_results
                chat_result['has_code_execution'] = True
                execution_summary = self._format_execution_summary(execution_results)
                chat_result['response'] += f"\n\n{execution_summary}"
        
        return chat_result

    def _format_execution_summary(self, execution_results: List[Dict]) -> str:
        summary = "🚀 **Kod Çalıştırma Sonuçları:**\n"
        for i, result in enumerate(execution_results, 1):
            lang = result['language']
            exec_result = result['result']
            summary += f"\n**{i}. {lang.upper()} Kodu:**\n"
            if exec_result.get('success'):
                summary += "✅ **Başarılı**\n"
                if exec_result.get('stdout'):
                    summary += f"```\n{exec_result['stdout']}\n```\n"
                summary += f"⏱️ Süre: {exec_result.get('execution_time', 0):.2f}s\n"
            else:
                summary += "❌ **Hatalı**\n"
                if exec_result.get('stderr'):
                    summary += f"```\n{exec_result['stderr']}\n```\n"
                if 'error' in exec_result:
                    summary += f"Hata: {exec_result['error']}\n"
        return summary

    def get_user_stats(self, user_id: str) -> Dict[str, Any]:
        if user_id not in self.sessions:
            return {"error": "Session bulunamadı"}
        session = self.sessions[user_id]
        return {
            "user_id": user_id,
            "session_id": session.session_id,
            "created_at": session.created_at,
            "last_activity": session.last_activity,
            "request_count": session.request_count,
            "context_messages": len(session.context_history),
            "preferred_model": session.preferred_model,
            "avg_response_time": session.avg_response_time,
            "error_count": session.error_count
        }

    def get_system_stats(self) -> Dict[str, Any]:
        active_sessions = sum(1 for s in self.sessions.values() if s.is_active())
        all_models = []
        
        # Ollama modelleri
        for gpu_type, config in GPU_MODEL_ROUTING.items():
            if gpu_type == "primary":
                endpoint = config["endpoint"]
                if self.is_ollama_running(endpoint):
                    models = self.get_available_models(endpoint)
                    all_models.extend(models)
        
        # Stable Diffusion modeli
        if self.is_comfyui_running():
            all_models.append("stable-diffusion-v1.5")
        
        all_models = list(set(all_models))
        
        return {
            "total_requests": self.stats["total_requests"],
            "successful_requests": self.stats["successful_requests"],
            "failed_requests": self.stats["failed_requests"],
            "success_rate": self.stats["successful_requests"] / max(1, self.stats["total_requests"]),
            "avg_response_time": self.stats["avg_response_time"],
            "active_sessions": active_sessions,
            "total_sessions": len(self.sessions),
            "model_usage": dict(self.stats["model_usage"]),
            "available_models": all_models,
            "load_balancer_status": dict(self.load_balancer.active_requests),
            "comfyui_status": "running" if self.is_comfyui_running() else "offline"
        }

    def set_user_model_preference(self, user_id: str, model_name: str) -> bool:
        session = self.get_or_create_session(user_id)
        if model_name in OLLAMA_MODELS or model_name == "auto":
            session.preferred_model = model_name
            return True
        return False

    def get_code_agent_stats(self) -> Dict[str, Any]:
        return self.code_agent.get_stats()

    def cleanup_code_agent(self):
        pass  # Cleanup işlemleri gerekirse burada yapılır



# Football Prediction Integration
class FootballPredictionAgent:
    """API-Football entegrasyonu - sadece analiz, kesin tahmin YOK"""
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv('FOOTBALL_API_KEY', '')
        self.base_url = "https://v3.football.api-sports.io"
        self.headers = {
            'x-rapidapi-key': self.api_key,
            'x-rapidapi-host': 'v3.football.api-sports.io'
        }
        self.enabled = bool(self.api_key)
        
    def search_team(self, team_name: str) -> Optional[int]:
        """Takım adından ID bul"""
        if not self.enabled:
            return None
        try:
            response = requests.get(
                f"{self.base_url}/teams",
                headers=self.headers,
                params={"search": team_name},
                timeout=10
            )
            if response.status_code == 200:
                data = response.json()
                if data.get("response") and len(data["response"]) > 0:
                    return data["response"][0]["team"]["id"]
        except Exception as e:
            logger.error(f"Team search error: {e}")
        return None
    
    def get_team_statistics(self, team_id: int, league_id: int = 203, season: int = 2024) -> Dict:
        """Takım istatistikleri"""
        if not self.enabled:
            return {}
        try:
            response = requests.get(
                f"{self.base_url}/teams/statistics",
                headers=self.headers,
                params={"team": team_id, "league": league_id, "season": season},
                timeout=10
            )
            return response.json() if response.status_code == 200 else {}
        except Exception as e:
            logger.error(f"Statistics error: {e}")
            return {}
    
    def analyze_match(self, team1: str, team2: str, league_id: int = 203) -> str:
        """Maç analizi için prompt oluştur"""
        if not self.enabled:
            return f"⚽ Futbol API entegrasyonu aktif değil.\n\nGenel analiz: {team1} vs {team2} maçı için istatistik tabanlı bir değerlendirme yapamıyorum."
        
        team1_id = self.search_team(team1)
        team2_id = self.search_team(team2)
        
        if not team1_id or not team2_id:
            return f"❌ Takımlar bulunamadı: {team1}, {team2}"
        
        stats1 = self.get_team_statistics(team1_id, league_id)
        stats2 = self.get_team_statistics(team2_id, league_id)
        
        # İstatistiklerden özet çıkar
        def extract_stats(stats_data):
            if not stats_data.get("response"):
                return "Veri yok"
            r = stats_data["response"]
            fixtures = r.get("fixtures", {})
            goals = r.get("goals", {})
            return f"""
- Maç: {fixtures.get('played', {}).get('total', 0)}
- Galibiyet: {fixtures.get('wins', {}).get('total', 0)}
- Gol: {goals.get('for', {}).get('total', {}).get('total', 0)} / Yenilen: {goals.get('against', {}).get('total', {}).get('total', 0)}
"""
        
        prompt = f"""⚽ **Maç Analizi: {team1} vs {team2}**

📊 **İstatistikler:**

{team1}:
{extract_stats(stats1)}

{team2}:
{extract_stats(stats2)}

**Lütfen şu konularda objektif bir analiz yap:**
1. Her iki takımın güçlü/zayıf yönleri
2. İstatistiksel karşılaştırma
3. Olası senaryo değerlendirmesi

⚠️ **ÖNEMLİ:** Kesin tahmin YOK, sadece istatistiksel değerlendirme yap. Futbolda sürprizler olur."""

        return prompt

# MultiUserOllamaRunner sınıfına eklenecek metod
def predict_football_match(self, team1: str, team2: str, user_id: str = "football_user") -> Dict[str, Any]:
    """Football match prediction"""
    try:
        if not hasattr(self, 'football_agent'):
            self.football_agent = FootballPredictionAgent()
        
        analysis_prompt = self.football_agent.analyze_match(team1, team2)
        
        result = self.chat_with_model(
            model_name="qwen2.5:14b-instruct",
            prompt=analysis_prompt,
            user_id=user_id,
            system_prompt="Sen futbol istatistik analistisin. Sadece verilere dayalı objektif değerlendirme yaparsın, KESİN TAHMİN VERMEZSİN.",
            auto_select_model=False
        )
        
        if "error" in result:
            return result
        
        disclaimer = "\n\n⚠️ **UYARI:** Bu bir istatistiksel analiz, kesin tahmin DEĞİLDİR. Bahis/kumar amaçlı kullanmayın."
        
        return {
            "success": True,
            "analysis": result.get("response", "") + disclaimer,
            "model": result.get("model"),
            "response_time": result.get("response_time")
        }
        
    except Exception as e:
        logger.error(f"Football prediction error: {e}")
        return {"error": str(e)}

# Global instance'dan ÖNCE bu metodu ekle
MultiUserOllamaRunner.predict_football_match = predict_football_match

# Global instance (değişmeden)
multi_user_ollama = MultiUserOllamaRunner()
multi_user_ollama.football_agent = FootballPredictionAgent()

# Backward compatibility functions
def send_prompt(model_name: str, prompt: str, context: str = "", user_id: str = "legacy_user") -> str:
    result = multi_user_ollama.chat_with_model(
        model_name=model_name,
        prompt=prompt,
        user_id=user_id,
        use_context=bool(context),
        auto_select_model=(model_name == "auto")
    )
    return result.get("response", f"❌ Hata: {result.get('error', 'Yanıt alınamadı')}")

def send_prompt_with_execution(model_name: str, prompt: str, context: str = "", 
                             user_id: str = "legacy_user", auto_execute: bool = True) -> str:
    result = multi_user_ollama.chat_with_code_execution(
        model_name=model_name,
        prompt=prompt,
        user_id=user_id,
        use_context=bool(context),
        auto_execute=auto_execute
    )
    return result.get("response", f"❌ Hata: {result.get('error', 'Yanıt alınamadı')}")

def start_model(model_name: str):
    endpoint = multi_user_ollama.load_balancer.get_best_endpoint(model_name)
    if model_name == "stable-diffusion-v1.5":
        if not multi_user_ollama.is_comfyui_running():
            raise RuntimeError("ComfyUI servisi çalışmıyor")
        print(f"Model '{model_name}' hazır - ComfyUI: http://localhost:8188")
    else:
        if not multi_user_ollama.is_ollama_running(endpoint):
            raise RuntimeError(f"Ollama servisi çalışmıyor: {endpoint}")
        available_models = multi_user_ollama.get_available_models(endpoint)
        if model_name not in available_models:
            raise ValueError(f"Model '{model_name}' bulunamadı")
        print(f"Model '{model_name}' hazır - Endpoint: {endpoint}")



if __name__ == "__main__":
    print("🚀 Enhanced Multi-User Ollama Runner başlatılıyor...")
    
    # Sistem kontrolü
    print(f"\n📊 Sistem Durumu:")
    try:
        stats = multi_user_ollama.get_system_stats()
        print(f"  Mevcut modeller: {stats['available_models']}")
        print(f"  ComfyUI durumu: {stats['comfyui_status']}")
        
        if stats['available_models']:
            print("\n✅ System ready!")
        else:
            print("\n❌ Hiçbir model bulunamadı!")
            
    except Exception as e:
        print(f"\n❌ Sistem başlatma hatası: {str(e)}")
    
    print("\nSistem hazır. Programı import ederek kullanabilirsiniz:")
    print("  from multi_user_ollama_runner import multi_user_ollama")
    print("  result = multi_user_ollama.chat_with_model('auto', 'Merhaba')")