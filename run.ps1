# Smart Road Vision PowerShell Launcher
Write-Host "===================================================" -ForegroundColor Cyan
Write-Host "    SMART ROAD VISION (SafeRoad AI Engine)" -ForegroundColor Green
Write-Host "===================================================" -ForegroundColor Cyan
Write-Host ""

if (Get-Command py -ErrorAction SilentlyContinue) {
    Write-Host "Starting with py launcher..." -ForegroundColor Yellow
    py main.py $args
} elseif (Get-Command python -ErrorAction SilentlyContinue) {
    Write-Host "Starting with python..." -ForegroundColor Yellow
    python main.py $args
} elseif (Test-Path "$env:LOCALAPPDATA\Python\pythoncore-3.14-64\python.exe") {
    Write-Host "Starting with Python 3.14..." -ForegroundColor Yellow
    & "$env:LOCALAPPDATA\Python\pythoncore-3.14-64\python.exe" main.py $args
} else {
    Write-Host "ERROR: Python was not found in PATH." -ForegroundColor Red
}
