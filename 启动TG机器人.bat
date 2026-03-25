@echo off
chcp 65001 >nul 2>nul
title FC3D_AI Telegram Bot
cd /d %~dp0
echo ========================================
echo   FC3D_AI Telegram Bot
echo   �� Ctrl+C ֹͣ
echo ========================================
echo.
python tg_bot.py
pause
