# Build the local image
docker build -t cortextia-local .

# Run the container
# -p 7860:7860 -> Map port 7860
# --env-file .env -> Load keys from .env if it exists
# -v ${PWD}/data:/app/backend/data -> Persist data locally
# --rm -> Remove container when stopped

if (Test-Path .env) {
    Write-Host "Starting with .env file..." -ForegroundColor Green
    docker run --rm -it `
        -p 7860:7860 `
        --env-file .env `
        -v "${PWD}/data:/app/backend/data" `
        --name cortextia-dev `
        cortextia-local
} else {
    Write-Host "Warning: .env file not found. Starting with defaults (OpenRouter will not work)." -ForegroundColor Yellow
    docker run --rm -it `
        -p 7860:7860 `
        -v "${PWD}/data:/app/backend/data" `
        --name cortextia-dev `
        cortextia-local
}
