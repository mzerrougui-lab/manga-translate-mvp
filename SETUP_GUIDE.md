# 🚀 MangaTranslate MVP - Complete Setup Guide

## For Hackathon Judges & Testers

This guide will get you up and running in **under 5 minutes**.

---

## ⚡ Super Quick Start (Windows)

1. **Download** this entire folder
2. **Double-click** `start.bat`
3. **Wait** for the browser to open automatically
4. **Upload** a manga/comic image
5. **Click** "Process Image"

Done! 🎉

---

## 📋 Detailed Setup Instructions

### Prerequisites

- **Windows 10/11** (recommended)
- **Python 3.8 or higher**
  - Download from: https://www.python.org/downloads/
  - ⚠️ During installation, check "Add Python to PATH"

### Step 1: Install Python (if needed)

1. Go to https://www.python.org/downloads/
2. Download Python 3.11 (recommended)
3. Run the installer
4. **IMPORTANT**: Check "Add Python to PATH" box
5. Click "Install Now"
6. Wait for installation to complete

### Step 2: Verify Python Installation

Open Command Prompt (Win+R, type `cmd`, press Enter):

```bash
python --version
```

Should show: `Python 3.x.x`

If not, restart your computer and try again.

### Step 3: Run the App

**Option A: Double-Click Method** ⭐ RECOMMENDED

1. Navigate to the `manga-translate-mvp` folder
2. Double-click `start.bat`
3. A terminal window will open
4. Wait 2-3 minutes for first-time setup
5. Browser will open automatically to http://localhost:8501

**Option B: Manual Method**

Open Command Prompt in the project folder:

```bash
# Create virtual environment
python -m venv .venv

# Activate it
.venv\Scripts\activate

# Install dependencies (takes 2-3 minutes)
pip install -r requirements.txt

# Run the app
streamlit run app.py
```

### Step 4: Use the App

1. **Upload an image**
   - Click "Browse files"
   - Select a manga/comic page (PNG or JPG)

2. **Configure settings** (sidebar)
   - Execution mode: Start with "Local"
   - OCR language: Choose your image's language
   - Target language: Choose translation language

3. **Click "Process Image"**
   - Wait for OCR to complete
   - View annotated result
   - Download outputs

---

## 🔧 Optional: Daytona Sandbox Setup

For secure, isolated execution:

1. **Get Daytona API Key**
   - Sign up at https://www.daytona.io
   - Navigate to API settings
   - Generate a new API key
   - Copy it

2. **Configure in App**
   - In sidebar, select "Daytona Sandbox"
   - Paste your API key
   - First run will take ~2 minutes (installs dependencies)

3. **Process Images Securely**
   - All processing happens in isolated sandbox
   - No local dependencies conflicts
   - Reproducible environment

---

## 🔑 Optional: OpenAI Translation Setup

For better translation quality:

1. **Get OpenAI API Key**
   - Sign up at https://platform.openai.com
   - Navigate to API keys
   - Create new secret key
   - Copy it

2. **Configure in App**
   - Select "OpenAI" in translation backend
   - Paste your API key
   - Choose model (default: gpt-4o-mini)

---

## 🧪 Testing the App

### Test with Local Mode (No API keys needed)

1. Upload any manga/comic image
2. Select "Local" execution mode
3. OCR language: "ja" (Japanese) or "en" (English)
4. Target language: "en" or "ar"
5. Translation: "LibreTranslate (free)"
6. Click "Process Image"

Expected results:
- Annotated image with red numbered boxes
- Side-by-side original and translated text
- Downloadable PNG, JSON, and CSV files

### Test with Daytona Mode (Requires Daytona API key)

1. Same as above, but select "Daytona Sandbox"
2. Enter your Daytona API key
3. First run takes longer (installing dependencies)
4. Subsequent runs are faster (reuses sandbox)

---

## 🐛 Common Issues & Solutions

### Issue: "Python is not recognized"

**Solution**: 
1. Reinstall Python with "Add to PATH" checked
2. OR manually add Python to PATH:
   - Search "Environment Variables" in Windows
   - Edit "Path" under System Variables
   - Add: `C:\Users\YourName\AppData\Local\Programs\Python\Python311`

### Issue: "pip is not recognized"

**Solution**: Same as above, also add:
- `C:\Users\YourName\AppData\Local\Programs\Python\Python311\Scripts`

### Issue: start.bat shows error

**Solution**: 
1. Open Command Prompt
2. Navigate to project folder: `cd path\to\manga-translate-mvp`
3. Run manually:
   ```bash
   python -m venv .venv
   .venv\Scripts\activate
   pip install -r requirements.txt
   streamlit run app.py
   ```

### Issue: "EasyOCR is taking forever"

**Solution**: This is normal on first run. EasyOCR downloads language models (~100-500MB). Wait it out. Subsequent runs are much faster.

### Issue: "No text detected"

**Solutions**:
1. Lower confidence threshold (try 0.2)
2. Ensure image has clear text
3. Select correct OCR language
4. Try a different image

### Issue: "Translation failed"

**Solutions**:
1. If using LibreTranslate: It's free but unreliable. Try again or use OpenAI.
2. If using OpenAI: Check API key is valid and has credits
3. Check internet connection

---

## 📊 What to Test

### Basic Functionality
- ✅ Upload PNG image
- ✅ Upload JPG image
- ✅ Process with Local mode
- ✅ Download annotated PNG
- ✅ Download JSON results
- ✅ Download CSV results

### Advanced Features
- ✅ Process with Daytona mode
- ✅ Use OpenAI translation
- ✅ Merge nearby text boxes
- ✅ Adjust confidence threshold
- ✅ Multiple languages (ja, en, fr, es, ko, zh)

### Edge Cases
- ✅ Very small text
- ✅ Very large images
- ✅ Low-quality scans
- ✅ Multiple text regions
- ✅ Empty images (no text)

---

## 📈 Performance Expectations

| Operation | Local Mode | Daytona Mode |
|-----------|------------|--------------|
| First run | 30-60s | 2-3 minutes |
| Subsequent | 10-20s | 15-30s |
| OCR only | 5-10s | 10-15s |
| Translation | 5-10s | 5-10s |

*Times vary based on image size and complexity*

---

## 🎯 Demo Tips for Hackathon

1. **Pre-install dependencies** before demo
2. **Warm up Daytona sandbox** with one test run
3. **Use high-quality sample images** (clear text, good contrast)
4. **Prepare multiple examples** (different languages)
5. **Show both execution modes** (local vs sandbox)
6. **Highlight downloads** (PNG, JSON, CSV)

### Good Demo Images
- Single manga panel with 2-3 speech bubbles
- High contrast (black text on white)
- Clear, legible font
- Not too much text per bubble

### What to Avoid
- Very low resolution scans
- Handwritten text
- Extremely stylized fonts
- Tiny text (< 12pt)

---

## 📞 Getting Help

If you encounter issues:

1. **Check this guide** - most common issues are covered
2. **Read README.md** - comprehensive documentation
3. **Check the terminal** - error messages are helpful
4. **Try Local mode first** - eliminates network issues
5. **Use smaller test images** - faster debugging

---

## ✅ Verification Checklist

Before your demo/submission:

- [ ] Python installed and in PATH
- [ ] All dependencies installed (`pip list` shows easyocr, streamlit, etc.)
- [ ] start.bat runs without errors
- [ ] Browser opens to Streamlit app
- [ ] Can upload an image successfully
- [ ] Local mode processes correctly
- [ ] Can download all three output files
- [ ] (Optional) Daytona mode works with API key
- [ ] (Optional) OpenAI translation works with API key

---

**Need help?** Open an issue on GitHub or contact the maintainers.

**Good luck with your hackathon! 🚀**
