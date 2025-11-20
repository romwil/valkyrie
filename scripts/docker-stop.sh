#!/bin/bash
# Docker stop script for Valkyrie

set -e

echo "🛑 Stopping Valkyrie services..."

# Load environment variables if .env exists
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

# Determine environment
ENVIRONMENT=${ENVIRONMENT:-production}

# Stop services
if [ "$ENVIRONMENT" = "development" ]; then
    docker-compose -f docker-compose.yml -f docker-compose.dev.yml down
else
    docker-compose -f docker-compose.yml -f docker-compose.prod.yml down
fi

echo "✅ Services stopped!"
