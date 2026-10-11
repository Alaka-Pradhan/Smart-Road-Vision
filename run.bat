@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"
title Smart Road Vision - AI Traffic Monitoring
echo ===================================================
echo     SMART ROAD VISION (SafeRoad AI Engine)
echo ===================================================
echo.

REM 1. Check if virtual environment exists
if exist "venv\Scripts\python.exe" (
    set "PY_CMD=venv\Scripts\python.exe"
    goto found_python
)

REM 2. Check py launcher
py -c "import sys; sys.exit(0)" >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    set "PY_CMD=py"
    goto found_python
)

REM 3. Check python command
python -c "import sys; sys.exit(0)" >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    set "PY_CMD=python"
    goto found_python
)

REM 4. Fallback to LocalAppData
if exist "%LOCALAPPDATA%\Python\pythoncore-3.14-64\python.exe" (
    set "PY_CMD=%LOCALAPPDATA%\Python\pythoncore-3.14-64\python.exe"
    goto found_python
)

echo [ERROR] Python was not found on this computer.
echo.
echo Please install Python (3.10 - 3.12 recommended) from https://www.python.org/downloads/
echo Make sure to check the box: [x] "Add python.exe to PATH"
echo.
pause
exit /b 1

:found_python
echo Using Python: !PY_CMD!
echo.

REM Check core dependencies
!PY_CMD! -c "import cv2, ultralytics, torch" >nul 2>&1
if %ERRORLEVEL% EQU 0 goto run_app

echo [SETUP] Core libraries are not installed yet.
echo Installing dependencies from requirements.txt... Please wait.
echo.
!PY_CMD! -m pip install -r requirements.txt
if %ERRORLEVEL% NEQ 0 goto install_failed

echo.
echo [SETUP] All dependencies installed successfully!
echo.
goto run_app

:install_failed
echo.
echo [ERROR] Failed to install dependencies automatically.
echo Please open Command Prompt in this folder and run:
echo   !PY_CMD! -m pip install -r requirements.txt
echo.
pause
exit /b 1

:run_app
echo Launching Smart Road Vision...
!PY_CMD! main.py %*

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] Application stopped with exit code %ERRORLEVEL%.
    pause
)


