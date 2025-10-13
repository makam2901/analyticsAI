#!/bin/bash

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo "📋 Showing Analytics AI Platform logs..."

# Change to project directory and docker subdirectory
cd "$PROJECT_DIR/docker"
docker-compose logs -f