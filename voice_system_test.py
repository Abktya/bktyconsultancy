# voice_system_test.py - Run this to test your voice system independently

import sys
import os

def test_voice_system():
    """Test voice system components individually"""
    
    print("🧪 Testing Voice System Components...")
    print("="*50)
    
    # Test 1: Import dependencies
    try:
        import sounddevice as sd
        import soundfile as sf
        import pyttsx3
        from faster_whisper import WhisperModel
        print("✅ 1. All dependencies imported successfully")
    except ImportError as e:
        print(f"❌ 1. Import failed: {e}")
        return False
    
    # Test 2: Audio devices
    try:
        devices = sd.query_devices()
        input_devices = [d for d in devices if d['max_input_channels'] > 0]
        print(f"✅ 2. Audio devices: {len(input_devices)} input devices found")
        
        # Show input devices
        for i, device in enumerate(input_devices):
            print(f"   📱 Device {i}: {device['name']}")
    except Exception as e:
        print(f"❌ 2. Audio device check failed: {e}")
        return False
    
    # Test 3: TTS Engine
    try:
        engine = pyttsx3.init()
        voices = engine.getProperty("voices")
        print(f"✅ 3. TTS Engine: {len(voices)} voices available")
        
        # Test Turkish voices
        tr_voices = [v for v in voices if 'tr' in v.id.lower() or 'turkish' in str(getattr(v, 'name', '')).lower()]
        print(f"   🇹🇷 Turkish voices found: {len(tr_voices)}")
        
        # Test speech
        print("   🔊 Testing speech...")
        engine.say("Voice system test successful")
        engine.runAndWait()
        print("   ✅ TTS test completed")
        
    except Exception as e:
        print(f"❌ 3. TTS test failed: {e}")
        return False
    
    # Test 4: Whisper Model (this might take time on first run)
    try:
        print("   📥 Loading Whisper model (may download ~100MB on first run)...")
        whisper = WhisperModel("small", device="cpu", compute_type="float32")
        print("✅ 4. Whisper model loaded successfully")
    except Exception as e:
        print(f"❌ 4. Whisper model failed: {e}")
        return False
    
    # Test 5: Voice Interface Class
    try:
        # Import your voice interface
        sys.path.append(os.path.dirname(os.path.abspath(__file__)))
        from voice_blueprint import VoiceInterface
        
        voice_interface = VoiceInterface()
        if voice_interface.is_available():
            print("✅ 5. VoiceInterface initialized successfully")
        else:
            print("❌ 5. VoiceInterface not fully available")
            return False
    except ImportError as e:
        print(f"⚠️ 5. Could not import VoiceInterface (this is OK if file doesn't exist yet): {e}")
    except Exception as e:
        print(f"❌ 5. VoiceInterface test failed: {e}")
        return False
    
    print("="*50)
    print("🎉 All voice system components working correctly!")
    print("\nNext steps:")
    print("1. Make sure voice_blueprint.py is in your project directory")
    print("2. Add blueprint registration to app.py")
    print("3. Test the /voice/status endpoint")
    print("4. Try the voice button in your web interface")
    
    return True

if __name__ == "__main__":
    test_voice_system()
