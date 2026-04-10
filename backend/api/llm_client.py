import httpx
from openai import AsyncOpenAI
import warnings
warnings.filterwarnings('ignore', category=FutureWarning, module='google.generativeai')
import google.generativeai as genai
from backend.config import settings

# Initialize clients lazily
_openai_client = None
_gemini_configured = False

def get_openai_client():
    global _openai_client
    if _openai_client is None:
        if settings.OPENAI_API_KEY and settings.OPENAI_API_KEY != "sk-placeholder" and settings.OPENAI_API_KEY != "":
            _openai_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
    return _openai_client

def get_gemini_client():
    global _gemini_configured
    if not _gemini_configured:
        if settings.GEMINI_API_KEY and settings.GEMINI_API_KEY != "your-gemini-key-here" and settings.GEMINI_API_KEY != "":
            genai.configure(api_key=settings.GEMINI_API_KEY)
            _gemini_configured = True
    return _gemini_configured

async def generate_response(user_text: str, user_emotion: str) -> str:
    """
    Generate an AI response that adapts to the user's emotion.
    Tries OpenAI first, falls back to Gemini Flash on failure or missing key.
    """
    system_prompt = f"""You are a supportive, empathetic, and conversational AI companion. 
The user's current input is: {user_emotion}. 
Match their pace,emotions and language.
If they are sad, be supportive and gentle. If happy, share their excitement. If angry, be calm and de-escalating.
Keep your responses conversational, concise (1-3 sentences), and natural for text-to-speech. Do not use emojis, markdown, or special formatting since your response will be spoken aloud."""

    # 1. Try Gemini (Primary)
    if get_gemini_client():
        try:
            model_name = settings.GEMINI_MODEL
                
            model = genai.GenerativeModel(
                model_name=model_name,
                system_instruction=system_prompt
            )
            
            # Gemini async generation
            response = await model.generate_content_async(
                user_text,
                generation_config={"temperature": 0.7, "max_output_tokens": 1000}
            )
            return response.text.strip()
        except Exception as e:
            print(f"[LLM] Gemini Error: {e}. Falling back to OpenAI...")
    else:
        print("[LLM] Gemini key missing or invalid. Trying OpenAI...")

    # 2. Try OpenAI Fallback
    openai_client = get_openai_client()
    if openai_client:
        try:
            response = await openai_client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_text}
                ],
                temperature=0.7,
                max_tokens=1000
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"[LLM] OpenAI Error: {e}")
            raise Exception(f"OpenAI LLM API failed: {e}")

    # 3. Both failed / neither configured
    raise Exception("No AI provider keys have been configured yet. Please check the backend settings (.env).")
