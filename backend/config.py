import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    OPENAI_API_KEY: str = "sk-placeholder"
    OPENAI_MODEL: str = "gpt-4o-mini"
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-3.0-flash"
    HOST: str = "0.0.0.0"
    PORT: int = 9000
    TTS_VOICE: str = "en-US-AriaNeural"
    FACE_EMOTION_WEIGHT: float = 0.7
    VOICE_EMOTION_WEIGHT: float = 0.3
    VOSK_MODEL: str = "vosk-model-small-en-us-0.15"
    DEBUG: bool = False
    AVATAR_MODE: str = "svg"

    class Config:
        env_file = ".env"
        env_file_encoding = 'utf-8'

settings = Settings()
