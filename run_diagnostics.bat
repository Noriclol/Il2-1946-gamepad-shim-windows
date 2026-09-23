@echo off
setlocal
cd /d "%~dp0"

where python >nul 2>nul
if errorlevel 1 (
    echo Python was not found on this computer.
    echo Please install Python 3.12 from https://www.python.org/downloads/
    echo IMPORTANT: on the first install screen, check the box that says
    echo "Add python.exe to PATH" before clicking Install.
    echo Then double-click this file again.
    pause
    exit /b 1
)

if not exist venv (
    echo First-time setup, this may take a minute...
    python -m venv venv
)

echo Installing dependencies...
venv\Scripts\pip install --quiet pygame pyvjoy

echo.
echo Running diagnostics now. Just follow the prompts on screen
echo ^(press buttons / move sticks when it asks^) - no rush.
echo.
venv\Scripts\python scripts\windows_diagnostics.py

echo.
echo ============================================================
echo Done! A file called log.txt was created in this same folder.
echo Please send that log.txt file back.
echo ============================================================
pause
