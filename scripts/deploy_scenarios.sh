#!/bin/bash
# Deploy test scenarios to Kubernetes cluster

set -e

# Continue on errors for individual deployments
set +e

echo "🚀 Deploying test scenarios to Kubernetes cluster..."

# Check if kubectl is configured
if ! kubectl cluster-info &> /dev/null; then
    echo "❌ kubectl is not configured or cluster is not accessible"
    echo "Run: ./scripts/setup_kind.sh to create a local cluster"
    exit 1
fi

# Deploy Scenario A: OOMKilled Pods
echo ""
echo "📦 Deploying Scenario A: OOMKilled Pods..."
kubectl apply -f tests/scenarios/scenario_a_oom/variant_1_memory_limit_low.yaml && echo "  ✅ variant_1 deployed" || echo "  ⚠️  variant_1 failed"
kubectl apply -f tests/scenarios/scenario_a_oom/variant_2_memory_leak.yaml && echo "  ✅ variant_2 deployed" || echo "  ⚠️  variant_2 failed"
kubectl apply -f tests/scenarios/scenario_a_oom/variant_3_jvm_heap.yaml && echo "  ✅ variant_3 deployed" || echo "  ⚠️  variant_3 failed"

# Wait for deployments to be created
sleep 2

# Show status
echo ""
echo "📊 Deployment status:"
kubectl get deployments -n default | grep oom-app || true

echo ""
echo "📊 Pod status (will show OOMKilled after a few seconds):"
kubectl get pods -n default | grep oom-app || true

# Deploy Scenario B: Broken Service
echo ""
echo "📦 Deploying Scenario B: Broken Service..."
kubectl apply -f tests/scenarios/scenario_b_service/broken_service.yaml && echo "  ✅ broken_service deployed" || echo "  ⚠️  broken_service failed"

set -e

sleep 2

echo ""
echo "📊 Service status:"
kubectl get svc broken-service -n default || true

echo ""
echo "📊 Endpoints (should be empty due to label mismatch):"
kubectl get endpoints broken-service -n default || true

echo ""
echo "✅ Test scenarios deployed!"
echo ""
echo "Next steps:"
echo "  1. Wait for pods to be OOMKilled:"
echo "     kubectl get pods -w"
echo ""
echo "  2. Check service endpoints:"
echo "     kubectl get endpoints broken-service"
echo ""
echo "  3. Run the SRE agent:"
echo "     python -m sre_agent.cli diagnose --namespace default --deployment oom-app-v1"
echo "     python -m sre_agent.cli diagnose --namespace default --service broken-service"

