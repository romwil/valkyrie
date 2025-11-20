#!/bin/bash
# Docker cleanup script for Valkyrie

set -e

echo "🧹 Cleaning up Valkyrie Docker resources..."

# Load environment variables if .env exists
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

# Determine environment
ENVIRONMENT=${ENVIRONMENT:-production}

# Stop and remove containers
if [ "$ENVIRONMENT" = "development" ]; then
    docker-compose -f docker-compose.yml -f docker-compose.dev.yml down -v
else
    docker-compose -f docker-compose.yml -f docker-compose.prod.yml down
fi

# Remove unused images
echo "🗑️  Removing unused Docker images..."
docker image prune -f

# Remove unused volumes (be careful!)
read -p "Remove unused volumes? (y/N) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    docker volume prune -f
fi

echo "✅ Cleanup complete!"
