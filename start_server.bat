@echo off
chcp 65001 >nul
cd /d "%~dp0"
title 供应链管理系统

echo ============================================
echo   供应链管理系统 - 服务器启动
echo ============================================
echo.

REM ===== 设置 Turso 环境变量 =====
set TURSO_DATABASE_URL=libsql://supply-chain-data-management-guanyibei41-creator.aws-us-east-2.turso.io
set TURSO_AUTH_TOKEN=eyJhbGciOiJFZERTQSIsInR5cCI6IkpXVCJ9.eyJhIjoicnciLCJpYXQiOjE3ODIyMDcwMDMsImlkIjoiMDE5ZWYzY2QtMjAwMS03NWYyLWEyMWItMTc5MDQ0NmYwYjE1IiwicmlkIjoiZDk5NDM2ODktOTRmNC00NDQ2LThlMDAtOTJmNzlkYTM1ODljIn0.TfA-mC1LKS6HDlNuocDF1o0nhod8ddoL0WYkLoog7xsl6DS7novYtfUPHw3y3hAAtD-7SZ-0GT_tMJFuW7OHCQ

echo [1/2] 启动 Flask (Turso 云数据库)...
start "供应链-Flask" /MIN python app.py
timeout /t 4 /nobreak >nul

echo [2/2] 启动 Cloudflare 公网隧道...
start "Cloudflare-隧道" cloudflared.exe tunnel --url http://localhost:5000 --no-autoupdate

echo.
echo ============================================
echo.
echo   服务器已启动！
echo.
echo   公网地址：查看 "Cloudflare-隧道" 窗口
echo   找到类似 https://xxx.trycloudflare.com 的地址
echo.
echo   管理员: admin / scm2026!@
echo.
echo   关闭电脑前不要关闭 Flask 和隧道窗口！
echo.
echo ============================================
echo.
pause
