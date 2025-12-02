#!/bin/bash
# Setup script for Kubernetes SRE Agent

set -e

echo "🔍 Checking prerequisites..."

# Check Docker
if ! docker ps > /dev/null 2>&1; then
    echo "❌ Docker daemon is not running!"
    echo ""
    echo "Please start Docker Desktop:"
    echo "  - macOS: Open Docker Desktop application"
    echo "  - Linux: sudo systemctl start docker"
    exit 1
fi
echo "✅ Docker is running"

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 not found"
    exit 1
fi
echo "✅ Python found: $(python3 --version)"

# Start infrastructure
echo ""
echo "🚀 Starting infrastructure services..."
docker-compose up -d

echo ""
echo "⏳ Waiting for services to be healthy..."
sleep 5

# Check Qdrant
if curl -f http://localhost:6333/health > /dev/null 2>&1; then
    echo "✅ Qdrant is running"
else
    echo "⚠️  Qdrant may still be starting..."
fi

# Check RabbitMQ
if docker exec sre-agent-rabbitmq rabbitmq-diagnostics check_running > /dev/null 2>&1; then
    echo "✅ RabbitMQ is running"
else
    echo "⚠️  RabbitMQ may still be starting..."
fi

# Check OpenRouter API key
if [ -z "$OPENROUTER_API_KEY" ]; then
    echo ""
    echo "⚠️  OPENROUTER_API_KEY not set!"
    echo "   Export it: export OPENROUTER_API_KEY='your-key'"
else
    echo "✅ OpenRouter API key is set"
fi

echo ""
echo "✅ Setup complete!"
echo ""
echo "Next steps:"
echo "  1. Install dependencies: uv sync (or poetry install)"
echo "  2. Start the agent: python -m sre_agent.web"
echo "  3. Or use CLI: sre-agent diagnose --namespace default --deployment my-app"

