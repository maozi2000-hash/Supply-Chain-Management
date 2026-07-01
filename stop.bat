@echo off
title Supply Chain - Stop

echo ============================================
echo   Supply Chain Management - Stop
echo ============================================
echo.

netstat -ano | findstr ":5000" >nul
if errorlevel 1 (
  echo   Port 5000 is free, nothing to stop.
  pause
  exit /b 0
)

echo Stopping processes on port 5000...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":5000"') do (
  echo   Killing PID %%a
  taskkill /PID %%a /F
)

echo.
echo   Stopped.
echo ============================================
echo.
pause
