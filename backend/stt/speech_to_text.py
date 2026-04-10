import os
import json
import io
import wave
import struct
from backend.config import settings

# ============================================================
# STT Engine Priority:
#   1. Google Speech Recognition (free, online, high accuracy)
#   2. OpenAI Whisper local (if installed — best offline quality) 
#   3. Vosk (offline, fast, but lower accuracy with small model)
# ============================================================

# --- Google SpeechRecognition (Primary) ---
_sr_available = False
try:
    import speech_recognition as sr
    _sr_available = True
    print("[STT] SpeechRecognition library loaded (Google STT available).")
except ImportError:
    print("[STT] SpeechRecognition not installed. Google STT unavailable.")

# --- Whisper Local (Optional high-quality offline) ---
_whisper_model = None
_whisper_available = False
try:
    import whisper as whisper_lib
    _whisper_available = True
    print("[STT] OpenAI Whisper library detected. Will load model on first use.")
except ImportError:
    pass

# --- Vosk (Offline fallback) ---
_vosk_model = None
_vosk_available = False
try:
    from vosk import Model as VoskModel, KaldiRecognizer
    _vosk_available = True
    print("[STT] Vosk library loaded.")
except ImportError:
    print("[STT] Vosk not installed. Offline STT fallback unavailable.")


def _init_vosk():
    """Initialize Vosk model lazily."""
    global _vosk_model
    if _vosk_model is not None:
        return _vosk_model
    
    model_path = os.path.join(os.getcwd(), 'models', settings.VOSK_MODEL)
    
    if os.path.exists(model_path):
        try:
            _vosk_model = VoskModel(model_path)
            print(f"[STT] Vosk model loaded from {model_path}")
            return _vosk_model
        except Exception as e:
            print(f"[STT] Vosk model load error: {e}")
    
    # Try auto-download
    try:
        _vosk_model = VoskModel(lang="en-us")
        print("[STT] Vosk default model downloaded.")
        return _vosk_model
    except Exception as e:
        print(f"[STT] Vosk auto-download failed: {e}")
    
    return None


def _init_whisper():
    """Initialize Whisper model lazily."""
    global _whisper_model
    if _whisper_model is not None:
        return _whisper_model
    
    if not _whisper_available:
        return None
    
    try:
        # Use "base" model — good balance of speed vs accuracy (~150MB)
        _whisper_model = whisper_lib.load_model("base")
        print("[STT] Whisper 'base' model loaded successfully.")
        return _whisper_model
    except Exception as e:
        print(f"[STT] Whisper model load failed: {e}")
        return None


def _pcm_to_wav_bytes(pcm_data: bytes, sample_rate: int = 16000, sample_width: int = 2) -> bytes:
    """Convert raw PCM bytes to a WAV file in memory."""
    buf = io.BytesIO()
    with wave.open(buf, 'wb') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(sample_width)
        wf.setframerate(sample_rate)
        wf.writeframes(pcm_data)
    buf.seek(0)
    return buf.read()


def _transcribe_google(audio_data: bytes, sample_rate: int = 16000) -> str:
    """Transcribe using Google Speech Recognition (free tier, online)."""
    if not _sr_available:
        return ""
    
    try:
        r = sr.Recognizer()
        # Adjust for ambient noise sensitivity
        r.energy_threshold = 300
        r.dynamic_energy_threshold = False
        
        audio = sr.AudioData(audio_data, sample_rate, 2)  # 2 = sample_width (16-bit PCM)
        text = r.recognize_google(audio)
        if text:
            print(f"[STT] Google result: '{text}'")
        return text or ""
    except sr.UnknownValueError:
        print("[STT] Google: could not understand audio")
        return ""
    except sr.RequestError as e:
        print(f"[STT] Google API error: {e}")
        return ""
    except Exception as e:
        print(f"[STT] Google unexpected error: {e}")
        return ""


def _transcribe_whisper(audio_data: bytes, sample_rate: int = 16000) -> str:
    """Transcribe using OpenAI Whisper (local, offline, high quality)."""
    model = _init_whisper()
    if model is None:
        return ""
    
    try:
        import numpy as np
        import tempfile
        
        # Whisper needs a file path or numpy array
        wav_bytes = _pcm_to_wav_bytes(audio_data, sample_rate)
        
        # Write to temp file
        tmp_path = os.path.join(os.getcwd(), 'frontend', 'assets', 'audio', '_stt_temp.wav')
        with open(tmp_path, 'wb') as f:
            f.write(wav_bytes)
        
        result = model.transcribe(tmp_path, language="en", fp16=False)
        text = result.get("text", "").strip()
        
        # Clean up
        try:
            os.remove(tmp_path)
        except:
            pass
        
        if text:
            print(f"[STT] Whisper result: '{text}'")
        return text
    except Exception as e:
        print(f"[STT] Whisper error: {e}")
        return ""


def _transcribe_vosk(audio_data: bytes, sample_rate: int = 16000) -> str:
    """Transcribe using Vosk (offline, fast)."""
    if not _vosk_available:
        return ""
    
    model = _init_vosk()
    if model is None:
        return ""
    
    try:
        rec = KaldiRecognizer(model, sample_rate)
        
        rec.AcceptWaveform(audio_data)
        res = json.loads(rec.FinalResult())
        text = res.get("text", "")
        
        if not text:
            partial_res = json.loads(rec.PartialResult())
            text = partial_res.get("partial", "")
        
        if text:
            print(f"[STT] Vosk result: '{text}'")
        return text
    except Exception as e:
        print(f"[STT] Vosk error: {e}")
        return ""


def transcribe_audio(audio_data: bytes, sample_rate: int = 16000) -> str:
    """
    Convert raw PCM audio bytes to text.
    
    Engine priority:
      1. Google Speech Recognition (online, free, best accuracy)
      2. OpenAI Whisper local (if installed — excellent offline)
      3. Vosk (offline fallback)
    """
    if not audio_data or len(audio_data) < 500:
        print("[STT] Audio data too short, skipping.")
        return ""
    
    print(f"[STT] Processing {len(audio_data)} bytes of audio...")
    
    # 1. Try Google STT first (best accuracy, requires internet)
    text = _transcribe_google(audio_data, sample_rate)
    if text.strip():
        return text
    
    # 2. Try Whisper local (if available)
    if _whisper_available:
        text = _transcribe_whisper(audio_data, sample_rate)
        if text.strip():
            return text
    
    # 3. Fall back to Vosk
    text = _transcribe_vosk(audio_data, sample_rate)
    if text.strip():
        return text
    
    print("[STT] All engines failed to produce text.")
    return ""
