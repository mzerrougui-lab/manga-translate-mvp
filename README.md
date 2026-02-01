# MangaTranslate MVP (Streamlit)

A simple “manga page translator” MVP:
- Upload a manga page image
- Detect text regions (speech bubbles / captions) using **EasyOCR**
- Extract text (OCR)
- Translate the extracted text using **OpenAI** (recommended) or **LibreTranslate**
- Export results as **JSON / CSV** + a preview image with numbered boxes

> Note: This project focuses on a clean pipeline + export. It does **not** do perfect bubble cleaning / inpainting yet (that’s a future upgrade).

---

## How it works (pipeline)

1) **Image upload** (PNG/JPG)  
2) **OCR (EasyOCR)**  
   - Finds text boxes + reads text
   - The app uses “safe language combos” internally because EasyOCR has compatibility rules (e.g., Japanese/Chinese models require pairing with English).
3) **Language detection (heuristic)**  
   - If you choose Auto mode, the app guesses the source language from detected characters (Arabic/Japanese/Korean/Chinese/etc.).
4) **Translation**
   - **OpenAI**: translates text (can be sequential to reduce 429 rate limits).
   - **LibreTranslate**: fallback option (public instances may throttle or be unstable).
5) **Export**
   - `results.json` and `results.csv`
   - `annotated.png` (numbered bounding boxes so you can review reading order)

---

## Run on Windows (no terminal commands)

1) Download/clone the repo  
2) Double-click:
- `install.bat` (first time)
- `start.bat` (every time you want to run)

Then open:
- http://localhost:8501

---

## API keys (translation)

### OpenAI (recommended)
You need an OpenAI API key to translate with OpenAI.
- Put it in the app UI when asked, **or**
- Set environment variable: `OPENAI_API_KEY`

If you see **OpenAI error: 429**, it means you hit rate limits (too many requests / not enough quota). Fixes:
- Use **sequential translation**
- Translate fewer bubbles per run
- Wait a bit and retry
- Make sure your key has billing/quota enabled in your OpenAI account

### LibreTranslate (fallback)
LibreTranslate public endpoints are often rate-limited and sometimes return the same text unchanged.
If you want stable LibreTranslate, you usually need a **self-hosted** instance or a paid endpoint.

---

## Daytona mode (optional)

If you enable the Daytona path:
- OCR + translation can run inside a Daytona sandbox (isolated execution)
- Useful for hackathon story: “we run untrusted processing in a secure isolated environment”

You still need the same translation API key (OpenAI / LibreTranslate).

---

## Known limitations (honest notes)

- OCR quality depends heavily on image clarity, font style, and resolution.
- Reading order is a heuristic (numbered boxes help you verify).
- OpenAI can rate limit (429) depending on your plan/quota.
- LibreTranslate public endpoints may fail or return unchanged text.
- This MVP does not yet erase original bubble text or typeset translated text into bubbles.

---

## Built with

- Python
- Streamlit (UI)
- EasyOCR (OCR)
- OpenAI API (translation)
- LibreTranslate (optional fallback)
- Pillow / NumPy / Pandas (image + exports)

---

## Project structure (main files)

- `app.py` — Streamlit UI + pipeline
- `ocr_utils.py` — OCR helpers + safe language handling
- `translate_utils.py` — translation backends + retry logic
- `export_utils.py` — JSON/CSV/image export helpers
- `sandbox_worker.py` — Daytona sandbox worker (optional)
- `install.bat`, `start.bat` — Windows launchers

---

## License

See `LICENSE`.
