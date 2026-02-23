# Check if image exists
$imageExists = docker images -q cortextia-local
if (-not $imageExists) {
    Write-Host "Initial build required..." -ForegroundColor Cyan
    docker build -t cortextia-local .
}

# Run the container
if (Test-Path .env) {
    Write-Host "Starting Cortextia AI at http://localhost:7860..." -ForegroundColor Green
    docker run --rm -d `
        -p 7860:7860 `
        --env-file .env `
        -v "${PWD}/data:/app/backend/data" `
        --name cortextia-dev `
        cortextia-local
    Write-Host "Container is running in the background."
}
else {
    Write-Host "Error: .env file missing. Please create it from .env.example." -ForegroundColor Red
}
