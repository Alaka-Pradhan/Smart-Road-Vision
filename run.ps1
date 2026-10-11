# Smart Road Vision PowerShell Launcher
Write-Host "===================================================" -ForegroundColor Cyan
Write-Host "    SMART ROAD VISION (SafeRoad AI Engine)" -ForegroundColor Green
Write-Host "===================================================" -ForegroundColor Cyan
Write-Host ""

$pythonCmd = $null

if (Test-Path "venv\Scripts\python.exe") {
    $pythonCmd = "venv\Scripts\python.exe"
} elseif (Get-Command py -ErrorAction SilentlyContinue) {
    $pythonCmd = "py"
} elseif (Get-Command python -ErrorAction SilentlyContinue) {
    $pythonCmd = "python"
} elseif (Test-Path "$env:LOCALAPPDATA\Python\pythoncore-3.14-64\python.exe") {
    $pythonCmd = "$env:LOCALAPPDATA\Python\pythoncore-3.14-64\python.exe"
}

if (-not $pythonCmd) {
    Write-Host "[ERROR] Python was not found on this computer." -ForegroundColor Red
    Write-Host "Please install Python 3.10+ from https://www.python.org/downloads/ and check 'Add python.exe to PATH'." -ForegroundColor Yellow
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Host "Using Python: $pythonCmd" -ForegroundColor Cyan

# Check dependencies
& $pythonCmd -c "import cv2, ultralytics, torch" 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "[SETUP] Core dependencies missing. Installing requirements from requirements.txt..." -ForegroundColor Yellow
    & $pythonCmd -m pip install -r requirements.txt
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[ERROR] Dependency installation failed." -ForegroundColor Red
        Read-Host "Press Enter to exit"
        exit 1
    }
}

Write-Host "Launching application..." -ForegroundColor Green
& $pythonCmd main.py $args

if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERROR] Application exited with error code $LASTEXITCODE." -ForegroundColor Red
    Read-Host "Press Enter to exit"
}

