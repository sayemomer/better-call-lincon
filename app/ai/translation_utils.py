"""
Translation utilities for document extraction.
Detects non-English text and translates to English using the LLM.
"""

import logging
import os

from langdetect import DetectorFactory, detect, LangDetectException

# Seed for deterministic language detection (important for short/ambiguous text)
DetectorFactory.seed = 0

logger = logging.getLogger(__name__)

# Minimum text length to attempt language detection (langdetect is unreliable on very short text)
MIN_TEXT_LENGTH_FOR_DETECTION = 50


def detect_language(text: str) -> str | None:
    """
    Detect the language of the given text.
    Returns ISO 639-1 language code (e.g. 'en', 'fr', 'es') or None if undetectable.
    """
    if not text or len(text.strip()) < MIN_TEXT_LENGTH_FOR_DETECTION:
        return None
    try:
        return detect(text.strip())
    except LangDetectException:
        return None


def translate_to_english(text: str) -> str:
    """
    Translate non-English text to English using the OpenRouter LLM.
    Returns the translated text, or the original if translation fails.
    """
    openrouter_api_key = os.getenv("OPENROUTER_API_KEY")
    if not openrouter_api_key:
        logger.warning("OPENROUTER_API_KEY not set; skipping translation")
        return text

    # OpenRouter expects model ID like "openai/gpt-4o-mini" or "google/gemini-2.0-flash-001"
    # (no "openrouter/" prefix - that's only for litellm routing)
    model = os.getenv("OPENROUTER_MODEL", "google/gemini-2.0-flash-001")
    model = model.removeprefix("openrouter/")  # Strip prefix if set by mistake

    try:
        import httpx

        system_prompt = (
            "You are a professional translator. Translate the following document text to English. "
            "Preserve the original structure, formatting (markdown, headers, lists), dates in YYYY-MM-DD, "
            "and numbers exactly as they appear. For proper nouns (person names, place names), transliterate "
            "to Latin/English spelling (e.g. مهدیه → Mahdieh, شکریان → Shakarian). Output ONLY the translated text, no explanations."
        )
        response = httpx.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={"Authorization": f"Bearer {openrouter_api_key}"},
            json={
                "model": model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": text},
                ],
            },
            timeout=60.0,
        )
        response.raise_for_status()
        data = response.json()
        translated = data["choices"][0]["message"]["content"]
        if translated and translated.strip():
            return translated.strip()
    except Exception as e:
        logger.warning("Translation failed: %s; using original text", e)

    return text


def ensure_english(text: str) -> str:
    """
    If the text is in a language other than English, translate it to English.
    Returns the original text if already English, or the translated text.
    """
    lang = detect_language(text)
    if lang is None:
        # Assume English if we can't detect (e.g. short text, mixed content)
        return text
    if lang == "en":
        return text
    logger.info("Detected non-English language '%s'; translating to English", lang)
    return translate_to_english(text)
