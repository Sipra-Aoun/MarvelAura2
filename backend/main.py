import os
import json
import base64
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import warnings

warnings.filterwarnings('ignore', category=FutureWarning, module='google.generativeai')
warnings.filterwarnings('ignore', category=RuntimeWarning, module='numpy.core.getlimits')

from backend.config import settings
from backend.emotion.face_emotion import detect_face_emotion
from backend.emotion.voice_emotion import detect_voice_emotion
from backend.emotion.fusion import fuse_emotions
from backend.api.llm_client import generate_response
from backend.tts.text_to_speech import generate_speech
# Note: Vosk STT disabled in WebSockets here if raw audio isn't sent properly, 
# relying on browser WebSpeech API for frontend STT usually works better for latency,
# but we have the model available in backend.stt for server-side processing.

app = FastAPI(title="MarvelAura2 API", description="Emotion-aware AI companion backend")

# CORS for local dev
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount frontend
frontend_dir = os.path.join(os.getcwd(), 'frontend')
os.makedirs(os.path.join(frontend_dir, 'assets', 'audio'), exist_ok=True)
os.makedirs(os.path.join(frontend_dir, 'assets', 'avatars'), exist_ok=True)

# Important: Static files must be mounted last after API routes if wildcard, 
# but here we distinctively mount static paths
app.mount("/assets", StaticFiles(directory=os.path.join(frontend_dir, 'assets')), name="assets")
app.mount("/js", StaticFiles(directory=os.path.join(frontend_dir, 'js')), name="js")
app.mount("/css", StaticFiles(directory=os.path.join(frontend_dir, 'css')), name="css")


# Keep track of active connections
class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def send_json(self, message: dict, websocket: WebSocket):
        await websocket.send_json(message)

manager = ConnectionManager()

@app.websocket("/ws/chat")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # Receive text data (JSON)
            data = await websocket.receive_text()
            payload = json.loads(data)
            
            message_type = payload.get("type")
            
            if message_type == "chat":
                user_text = payload.get("text", "")
                face_data = payload.get("face_frame", "")
                voice_data = payload.get("voice_audio", "") # base64 encoded audio or null if using browser STT
                
                # If voice_data is provided, perform STT
                if voice_data:
                    from backend.stt.speech_to_text import transcribe_audio
                    import base64
                    try:
                        voice_data += "=" * ((4 - len(voice_data) % 4) % 4)
                        audio_bytes = base64.b64decode(voice_data)
                        stt_text = transcribe_audio(audio_bytes)
                        if stt_text and stt_text.strip():
                            user_text = stt_text
                            # Send transcription back so frontend can display it
                            await manager.send_json({
                                "type": "transcription",
                                "text": user_text
                            }, websocket)
                        else:
                            await manager.send_json({
                                "type": "response",
                                "text": "I couldn't hear you clearly. Could you repeat that?",
                                "emotion": "neutral",
                                "audio_url": ""
                            }, websocket)
                            continue
                    except Exception as e:
                        print(f"Error decoding audio or STT: {e}")
                        await manager.send_json({
                            "type": "error",
                            "message": f"STT Error: {str(e)}"
                        }, websocket)
                        continue
                
                # 1. Emotion Detection
                # Process Face
                face_result = {"emotion": "neutral", "score": 1.0}
                
                if face_data:
                    face_result = detect_face_emotion(face_data)
                    if face_result.get("emotion") != "neutral" or settings.DEBUG:
                        print(f"[Emotion] Face: {face_result.get('emotion')} (score={face_result.get('score', 0):.2f})")
                
                # For simplicity in testing if audio isn't raw, fallback to neutral
                voice_result = {"emotion": "neutral", "score": 1.0}
                
                # Fuse
                final_emotion = fuse_emotions(face_result, voice_result)["emotion"]
                
                # Notify frontend immediately of detected emotion
                await manager.send_json({
                    "type": "emotion_update",
                    "emotion": final_emotion
                }, websocket)
                
                if user_text.strip():
                    # 2. LLM Processing
                    try:
                        ai_text = await generate_response(user_text, final_emotion)
                    except Exception as e:
                        print(f"LLM Processing Error: {e}")
                        await manager.send_json({
                            "type": "error",
                            "message": f"API Key / LLM Error: {str(e)}"
                        }, websocket)
                        continue
                    
                    # 3. TTS Generation
                    # Generate audio file
                    audio_path = await generate_speech(ai_text)
                    audio_filename = os.path.basename(audio_path) if audio_path else ""
                    
                    # Send complete response
                    await manager.send_json({
                        "type": "response",
                        "text": ai_text,
                        "emotion": final_emotion,
                        "audio_url": f"/assets/audio/{audio_filename}" if audio_filename else ""
                    }, websocket)
                
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        print(f"WebSocket Error: {e}")
        try:
            await manager.send_json({"type": "error", "message": str(e)}, websocket)
        except:
            pass
            
@app.get("/api/health")
async def health_check():
    return {"status": "ok", "message": "MarvelAura2 API is running"}

app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")
