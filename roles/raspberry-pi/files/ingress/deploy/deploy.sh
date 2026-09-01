#!/bin/sh
set -e

echo "Deploying $(pwd)"
docker compose --profile prod pull
docker compose --profile prod up -d
docker image prune -f
echo "Deploy complete"
