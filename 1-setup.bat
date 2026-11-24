@echo off
cd /d "%~dp0"
echo Installing requirements...
py -m pip install -r requirements.txt
if not exist .env copy .env.example .env
echo.
echo Done. Now open .env in Notepad and paste your Telegram token and chat ID.
notepad .env
pause
