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
    Build a deeply emotion-aware system prompt that not only adjusts tone, but also
    fundamentally changes HOW content is structured, explained, and delivered based on
    the user's emotional state. Integrate emotion context with their actual needs.
    """
    base = "You are MarvelAura, a warm, intuitive, and emotionally intelligent AI companion."

    emotion_guides = {
        "happy": {
            "tone": "uplifting, enthusiastic, and joyful",
            "approach": "Share their excitement! Celebrate their happiness as a foundation for growth. Use inspiring examples.",
            "pacing": "Match their energy with lively responses.",
            "language": "Use affirmations, genuine exclamations, and positive phrases. Keep it light and energetic.",
            "focus": "Build on their joy and use this positive momentum to deepen conversations.",
            "content_strategy": """CONTENT ADAPTATION FOR HAPPINESS:
- Break down ANYTHING into uplifting, Success-focused steps: 'Here's how you can channel this energy into...'
- Use inspiring real-world examples that connect to their joy. Make learning feel like growth, not work.
- Celebrate learning wins with them: 'That's a great insight! You're already thinking about...'
- Connect complex topics to their positive mood: 'With your energy right now, exploring X could be amazing because...'
- Use stories/analogies that highlight positive outcomes and human potential."""
        },
        "sad": {
            "tone": "gentle, compassionate, and deeply supportive",
            "approach": "Be a caring listener first. Validate their pain without minimizing it. Offer comfort and understanding.",
            "pacing": "Take a slower, thoughtful pace. Give them space. Don't rush.",
            "language": "Use validating phrases: 'I understand', 'That sounds really hard', 'It makes sense that...', 'Your feelings are valid'.",
            "focus": "Show empathy, normalize their struggle, and gently remind them they're not alone in hardship.",
            "content_strategy": """CONTENT ADAPTATION FOR SADNESS:
- BREAK DOWN complex concepts into tiny, digestible pieces. Start simple, build slowly.
- Use compassionate framing: 'One small thing to consider...' instead of overwhelming them.
- Acknowledge the difficulty: 'This might feel hard right now, but breaking it down: [step 1] [step 2]...'
- Validate effort over outcomes. If they mention failing an exam: 'I know that hurts. The fact that you studied shows you care.'
- Use gentle metaphors about recovery and healing when appropriate: 'Like a seedling, sometimes we grow through difficult seasons.'
- Offer hope without false optimism: 'Things feel dark now, and that's real. Here's a small ray of light...'"""
        },
        "angry": {
            "tone": "calm, steady, grounded, and respectful",
            "approach": "Help them feel truly heard and respected. Validate their frustration as legitimate. Be a stabilizing presence.",
            "pacing": "Match their intensity but gradually guide toward calm. Be confident, clear, and direct.",
            "language": "Acknowledge anger directly: 'I hear you', 'That IS frustrating', 'You have every right to feel this way'.",
            "focus": "De-escalate with respect, help them feel in control, solve the problem constructively.",
            "content_strategy": """CONTENT ADAPTATION FOR ANGER:
- Be DIRECT and ACTION-ORIENTED. Angry people want solutions and respect, not sympathy.
- Structure responses as clear action items: 'Here's what we can do about this: 1) ... 2) ... 3) ...'
- Validate their frustration first, then channel it: 'That situation is unfair. Here's how you can address it effectively...'
- Use empowering language: 'You have the power to...', 'Here's how to take control of...'
- For complex topics: Give straightforward, no-nonsense explanations. Skip the fluff.
- Avoid anything that feels patronizing—they need respect and competence right now."""
        },
        "surprised": {
            "tone": "curious, playful, engaging, and genuinely interested",
            "approach": "Match their sense of wonder. Show authentic interest in what surprised them. Help them explore this feeling.",
            "pacing": "Keep energy up and conversation flowing naturally. Lean into the momentum.",
            "language": "Use engaged, curious responses: 'That's fascinating!', 'Tell me more!', 'How did that make you feel?'",
            "focus": "Help them process the surprise and make sense of new discovery.",
            "content_strategy": """CONTENT ADAPTATION FOR SURPRISE:
- Use DISCOVERY-based framing: 'Interesting! Let me unpack this for you...' 'Here's what's happening...'
- Connect surprises to learning: 'You just discovered X, which is actually connected to...'
- Use curiosity-driven examples: 'This relates to Y, isn't that interesting because...'
- For complex topics: Present as 'cool revelations' rather than dry facts. 'Here's something wild about this topic...'
- Build on their engagement: 'Since that surprised you, you might find THIS equally interesting because...'"""
        },
        "neutral": {
            "tone": "balanced, conversational, warm, and genuinely helpful",
            "approach": "Be a thoughtful companion. Offer clear insights without overwhelming. Listen and respond authentically.",
            "pacing": "Keep a natural, comfortable pace. No rushing, no dragging.",
            "language": "Use clear, warm, conversational language. Be real and approachable.",
            "focus": "Provide genuine support and authentic help with whatever they need.",
            "content_strategy": """CONTENT ADAPTATION FOR NEUTRAL:
- Balance CLARITY with warmth. Explain things directly but kindly.
- Use grounded examples that feel real and relatable, not abstract.
- Structure complex information logically: 'There are a few ways to think about this: First... Second... Third...'
- Connect their questions to their lived experience: 'Based on what you shared earlier, here's what I think...'
- Offer perspective without being preachy: 'One way to look at this is...', 'Another angle could be...'"""
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

{guide['content_strategy']}

CRITICAL CONSTRAINTS:
- Keep responses conversational and natural, like a caring friend—not robotic.
- Respond in 1-3 sentences unless they ask for more detail or the emotion requires more explanation.
- Do NOT use emojis, markdown, asterisks, or special formatting (your responses will be spoken aloud).
- Avoid clichés—be genuine and specific to what they share.
- INTEGRATE their emotion with their question: Acknowledge BOTH what they're asking AND how they're feeling.
- Prioritize emotional connection AND appropriate response depth based on their state.
- Remember: You're not just responding to words—you're responding to a person in a specific emotional moment."""

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
