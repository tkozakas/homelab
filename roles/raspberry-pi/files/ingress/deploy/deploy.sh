#!/bin/sh
set -e

exec 9>"/tmp/deploy-$(basename "$(pwd)").lock"
flock 9

echo "Deploying $(pwd)"
docker compose --profile prod pull
docker compose --profile prod up -d --remove-orphans
docker image prune -f
echo "Deploy complete"
