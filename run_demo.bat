@echo off
title Smart Road Vision - AI Traffic Monitoring (Demo Mode)
echo ===================================================
echo     SMART ROAD VISION (Demo Auto-Start)
echo ===================================================
echo.

REM Try using Python launcher 'py' first
py --version >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo Launching with 'py main.py --demo'...
    py main.py --demo
    goto end
)

REM Fallback to 'python'
python --version >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo Launching with 'python main.py --demo'...
    python main.py --demo
    goto end
)

REM Fallback to explicit user AppData path
if exist "%LOCALAPPDATA%\Python\pythoncore-3.14-64\python.exe" (
    echo Launching with installed Python 3.14...
    "%LOCALAPPDATA%\Python\pythoncore-3.14-64\python.exe" main.py --demo
    goto end
)

echo ERROR: Neither 'py' nor 'python' was found in your PATH.
pause

:end
