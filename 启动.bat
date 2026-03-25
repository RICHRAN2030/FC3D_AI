@echo off
chcp 65001 >nul 2>nul
title FC3D_AI
cd /d "%~dp0"
python main.py
pause
