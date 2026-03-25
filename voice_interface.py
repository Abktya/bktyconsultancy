# voice_interface.py - Fixed version with is_available method
import sounddevice as sd
import soundfile as sf
import tempfile
import pyttsx3
import os
import logging
from faster_whisper import WhisperModel
from multi_user_ollama_runner import multi_user_ollama

logger = logging.getLogger(__name__)

class VoiceInterface:
    """Voice interface with proper availability checking"""
    
    def __init__(self, model="auto", samplerate=16000):
        self.model = model
        self.samplerate = samplerate
        self.whisper = None
        self.tts_engine = None
        
        # Initialize STT (Whisper)
        try:
            self.whisper = WhisperModel("small", device="cpu", compute_type="float32")
            logger.info("✅ Whisper model loaded")
        except Exception as e:
            logger.error(f"❌ Whisper initialization failed: {e}")
        
        # Initialize TTS (pyttsx3)
        try:
            self.tts_engine = pyttsx3.init()
            voices = self.tts_engine.getProperty("voices")
            if voices:
                # Try to find Turkish voice
                tr_voice = next((v for v in voices if 'tr' in v.id.lower() or 'turkish' in str(getattr(v, 'name', '')).lower()), None)
                if tr_voice:
                    self.tts_engine.setProperty("voice", tr_voice.id)
                    print(f"✅ Türkçe ses seçildi: {tr_voice.id}")
                else:
                    self.tts_engine.setProperty("voice", voices[0].id)
                    print(f"✅ Default voice selected: {voices[0].id}")
                
                # Set speech rate and volume
                self.tts_engine.setProperty("rate", 150)  # Slower speech
                self.tts_engine.setProperty("volume", 0.9)
            else:
                logger.warning("No TTS voices found")
        except Exception as e:
            logger.error(f"❌ TTS initialization failed: {e}")
            self.tts_engine = None

    def is_available(self):
        """Check if voice interface is properly initialized"""
        return (self.whisper is not None and self.tts_engine is not None)

    def record_audio(self, duration=5):
        """Record audio from microphone"""
        try:
            print(f"🎙️ {duration} saniye konuşun...")
            
            # Check if microphone is available
            devices = sd.query_devices()
            input_device = None
            for i, device in enumerate(devices):
                if device['max_input_channels'] > 0:
                    input_device = i
                    break
            
            if input_device is None:
                raise Exception("No input device (microphone) found")
            
            # Record audio
            audio = sd.rec(
                int(duration * self.samplerate),
                samplerate=self.samplerate,
                channels=1,
                dtype="float32",
                device=input_device
            )
            sd.wait()  # Wait for recording to complete
            
            # Save to temporary file
            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as f:
                sf.write(f.name, audio, self.samplerate)
                return f.name
                
        except Exception as e:
            print(f"❌ Ses kaydı başarısız: {e}")
            raise Exception(f"Audio recording failed: {str(e)}")

    def transcribe(self, audio_file):
        """STT: Ses dosyasını metne çevir"""
        if not audio_file or not os.path.exists(audio_file):
            return ""
        
        try:
            segments, info = self.whisper.transcribe(audio_file, language="tr")
            text = " ".join([seg.text for seg in segments]).strip()
            print(f"📝 Algılanan ({info.language}): {text}")
            
            # Clean up temp file
            try:
                os.unlink(audio_file)
            except:
                pass
                
            return text
        except Exception as e:
            print(f"❌ Transcribe hatası: {e}")
            return ""

    def speak(self, text):
        """TTS: Yanıtı seslendir"""
        print(f"🤖 Yanıt: {text}")
        if self.tts_engine:
            try:
                self.tts_engine.say(text)
                self.tts_engine.runAndWait()
            except Exception as e:
                print(f"⚠️ TTS hata verdi: {e}")

    def ask(self, user_id="voice_user", duration=5):
        """Sesli soru-cevap döngüsü"""
        if not self.is_available():
            raise Exception("Voice interface not properly initialized")
        
        # Record audio
        audio_file = self.record_audio(duration)
        
        # Transcribe speech to text
        user_text = self.transcribe(audio_file)
        if not user_text:
            raise Exception("Could not understand speech")

        # Get AI response
        try:
            result = multi_user_ollama.chat_with_model("auto", user_text, user_id=user_id)
            if "error" in result:
                bot_response = f"AI Error: {result['error']}"
            else:
                bot_response = result.get("response", "No response received")
        except Exception as e:
            bot_response = f"AI connection failed: {str(e)}"

        # Speak the response
        self.speak(bot_response)
        
        return {
            "user": user_text,
            "bot": bot_response,
            "model": result.get("model", "unknown") if "error" not in result else "error"
        }