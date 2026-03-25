# voice_blueprint.py - Web uyumlu voice chat sistemi
from flask import Blueprint, jsonify, request, send_file
import os
import tempfile
import uuid
import logging
from werkzeug.utils import secure_filename
from faster_whisper import WhisperModel
import pyttsx3
from multi_user_ollama_runner import multi_user_ollama

logger = logging.getLogger(__name__)

voice_bp = Blueprint("voice", __name__)

# Global objects
whisper_model = None
tts_engine = None

def init_voice_system():
    """Voice sistemini başlat"""
    global whisper_model, tts_engine
    
    try:
        if whisper_model is None:
            whisper_model = WhisperModel("small", device="cpu", compute_type="float32")
            logger.info("Whisper model loaded")
        
        if tts_engine is None:
            tts_engine = pyttsx3.init()
            # Türkçe ses ayarla
            voices = tts_engine.getProperty("voices")
            tr_voice = next((v for v in voices if 'tr' in v.id.lower()), None)
            if tr_voice:
                tts_engine.setProperty("voice", tr_voice.id)
            tts_engine.setProperty("rate", 150)
            tts_engine.setProperty("volume", 0.9)
            logger.info("TTS engine initialized")
        
        return True
    except Exception as e:
        logger.error(f"Voice system init error: {e}")
        return False

def transcribe_audio(audio_path):
    """Ses dosyasını metne çevir"""
    try:
        if not whisper_model:
            raise Exception("Whisper model not initialized")
        
        segments, info = whisper_model.transcribe(audio_path, language="tr")
        text = " ".join([seg.text for seg in segments]).strip()
        
        return {
            "success": True,
            "text": text,
            "language": info.language
        }
    except Exception as e:
        logger.error(f"Transcription error: {e}")
        return {
            "success": False,
            "error": str(e)
        }


def text_to_speech(text, output_dir="static/audio"):
    """Metni ses dosyasına çevir"""
    try:
        if not tts_engine:
            raise Exception("TTS engine not initialized")
        
        # Çıktı dizinini oluştur
        os.makedirs(output_dir, exist_ok=True)
        
        # Benzersiz dosya adı
        filename = f"tts_{uuid.uuid4().hex[:8]}.wav"
        output_path = os.path.join(output_dir, filename)
        
        # TTS ile ses dosyası oluştur
        tts_engine.save_to_file(text, output_path)
        tts_engine.runAndWait()
        
        # Dosya oluşturuldu mu kontrol et
        if os.path.exists(output_path):
            return {
                "success": True,
                "audio_path": output_path,
                "audio_url": f"/audio/{filename}",
                "filename": filename
            }
        else:
            raise Exception("Audio file was not created")
            
    except Exception as e:
        logger.error(f"TTS error: {e}")
        return {
            "success": False,
            "error": str(e)
        }

@voice_bp.route("/process", methods=["POST"])
def process_voice():
    """Web voice chat ana endpoint'i"""
    try:
        # Voice sistemini başlat
        if not init_voice_system():
            return jsonify({
                "success": False,
                "error": "Voice system could not be initialized"
            }), 500
        
        # Ses dosyasını kontrol et
        if 'audio' not in request.files:
            return jsonify({
                "success": False,
                "error": "No audio file provided"
            }), 400
        
        audio_file = request.files['audio']
        if audio_file.filename == '':
            return jsonify({
                "success": False,
                "error": "No audio file selected"
            }), 400
        
        # Güvenli geçici dosya oluştur
        import tempfile
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
            audio_file.save(temp_file.name)
            temp_path = temp_file.name
        
        try:
            # 1. STT - Ses'ten metne
            transcription_result = transcribe_audio(temp_path)
            if not transcription_result["success"]:
                return jsonify({
                    "success": False,
                    "error": f"Transcription failed: {transcription_result['error']}"
                })
            
            user_text = transcription_result["text"]
            if not user_text.strip():
                return jsonify({
                    "success": False,
                    "error": "No speech detected in audio"
                })
            
            # 2. AI yanıtı al
            user_id = request.form.get('user_id', 'web_voice_user')
            from multi_user_ollama_runner import multi_user_ollama
            ai_result = multi_user_ollama.chat_with_model(
                model_name="auto",
                prompt=user_text,
                user_id=user_id
            )
            
            if "error" in ai_result:
                ai_response = f"AI hatası: {ai_result['error']}"
            else:
                ai_response = ai_result.get("response", "Yanıt alınamadı")
            
            # 3. TTS - AI yanıtını sese çevir
            tts_result = text_to_speech(ai_response)
            
            response_data = {
                "success": True,
                "transcription": user_text,
                "ai_response": ai_response,
                "model_used": ai_result.get("model", "unknown"),
                "response_time": ai_result.get("response_time", 0)
            }
            
            # TTS başarılıysa ses URL'i ekle
            if tts_result["success"]:
                response_data["audio_url"] = tts_result["audio_url"]
                response_data["has_audio"] = True
            else:
                response_data["tts_error"] = tts_result["error"]
                response_data["has_audio"] = False
            
            return jsonify(response_data)
            
        finally:
            # Geçici dosyayı temizle
            try:
                import os
                os.unlink(temp_path)
            except:
                pass
            
    except Exception as e:
        import logging
        logging.error(f"Voice process error: {e}", exc_info=True)
        return jsonify({
            "success": False,
            "error": f"Server error: {str(e)}"
        }), 500

        
@voice_bp.route("/status", methods=["GET"])
def voice_status():
    """Voice system status"""
    try:
        system_ok = init_voice_system()
        
        status = {
            "system_initialized": system_ok,
            "whisper_available": whisper_model is not None,
            "tts_available": tts_engine is not None,
            "dependencies_installed": True
        }
        
        return jsonify({
            "success": True,
            "status": status
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        })

# Audio dosyalarını serve etmek için route
@voice_bp.route("/audio/<filename>", methods=["GET"])
def serve_audio(filename):
    """Oluşturulan ses dosyalarını serve et"""
    try:
        # Güvenlik kontrolü
        secure_name = secure_filename(filename)
        if secure_name != filename:
            return "Invalid filename", 400
        
        audio_dir = "static/audio"
        file_path = os.path.join(audio_dir, secure_name)
        
        # Dosya var mı ve güvenli mi kontrol et
        if not os.path.exists(file_path):
            return "File not found", 404
        
        if not file_path.startswith(os.path.abspath(audio_dir)):
            return "Access denied", 403
        
        return send_file(file_path, mimetype="audio/wav")
        
    except Exception as e:
        logger.error(f"Audio serve error: {e}")
        return "Server error", 500

# Eski endpoint'leri deaktif et (backward compatibility)
@voice_bp.route("/ask", methods=["POST"])
def voice_ask_deprecated():
    """Eski endpoint - artık kullanılmıyor"""
    return jsonify({
        "success": False,
        "error": "This endpoint is deprecated. Use /voice/process instead.",
        "new_endpoint": "/voice/process"
    }), 410

# Initialize on import
init_voice_system()