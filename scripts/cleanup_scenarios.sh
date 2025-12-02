#!/bin/bash
# Cleanup test scenarios from Kubernetes cluster

set -e

echo "🧹 Cleaning up test scenarios..."

# Delete Scenario A deployments
echo ""
echo "🗑️  Deleting Scenario A: OOMKilled Pods..."
kubectl delete deployment oom-app-v1 -n default --ignore-not-found=true
kubectl delete deployment oom-app-v2 -n default --ignore-not-found=true
kubectl delete deployment oom-app-v3 -n default --ignore-not-found=true

# Delete Scenario B
echo ""
echo "🗑️  Deleting Scenario B: Broken Service..."
kubectl delete deployment healthy-app -n default --ignore-not-found=true
kubectl delete service broken-service -n default --ignore-not-found=true

echo ""
echo "✅ Cleanup complete!"

