from backend.config import settings

def fuse_emotions(face_result: dict, voice_result: dict) -> dict:
    """
    Combine face and voice emotions using weighted averages.
    """
    f_weight = settings.FACE_EMOTION_WEIGHT
    v_weight = settings.VOICE_EMOTION_WEIGHT
    
    # If one of them is missing/default neutral, rely more on the other
    if face_result.get("emotion") == "neutral" and face_result.get("score") == 1.0:
        f_weight = 0.2
        v_weight = 0.8
        
    if voice_result.get("emotion") == "neutral" and voice_result.get("score") == 1.0:
        f_weight = 0.8
        v_weight = 0.2
        
    # Standardize classes
    emotions = ["happy", "sad", "angry", "surprised", "neutral"]
    
    # Initialize combined scores
    combined = {e: 0.0 for e in emotions}
    
    # Get scores dicts
    f_scores = face_result.get("all_scores", {face_result.get("emotion", "neutral"): face_result.get("score", 1.0)})
    v_scores = voice_result.get("all_scores", {voice_result.get("emotion", "neutral"): voice_result.get("score", 1.0)})
    
    # Weighted sum
    for e in emotions:
        combined[e] += f_scores.get(e, 0.0) * f_weight
        combined[e] += v_scores.get(e, 0.0) * v_weight
        
    # Find max
    top_emotion = max(combined, key=combined.get)
    
    # Normalize
    total = sum(combined.values())
    if total > 0:
        combined = {k: v/total for k, v in combined.items()}
        
    return {
        "emotion": top_emotion,
        "score": combined[top_emotion],
        "face_contributed": f_scores.get(top_emotion, 0),
        "voice_contributed": v_scores.get(top_emotion, 0)
    }
