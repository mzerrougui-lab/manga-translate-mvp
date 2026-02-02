"""
Translation utilities with batched OpenAI to avoid 429 rate limits

Fixed issues:
1. Batched translation (18 texts per request) instead of 1-per-request
2. Exponential backoff with retries on 429 errors
3. Proper JSON parsing with fallback handling
4. Language detection using Unicode ranges
"""
from __future__ import annotations

import json
import random
import time
from typing import List, Dict, Optional

import requests


# ============================================================================
# Language Detection (Unicode-based heuristics)
# ============================================================================

def detect_batch_language(items: List[Dict]) -> str:
    """
    Heuristic language detection based on Unicode ranges in the OCR text.
    Returns: "en", "ar", "ja", "ko", "ch_sim", "fr"
    """
    text = " ".join([(it.get("text") or "") for it in items]).strip()
    if not text:
        return "en"

    def has_range(lo: int, hi: int) -> bool:
        return any(lo <= ord(ch) <= hi for ch in text)

    # Arabic (0x0600-0x06FF, 0x0750-0x077F)
    if has_range(0x0600, 0x06FF) or has_range(0x0750, 0x077F):
        return "ar"

    # Japanese Kana (Hiragana: 0x3040-0x309F, Katakana: 0x30A0-0x30FF)
    if has_range(0x3040, 0x309F) or has_range(0x30A0, 0x30FF):
        return "ja"

    # Korean Hangul (0xAC00-0xD7AF)
    if has_range(0xAC00, 0xD7AF):
        return "ko"

    # CJK Unified Ideographs (0x4E00-0x9FFF) - Chinese or Japanese Kanji
    # If no kana/hangul, assume Chinese
    if has_range(0x4E00, 0x9FFF):
        return "ch_sim"

    # French detection (basic - looks for accented characters)
    if has_range(0x00C0, 0x00FF):  # Latin-1 Supplement (includes é, è, à, etc.)
        return "fr"

    # Default: English
    return "en"


# ============================================================================
# LibreTranslate (free, single-request fallback)
# ============================================================================

def translate_libre(text: str, src: str, tgt: str) -> str:
    """
    Translate using LibreTranslate (public endpoint).
    May be unreliable or rate-limited.
    """
    try:
        url = "https://libretranslate.com/translate"
        data = {"q": text, "source": src, "target": tgt, "format": "text"}
        r = requests.post(url, json=data, headers={"Content-Type": "application/json"}, timeout=25)
        if r.ok:
            return r.json().get("translatedText", text)
        return text
    except Exception:
        return text


# ============================================================================
# OpenAI Chat Completions (batched with retries)
# ============================================================================

def _openai_chat_completions(
    api_key: str,
    model: str,
    messages: List[Dict],
    timeout_s: int = 90,
) -> requests.Response:
    """Make OpenAI chat completion request"""
    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": model,
        "messages": messages,
        "temperature": 0.2,
    }
    return requests.post(url, headers=headers, json=payload, timeout=timeout_s)


def translate_openai_batch(
    texts: List[str],
    src: str,
    tgt: str,
    api_key: str,
    model: str = "gpt-4o-mini",
    max_retries: int = 5,
) -> List[str]:
    """
    Translate a batch of texts with ONE OpenAI request.
    
    This is critical for avoiding 429 rate limits:
    - Before: N requests for N texts = high 429 probability
    - After: 1 request for N texts = much lower 429 probability
    
    Returns: List of translations (same length as input)
    """
    if not api_key:
        return [f"[Missing OpenAI key] {t}" for t in texts]

    # Normalize language codes for better prompt clarity
    lang_map = {
        "ch_sim": "zh",
        "ch_tra": "zh",
        "zh_sim": "zh",
        "zh_tra": "zh",
    }
    src = lang_map.get(src, src)
    tgt = lang_map.get(tgt, tgt)

    # Build strict JSON-only prompt
    user_payload = {
        "source_language": src,
        "target_language": tgt,
        "segments": texts,
        "instructions": "Return ONLY valid JSON with key 'translations' (array of strings), same length as segments. No extra text."
    }

    messages = [
        {
            "role": "system",
            "content": "You are a precise translator. Output strictly as JSON only, no markdown, no explanations."
        },
        {
            "role": "user",
            "content": json.dumps(user_payload, ensure_ascii=False)
        },
    ]

    last_err = None
    
    for attempt in range(max_retries):
        try:
            r = _openai_chat_completions(api_key, model, messages, timeout_s=90)
            
            # Handle 429 rate limit with exponential backoff (and detect quota errors)
            if r.status_code == 429:
                # Check for quota issues
                try:
                    err = r.json().get("error", {}) if r.content else {}
                    if "insufficient_quota" in str(err):
                        last_err = "insufficient_quota"
                        break
                except Exception:
                    pass

                retry_after = r.headers.get("Retry-After")
                if retry_after and retry_after.isdigit():
                    sleep_s = int(retry_after)
                else:
                    sleep_s = (2 ** attempt) + (random.random() * 1.5)

                sleep_s = min(45, sleep_s)
                last_err = f"429 rate limit (attempt {attempt+1}/{max_retries}), waiting {sleep_s:.1f}s"
                print(f"[OpenAI] {last_err}")
                time.sleep(sleep_s)
                continue
            
            if not r.ok:
                last_err = f"OpenAI error {r.status_code}: {r.text[:200]}"
                print(f"[OpenAI] {last_err}")
                break

            # Parse response
            content = r.json()["choices"][0]["message"]["content"].strip()

            # Remove markdown code fences if present
            if content.startswith("```"):
                content = content.strip("`")
                if content.startswith("json"):
                    content = content[4:].strip()

            # Parse JSON
            data = json.loads(content)
            translations = data.get("translations")
            
            # Validate
            if not isinstance(translations, list) or len(translations) != len(texts):
                raise ValueError(f"Bad JSON shape: expected list of {len(texts)}")
            
            # Ensure all are strings
            return [str(t) if t is not None else texts[i] for i, t in enumerate(translations)]

        except json.JSONDecodeError as e:
            last_err = f"JSON parse error: {e}"
            print(f"[OpenAI] {last_err}")
            time.sleep(min(10, 1.5 + attempt))
            
        except Exception as e:
            last_err = f"Unexpected error: {e}"
            print(f"[OpenAI] {last_err}")
            time.sleep(min(10, 1.5 + attempt))

    # Failure fallback
    tag = f"[OpenAI failed: {last_err}]" if last_err else "[OpenAI failed]"
    print(f"[OpenAI] Giving up after {max_retries} retries: {tag}")
    return [f"{tag} {t}" for t in texts]


# ============================================================================
# Main Translation Function (with batching)
# ============================================================================

def translate_batch(
    items: List[Dict],
    ocr_lang: str,
    target_lang: str,
    backend: str,
    openai_key: str = "",
    openai_model: str = "gpt-4o-mini",
    batch_size: int = 18,
) -> List[Dict]:
    """
    Translate OCR items using selected backend.
    
    For OpenAI: Translates in batches of ~18 to:
    - Reduce total API calls
    - Avoid 429 rate limits
    - Stay within reasonable token limits
    """
    if not items:
        return items

    texts = [(it.get("text") or "").strip() for it in items]

    # OpenAI (Batched)
    if backend.startswith("OpenAI"):
        translated_texts: List[str] = []
        
        # Process in batches to reduce API calls
        for i in range(0, len(texts), batch_size):
            chunk = texts[i : i + batch_size]
            print(f"[OpenAI] Translating batch {i//batch_size + 1} ({len(chunk)} items)...")
            
            chunk_results = translate_openai_batch(
                chunk,
                ocr_lang,
                target_lang,
                api_key=openai_key,
                model=openai_model,
            )
            
            # Per-item fallback check
            for original, result in zip(chunk, chunk_results):
                if result.startswith("[OpenAI failed"):
                    try:
                        # Attempt fallback (LibreTranslate)
                        fallback = translate_libre(original, src=ocr_lang, tgt=target_lang)
                        translated_texts.append(fallback)
                    except Exception:
                        translated_texts.append(result)
                else:
                    translated_texts.append(result)

            # Small pacing
            time.sleep(0.5)

        for i, item in enumerate(items):
            item["translation"] = translated_texts[i] if i < len(translated_texts) else item.get("text", "")

        return items
        
    else:
        # LibreTranslate (one-by-one)
        for item in items:
            t = (item.get("text") or "").strip()
            item["translation"] = translate_libre(t, src=ocr_lang, tgt=target_lang)
        return items
