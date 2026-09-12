#!/bin/sh
set -e

exec 9>"/tmp/deploy-$(basename "$(pwd)").lock"
flock 9

echo "Deploying $(pwd)"
docker network inspect ingress >/dev/null 2>&1 || docker network create ingress
docker compose --profile prod pull
docker compose --profile prod up -d --remove-orphans
docker image prune -f
echo "Deploy complete"
