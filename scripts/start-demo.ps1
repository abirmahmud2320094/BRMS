$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Write-Host "Starting BRMS presentation demo..." -ForegroundColor Cyan

if (-not (Test-Path "$Root\backend\.venv")) {
    py -m venv "$Root\backend\.venv"
}
& "$Root\backend\.venv\Scripts\Activate.ps1"
pip install -r "$Root\backend\requirements.txt"

if (-not (Test-Path "$Root\frontend\node_modules")) {
    Push-Location "$Root\frontend"; npm install; Pop-Location
}

@"
VITE_API_BASE_URL=http://127.0.0.1:8000/api/v1
VITE_DEMO_MODE=true
"@ | Set-Content "$Root\frontend\.env.local"

$env:AUTH_MODE="demo"
$env:DATA_MODE="local"
$env:LOCAL_DATA_PATH="$Root\backend\data\local_data.json"
$env:CORS_ORIGINS="http://localhost:5173,http://127.0.0.1:5173"

Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$Root\backend'; & '.\.venv\Scripts\Activate.ps1'; `$env:AUTH_MODE='demo'; `$env:DATA_MODE='local'; `$env:LOCAL_DATA_PATH='data/local_data.json'; python run_demo.py"
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$Root\frontend'; npm run dev"
Write-Host "Open http://localhost:5173" -ForegroundColor Green
