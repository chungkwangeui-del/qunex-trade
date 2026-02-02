@echo off
title QunexTrade - Agent Control Center
cd /d "%~dp0"

:: Show welcome screen
python -m agents.cli welcome

:: Wait for user input
echo.
echo Press any key to start workers, or close this window to exit...
pause > nul

:: Start workers
python -m agents.cli work


