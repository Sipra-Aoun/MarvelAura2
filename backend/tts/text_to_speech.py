import os
import edge_tts
from backend.config import settings

async def generate_speech(text: str, output_path: str = None) -> str:
    """
    Generate speech from text using Microsoft Edge Neural Voices via edge-tts module.
    Extremely fast, high quality, minimal memory footprint.
    """
    if not text:
        return ""
        
    if output_path is None:
        # Create a temp output file in the static assets dir
        static_dir = os.path.join(os.getcwd(), 'frontend', 'assets', 'audio')
        os.makedirs(static_dir, exist_ok=True)
        output_path = os.path.join(static_dir, 'response.mp3')
        
    try:
        voice = settings.TTS_VOICE
        communicate = edge_tts.Communicate(text, voice)
        await communicate.save(output_path)
        return output_path
    except Exception as e:
        print(f"TTS Error: {e}")
        return ""
