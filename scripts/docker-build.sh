#!/bin/bash
# Docker build script for Valkyrie

set -e

echo "🔨 Building Valkyrie Docker images..."

# Load environment variables if .env exists
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

# Determine environment
ENVIRONMENT=${ENVIRONMENT:-production}
echo "📦 Building for environment: $ENVIRONMENT"

# Build images
if [ "$ENVIRONMENT" = "development" ]; then
    docker-compose -f docker-compose.yml -f docker-compose.dev.yml build --parallel
else
    docker-compose -f docker-compose.yml -f docker-compose.prod.yml build --parallel
fi

echo "✅ Build complete!"
