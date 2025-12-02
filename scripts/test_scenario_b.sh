#!/bin/bash
# Quick test of Scenario B: Broken Service

set -e

export PYTHONPATH="${PYTHONPATH}:$(pwd)/src"

echo "🔍 Testing Scenario B: Broken Service (broken-service)"
echo ""

# Show current state
echo "📊 Service Status:"
kubectl get svc broken-service -n default 2>/dev/null || echo "  Service not found"
echo ""

echo "📋 Endpoints (should be empty):"
kubectl get endpoints broken-service -n default 2>/dev/null || echo "  No endpoints found"
echo ""

echo "📋 Service Selector:"
kubectl get svc broken-service -n default -o jsonpath='{.spec.selector}' 2>/dev/null | jq . || echo "  No selector"
echo ""

echo "📋 Available Pod Labels:"
kubectl get pods -n default -l app=healthy-app -o json | jq -r '.items[] | "\(.metadata.name): \(.metadata.labels | to_entries | map("\(.key)=\(.value)") | join(", "))"' || echo "  No pods found"
echo ""

echo "🤖 Running SRE Agent Diagnosis..."
echo ""

python -m sre_agent.cli diagnose --namespace default --service broken-service

echo ""
echo "✅ Diagnosis complete!"
echo ""
echo "The agent should detect the label mismatch between service selector and pod labels."
echo "To execute the proposed fix, run:"
echo "  ./scripts/run_agent.sh execute --namespace default --service broken-service"

