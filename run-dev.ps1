# PowerShell script to run RAGFlow MVP in development mode

Write-Host "Starting RAGFlow MVP in development mode..." -ForegroundColor Green

# Check if .env file exists
if (-not (Test-Path ".env")) {
    Write-Host "Error: .env file not found. Please run setup.ps1 first." -ForegroundColor Red
    exit 1
}

# Check if Docker is running
try {
    docker info > $null 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Error: Docker is not running. Please start Docker Desktop." -ForegroundColor Red
        exit 1
    }
} catch {
    Write-Host "Error: Docker is not available." -ForegroundColor Red
    exit 1
}

Write-Host "Starting services..." -ForegroundColor Yellow

# Start services in development mode
docker compose up --build

# If user presses Ctrl+C, clean up
trap {
    Write-Host "`nStopping services..." -ForegroundColor Yellow
    docker compose down
    exit 0
}
