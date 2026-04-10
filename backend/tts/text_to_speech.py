import os
import edge_tts
from backend.config import settings

# Emotion-to-voice mapping with emotional prosody
EMOTION_VOICE_MAP = {
    "happy": {
        "voice": "en-US-AriaNeural",  # Bright, energetic female voice
        "rate": 1.1,  # Slightly faster to match excitement
        "pitch": 1.15,  # Slightly higher pitch conveys joy
    },
    "sad": {
        "voice": "en-US-JennyNeural",  # Warm, gentle female voice
        "rate": 0.85,  # Slower pace for thoughtfulness
        "pitch": 0.9,  # Slightly lower tone conveys sadness
    },
    "angry": {
        "voice": "en-US-GuyNeural",  # Deeper, more authoritative male voice
        "rate": 1.05,  # Slightly faster to convey intensity
        "pitch": 0.95,  # Slightly lower conveys assertiveness
    },
    "surprised": {
        "voice": "en-US-AriaNeural",  # Clear, engaged female voice
        "rate": 1.15,  # Faster pacing matches surprise/excitement
        "pitch": 1.2,  # Higher pitch conveys surprise
    },
    "neutral": {
        "voice": settings.TTS_VOICE,  # Default from config
        "rate": 1.0,
        "pitch": 1.0,
    }
}

async def generate_speech(text: str, emotion: str = "neutral", output_path: str = None) -> str:
    """
    Generate speech from text using Microsoft Edge Neural Voices with emotion-aware prosody.
    Adjusts voice and speech rate based on detected user emotion.
    
    Args:
        text: The text to synthesize
        emotion: User's detected emotion (happy, sad, angry, surprised, neutral)
        output_path: Optional custom output path
    
    Returns:
        Path to generated audio file or empty string on error
    """
    if not text:
        return ""
        
    if output_path is None:
        # Create a temp output file in the static assets dir
        static_dir = os.path.join(os.getcwd(), 'frontend', 'assets', 'audio')
        os.makedirs(static_dir, exist_ok=True)
        output_path = os.path.join(static_dir, 'response.mp3')
    
    try:
        # Normalize emotion key
        emotion_key = emotion.strip().lower() if emotion else "neutral"
        if emotion_key not in EMOTION_VOICE_MAP:
            emotion_key = "neutral"
        
        voice_config = EMOTION_VOICE_MAP[emotion_key]
        voice = voice_config["voice"]
        rate = voice_config["rate"]
        
        # Convert rate to edge-tts format: 1.0 = normal, 1.1 = 10% faster, 0.85 = 15% slower
        # edge-tts expects rate as a string like "+20%" or "-10%" relative to normal
        if rate >= 1.0:
            rate_str = f"+{int((rate - 1.0) * 100)}%"
        else:
            rate_str = f"{int((rate - 1.0) * 100)}%"
        
        # Use edge-tts with voice and rate parameters
        communicate = edge_tts.Communicate(text, voice, rate=rate_str)
        await communicate.save(output_path)
        
        print(f"[TTS] Generated audio with emotion: {emotion_key} | Voice: {voice} | Rate: {rate_str}")
        return output_path
        
    except Exception as e:
        print(f"TTS Error generating speech: {e}")
        import traceback
        traceback.print_exc()
        return ""
