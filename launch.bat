@echo off
setlocal
cd /d "%~dp0"

if not exist venv (
    echo First-time setup, this may take a minute...
    python -m venv venv
)

venv\Scripts\python -c "import pygame, pyvjoy" >nul 2>&1
if errorlevel 1 (
    echo Installing dependencies ^(pygame, pyvjoy^)...
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
)

venv\Scripts\python -m res.main
pause
