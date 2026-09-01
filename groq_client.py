"""
groq_client.py
Talks to the Groq API to generate a short stoic/motivational quote plus
matching hashtags. Returns clean, already-validated data — callers never
need to touch raw Groq output.
"""

import json
import re

import requests

from config import GROQ_API_KEY, GROQ_API_URL, GROQ_MODEL, MAX_QUOTE_WORDS, MIN_HASHTAGS, MAX_HASHTAGS

_SYSTEM_PROMPT = f"""You write short, powerful, stoic motivational quotes for a
dark-aesthetic TikTok text-post account. Rules:
- The quote must be original, not a famous existing quote, and under {MAX_QUOTE_WORDS} words.
- Tone: stoic, disciplined, no-excuses, dark/serious — not cheesy or corny.
- No emojis, no quotation marks around the quote text.
- Also generate {MIN_HASHTAGS}-{MAX_HASHTAGS} relevant hashtags (no # symbol needed, just the words).
Respond ONLY with valid JSON in this exact shape, nothing else before or after:
{{"quote": "...", "hashtags": ["word1", "word2", "word3"]}}
"""


class GroqGenerationError(Exception):
    pass


def _call_groq(avoid_quotes: list[str] | None = None) -> dict:
    if not GROQ_API_KEY:
        raise GroqGenerationError("GROQ_API_KEY is not set in the environment.")

    user_prompt = "Generate one new quote and its hashtags."
    if avoid_quotes:
        avoid_list = "; ".join(avoid_quotes[-5:])  # keep prompt short
        user_prompt += f" Do NOT repeat or closely reword any of these already-used quotes: {avoid_list}"

    response = requests.post(
        GROQ_API_URL,
        headers={
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json",
        },
        json={
            "model": GROQ_MODEL,
            "messages": [
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 1.0,  # higher temp = more variety, helps avoid repeats
            "response_format": {"type": "json_object"},
        },
        timeout=30,
    )
    response.raise_for_status()
    raw_content = response.json()["choices"][0]["message"]["content"]

    try:
        data = json.loads(raw_content)
    except json.JSONDecodeError as exc:
        raise GroqGenerationError(f"Groq did not return valid JSON: {raw_content!r}") from exc

    return data


def _validate(data: dict) -> tuple[str, list[str]]:
    quote = str(data.get("quote", "")).strip()
    hashtags = data.get("hashtags", [])

    if not quote:
        raise GroqGenerationError("Groq returned an empty quote.")

    word_count = len(quote.split())
    if word_count > MAX_QUOTE_WORDS:
        raise GroqGenerationError(f"Quote too long ({word_count} words): {quote!r}")

    if not isinstance(hashtags, list) or len(hashtags) < MIN_HASHTAGS:
        raise GroqGenerationError(f"Not enough hashtags returned: {hashtags!r}")

    # Clean hashtags: strip whitespace/#, drop empties, dedupe
    cleaned = []
    for tag in hashtags[:MAX_HASHTAGS]:
        tag = re.sub(r"[^A-Za-z0-9_]", "", str(tag))
        if tag and tag.lower() not in [c.lower() for c in cleaned]:
            cleaned.append(tag)

    if len(cleaned) < MIN_HASHTAGS:
        raise GroqGenerationError(f"Not enough valid hashtags after cleaning: {cleaned!r}")

    return quote, cleaned


def generate_quote(avoid_quotes: list[str] | None = None) -> dict:
    """
    Returns {"quote": str, "hashtags": list[str]}.
    Raises GroqGenerationError on any bad/invalid response — caller decides
    whether to retry.
    """
    raw = _call_groq(avoid_quotes=avoid_quotes)
    quote, hashtags = _validate(raw)
    return {"quote": quote, "hashtags": hashtags}
