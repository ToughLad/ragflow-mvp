# PowerShell setup script for RAGFlow MVP on Windows

Write-Host "Setting up RAGFlow MVP for Windows..." -ForegroundColor Green

# Check if Docker is installed
$dockerVersion = docker --version 2>$null
if (-not $dockerVersion) {
    Write-Host "Docker is required but not installed. Please install Docker Desktop." -ForegroundColor Red
    exit 1
}
Write-Host "Docker found: $dockerVersion" -ForegroundColor Green

# Check if Docker Compose is available
$composeVersion = docker compose version 2>$null
if (-not $composeVersion) {
    Write-Host "Docker Compose is required but not found." -ForegroundColor Red
    exit 1
}
Write-Host "Docker Compose found: $composeVersion" -ForegroundColor Green

# Create necessary directories
Write-Host "Creating directories..." -ForegroundColor Yellow
$directories = @("config", "data", "logs", "models")
foreach ($dir in $directories) {
    if (-not (Test-Path $dir)) {
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
        Write-Host "Created directory: $dir" -ForegroundColor Green
    }
}

# Copy environment template if .env doesn't exist
if (-not (Test-Path ".env")) {
    if (Test-Path ".env.example") {
        Copy-Item ".env.example" ".env"
        Write-Host "Created .env file from template" -ForegroundColor Green
        Write-Host "Please edit .env file with your configuration before continuing" -ForegroundColor Yellow
    } else {
        Write-Host "Warning: .env.example not found" -ForegroundColor Yellow
    }
}

# Check if Ollama is configured
Write-Host "Checking Ollama configuration..." -ForegroundColor Yellow
$env:OLLAMA_HOST = if ($env:OLLAMA_HOST) { $env:OLLAMA_HOST } else { "http://localhost:11434" }
try {
    $ollamaResponse = Invoke-RestMethod -Uri "$env:OLLAMA_HOST/api/tags" -TimeoutSec 5
    Write-Host "Ollama is accessible at $env:OLLAMA_HOST" -ForegroundColor Green
} catch {
    Write-Host "Warning: Cannot connect to Ollama at $env:OLLAMA_HOST" -ForegroundColor Yellow
    Write-Host "Please ensure Ollama is running and accessible" -ForegroundColor Yellow
}

# Pull required model
Write-Host "Pulling Mistral model..." -ForegroundColor Yellow
try {
    $pullResponse = Invoke-RestMethod -Uri "$env:OLLAMA_HOST/api/pull" -Method Post -Body (@{name="mistral"} | ConvertTo-Json) -ContentType "application/json" -TimeoutSec 300
    Write-Host "Mistral model pulled successfully" -ForegroundColor Green
} catch {
    Write-Host "Warning: Failed to pull Mistral model. Please run: ollama pull mistral" -ForegroundColor Yellow
}

# Build and start services
Write-Host "Building and starting Docker services..." -ForegroundColor Yellow
docker compose up --build -d

if ($LASTEXITCODE -eq 0) {
    Write-Host "`nRAGFlow MVP setup completed successfully!" -ForegroundColor Green
    Write-Host "`nServices starting up..." -ForegroundColor Yellow
    Write-Host "API will be available at: http://localhost:8000" -ForegroundColor Cyan
    Write-Host "PostgreSQL will be available at: localhost:5432" -ForegroundColor Cyan
    Write-Host "Redis will be available at: localhost:6379" -ForegroundColor Cyan
    Write-Host "`nTo check status: docker compose ps" -ForegroundColor Cyan
    Write-Host "To view logs: docker compose logs -f" -ForegroundColor Cyan
    Write-Host "To stop: docker compose down" -ForegroundColor Cyan
    
    Write-Host "`nNext steps:" -ForegroundColor Yellow
    Write-Host "1. Configure your .env file with Google OAuth credentials" -ForegroundColor White
    Write-Host "2. Set up domain-wide delegation for @ivc-valves.com emails" -ForegroundColor White  
    Write-Host "3. Add service_account.json to config/ directory" -ForegroundColor White
    Write-Host "4. Configure SMTP settings for email delivery" -ForegroundColor White
} else {
    Write-Host "Setup failed. Please check Docker logs for details." -ForegroundColor Red
    exit 1
}
