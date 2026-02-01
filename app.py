"""
MangaTranslate MVP - Streamlit App
Translate manga/comic pages with OCR + AI translation

Fixed issues:
1. EasyOCR language compatibility (ch_sim only with en)
2. Cached readers to avoid repeated downloads
3. Auto language detection with safe multi-lang pass
4. Batched OpenAI translation to avoid 429 errors
"""
import io
import streamlit as st
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import easyocr
from typing import List, Tuple

from ocr_utils import box_to_rect, sort_reading_order, merge_nearby_boxes
from translate_utils import translate_batch
from export_utils import export_json, export_csv
from daytona_runner import run_in_daytona, reset_sandbox


# ============================================================================
# EasyOCR Safe Language Handling + Caching
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
    
    # Japanese, Korean - pair with English for better results
    if primary in ("ja", "ko"):
        return [primary, "en"]
    
    # Arabic - can work alone or with English
    if primary == "ar":
        return ["ar", "en"]
    
    # Other languages (fr, es, de, ru, pt, etc.)
    if primary in ("fr", "es", "de", "ru", "pt", "it", "tr"):
        return [primary, "en"]
    
    # Default: just the language
    return [primary if primary else "en"]


@st.cache_resource(show_spinner=False)
def get_easyocr_reader(langs: Tuple[str, ...]):
    """
    Cached EasyOCR reader - downloads models only once per language combination.
    Uses tuple for hashability (required by cache_resource).
    
    IMPORTANT: This prevents repeated 100-500MB downloads on every Streamlit rerun!
    """
    return easyocr.Reader(list(langs), gpu=False)


def run_ocr(img_np: np.ndarray, primary_lang: str):
    """
    Run OCR with a single primary language (safely mapped to compatible list).
    Returns raw EasyOCR results: [(box, text, conf), ...]
    """
    langs = tuple(safe_easyocr_lang_list(primary_lang))
    reader = get_easyocr_reader(langs)
    return reader.readtext(img_np)


def run_ocr_auto(img_np: np.ndarray):
    """
    Auto language detection for manga pages.

    IMPORTANT (EasyOCR limitation):
    - Some scripts (Japanese, Chinese, etc.) are ONLY compatible with English in the same reader.
      Example: for Japanese you must use ["ja","en"], not ["ja","ko","en",...].

    Strategy:
    - Try a few SAFE language configurations one-by-one.
    - Score the OCR results and pick the best.
    """
    def _clean(raw):
        cleaned = []
        for box, text, conf in raw:
            t = (text or "").strip()
            if t:
                cleaned.append((box, t, float(conf)))
        return cleaned

    def _score(raw):
        raw = _clean(raw)
        if not raw:
            return 0.0
        confs = [r[2] for r in raw]
        avg_conf = sum(confs) / max(1, len(confs))
        # Weight both count and confidence
        return len(raw) * avg_conf

    # Most manga pages: Japanese or Chinese. Keep the list short to reduce downloads.
    candidates = ["ja", "ch_sim", "ko", "en", "ar", "fr", "ch_tra"]

    best = {"lang": "en", "raw": [], "score": 0.0}

    for primary in candidates:
        langs = tuple(safe_easyocr_lang_list(primary))
        try:
            reader = get_easyocr_reader(langs)
            raw = reader.readtext(img_np)
        except Exception:
            continue

        s = _score(raw)
        if s > best["score"]:
            best = {"lang": primary, "raw": raw, "score": s}

        # Early exit if we already got a strong result
        if best["score"] >= 6.0 and len(_clean(best["raw"])) >= 8:
            break

    # If best language is English but the content is clearly non-English, it's still OK:
    # translation can run with src="auto" or src=best["lang"] depending on backend.
    return best["lang"], best["raw"]

def draw_numbered_boxes(img: Image.Image, items: list) -> Image.Image:
    """Draw numbered red boxes on image"""
    out = img.convert("RGB").copy()
    draw = ImageDraw.Draw(out)
    
    try:
        font = ImageFont.truetype("DejaVuSans.ttf", 22)
    except Exception:
        font = ImageFont.load_default()

    for item in items:
        i = item["index"]
        box = item["box"]
        x1, y1, x2, y2 = box_to_rect(box)

        # Red rectangle
        draw.rectangle([x1, y1, x2, y2], outline=(255, 0, 0), width=3)
        # Red label background
        draw.rectangle([x1, y1, x1 + 36, y1 + 30], fill=(255, 0, 0))
        # White number
        draw.text((x1 + 7, y1 + 3), str(i), fill=(255, 255, 255), font=font)

    return out


# ============================================================================
# Local Processing
# ============================================================================

def process_local(
    img: Image.Image,
    ocr_lang: str,
    target_lang: str,
    backend: str,
    min_conf: float,
    merge_lines: bool,
    openai_key: str = "",
    openai_model: str = "gpt-4o-mini"
):
    """Process image locally with safe EasyOCR handling"""
    
    img_np = np.array(img.convert("RGB"))
    
    # OCR - handle auto vs manual language selection
    with st.spinner("Running OCR..."):
        if ocr_lang == "auto":
            detected_lang, raw_results = run_ocr_auto(img_np)
            st.info(f"🔍 **Auto-detected language:** {detected_lang}")
        else:
            raw_results = run_ocr(img_np, ocr_lang)
            detected_lang = ocr_lang
    
    # Process results
    items = []
    for box, text, conf in raw_results:
        t = (text or "").strip()
        if not t or conf < min_conf:
            continue
        
        items.append({
            "text": t,
            "box": [(float(p[0]), float(p[1])) for p in box],
            "conf": float(conf)
        })
    
    st.success(f"Found {len(items)} text regions")
    
    if not items:
        st.warning("No text detected. Try adjusting the confidence threshold.")
        return
    
    # Merge nearby boxes if requested
    if merge_lines:
        items = merge_nearby_boxes(items)
        st.info(f"After merging: {len(items)} text regions")
    
    # Sort reading order
    items = sort_reading_order(items)
    
    # Index them
    for idx, item in enumerate(items, start=1):
        item["index"] = idx
    
    # Translate (uses batching for OpenAI to avoid 429)
    with st.spinner(f"Translating to {target_lang}..."):
        items = translate_batch(
            items,
            detected_lang,
            target_lang,
            backend,
            openai_key,
            openai_model
        )
    
    st.success("Translation complete!")
    
    # Draw annotated image
    annotated = draw_numbered_boxes(img, items)
    
    # Display results
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Annotated Image")
        st.image(annotated, use_container_width=True)
    
    with col2:
        st.subheader("Translations")
        for item in items:
            with st.expander(f"#{item['index']} - Confidence: {item['conf']:.2f}"):
                st.write("**Original:**", item["text"])
                st.write("**Translation:**", item.get("translation", "[No translation]"))
    
    # Download buttons
    st.subheader("Downloads")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        buf = io.BytesIO()
        annotated.save(buf, format="PNG")
        st.download_button(
            "📥 Download Annotated PNG",
            buf.getvalue(),
            "annotated.png",
            "image/png"
        )
    
    with col2:
        json_str = export_json(items)
        st.download_button(
            "📥 Download JSON",
            json_str,
            "results.json",
            "application/json"
        )
    
    with col3:
        csv_str = export_csv(items)
        st.download_button(
            "📥 Download CSV",
            csv_str,
            "results.csv",
            "text/csv"
        )


# ============================================================================
# Main UI
# ============================================================================

def main():
    st.title("📖 MangaTranslate MVP")
    st.markdown("""
    Upload a manga or comic page image, and this app will:
    1. Auto-detect or manually select text language
    2. Detect text using OCR (EasyOCR)
    3. Sort text in reading order
    4. Translate to your target language (batched for OpenAI)
    5. Generate annotated image with numbered boxes
    """)
    
    # Sidebar
    with st.sidebar:
        st.header("⚙️ Settings")
        
        # Execution mode
        execution_mode = st.selectbox(
            "Execution Mode",
            ["Local", "Daytona Sandbox"],
            index=0,
            help="Local runs on your machine. Daytona runs in an isolated sandbox for security."
        )
        
        # Daytona settings
        if execution_mode == "Daytona Sandbox":
            st.markdown("---")
            st.subheader("🔒 Daytona Settings")
            
            daytona_key = st.text_input(
                "Daytona API Key",
                type="password",
                help="Get your API key from the Daytona dashboard"
            )
            
            if st.button("🔄 Reset Sandbox"):
                try:
                    reset_sandbox(daytona_key if daytona_key else None)
                    st.success("Sandbox reset! Next run will reinstall dependencies.")
                except Exception as e:
                    st.error(f"Failed to reset sandbox: {e}")
        
        st.markdown("---")
        
        # OCR settings
        st.subheader("🔍 OCR Settings")
        
        ocr_lang = st.selectbox(
            "OCR Language",
            ["auto", "ja", "en", "ar", "ko", "ch_sim", "ch_tra", "fr", "es", "de", "ru", "pt"],
            index=0,
            help="Auto-detect recommended for manga. Manual selection for specific languages."
        )
        
        if ocr_lang == "auto":
            st.info("💡 Two-pass detection: Safe multi-lang first, then Chinese if needed")
        
        min_conf = st.slider(
            "Minimum Confidence",
            0.0, 1.0, 0.35,
            help="Filter out low-confidence detections"
        )
        
        merge_lines = st.checkbox(
            "Merge nearby text boxes",
            value=True,
            help="Combine text boxes that are close together"
        )
        
        st.markdown("---")
        
        # Translation settings
        st.subheader("🌍 Translation Settings")
        
        target_lang = st.selectbox(
            "Target Language",
            ["en", "ar", "fr", "es", "de", "ru", "pt", "ja", "ko", "zh"],
            index=0,
            help="Language to translate to"
        )
        
        backend = st.selectbox(
            "Translation Backend",
            [
                "LibreTranslate (free, may be unreliable)",
                "OpenAI (API key required, batched)"
            ],
            index=0
        )
        
        openai_key = ""
        openai_model = "gpt-4o-mini"
        
        if backend.startswith("OpenAI"):
            openai_key = st.text_input(
                "OpenAI API Key",
                type="password",
                help="Required for OpenAI translation"
            )
            
            openai_model = st.text_input(
                "OpenAI Model",
                value="gpt-4o-mini",
                help="Model to use for translation"
            )
            
            st.info("💡 Batched translation (18 texts/request) reduces API calls and avoids 429 rate limits")
        
        st.markdown("---")
        st.markdown("""
        ### 💡 Quick Start
        1. Upload an image
        2. Keep "auto" language detection
        3. Click "Process Image"
        4. Download results
        """)
    
    # Main content
    uploaded_file = st.file_uploader(
        "Upload Image (PNG/JPG)",
        type=["png", "jpg", "jpeg"],
        help="Upload a manga or comic page"
    )
    
    if uploaded_file is not None:
        img = Image.open(uploaded_file).convert("RGB")
        
        st.image(img, caption="Uploaded Image", use_container_width=True)
        
        if st.button("🚀 Process Image", type="primary"):
            
            if execution_mode == "Daytona Sandbox" and not daytona_key:
                st.error("⚠️ Please provide a Daytona API key in the sidebar")
                st.stop()
            
            if backend.startswith("OpenAI") and not openai_key:
                st.error("⚠️ Please provide an OpenAI API key in the sidebar")
                st.stop()
            
            if execution_mode == "Daytona Sandbox":
                st.info("🔒 Running in Daytona Sandbox (secure, isolated execution)")
                
                try:
                    buf = io.BytesIO()
                    img.save(buf, format="PNG")
                    img_bytes = buf.getvalue()
                    
                    with st.spinner("Processing in Daytona sandbox..."):
                        outputs = run_in_daytona(
                            image_bytes=img_bytes,
                            ocr_lang=ocr_lang,
                            target_lang=target_lang,
                            translator_backend=backend,
                            openai_key=openai_key,
                            openai_model=openai_model,
                            daytona_api_key=daytona_key,
                            min_conf=min_conf,
                            merge_lines=merge_lines
                        )
                    
                    st.success("Processing complete!")
                    
                    annotated = Image.open(io.BytesIO(outputs["annotated_png"]))
                    st.subheader("Annotated Image")
                    st.image(annotated, use_container_width=True)
                    
                    st.subheader("Downloads")
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        st.download_button(
                            "📥 Download Annotated PNG",
                            outputs["annotated_png"],
                            "annotated.png",
                            "image/png"
                        )
                    
                    with col2:
                        st.download_button(
                            "📥 Download JSON",
                            outputs["results_json"],
                            "results.json",
                            "application/json"
                        )
                    
                    with col3:
                        st.download_button(
                            "📥 Download CSV",
                            outputs["results_csv"],
                            "results.csv",
                            "text/csv"
                        )
                
                except Exception as e:
                    st.error(f"❌ Daytona processing failed: {e}")
                    st.info("💡 Try using Local mode or check your Daytona API key")
            
            else:
                st.info("💻 Running locally on your machine")
                process_local(
                    img,
                    ocr_lang,
                    target_lang,
                    backend,
                    min_conf,
                    merge_lines,
                    openai_key,
                    openai_model
                )
    
    else:
        st.info("👆 Upload an image to get started")
    
    st.markdown("---")
    st.markdown("""
    <div style='text-align: center; color: #666;'>
        <p>Built with ❤️ for hackathons • Powered by EasyOCR, Daytona, and Streamlit</p>
        <p><small>✨ Features: Cached EasyOCR readers • Auto language detection • Batched OpenAI translation</small></p>
    </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()
