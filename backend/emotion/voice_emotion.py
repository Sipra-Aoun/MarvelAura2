import librosa
import numpy as np

def detect_voice_emotion(audio_data: bytes, sample_rate: int = 16000) -> dict:
    """
    Detect emotion from audio bytes.
    Extracts MFCC features and uses heuristics for fast low-latency evaluation.
    """
    try:
        # Check if empty
        if not audio_data or len(audio_data) < 1000:
            return {"emotion": "neutral", "score": 1.0}
            
        # Convert bytes to numpy array
        # Assuming PCM 16-bit 16kHz audio from frontend
        audio_array = np.frombuffer(audio_data, dtype=np.int16).astype(np.float32) / 32768.0
        
        # Use librosa to extract features
        # Compute root-mean-square (RMS) energy
        rms = librosa.feature.rms(y=audio_array)[0]
        mean_rms = np.mean(rms)
        
        # Compute spectral centroid (brightness)
        cent = librosa.feature.spectral_centroid(y=audio_array, sr=sample_rate)[0]
        mean_cent = np.mean(cent)
        
        # Compute pitch (fundamental frequency)
        pitches, magnitudes = librosa.piptrack(y=audio_array, sr=sample_rate)
        # Get mean pitch of non-zero pitches
        active_pitches = pitches[magnitudes > np.median(magnitudes)]
        mean_pitch = np.mean(active_pitches) if len(active_pitches) > 0 else 0
        
        # Simple heuristics
        scores = {
            "happy": 0.0,
            "sad": 0.0,
            "angry": 0.0,
            "surprised": 0.0,
            "neutral": 0.5 
        }
        
        # High energy, high pitch, bright -> happy/surprised
        if mean_rms > 0.05:
            if mean_pitch > 300:
                scores["surprised"] += 0.7
                scores["happy"] += 0.5
            else:
                scores["angry"] += 0.8  # High energy, lower pitch
                
        # Low energy, low pitch -> sad
        elif mean_rms < 0.01 and mean_pitch > 0:
            scores["sad"] += 0.8
            scores["neutral"] += 0.4
            
        # Normal speaking
        else:
            scores["neutral"] += 0.9
            
        # Find dominant
        top_emotion = max(scores, key=scores.get)
        
        # Normalize
        total = sum(scores.values())
        if total > 0:
            scores = {k: v/total for k, v in scores.items()}
            
        return {
            "emotion": top_emotion,
            "score": scores[top_emotion],
            "all_scores": scores
        }
        
    except Exception as e:
        print(f"Voice emotion error: {e}")
        return {"emotion": "neutral", "score": 1.0, "error": str(e)}

if __name__ == "__main__":
    pass
