"""
Sandbox worker - runs inside Daytona sandbox
Performs OCR, translation, and exports

Fixed issues:
1. Safe EasyOCR language handling (ch_sim only with en)
2. Batched OpenAI translation to avoid 429 errors
3. Auto language detection support
4. Proper error handling and retries
"""
import argparse
import json
import random
import time
from typing import List, Dict

import numpy as np
from PIL import Image, ImageDraw, ImageFont
import pandas as pd
import easyocr
import requests

def safe_easyocr_lang_list(primary: str):
    """
    Build a SAFE EasyOCR language list.

    EasyOCR has compatibility constraints:
    - ja requires ["ja","en"]
    - ko requires ["ko","en"]
    - ch_sim requires ["ch_sim","en"]
    - ch_tra requires ["ch_tra","en"]
    """
    p = (primary or "").strip().lower()
    if p in ("ja", "japanese"):
        return ["ja", "en"]
    if p in ("ko", "korean"):
        return ["ko", "en"]
    if p in ("ch_sim", "zh", "zh-cn", "chinese_sim"):
        return ["ch_sim", "en"]
    if p in ("ch_tra", "zh-tw", "zh-hant", "chinese_tra"):
        return ["ch_tra", "en"]
    if p in ("ar", "arabic"):
        return ["ar", "en"]
    if p in ("fr", "french"):
        return ["fr", "en"]
    # default
    return [p] if p else ["en"]


def run_ocr_auto(img_np: np.ndarray):
    """
    Try safe language configs one-by-one and pick the best OCR score.
    """
    def _clean(raw):
        out = []
        for box, text, conf in raw:
            t = (text or "").strip()
            if t:
                out.append((box, t, float(conf)))
        return out

    def _score(raw):
        raw = _clean(raw)
        if not raw:
            return 0.0
        confs = [r[2] for r in raw]
        avg_conf = sum(confs) / max(1, len(confs))
        return len(raw) * avg_conf

    candidates = ["ja", "ch_sim", "ko", "en", "ar", "fr", "ch_tra"]
    best_lang = "en"
    best_raw = []
    best_score = 0.0

    for primary in candidates:
        langs = safe_easyocr_lang_list(primary)
        try:
            reader = easyocr.Reader(langs, gpu=False)
            raw = reader.readtext(img_np)
        except Exception:
            continue

        s = _score(raw)
        if s > best_score:
            best_score, best_lang, best_raw = s, primary, raw

        if best_score >= 6.0 and len(_clean(best_raw)) >= 8:
            break

    return best_lang, best_raw


# ============================================================================
# EasyOCR Safe Language Handling
# ============================================================================

def safe_easyocr_lang_list(primary: str) -> List[str]:
    """
    Return EasyOCR-compatible language list.
    Critical: Chinese (ch_sim/ch_tra) ONLY works with English.
    """
    primary = (primary or "en").strip().lower()
    
    # Chinese must be paired ONLY with English
    if primary in ("ch_sim", "ch_tra", "zh_sim", "zh_tra"):
        return ["ch_sim", "en"] if primary.startswith("ch_sim") or primary == "zh_sim" else ["ch_tra", "en"]
    
    # Japanese, Korean - pair with English
    if primary in ("ja", "ko"):
        return [primary, "en"]
    
    # Arabic
    if primary == "ar":
        return ["ar", "en"]
    
    # Other languages
    if primary in ("fr", "es", "de", "ru", "pt", "it", "tr"):
        return [primary, "en"]
    
    return [primary if primary else "en"]


def run_ocr(img_np: np.ndarray, primary_lang: str):
    """Run OCR with safe language list"""
    langs = safe_easyocr_lang_list(primary_lang)
    reader = easyocr.Reader(langs, gpu=False)
    return reader.readtext(img_np)


def run_ocr_auto(img_np: np.ndarray):
    """
    Auto language detection:
    Pass 1: Safe multi-lang (no Chinese)
    Pass 2: Chinese if needed
    """
    # Pass 1
    reader1 = easyocr.Reader(["ja", "ko", "en", "ar", "fr"], gpu=False)
    raw1 = reader1.readtext(img_np)
    
    if len(raw1) >= 4:
        return "auto", raw1
    
    # Pass 2: Chinese
    raw2 = run_ocr(img_np, "ch_sim")
    
    if len(raw2) > len(raw1):
        return "ch_sim", raw2
    
    return "auto", raw1


# ============================================================================
# OCR Utilities
# ============================================================================

def box_to_rect(box):
    """Convert 4-point box to rectangle"""
    xs = [p[0] for p in box]
    ys = [p[1] for p in box]
    return min(xs), min(ys), max(xs), max(ys)


def rect_center(rect):
    """Get center of rectangle"""
    x1, y1, x2, y2 = rect
    return (x1 + x2) / 2.0, (y1 + y2) / 2.0


def sort_reading_order(items):
    """Sort items in reading order"""
    if not items:
        return items
    
    centers = [((rect_center(box_to_rect(it["box"]))), it) for it in items]
    ys = [c[0][1] for c in centers]
    y_span = max(ys) - min(ys) if ys else 1.0
    row_bucket = max(12.0, y_span / 20.0)

    def row_key(y):
        return int(y // row_bucket)

    buckets = {}
    for (cx, cy), it in centers:
        buckets.setdefault(row_key(cy), []).append(((cx, cy), it))

    ordered = []
    for rk in sorted(buckets.keys()):
        row_sorted = sorted(buckets[rk], key=lambda t: t[0][0])
        ordered.extend([it for _, it in row_sorted])
    
    return ordered


def merge_nearby_boxes(items, threshold=50.0):
    """Merge nearby text boxes"""
    if not items or len(items) <= 1:
        return items
    
    merged = []
    skip = set()
    
    for i, item in enumerate(items):
        if i in skip:
            continue
        
        rect_i = box_to_rect(item["box"])
        cx_i, cy_i = rect_center(rect_i)
        to_merge = [item]
        
        for j in range(i + 1, len(items)):
            if j in skip:
                continue
            
            rect_j = box_to_rect(items[j]["box"])
            cx_j, cy_j = rect_center(rect_j)
            
            if abs(cy_i - cy_j) < threshold / 2 and abs(cx_i - cx_j) < threshold * 2:
                to_merge.append(items[j])
                skip.add(j)
        
        if len(to_merge) == 1:
            merged.append(item)
        else:
            merged_text = " ".join([it["text"] for it in to_merge])
            all_boxes = [box_to_rect(it["box"]) for it in to_merge]
            
            x1 = min([b[0] for b in all_boxes])
            y1 = min([b[1] for b in all_boxes])
            x2 = max([b[2] for b in all_boxes])
            y2 = max([b[3] for b in all_boxes])
            
            merged_box = [[x1, y1], [x2, y1], [x2, y2], [x1, y2]]
            avg_conf = sum([it["conf"] for it in to_merge]) / len(to_merge)
            
            merged.append({
                "text": merged_text,
                "box": merged_box,
                "conf": avg_conf
            })
    
    return merged


# ============================================================================
# Translation
# ============================================================================

def translate_libre(text, src, tgt):
    """Translate using LibreTranslate"""
    try:
        url = "https://libretranslate.com/translate"
        r = requests.post(
            url,
            json={"q": text, "source": src, "target": tgt, "format": "text"},
            headers={"Content-Type": "application/json"},
            timeout=25
        )
        if r.ok:
            return r.json().get("translatedText", text)
        return text
    except Exception:
        return text


def translate_openai_batch(texts, src, tgt, key, model, max_retries=5):
    """
    Batched OpenAI translation to avoid 429 errors.
    Translates all texts in ONE request.
    """
    if not key:
        return [f"[Missing OpenAI key] {t}" for t in texts]

    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json"
    }

    # Normalize language codes
    lang_map = {"ch_sim": "zh", "ch_tra": "zh", "zh_sim": "zh", "zh_tra": "zh"}
    src = lang_map.get(src, src)
    tgt = lang_map.get(tgt, tgt)

    user_payload = {
        "source_language": src,
        "target_language": tgt,
        "segments": texts,
        "instructions": "Return ONLY valid JSON with key 'translations' (array of strings), same length as segments."
    }

    messages = [
        {
            "role": "system",
            "content": "You are a precise translator. Output strictly as JSON only, no markdown."
        },
        {
            "role": "user",
            "content": json.dumps(user_payload, ensure_ascii=False)
        },
    ]

    last_err = None
    
    for attempt in range(max_retries):
        try:
            payload = {
                "model": model,
                "messages": messages,
                "temperature": 0.2
            }
            r = requests.post(url, headers=headers, json=payload, timeout=90)

            # Handle 429 with exponential backoff
            if r.status_code == 429:
                retry_after = r.headers.get("Retry-After")
                if retry_after and retry_after.isdigit():
                    sleep_s = int(retry_after)
                else:
                    sleep_s = (2 ** attempt) + random.random()
                
                sleep_s = min(30, sleep_s)
                last_err = f"429 rate limit (attempt {attempt+1}/{max_retries})"
                print(f"[OpenAI] {last_err}, waiting {sleep_s:.1f}s")
                time.sleep(sleep_s)
                continue

            if not r.ok:
                last_err = f"OpenAI error {r.status_code}"
                print(f"[OpenAI] {last_err}")
                break

            # Parse response
            content = r.json()["choices"][0]["message"]["content"].strip()

            # Remove markdown fences
            if content.startswith("```"):
                content = content.strip("`")
                if content.startswith("json"):
                    content = content[4:].strip()

            data = json.loads(content)
            translations = data.get("translations")
            
            if not isinstance(translations, list) or len(translations) != len(texts):
                raise ValueError("Bad JSON shape/length")
            
            return [str(t) if t is not None else texts[i] for i, t in enumerate(translations)]

        except Exception as e:
            last_err = str(e)
            print(f"[OpenAI] Error: {last_err}")
            time.sleep(min(10, 1.5 + attempt))

    # Fallback
    tag = f"[OpenAI failed: {last_err}]" if last_err else "[OpenAI failed]"
    return [f"{tag} {t}" for t in texts]


# ============================================================================
# Drawing
# ============================================================================

def draw_numbered_boxes(img: Image.Image, items: List[Dict]) -> Image.Image:
    """Draw numbered boxes on image"""
    out = img.convert("RGB").copy()
    draw = ImageDraw.Draw(out)
    
    try:
        font = ImageFont.truetype("DejaVuSans.ttf", 22)
    except Exception:
        font = ImageFont.load_default()

    for it in items:
        i = it["index"]
        box = it["box"]
        x1, y1, x2, y2 = box_to_rect(box)

        draw.rectangle([x1, y1, x2, y2], outline=(255, 0, 0), width=3)
        draw.rectangle([x1, y1, x1 + 36, y1 + 30], fill=(255, 0, 0))
        draw.text((x1 + 7, y1 + 3), str(i), fill=(255, 255, 255), font=font)

    return out


# ============================================================================
# Main
# ============================================================================

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--image", required=True)
    ap.add_argument("--ocr_lang", required=True)
    ap.add_argument("--target_lang", required=True)
    ap.add_argument("--backend", required=True)
    ap.add_argument("--min_conf", type=float, default=0.35)
    ap.add_argument("--merge_lines", action="store_true")
    ap.add_argument("--openai_key", default="")
    ap.add_argument("--openai_model", default="gpt-4o-mini")
    args = ap.parse_args()

    # Load image
    img = Image.open(args.image).convert("RGB")
    img_np = np.array(img)

    # OCR
    print(f"Running OCR with language: {args.ocr_lang}")
    
    if args.ocr_lang == "auto":
        detected_lang, raw = run_ocr_auto(img_np)
        print(f"Auto-detected language: {detected_lang}")
        ocr_lang = detected_lang
    else:
        raw = run_ocr(img_np, args.ocr_lang)
        ocr_lang = args.ocr_lang

    # Process OCR results
    items = []
    for box, text, conf in raw:
        t = (text or "").strip()
        if not t or conf < args.min_conf:
            continue
        
        items.append({
            "text": t,
            "box": [(float(p[0]), float(p[1])) for p in box],
            "conf": float(conf)
        })

    print(f"Found {len(items)} text regions")

    # Merge nearby boxes if requested
    if args.merge_lines:
        items = merge_nearby_boxes(items)
        print(f"After merging: {len(items)} text regions")

    # Sort reading order
    items = sort_reading_order(items)

    # Index them
    for idx, it in enumerate(items, start=1):
        it["index"] = idx

    # Translate (batched for OpenAI)
    print(f"Translating to {args.target_lang} using {args.backend}")
    
    if args.backend.startswith("OpenAI"):
        # Batch all texts together
        texts = [it["text"] for it in items]
        batch_size = 18
        
        all_translations = []
        for i in range(0, len(texts), batch_size):
            chunk = texts[i:i+batch_size]
            print(f"Translating batch {i//batch_size + 1} ({len(chunk)} texts)...")
            
            translations = translate_openai_batch(
                chunk,
                ocr_lang,
                args.target_lang,
                args.openai_key,
                args.openai_model
            )
            all_translations.extend(translations)
        
        # Attach translations
        for it, tr in zip(items, all_translations):
            it["translation"] = tr
    else:
        # LibreTranslate (one-by-one)
        for it in items:
            it["translation"] = translate_libre(
                it["text"],
                ocr_lang,
                args.target_lang
            )

    # Draw annotated image
    annotated = draw_numbered_boxes(img, items)
    annotated.save("annotated.png", format="PNG")
    print("Saved annotated.png")

    # Export JSON
    with open("results.json", "w", encoding="utf-8") as f:
        json.dump({"items": items}, f, ensure_ascii=False, indent=2)
    print("Saved results.json")

    # Export CSV
    df = pd.DataFrame([{
        "index": it["index"],
        "text": it["text"],
        "translation": it["translation"],
        "conf": it["conf"],
        "box": it["box"]
    } for it in items])
    df.to_csv("results.csv", index=False)
    print("Saved results.csv")


if __name__ == "__main__":
    main()
