#!/bin/bash
# Start UI with proper API key check

set -e

cd "$(dirname "$0")/.."

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "=========================================="
echo "K8s SRE Agent - UI Launcher"
echo "=========================================="
echo ""

# Check virtual environment
if [ ! -d ".venv" ]; then
    echo -e "${RED}❌ Virtual environment not found${NC}"
    echo "Run: python -m venv .venv && source .venv/bin/activate && pip install -e ."
    exit 1
fi

# Activate venv
source .venv/bin/activate

# Check API key
if [ -z "$OPENROUTER_API_KEY" ]; then
    echo -e "${RED}❌ OPENROUTER_API_KEY not set!${NC}"
    echo ""
    echo "Please set it:"
    echo "  export OPENROUTER_API_KEY='YOUR_API_KEY_HERE'"
    echo ""
    echo "Or add to your shell profile (~/.zshrc or ~/.bashrc):"
    echo "  export OPENROUTER_API_KEY='your-key-here'"
    exit 1
fi

echo -e "${GREEN}✅ API key configured${NC}"
echo ""

# Check Qdrant
if ! curl -s http://localhost:6333/readyz > /dev/null 2>&1; then
    echo -e "${YELLOW}⚠️  Qdrant not running on localhost:6333${NC}"
    echo "Start it with: docker-compose up -d qdrant"
    echo ""
fi

# Check kubectl
if ! kubectl cluster-info &> /dev/null; then
    echo -e "${YELLOW}⚠️  Cannot connect to Kubernetes cluster${NC}"
    echo ""
fi

echo "Starting UI..."
echo "URL: http://localhost:7860"
echo "Press Ctrl+C to stop"
echo ""

k8s-sre-agent ui

