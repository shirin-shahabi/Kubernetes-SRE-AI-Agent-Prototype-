#!/bin/bash
# Quick test of Scenario A: OOMKilled Pod

set -e

export PYTHONPATH="${PYTHONPATH}:$(pwd)/src"

echo "🔍 Testing Scenario A: OOMKilled Pod (oom-app-v1)"
echo ""

# Show current state
echo "📊 Current Pod Status:"
kubectl get pods -n default | grep oom-app-v1 || echo "  Pod not found"
echo ""

# Show OOMKilled evidence
echo "📋 Pod Details (checking for OOMKilled):"
POD_NAME=$(kubectl get pods -n default -l app=oom-app -o jsonpath='{.items[0].metadata.name}' 2>/dev/null || echo "")
if [ -n "$POD_NAME" ]; then
    kubectl describe pod $POD_NAME -n default | grep -A 5 "Last State" || echo "  No termination info"
    echo ""
    echo "Recent Events:"
    kubectl get events -n default --field-selector involvedObject.name=$POD_NAME --sort-by='.lastTimestamp' | tail -3
fi

echo ""
echo "🤖 Running SRE Agent Diagnosis..."
echo ""

python -m sre_agent.cli diagnose --namespace default --deployment oom-app-v1

echo ""
echo "✅ Diagnosis complete!"
echo ""
echo "To see the proposed fix command, check the output above."
echo "To execute the fix, run:"
echo "  ./scripts/run_agent.sh execute --namespace default --deployment oom-app-v1"

