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
venv\Scripts\pip install pygame pyvjoy

venv\Scripts\python -c "import pygame, pyvjoy" >nul 2>&1
if errorlevel 1 (
    echo.
    echo ERROR: pygame/pyvjoy still could not be installed. Scroll up for
    echo pip's error output above. Common causes: no internet connection,
    echo antivirus blocking pip, or "python" pointing at the Microsoft
    echo Store app stub instead of a real Python install ^(reinstall from
    echo https://www.python.org/downloads/ and check "Add python.exe to
    echo PATH" if so^).
    echo.
    echo Try deleting the "venv" folder next to this script and running
    echo it again once the underlying issue is fixed.
    pause
    exit /b 1
)

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
