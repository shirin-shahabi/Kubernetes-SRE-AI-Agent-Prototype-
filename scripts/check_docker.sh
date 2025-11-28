#!/bin/bash
# Check if Docker is running

if ! docker ps > /dev/null 2>&1; then
    echo "❌ Docker daemon is not running!"
    echo ""
    echo "Please start Docker Desktop:"
    echo "  - macOS: Open Docker Desktop application"
    echo "  - Linux: sudo systemctl start docker"
    echo ""
    echo "Then run: docker-compose up -d"
    exit 1
fi

echo "✅ Docker is running"
docker ps
exit 0

