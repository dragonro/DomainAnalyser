#!/bin/bash

# -----------------------------
# build_push_container.sh
# Build, tag, and push a multi-platform Docker image to Docker Hub
# -----------------------------

# --- CONFIG ---
IMAGE_NAME="domana"                  # local image name
DOCKER_USER="adrianbega"             # your Docker Hub username
DOCKER_REPO="domana"                 # repository name on Docker Hub
TAG="0.6"                            # change to version if needed // latest

# --- ENABLE BUILDX ---
echo "[+] Enabling Docker Buildx..."
docker buildx create --use --name multiarch-builder || docker buildx use multiarch-builder

# --- BUILD MULTI-PLATFORM IMAGE ---
echo "[+] Building multi-platform Docker image..."
docker buildx build --platform linux/amd64,linux/arm64 \
  -t ${DOCKER_USER}/${DOCKER_REPO}:${TAG} \
  --push .

# --- DONE ---
echo "[✓] Multi-platform image pushed: https://hub.docker.com/r/${DOCKER_USER}/${DOCKER_REPO}"