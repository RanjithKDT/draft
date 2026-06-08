@echo off
setlocal

cd /d "%~dp0.."

:: Run setup if venv doesn't exist yet
if not exist ".venv\Scripts\python.exe" (
    echo [Hyva Simulator] venv not found — running setup first...
    python setup.py
    if errorlevel 1 (
        echo Setup failed. Exiting.
        pause
        exit /b 1
    )
)

:: Activate venv and launch
call .venv\Scripts\activate.bat
python main.py
