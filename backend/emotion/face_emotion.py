import cv2
import mediapipe as mp
import numpy as np
import base64
import os

# Initialize MediaPipe gracefully
face_landmarker = None

try:
    from mediapipe.tasks import python
    from mediapipe.tasks.python import vision
    
    model_path = os.path.join(os.path.dirname(__file__), 'face_landmarker.task')
    if os.path.exists(model_path):
        base_options = python.BaseOptions(model_asset_path=model_path)
        options = vision.FaceLandmarkerOptions(
            base_options=base_options,
            output_face_blendshapes=True,
            output_facial_transformation_matrixes=True,
            num_faces=1
        )
        face_landmarker = vision.FaceLandmarker.create_from_options(options)
        print("[FaceEmotion] MediaPipe Face Landmarker loaded successfully with blendshapes.")
    else:
        print(f"[WARNING] MediaPipe model not found at {model_path}. Face emotion will default to neutral.")
except (ImportError, AttributeError, Exception) as e:
    print(f"[WARNING] MediaPipe Face Landmarker initialization failed: {e}. Face emotion will default to neutral.")


def _get_blendshape_value(blendshapes, name):
    """Extract a blendshape value by name. Returns 0.0 if not found."""
    for bs in blendshapes:
        if bs.category_name == name:
            return bs.score
    return 0.0


def _classify_emotion_from_blendshapes(blendshapes):
    """
    Classify emotion using MediaPipe face blendshapes.
    
    Key blendshapes used:
    - mouthSmileLeft/Right: smile intensity (happy)
    - browDownLeft/Right: brow furrowing (angry)
    - mouthFrownLeft/Right: frown (sad/angry) 
    - browInnerUp: inner brow raise (sad/surprised)
    - jawOpen: jaw opening (surprised)
    - eyeWideLeft/Right: eye widening (surprised)
    - mouthPucker/mouthShrugUpper: various mouth shapes
    - cheekSquintLeft/Right: cheek squint (happy)
    """
    # Extract relevant blendshape values
    smile_left = _get_blendshape_value(blendshapes, 'mouthSmileLeft')
    smile_right = _get_blendshape_value(blendshapes, 'mouthSmileRight')
    smile_avg = (smile_left + smile_right) / 2.0
    
    frown_left = _get_blendshape_value(blendshapes, 'mouthFrownLeft')
    frown_right = _get_blendshape_value(blendshapes, 'mouthFrownRight')
    frown_avg = (frown_left + frown_right) / 2.0
    
    brow_down_left = _get_blendshape_value(blendshapes, 'browDownLeft')
    brow_down_right = _get_blendshape_value(blendshapes, 'browDownRight')
    brow_down_avg = (brow_down_left + brow_down_right) / 2.0
    
    brow_inner_up = _get_blendshape_value(blendshapes, 'browInnerUp')
    brow_outer_up_left = _get_blendshape_value(blendshapes, 'browOuterUpLeft')
    brow_outer_up_right = _get_blendshape_value(blendshapes, 'browOuterUpRight')
    brow_up_avg = (brow_inner_up + brow_outer_up_left + brow_outer_up_right) / 3.0
    
    jaw_open = _get_blendshape_value(blendshapes, 'jawOpen')
    
    eye_wide_left = _get_blendshape_value(blendshapes, 'eyeWideLeft')
    eye_wide_right = _get_blendshape_value(blendshapes, 'eyeWideRight')
    eye_wide_avg = (eye_wide_left + eye_wide_right) / 2.0
    
    cheek_squint_left = _get_blendshape_value(blendshapes, 'cheekSquintLeft')
    cheek_squint_right = _get_blendshape_value(blendshapes, 'cheekSquintRight')
    cheek_squint_avg = (cheek_squint_left + cheek_squint_right) / 2.0
    
    eye_squint_left = _get_blendshape_value(blendshapes, 'eyeSquintLeft')
    eye_squint_right = _get_blendshape_value(blendshapes, 'eyeSquintRight')
    eye_squint_avg = (eye_squint_left + eye_squint_right) / 2.0
    
    mouth_press_left = _get_blendshape_value(blendshapes, 'mouthPressLeft')
    mouth_press_right = _get_blendshape_value(blendshapes, 'mouthPressRight')
    mouth_press_avg = (mouth_press_left + mouth_press_right) / 2.0

    # Score each emotion using weighted blendshape combinations
    scores = {
        "happy": 0.0,
        "sad": 0.0,
        "angry": 0.0,
        "surprised": 0.0,
        "neutral": 0.10  # Keep a baseline, but let subtle expressions still surface
    }
    
    # --- HAPPY ---
    # Strong smile + cheek squint + eye squint (Duchenne smile)
    happy_score = (
        smile_avg * 0.50 +
        cheek_squint_avg * 0.25 +
        eye_squint_avg * 0.15 +
        max(0, 0.1 - frown_avg) * 1.0  # Bonus if NOT frowning
    )
    scores["happy"] = min(1.0, happy_score)
    
    # --- SAD ---
    # Frown + inner brow raise + low smile
    sad_score = (
        frown_avg * 0.52 +
        brow_inner_up * 0.42 +
        max(0, 0.12 - smile_avg) * 1.6 +  # Bonus if NOT smiling
        max(0, 0.2 - brow_down_avg) * 0.35 +  # Sad is typically less furrowed than angry
        mouth_press_avg * 0.05
    )
    scores["sad"] = min(1.0, sad_score)
    
    # --- ANGRY ---
    # Brow down + frown + mouth press + low brow up
    angry_score = (
        brow_down_avg * 0.40 +
        frown_avg * 0.25 +
        mouth_press_avg * 0.15 +
        max(0, 0.1 - brow_up_avg) * 1.0 +  # Bonus if brows NOT raised
        max(0, 0.05 - smile_avg) * 2.0 +  # Bonus if NOT smiling
        eye_squint_avg * 0.12  # Tension around eyes can indicate anger
    )
    scores["angry"] = min(1.0, angry_score)
    
    # --- SURPRISED ---
    # Eye wide + jaw open + brow raise
    surprised_score = (
        eye_wide_avg * 0.30 +
        jaw_open * 0.35 +
        brow_up_avg * 0.25 +
        max(0, 0.1 - brow_down_avg) * 1.0  # Bonus if brows NOT furrowed
    )
    scores["surprised"] = min(1.0, surprised_score)

    # Bias sad vs angry when sadness cues are clearly present.
    sadness_cue = (
        frown_avg >= 0.18 and
        brow_inner_up >= 0.12 and
        smile_avg <= 0.14 and
        brow_down_avg <= 0.22
    )
    if sadness_cue and scores["sad"] >= scores["angry"] * 0.75:
        scores["sad"] += 0.08

    # Find dominant emotion
    top_emotion = max(scores, key=scores.get)
    
    # Normalize scores to sum to 1
    total = sum(scores.values())
    if total > 0:
        scores = {k: round(v / total, 3) for k, v in scores.items()}
    
    return {
        "emotion": top_emotion,
        "score": scores[top_emotion],
        "all_scores": scores
    }


def detect_face_emotion(frame_base64: str) -> dict:
    """
    Detect emotion from a base64 encoded image frame.
    Uses MediaPipe Face Landmarker blendshapes for accurate emotion classification.
    Returns dictionary with top emotion and scores.
    """
    if face_landmarker is None:
        return {"emotion": "neutral", "score": 1.0, "error": "MediaPipe unavailable"}
        
    try:
        # Decode base64 frame
        if frame_base64.startswith('data:image'):
            frame_base64 = frame_base64.split(',')[1]
        
        frame_bytes = base64.b64decode(frame_base64)
        nparr = np.frombuffer(frame_bytes, np.uint8)
        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if frame is None:
            return {"emotion": "neutral", "score": 1.0}
            
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # Convert to mp.Image
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
        
        # Process frame
        results = face_landmarker.detect(mp_image)
        
        if not results.face_landmarks:
            return {"emotion": "neutral", "score": 1.0, "info": "no_face_detected"}
        
        # Use blendshapes for emotion classification (much more accurate than landmarks)
        if results.face_blendshapes and len(results.face_blendshapes) > 0:
            blendshapes = results.face_blendshapes[0]
            
            # Debug: print key blendshape values
            key_shapes = ['mouthSmileLeft', 'mouthSmileRight', 'mouthFrownLeft', 'mouthFrownRight',
                          'browDownLeft', 'browDownRight', 'browInnerUp', 'jawOpen', 
                          'eyeWideLeft', 'eyeWideRight', 'cheekSquintLeft', 'cheekSquintRight']
            vals = {}
            for bs in blendshapes:
                if bs.category_name in key_shapes:
                    vals[bs.category_name] = round(bs.score, 3)
            print(f"[FaceEmotion] Blendshapes: {vals}")
            
            result = _classify_emotion_from_blendshapes(blendshapes)
            print(f"[FaceEmotion] Result: {result['emotion']} (scores={result.get('all_scores', {})})")
            return result
        else:
            # Blendshapes not available — face detected but no expression data
            print("[FaceEmotion] WARNING: Face detected but no blendshapes available!")
            return {"emotion": "neutral", "score": 1.0, "info": "no_blendshapes"}
        
    except Exception as e:
        print(f"Face emotion error: {e}")
        return {"emotion": "neutral", "score": 1.0, "error": str(e)}

if __name__ == "__main__":
    pass