@echo off
cd /d "%~dp0"
title Supply Chain Setup

echo ============================================
echo   Supply Chain Management - First Run Setup
echo ============================================
echo.

echo [1/4] Checking Python...
where python >nul 2>&1
if errorlevel 1 (
  echo [ERROR] Python not found. Install Python 3.10+ first.
  echo Download: https://www.python.org/downloads/
  pause
  exit /b 1
)
python --version
echo.

echo [2/4] Creating virtual environment...
if exist ".venv\Scripts\python.exe" (
  echo   .venv already exists, skip
) else (
  python -m venv .venv
  if errorlevel 1 (
    echo [ERROR] Failed to create venv
    pause
    exit /b 1
  )
  echo   venv created
)
echo.

echo [3/4] Upgrading pip...
.venv\Scripts\python.exe -m pip install --upgrade pip
echo.

echo [4/4] Installing dependencies...
.venv\Scripts\python.exe -m pip install -r requirements.txt
if errorlevel 1 (
  echo [ERROR] Install failed
  pause
  exit /b 1
)

echo.
echo ============================================
echo   Setup complete!
echo   Next: double-click start.bat
echo   Login: admin / admin123
echo ============================================
echo.
pause
