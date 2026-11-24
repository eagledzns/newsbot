@echo off
cd /d "%~dp0"
chcp 65001 >nul
echo Preview only - nothing is posted to Telegram.
py -X utf8 bot.py --dry-run
pause
