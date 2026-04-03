#!/bin/sh
set -e

cd /app

echo "Pulling latest images..."
docker compose --profile prod pull backend-prod frontend-prod

echo "Restarting services..."
docker compose --profile prod up -d backend-prod frontend-prod

echo "Cleaning up old images..."
docker image prune -f

echo "Deploy complete"
