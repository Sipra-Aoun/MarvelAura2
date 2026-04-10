import httpx
from backend.config import settings


async def generate_ollama_response(user_text: str, system_prompt: str) -> str:
    """
    Generate a response from a local Ollama model using the /api/chat endpoint.
    """
    if not user_text or not user_text.strip():
        return ""

    base_url = settings.OLLAMA_BASE_URL.rstrip('/')
    url = f"{base_url}/api/chat"

    payload = {
        "model": settings.OLLAMA_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_text}
        ],
        "stream": False,
        "options": {
            "temperature": 0.7,
            "num_predict": 350
        }
    }

    timeout = httpx.Timeout(60.0, connect=5.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.post(url, json=payload)
        response.raise_for_status()
        data = response.json()

    message = data.get("message", {})
    content = message.get("content", "") if isinstance(message, dict) else ""
    if not content:
        raise Exception("Ollama returned an empty response")

    return content.strip()
