#!/bin/bash
# Quick test script for UI with human feedback

set -e

echo "=========================================="
echo "K8s SRE Agent - UI Testing Script"
echo "=========================================="
echo ""

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check prerequisites
echo "📋 Checking prerequisites..."

if ! command -v kubectl &> /dev/null; then
    echo "❌ kubectl not found. Please install kubectl."
    exit 1
fi

if ! kubectl cluster-info &> /dev/null; then
    echo "❌ Cannot connect to Kubernetes cluster."
    exit 1
fi

if ! docker ps &> /dev/null; then
    echo "❌ Docker not running. Please start Docker."
    exit 1
fi

echo -e "${GREEN}✅ Prerequisites OK${NC}"
echo ""

# Start Qdrant
echo "🗄️  Starting Qdrant..."
docker-compose up -d qdrant > /dev/null 2>&1
sleep 3

if curl -s http://localhost:6333/readyz > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Qdrant is running${NC}"
else
    echo -e "${YELLOW}⚠️  Qdrant may not be ready yet${NC}"
fi
echo ""

# Seed patterns (optional)
if [ -f "scripts/seed_patterns.py" ]; then
    echo "🌱 Seeding knowledge base..."
    source .venv/bin/activate 2>/dev/null || true
    python scripts/seed_patterns.py 2>/dev/null || echo -e "${YELLOW}⚠️  Could not seed patterns (may already exist)${NC}"
    echo ""
fi

# Deploy test scenario
echo "🚀 Deploying test scenario..."
SCENARIO=${1:-oom}

if [ "$SCENARIO" = "oom" ]; then
    echo "   Deploying OOMKilled scenario..."
    kubectl apply -f tests/scenarios/oom_killed/memory_limit_low.yaml > /dev/null 2>&1
    RESOURCE_TYPE="Deployment"
    RESOURCE_NAME="oom-test-app"
    echo -e "${GREEN}✅ Deployed oom-test-app${NC}"
elif [ "$SCENARIO" = "service" ]; then
    echo "   Deploying Broken Service scenario..."
    kubectl apply -f tests/scenarios/broken_service/label_mismatch.yaml > /dev/null 2>&1
    RESOURCE_TYPE="Service"
    RESOURCE_NAME="broken-svc-app"
    echo -e "${GREEN}✅ Deployed broken-svc-app${NC}"
else
    echo "❌ Unknown scenario: $SCENARIO"
    echo "Usage: $0 [oom|service]"
    exit 1
fi

echo ""
echo "⏳ Waiting for scenario to fail (10 seconds)..."
sleep 10

# Check status
if [ "$SCENARIO" = "oom" ]; then
    POD_STATUS=$(kubectl get pod -l app=oom-test-app -o jsonpath='{.items[0].status.containerStatuses[0].lastState.terminated.reason}' 2>/dev/null || echo "unknown")
    echo "   Pod status: $POD_STATUS"
elif [ "$SCENARIO" = "service" ]; then
    ENDPOINTS=$(kubectl get endpoints broken-svc-app -o jsonpath='{.subsets[*].addresses[*].ip}' 2>/dev/null || echo "")
    if [ -z "$ENDPOINTS" ]; then
        echo "   Service has no endpoints (expected)"
    fi
fi

echo ""
echo "=========================================="
echo -e "${GREEN}✅ Setup Complete!${NC}"
echo "=========================================="
echo ""
echo "📝 Next Steps:"
echo ""
echo "1. Start the UI in a new terminal:"
echo "   cd $(pwd)"
echo "   source .venv/bin/activate"
echo "   export OPENROUTER_API_KEY='your-key'"
echo "   k8s-sre-agent ui"
echo ""
echo "2. Open browser: http://localhost:7860"
echo ""
echo "3. In the UI:"
echo "   - Go to 'Diagnose' tab"
echo "   - Namespace: default"
echo "   - Resource Type: $RESOURCE_TYPE"
echo "   - Resource Name: $RESOURCE_NAME"
echo "   - Click 'Diagnose'"
echo "   - Copy the Workflow ID"
echo ""
echo "4. Go to 'Approve & Execute' tab:"
echo "   - Paste Workflow ID"
echo "   - Add feedback (optional)"
echo "   - Check 'Execute Fix'"
echo "   - Click 'Submit Approval'"
echo ""
echo "5. Verify fix:"
if [ "$SCENARIO" = "oom" ]; then
    echo "   kubectl get pods -l app=oom-test-app"
else
    echo "   kubectl get endpoints broken-svc-app"
fi
echo ""
echo "📖 Full guide: UI_TESTING_GUIDE.md"
echo ""

