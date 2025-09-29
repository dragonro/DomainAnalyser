#!/bin/bash

# Stop and remove old container if running
docker stop domain-analyser 2>/dev/null || true
docker rm domain-analyser 2>/dev/null || true

# Pull the latest version (update the tag as needed)
TAG="0.6"

echo "[+] Pulling Docker image adrianbega/domana:${TAG}..."
docker pull adrianbega/domana:${TAG}

# Run the container
echo "[+] Starting domain-analyser..."
docker run -d \
  --name domain-analyser \
  -p 3456:3000 \
  -v $(pwd)/backend/data:/app/backend/data \
  -e UVICORN_WORKERS=1 \
  -e PUBLIC_DOMAIN="localhost:3000" \
  --restart unless-stopped \
  adrianbega/domana:${TAG}

echo "[✓] domain-analyser running on port 3456"