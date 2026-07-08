@echo off
cd /d "%~dp0"
title Supply Chain Management

echo ============================================
echo   Supply Chain Management - Start
echo ============================================
echo.

if not exist ".venv\Scripts\python.exe" (
  echo [ERROR] venv not found. Run setup.bat first.
  pause
  exit /b 1
)

echo [1/3] Checking port 5000...
netstat -ano | findstr ":5000" >nul
if not errorlevel 1 (
  echo   Port in use, stopping old process...
  for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":5000"') do (
    taskkill /PID %%a /F >nul 2>&1
  )
  timeout /t 2 /nobreak >nul
)

echo [2/3] Starting Flask (hidden window)...
start "" /B ".venv\Scripts\pythonw.exe" app.py > server.log 2>&1
echo   Waiting for server...
timeout /t 4 /nobreak >nul

echo [3/3] Opening browser...
start "" "http://localhost:5000/login"

echo.
echo ============================================
echo   Server started!
echo   URL:  http://localhost:5000
echo   Login: admin / admin123
echo ============================================
echo.
timeout /t 6 /nobreak >nul
