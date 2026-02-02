@echo off
REM Alternative installation script for compatibility issues
REM Use this if start.bat fails to install dependencies

echo ========================================
echo MangaTranslate MVP - Alternative Installer
echo ========================================
echo.

REM Detect Python
py --version >nul 2>&1
if errorlevel 1 (
    set PYTHON_CMD=python
) else (
    set PYTHON_CMD=py
)

echo Using Python: 
%PYTHON_CMD% --version
echo.

REM Check for virtual environment
if not exist .venv (
    echo Creating virtual environment...
    %PYTHON_CMD% -m venv .venv
)

call .venv\Scripts\activate

echo.
echo Step 1: Upgrading pip, setuptools, wheel...
python -m pip install --upgrade pip setuptools wheel

echo.
echo Step 2: Installing core packages...
pip install --upgrade streamlit pillow requests

echo.
echo Step 3: Installing numpy (may take a moment)...
pip install --upgrade numpy

echo.
echo Step 4: Installing pandas (may take a moment)...
pip install --upgrade pandas

echo.
echo Step 5: Installing OpenCV...
pip install opencv-python-headless

echo.
echo Step 6: Installing EasyOCR (downloads models on first use)...
pip install easyocr

echo.
echo Step 7: Installing Daytona...
pip install daytona

echo.
echo ========================================
echo Installation Complete!
echo ========================================
echo.
echo To run the app, use: streamlit run app.py
echo Or double-click start.bat
echo.
pause
