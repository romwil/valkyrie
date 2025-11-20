#!/bin/bash
# Docker logs script for Valkyrie

set -e

# Default to all services
SERVICE=${1:-}

# Load environment variables if .env exists
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

# Determine environment
ENVIRONMENT=${ENVIRONMENT:-production}

echo "📋 Viewing logs for Valkyrie services..."

# Show logs
if [ "$ENVIRONMENT" = "development" ]; then
    if [ -z "$SERVICE" ]; then
        docker-compose -f docker-compose.yml -f docker-compose.dev.yml logs -f --tail=100
    else
        docker-compose -f docker-compose.yml -f docker-compose.dev.yml logs -f --tail=100 $SERVICE
    fi
else
    if [ -z "$SERVICE" ]; then
        docker-compose -f docker-compose.yml -f docker-compose.prod.yml logs -f --tail=100
    else
        docker-compose -f docker-compose.yml -f docker-compose.prod.yml logs -f --tail=100 $SERVICE
    fi
fi
