#!/bin/bash
# Interactive CLI demo of the SRE Agent

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  Kubernetes SRE AI Agent - CLI Demo${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Check prerequisites
if ! command -v kubectl &> /dev/null; then
    echo -e "${RED}❌ kubectl not found${NC}"
    exit 1
fi

if ! kubectl cluster-info &> /dev/null; then
    echo -e "${RED}❌ kubectl not configured or cluster not accessible${NC}"
    exit 1
fi

# Check if scenarios are deployed
echo -e "${YELLOW}📊 Checking cluster status...${NC}"
echo ""

# Check Scenario A deployments
echo -e "${BLUE}Scenario A: OOMKilled Pods${NC}"
kubectl get deployments -n default | grep oom-app || echo "  No OOM deployments found"
echo ""

# Check Scenario B service
echo -e "${BLUE}Scenario B: Broken Service${NC}"
kubectl get svc broken-service -n default 2>/dev/null && echo "  Service found" || echo "  Service not found"
kubectl get endpoints broken-service -n default 2>/dev/null | tail -1 || echo "  No endpoints"
echo ""

# Menu
echo -e "${GREEN}Select a scenario to diagnose:${NC}"
echo "  1) Scenario A: OOMKilled Pod (oom-app-v1)"
echo "  2) Scenario A: OOMKilled Pod (oom-app-v2)"
echo "  3) Scenario B: Broken Service (broken-service)"
echo "  4) Custom Deployment"
echo "  5) Custom Service"
echo "  6) Exit"
echo ""
read -p "Enter choice [1-6]: " choice

case $choice in
    1)
        NAMESPACE="default"
        RESOURCE_TYPE="Deployment"
        RESOURCE_NAME="oom-app-v1"
        ;;
    2)
        NAMESPACE="default"
        RESOURCE_TYPE="Deployment"
        RESOURCE_NAME="oom-app-v2"
        ;;
    3)
        NAMESPACE="default"
        RESOURCE_TYPE="Service"
        RESOURCE_NAME="broken-service"
        ;;
    4)
        read -p "Namespace [default]: " NAMESPACE
        NAMESPACE=${NAMESPACE:-default}
        read -p "Deployment name: " RESOURCE_NAME
        RESOURCE_TYPE="Deployment"
        ;;
    5)
        read -p "Namespace [default]: " NAMESPACE
        NAMESPACE=${NAMESPACE:-default}
        read -p "Service name: " RESOURCE_NAME
        RESOURCE_TYPE="Service"
        ;;
    6)
        echo "Exiting..."
        exit 0
        ;;
    *)
        echo -e "${RED}Invalid choice${NC}"
        exit 1
        ;;
esac

echo ""
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  Running Diagnosis${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Show current state with kubectl
echo -e "${YELLOW}📋 Current Resource State:${NC}"
if [ "$RESOURCE_TYPE" == "Deployment" ]; then
    echo ""
    echo "Deployment:"
    kubectl get deployment $RESOURCE_NAME -n $NAMESPACE -o wide 2>/dev/null || echo "  Not found"
    echo ""
    echo "Pods:"
    kubectl get pods -n $NAMESPACE -l app=$(kubectl get deployment $RESOURCE_NAME -n $NAMESPACE -o jsonpath='{.spec.selector.matchLabels.app}' 2>/dev/null || echo $RESOURCE_NAME) 2>/dev/null || kubectl get pods -n $NAMESPACE | grep $RESOURCE_NAME || echo "  No pods found"
    echo ""
    echo "Pod Events (last 5):"
    kubectl get events -n $NAMESPACE --field-selector involvedObject.name=$(kubectl get pods -n $NAMESPACE -l app=$(kubectl get deployment $RESOURCE_NAME -n $NAMESPACE -o jsonpath='{.spec.selector.matchLabels.app}' 2>/dev/null || echo $RESOURCE_NAME) -o jsonpath='{.items[0].metadata.name}' 2>/dev/null) --sort-by='.lastTimestamp' | tail -5 || echo "  No events"
else
    echo ""
    echo "Service:"
    kubectl get svc $RESOURCE_NAME -n $NAMESPACE -o wide 2>/dev/null || echo "  Not found"
    echo ""
    echo "Endpoints:"
    kubectl get endpoints $RESOURCE_NAME -n $NAMESPACE 2>/dev/null || echo "  No endpoints"
    echo ""
    echo "Service Selector:"
    kubectl get svc $RESOURCE_NAME -n $NAMESPACE -o jsonpath='{.spec.selector}' 2>/dev/null | jq . || echo "  No selector"
    echo ""
    echo "Available Pod Labels:"
    kubectl get pods -n $NAMESPACE -o json | jq -r '.items[] | select(.status.phase=="Running") | "\(.metadata.name): \(.metadata.labels)"' | head -5 || echo "  No running pods"
fi

echo ""
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  Agent Diagnosis${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Run the agent
export PYTHONPATH="${PYTHONPATH}:$(pwd)/src"

if [ "$RESOURCE_TYPE" == "Deployment" ]; then
    python -m sre_agent.cli diagnose --namespace $NAMESPACE --deployment $RESOURCE_NAME
else
    python -m sre_agent.cli diagnose --namespace $NAMESPACE --service $RESOURCE_NAME
fi

echo ""
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  Next Steps${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo "To execute the proposed fix, run:"
if [ "$RESOURCE_TYPE" == "Deployment" ]; then
    echo -e "${GREEN}  ./scripts/run_agent.sh execute --namespace $NAMESPACE --deployment $RESOURCE_NAME${NC}"
else
    echo -e "${GREEN}  ./scripts/run_agent.sh execute --namespace $NAMESPACE --service $RESOURCE_NAME${NC}"
fi
echo ""
echo "Or use kubectl directly to verify/apply fixes manually."

