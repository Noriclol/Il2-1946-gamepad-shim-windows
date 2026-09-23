@echo off
setlocal
cd /d "%~dp0"

if not exist venv (
    echo First-time setup, this may take a minute...
    python -m venv venv
    venv\Scripts\pip install --quiet pygame pyvjoy
)

venv\Scripts\python -m res.main
pause
