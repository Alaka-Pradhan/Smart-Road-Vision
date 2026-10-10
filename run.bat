@echo off
title Smart Road Vision - AI Traffic Monitoring
echo ===================================================
echo     SMART ROAD VISION (SafeRoad AI Engine)
echo ===================================================
echo.

REM Try using Python launcher 'py' first
py --version >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo Launching with 'py main.py'...
    py main.py
    goto end
)

REM Fallback to 'python'
python --version >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo Launching with 'python main.py'...
    python main.py
    goto end
)

REM Fallback to explicit user AppData path
if exist "%LOCALAPPDATA%\Python\pythoncore-3.14-64\python.exe" (
    echo Launching with installed Python 3.14...
    "%LOCALAPPDATA%\Python\pythoncore-3.14-64\python.exe" main.py
    goto end
)

echo ERROR: Neither 'py' nor 'python' was found in your PATH.
echo Please ensure Python is installed and check Windows App Execution Aliases.
pause

:end
