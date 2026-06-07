@echo off
chcp 65001 > nul
setlocal
cd /d "%~dp0"

if not exist ".venv" (
    echo [INFO] Checking Python version...
    
    py -3.11 -V >nul 2>&1
    if errorlevel 1 (
        echo.
        echo [ERROR] Python 3.11 was not found.
        echo [ERROR] Python 3.11 is required to run this application.
        echo [ERROR] Please install it from: https://www.python.org/
        echo.
        pause
        exit /b 1
    )

    echo [INFO] Python 3.11 detected. Creating virtual environment...
    py -3.11 -m venv .venv
)

call .venv\Scripts\activate

echo [INFO] Updating pip and installing dependencies...
python -m pip install --upgrade pip
pip install -r src\requirements.txt

echo [INFO] Starting Web Server...
start http://127.0.0.1:5000
python app.py

pause