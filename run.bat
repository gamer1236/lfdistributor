@echo off
title Local File Distributor - Server
cd /d "%~dp0"

echo ============================================================
echo           LOCAL FILE DISTRIBUTOR LAUNCHER
echo ============================================================
echo.

:: Check if Python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not in PATH.
    echo Please install Python 3.8 or newer and try again.
    pause
    exit /b 1
)

:: Create virtual environment if it doesn't exist
if not exist venv (
    echo [INFO] Creating Python virtual environment...
    python -m venv venv
    if %errorlevel% neq 0 (
        echo [ERROR] Failed to create virtual environment.
        pause
        exit /b 1
    )
)

:: Install/Update dependencies directly using venv python
echo [INFO] Checking and installing Python dependencies...
.\venv\Scripts\python.exe -m pip install --upgrade pip
.\venv\Scripts\pip.exe install -r requirements.txt
if %errorlevel% neq 0 (
    echo [ERROR] Dependency installation failed.
    pause
    exit /b 1
)

echo.
echo [SUCCESS] Setup complete! Starting Local File Distributor...
echo.

:: Run Flask app using the venv python
.\venv\Scripts\python.exe app.py
if %errorlevel% neq 0 (
    echo.
    echo [WARNING] Server stopped with error code %errorlevel%.
)

pause
