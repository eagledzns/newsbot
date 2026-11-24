@echo off
cd /d "%~dp0"
chcp 65001 >nul
echo Bot running: scans every 10 minutes and posts to Telegram. Close this window to stop.
py -X utf8 bot.py --loop 10
