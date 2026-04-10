from openai import AsyncOpenAI
import warnings
warnings.filterwarnings('ignore', category=FutureWarning, module='google.generativeai')
import google.generativeai as genai
from backend.config import settings
from backend.api.ollama_client import generate_ollama_response

# Initialize clients lazily
_openai_client = None
_gemini_configured = False


def _normalize_provider(provider: str) -> str:
    if not provider:
        provider = settings.LLM_PROVIDER
    value = str(provider).strip().lower()
    allowed = {"auto", "gemini", "openai", "ollama"}
    return value if value in allowed else "auto"


def _build_system_prompt(user_emotion: str) -> str:
    """
    Build an emotion-aware system prompt that tailors the AI's tone, pacing, and language
    to match and support the user's detected emotional state.
    """
    base = "You are MarvelAura, a warm, intuitive, and emotionally intelligent AI companion."

    emotion_guides = {
        "happy": {
            "tone": "uplifting, enthusiastic, and joyful",
            "approach": "Share their excitement! Use warm and positive language. Celebrate moments with them. Feel their energy.",
            "pacing": "Match their energy with lively responses.",
            "language": "Use affirmations, exclamations, and positive phrases. Keep it light and energetic.",
            "focus": "Build on their joy and share in their happiness."
        },
        "sad": {
            "tone": "gentle, compassionate, and supportive",
            "approach": "Be a caring listener first. Validate their feelings without minimizing them. Offer comfort and understanding.",
            "pacing": "Take a slower, thoughtful pace. Give them space to share.",
            "language": "Use warm, validating phrases like 'I understand', 'It sounds like you're going through something', 'That's valid'.",
            "focus": "Show empathy, normalize their struggle, and gently remind them they're not alone."
        },
        "angry": {
            "tone": "calm, steady, and grounding",
            "approach": "Help them feel heard and understood. Validate their frustration. Be a calming presence without dismissing their anger.",
            "pacing": "Match their intensity but guide toward calm. Be confident but not patronizing.",
            "language": "Acknowledge their feelings directly. Use phrases like 'I hear you', 'That sounds frustrating', 'You have every right to feel that way'.",
            "focus": "De-escalate gently, help them feel in control, and offer perspective when appropriate."
        },
        "surprised": {
            "tone": "curious, playful, and engaging",
            "approach": "Match their sense of wonder. Show genuine interest in what surprised them. Help them explore the emotion.",
            "pacing": "Keep energy up and conversation flowing naturally.",
            "language": "Use engaged, curious responses. 'That's interesting!', 'Tell me more', 'Wow, how did that make you feel?'",
            "focus": "Help them process and make sense of the surprise."
        },
        "neutral": {
            "tone": "balanced, conversational, and grounded",
            "approach": "Be a helpful, attentive companion. Offer thoughtful insights without overwhelming.",
            "pacing": "Keep a natural, comfortable pace.",
            "language": "Use clear, warm, conversational language. Be approachable and genuine.",
            "focus": "Provide genuine support and understanding."
        }
    }

    # Normalize emotion key
    emotion_key = user_emotion.strip().lower()
    if emotion_key not in emotion_guides:
        emotion_key = "neutral"

    guide = emotion_guides[emotion_key]

    system_prompt = f"""{base}

The user is currently feeling: {user_emotion}.

TONE: Be {guide['tone']}.

APPROACH: {guide['approach']}

PACING: {guide['pacing']}

LANGUAGE STYLE: {guide['language']}

PRIMARY FOCUS: {guide['focus']}

CRITICAL CONSTRAINTS:
- Keep responses conversational and natural, like a caring friend—not robotic.
- Respond in 1-3 sentences unless they ask for more detail.
- Do NOT use emojis, markdown, asterisks, or special formatting (your responses will be spoken aloud).
- Avoid clichés—be genuine and specific to what they share.
- Prioritize emotional connection over providing solutions, unless they ask for advice.
- Remember: You're here to listen, validate, and support—not fix everything."""

    return system_prompt

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

async def generate_response(user_text: str, user_emotion: str, provider: str = "auto") -> str:
    """
    Generate an AI response that deeply adapts to the user's emotion.
    """
    system_prompt = _build_system_prompt(user_emotion)

    selected_provider = _normalize_provider(provider)

    if selected_provider == "ollama":
        try:
            return await generate_ollama_response(user_text, system_prompt)
        except Exception as e:
            raise Exception(f"Ollama LLM API failed: {e}")

    if selected_provider == "gemini":
        if not get_gemini_client():
            raise Exception("Gemini provider selected but GEMINI_API_KEY is missing/invalid.")
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
            raise Exception(f"Gemini LLM API failed: {e}")

    if selected_provider == "openai":
        openai_client = get_openai_client()
        if not openai_client:
            raise Exception("OpenAI provider selected but OPENAI_API_KEY is missing/invalid.")
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
            raise Exception(f"OpenAI LLM API failed: {e}")

    # Auto mode fallback chain: Gemini -> OpenAI -> Ollama
    # 1. Try Gemini
    if get_gemini_client():
        try:
            model_name = settings.GEMINI_MODEL

            model = genai.GenerativeModel(
                model_name=model_name,
                system_instruction=system_prompt
            )

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

    # 3. Try local Ollama fallback
    try:
        return await generate_ollama_response(user_text, system_prompt)
    except Exception as e:
        print(f"[LLM] Ollama Error: {e}")

    # 4. All providers failed / misconfigured
    raise Exception(
        "No AI provider is available. Configure GEMINI_API_KEY or OPENAI_API_KEY, "
        "or run Ollama locally with the configured model."
    )
