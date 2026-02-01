# 🚀 Universal Installation Guide

This guide ensures MangaTranslate MVP works on **any Windows PC** with **any Python version** (3.8 - 3.13+).

---

## ✅ Prerequisites

- **Windows 10/11**
- **Python 3.8 or higher** (3.11 or 3.12 recommended for best compatibility)
- **Internet connection** (for downloading dependencies)

---

## 📦 Method 1: Automatic Installation (Recommended)

### Super Simple - Double-Click

1. **Download/extract** this entire folder
2. **Double-click** `start.bat`
3. **Wait** 2-5 minutes (first time only)
4. **Browser opens automatically** → Start using the app!

That's it! The batch file handles everything.

---

## 🔧 Method 2: Manual Installation (If Method 1 Fails)

### Step 1: Install Python (if not installed)

1. Download from: https://www.python.org/downloads/
2. **Recommended versions:**
   - Python 3.11.9 (best compatibility)
   - Python 3.12.x (also good)
   - Python 3.13.x (latest, but some packages may need workarounds)
3. During installation:
   - ✅ **CHECK "Add Python to PATH"** (very important!)
   - Choose "Install Now"

### Step 2: Verify Python Installation

Open Command Prompt (Win+R → type `cmd` → Enter):

```bash
python --version
```

Should show: `Python 3.x.x`

### Step 3: Navigate to Project Folder

```bash
cd C:\path\to\manga-translate-mvp
```

Example: `cd C:\Users\YourName\Desktop\manga-translate-mvp`

### Step 4: Create Virtual Environment

```bash
python -m venv .venv
```

### Step 5: Activate Virtual Environment

```bash
.venv\Scripts\activate
```

You should see `(.venv)` at the start of your command prompt.

### Step 6: Upgrade pip (Important!)

```bash
python -m pip install --upgrade pip
```

### Step 7: Install Dependencies

**Option A - Try binary-only first (fastest, works on Python 3.13):**

```bash
pip install --only-binary :all: -r requirements.txt
```

**Option B - If Option A fails (standard installation):**

```bash
pip install -r requirements.txt
```

**Option C - If Option B fails (install one by one):**

```bash
pip install streamlit
pip install pillow
pip install numpy
pip install pandas
pip install requests
pip install opencv-python-headless
pip install easyocr
pip install daytona
```

### Step 8: Run the App

```bash
streamlit run app.py
```

Browser should open to `http://localhost:8501`

---

## 🐛 Troubleshooting Common Issues

### Issue 1: "Python is not recognized"

**Solution:**
1. Reinstall Python with "Add to PATH" checked
2. OR add Python manually to PATH:
   - Search "Environment Variables" in Windows Start
   - Edit "Path" under System Variables
   - Add: `C:\Users\YourName\AppData\Local\Programs\Python\Python3XX`
3. Close and reopen Command Prompt

### Issue 2: "pip is not recognized"

**Solution:**
Same as Issue 1, also add to PATH:
- `C:\Users\YourName\AppData\Local\Programs\Python\Python3XX\Scripts`

### Issue 3: "Failed to build numpy" or "Failed to build pandas"

**Cause:** You're using Python 3.13 and packages don't have pre-built wheels yet.

**Solution A - Use binary-only installation:**
```bash
pip install --only-binary :all: numpy pandas
```

**Solution B - Downgrade to Python 3.11:**
1. Uninstall Python 3.13
2. Install Python 3.11.9 from https://www.python.org/downloads/
3. Delete `.venv` folder
4. Start over from Step 4

**Solution C - Install Microsoft C++ Build Tools:**
1. Download: https://visualstudio.microsoft.com/visual-cpp-build-tools/
2. Install "Desktop development with C++"
3. Restart computer
4. Try installing again

### Issue 4: "ERROR: Failed to build 'pillow'"

**Solution:**
```bash
pip install --upgrade pillow
```

Or install latest version:
```bash
pip install pillow --no-cache-dir
```

### Issue 5: EasyOCR takes forever on first run

**This is normal!** EasyOCR downloads language models (~100-500MB) on first use.
- First run: 2-5 minutes
- Subsequent runs: 10-30 seconds

Just be patient and let it finish.

### Issue 6: "ModuleNotFoundError: No module named 'streamlit'"

**Cause:** Virtual environment not activated.

**Solution:**
```bash
.venv\Scripts\activate
```

Then run the app again.

### Issue 7: Browser doesn't open automatically

**Solution:**
Manually open browser and go to: `http://localhost:8501`

Look in the terminal for the exact URL.

### Issue 8: Port 8501 already in use

**Solution:**
Kill the existing Streamlit process:
```bash
taskkill /F /IM streamlit.exe
```

Or run on different port:
```bash
streamlit run app.py --server.port 8502
```

---

## 🎯 Python Version Compatibility Matrix

| Python Version | numpy/pandas | EasyOCR | Streamlit | Recommended |
|----------------|--------------|---------|-----------|-------------|
| 3.8            | ✅ Binary    | ✅      | ✅        | ⚠️ Old      |
| 3.9            | ✅ Binary    | ✅      | ✅        | ✅          |
| 3.10           | ✅ Binary    | ✅      | ✅        | ✅          |
| 3.11           | ✅ Binary    | ✅      | ✅        | ⭐ Best     |
| 3.12           | ✅ Binary    | ✅      | ✅        | ✅          |
| 3.13           | ⚠️ May need source | ✅      | ✅        | ⚠️ Too new  |

**Recommendation:** Use **Python 3.11.9** for best compatibility.

---

## 📋 Verification Checklist

After installation, verify everything works:

```bash
# Check Python
python --version

# Check pip
pip --version

# Check installed packages
pip list | findstr "streamlit easyocr numpy pandas"

# Should see:
# streamlit         1.32.x
# easyocr          1.7.x
# numpy            1.26.x or 2.x.x
# pandas           2.x.x
```

---

## 🌐 Testing on Different PCs

To ensure it works on any PC:

1. **Copy entire folder** to target PC
2. **Double-click `start.bat`**
3. **First run takes longer** (downloads dependencies)
4. **Subsequent runs are fast**

No need to install anything except Python!

---

## 💾 Portable Version (Advanced)

To make a truly portable version:

1. Install everything once
2. Copy the entire folder including `.venv`
3. The `.venv` folder contains all dependencies
4. On new PC, just run `start.bat`

**Note:** This only works between PCs with the same:
- Windows version
- Python version (must match exactly)
- CPU architecture (64-bit vs 32-bit)

---

## 🔑 API Keys Setup (Optional)

### Daytona (for sandbox mode)
```bash
# Persistent
setx DAYTONA_API_KEY "your-key-here"

# Session only
set DAYTONA_API_KEY=your-key-here
```

Or enter directly in the Streamlit UI sidebar.

### OpenAI (for better translation)
Enter directly in the Streamlit UI sidebar when selecting "OpenAI" backend.

---

## 📞 Still Having Issues?

1. **Check Python version:** `python --version`
2. **Update pip:** `python -m pip install --upgrade pip`
3. **Check internet connection**
4. **Disable antivirus temporarily** (sometimes blocks pip)
5. **Run Command Prompt as Administrator**
6. **Try on a different network** (some corporate networks block pip)

---

## ✅ Success Indicators

You'll know it's working when:

- ✅ start.bat runs without errors
- ✅ Browser opens to Streamlit interface
- ✅ You can upload an image
- ✅ Processing completes successfully
- ✅ You can download annotated PNG/JSON/CSV

---

**Made with ❤️ to work on ANY Windows PC**

If you follow this guide, the app WILL work! 🚀
