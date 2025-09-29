#!/bin/bash

# -----------------------------
# push_container.sh
# Build, tag, and push a Docker image to Docker Hub
# -----------------------------

# --- CONFIG ---
IMAGE_NAME="domana"                  # local image name
DOCKER_USER="adrianbega"             # your Docker Hub username
DOCKER_REPO="domana"                 # repository name on Docker Hub
TAG="0.5"                            # change to version if needed // latest

# --- BUILD IMAGE ---
echo "[+] Building Docker image..."
docker build -t ${IMAGE_NAME}:${TAG} .

# --- TAG IMAGE FOR DOCKER HUB ---
echo "[+] Tagging image for Docker Hub..."
docker tag ${IMAGE_NAME}:${TAG} ${DOCKER_USER}/${DOCKER_REPO}:${TAG}

# --- PUSH TO DOCKER HUB ---
echo "[+] Pushing image to Docker Hub..."
docker push ${DOCKER_USER}/${DOCKER_REPO}:${TAG}

# --- DONE ---
echo "[✓] Image pushed: https://hub.docker.com/r/${DOCKER_USER}/${DOCKER_REPO}"
