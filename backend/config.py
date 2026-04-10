import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    OPENAI_API_KEY: str = "sk-placeholder"
    OPENAI_MODEL: str = "gpt-4o-mini"
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-2.5-flash"
    OLLAMA_BASE_URL: str = "http://127.0.0.1:11434"
    OLLAMA_MODEL: str = "mistral:7b-instruct-q4_K_M"
    LLM_PROVIDER: str = "auto"
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
