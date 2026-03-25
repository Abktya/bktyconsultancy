# ai_chat_blueprint.py
from flask import Blueprint, request, jsonify
from multi_user_ollama_runner import multi_user_ollama
import logging, uuid, time
from datetime import datetime

logger = logging.getLogger(__name__)

ai_chat_bp = Blueprint('ai_chat', __name__)

# --- i18n helpers ---
LANGS = {'tr', 'en'}

def detect_lang(path: str) -> str:
    return 'en' if '/en/' in path else 'tr'

_MESSAGES = {
    'tr': {
        'question_required': 'Soru gereklidir',
        'server_error': 'Sunucu hatası',
        'endpoint_not_found': 'Endpoint bulunamadı',
        'ollama_not_running': 'Ollama servisi çalışmıyor'
    },
    'en': {
        'question_required': 'Question is required',
        'server_error': 'Server error',
        'endpoint_not_found': 'Endpoint not found',
        'ollama_not_running': 'Ollama service is not running'
    }
}
def t(lang: str, key: str) -> str:
    return _MESSAGES.get(lang, _MESSAGES['tr']).get(key, key)

def now_iso() -> str:
    return datetime.utcnow().isoformat(timespec='milliseconds') + 'Z'

# --- routes ---

@ai_chat_bp.route('/<lang>/ask-ai-with-code', methods=['POST'])
def ask_ai_with_code(lang=None):
    """AI ile kod çalıştırma destekli sohbet"""
    try:  # TRY bloğu fonksiyonun başında olmalı
        lang = lang if lang in LANGS else 'tr'
        data = request.get_json(silent=True) or {}

        question = (data.get('question') or '').strip()
        if not question:
            return jsonify({"error": t(lang, 'question_required'), "lang": lang, "timestamp": now_iso()}), 400

        model = data.get('model', 'auto')
        user_id = str(data.get('user_id') or request.remote_addr or 'anonymous')[:64]
        enable_code_execution = bool(data.get('enable_code_execution', True))

        logger.info(f"[{lang}] AI request from {user_id} (model={model}): {question[:80]}...")

        start = time.perf_counter()
        if enable_code_execution:
            result = multi_user_ollama.chat_with_code_execution(
                model_name=model,
                prompt=question,
                user_id=user_id,
                auto_execute=True
            )
        else:
            result = multi_user_ollama.chat_with_model(
                model_name=model,
                prompt=question,
                user_id=user_id,
                auto_select_model=(model == "auto")
            )

        if isinstance(result, dict) and "error" in result:
            logger.error(f"[{lang}] AI error: {result['error']}")
            return jsonify({
                "error": result.get("error", t(lang, 'server_error')),
                "lang": lang,
                "timestamp": now_iso()
            }), 500

        request_id = (result or {}).get("request_id") if isinstance(result, dict) else None
        response_time = (result or {}).get("response_time") if isinstance(result, dict) else None
        request_id = request_id or uuid.uuid4().hex
        response_time = response_time or round((time.perf_counter() - start) * 1000)

        response_text = (result or {}).get("response") if isinstance(result, dict) else None
        response_model = (result or {}).get("model") if isinstance(result, dict) else None
        eval_count = (result or {}).get("eval_count", 0) if isinstance(result, dict) else 0

        response = {
            "choices": [{
                "message": {
                    "content": response_text or ("Yanıt alınamadı" if lang == 'tr' else "No response")
                }
            }],
            "model": response_model or model,
            "usage": {
                "total_tokens": eval_count,
                "completion_tokens": eval_count
            },
            "response_time": response_time,       # ms
            "request_id": request_id,
            "has_code_execution": (result or {}).get("has_code_execution", False) if isinstance(result, dict) else False,
            "code_executions": (result or {}).get("code_executions", []) if isinstance(result, dict) else [],
            "lang": lang,
            "timestamp": now_iso()
        }

        logger.info(f"[{lang}] AI response sent to {user_id} (request_id={request_id}, {response_time}ms)")
        return jsonify(response)

    except Exception as e:  # EXCEPT bloğu try ile aynı seviyede
        logger.error(f"[{detect_lang(request.path)}] AI chat error: {str(e)}", exc_info=True)
        lang = detect_lang(request.path)
        return jsonify({"error": f"{t(lang,'server_error')}: {str(e)}", "lang": lang, "timestamp": now_iso()}), 500


@ai_chat_bp.route('/models', methods=['GET'])
@ai_chat_bp.route('/<lang>/models', methods=['GET'])
def get_models(lang=None):
    """Mevcut modelleri listele"""
    try:
        lang = lang if lang in LANGS else detect_lang(request.path)

        if not multi_user_ollama.is_ollama_running():
            return jsonify({
                "error": t(lang, 'ollama_not_running'),
                "models": [],
                "lang": lang,
                "timestamp": now_iso()
            }), 503

        available_models = multi_user_ollama.get_available_models()

        from multi_user_ollama_runner import OLLAMA_MODELS
        models = []
        for model_name in available_models:
            display_name = OLLAMA_MODELS.get(model_name, model_name)
            models.append({
                "id": model_name,
                "name": display_name,
                "available": True
            })

        models.append({
            "id": "stable-diffusion-2.1",
            "name": "🎨 Stable Diffusion 2.1",
            "available": True
        })

        return jsonify({
            "models": models,
            "total": len(models),
            "lang": lang,
            "timestamp": now_iso()
        })

    except Exception as e:
        logger.error(f"[{detect_lang(request.path)}] Models endpoint error: {str(e)}")
        lang = detect_lang(request.path)
        return jsonify({"error": str(e), "models": [], "lang": lang, "timestamp": now_iso()}), 500


@ai_chat_bp.route('/status', methods=['GET'])
@ai_chat_bp.route('/<lang>/status', methods=['GET'])
def get_status(lang=None):
    """Sistem durumunu kontrol et"""
    try:
        lang = lang if lang in LANGS else detect_lang(request.path)

        ollama_running = multi_user_ollama.is_ollama_running()
        system_stats = multi_user_ollama.get_system_stats() or {}

        return jsonify({
            "status": "running" if ollama_running else "offline",
            "ollama_running": ollama_running,
            "available_models": system_stats.get("available_models", []),
            "total_requests": system_stats.get("total_requests", 0),
            "active_sessions": system_stats.get("active_sessions", 0),
            "success_rate": system_stats.get("success_rate", 0.0),
            "avg_response_time": system_stats.get("avg_response_time", 0.0),
            "lang": lang,
            "timestamp": now_iso()
        })

    except Exception as e:
        logger.error(f"[{detect_lang(request.path)}] Status endpoint error: {str(e)}")
        lang = detect_lang(request.path)
        return jsonify({
            "status": "error",
            "error": str(e),
            "ollama_running": False,
            "lang": lang,
            "timestamp": now_iso()
        }), 500


@ai_chat_bp.route('/health', methods=['GET'])
@ai_chat_bp.route('/<lang>/health', methods=['GET'])
def health_check(lang=None):
    """Basit health check"""
    lang = lang if lang in LANGS else detect_lang(request.path)
    return jsonify({"status": "ok", "service": "ai_chat_blueprint", "lang": lang, "timestamp": now_iso()})


# --- error handlers ---

@ai_chat_bp.errorhandler(404)
def not_found(error):
    lang = detect_lang(request.path)
    return jsonify({"error": t(lang, 'endpoint_not_found'), "lang": lang, "timestamp": now_iso()}), 404

@ai_chat_bp.errorhandler(500)
def internal_error(error):
    lang = detect_lang(request.path)
    return jsonify({"error": t(lang, 'server_error'), "lang": lang, "timestamp": now_iso()}), 500
