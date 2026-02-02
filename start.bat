@echo off
setlocal enabledelayedexpansion

echo ========================================
echo MangaTranslate MVP - Universal Launcher
echo ========================================
echo.

REM Check if Python is installed
py --version >nul 2>&1
if errorlevel 1 (
    python --version >nul 2>&1
    if errorlevel 1 (
        echo ERROR: Python is not installed or not in PATH
        echo Please install Python 3.8+ from https://www.python.org/downloads/
        echo During installation, make sure to check "Add Python to PATH"
        echo.
        pause
        exit /b 1
    )
    set PYTHON_CMD=python
) else (
    set PYTHON_CMD=py
)

echo Python found: 
%PYTHON_CMD% --version
echo.

REM Create venv if it doesn't exist
if not exist .venv (
    echo Creating virtual environment...
    %PYTHON_CMD% -m venv .venv
    if errorlevel 1 (
        echo ERROR: Failed to create virtual environment
        echo Try running: python -m pip install --upgrade pip
        pause
        exit /b 1
    )
    echo Virtual environment created successfully!
    echo.
)

REM Activate venv
echo Activating virtual environment...
call .venv\Scripts\activate
if errorlevel 1 (
    echo ERROR: Failed to activate virtual environment
    pause
    exit /b 1
)

REM Check if requirements.txt exists
if not exist requirements.txt (
    echo ERROR: requirements.txt not found
    echo Please ensure requirements.txt is in the current directory
    pause
    exit /b 1
)

REM Upgrade pip first (critical for compatibility)
echo Upgrading pip...
python -m pip install --upgrade pip --quiet
if errorlevel 1 (
    echo Warning: Could not upgrade pip, continuing anyway...
)

REM Install dependencies with compatibility options
echo.
echo Installing dependencies (this may take 2-5 minutes)...
echo Please be patient, especially on first run...
echo.

REM Try installing with binary-only first (faster, works on Python 3.13)
python -m pip install --only-binary :all: -r requirements.txt --quiet
if errorlevel 1 (
    echo.
    echo Binary installation failed, trying standard installation...
    echo This may take longer but should work...
    echo.
    python -m pip install -r requirements.txt
    if errorlevel 1 (
        echo.
        echo ERROR: Failed to install some dependencies
        echo.
        echo TROUBLESHOOTING:
        echo 1. If you're using Python 3.13, try Python 3.11 or 3.12
        echo 2. Run: python -m pip install --upgrade pip setuptools wheel
        echo 3. Install packages one by one: pip install streamlit pillow numpy pandas
        echo.
        pause
        exit /b 1
    )
)

echo.
echo Dependencies installed successfully!
echo.

REM Check if app.py exists
if not exist app.py (
    echo ERROR: app.py not found
    echo Please ensure app.py is in the current directory
    pause
    exit /b 1
)

echo ========================================
echo Starting Streamlit App...
echo ========================================
echo.
echo The app will open in your default browser automatically.
echo If it doesn't, copy the Local URL shown below and paste in browser.
echo.
echo To stop the server: Press Ctrl+C
echo.

REM Run the app
streamlit run app.py

REM If streamlit command fails
if errorlevel 1 (
    echo.
    echo ERROR: Streamlit failed to start
    echo Try: python -m streamlit run app.py
    pause
    exit /b 1
)

endlocal
