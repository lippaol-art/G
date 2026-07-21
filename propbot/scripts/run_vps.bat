@echo off
REM propbot autostart for a Windows VPS.
REM Add to Task Scheduler -> Trigger "At log on" -> Action: run this file.
REM Restarts the bot if it crashes; MT5 terminal must be running & logged in.

cd /d "%~dp0\.."

:loop
echo [%date% %time%] starting propbot...
python -m propbot.app
echo [%date% %time%] propbot exited (code %errorlevel%). Restarting in 15s...
timeout /t 15 /nobreak >nul
goto loop
