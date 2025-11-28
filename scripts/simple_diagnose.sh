#!/bin/bash
# Simple kubectl-based diagnosis script

set -e

NAMESPACE=${1:-default}
RESOURCE_TYPE=${2:-Deployment}
RESOURCE_NAME=${3}

if [ -z "$RESOURCE_NAME" ]; then
    echo "Usage: $0 [namespace] [Deployment|Service] <resource-name>"
    echo "Example: $0 default Deployment oom-app-v1"
    echo "Example: $0 default Service broken-service"
    exit 1
fi

echo "=========================================="
echo "Kubernetes Resource Diagnosis"
echo "=========================================="
echo ""
echo "Namespace: $NAMESPACE"
echo "Resource: $RESOURCE_TYPE/$RESOURCE_NAME"
echo ""

if [ "$RESOURCE_TYPE" == "Deployment" ]; then
    echo "📊 Deployment Status:"
    kubectl get deployment $RESOURCE_NAME -n $NAMESPACE 2>/dev/null || {
        echo "❌ Deployment not found"
        exit 1
    }
    echo ""
    
    echo "📊 Pod Status:"
    kubectl get pods -n $NAMESPACE -l app=$(kubectl get deployment $RESOURCE_NAME -n $NAMESPACE -o jsonpath='{.spec.selector.matchLabels.app}' 2>/dev/null || echo $RESOURCE_NAME) 2>/dev/null || kubectl get pods -n $NAMESPACE | grep $RESOURCE_NAME || echo "  No pods found"
    echo ""
    
    echo "🔍 Checking for OOMKilled:"
    PODS=$(kubectl get pods -n $NAMESPACE -l app=$(kubectl get deployment $RESOURCE_NAME -n $NAMESPACE -o jsonpath='{.spec.selector.matchLabels.app}' 2>/dev/null || echo $RESOURCE_NAME) -o jsonpath='{.items[*].metadata.name}' 2>/dev/null || echo "")
    if [ -n "$PODS" ]; then
        for POD in $PODS; do
            OOM=$(kubectl get pod $POD -n $NAMESPACE -o jsonpath='{.status.containerStatuses[0].lastState.terminated.reason}' 2>/dev/null || echo "")
            if [ "$OOM" == "OOMKilled" ]; then
                echo "  ✅ Found OOMKilled pod: $POD"
                echo ""
                echo "📋 Memory Limits:"
                kubectl get deployment $RESOURCE_NAME -n $NAMESPACE -o jsonpath='{.spec.template.spec.containers[*].resources.limits.memory}' | tr ' ' '\n' | sed 's/^/  /'
                echo ""
                echo "🤖 Running AI Agent Diagnosis..."
                export PYTHONPATH="${PYTHONPATH}:$(pwd)/src"
                ./scripts/run_agent.sh diagnose --namespace $NAMESPACE --deployment $RESOURCE_NAME
                exit 0
            fi
        done
        echo "  ℹ️  No OOMKilled pods found (checking other issues...)"
    else
        echo "  ⚠️  No pods found for this deployment"
    fi
    
elif [ "$RESOURCE_TYPE" == "Service" ]; then
    echo "📊 Service Status:"
    kubectl get svc $RESOURCE_NAME -n $NAMESPACE 2>/dev/null || {
        echo "❌ Service not found"
        exit 1
    }
    echo ""
    
    echo "📊 Endpoints:"
    ENDPOINTS=$(kubectl get endpoints $RESOURCE_NAME -n $NAMESPACE -o jsonpath='{.subsets[*].addresses[*].ip}' 2>/dev/null || echo "")
    if [ -z "$ENDPOINTS" ]; then
        echo "  ⚠️  No endpoints found!"
        echo ""
        echo "📋 Service Selector:"
        kubectl get svc $RESOURCE_NAME -n $NAMESPACE -o jsonpath='{.spec.selector}' | jq . 2>/dev/null || kubectl get svc $RESOURCE_NAME -n $NAMESPACE -o jsonpath='{.spec.selector}'
        echo ""
        echo "📋 Available Pod Labels:"
        kubectl get pods -n $NAMESPACE -o json | jq -r '.items[] | select(.status.phase=="Running") | "  \(.metadata.name): \(.metadata.labels | to_entries | map("\(.key)=\(.value)") | join(", "))"' | head -5
        echo ""
        echo "🤖 Running AI Agent Diagnosis..."
        export PYTHONPATH="${PYTHONPATH}:$(pwd)/src"
        ./scripts/run_agent.sh diagnose --namespace $NAMESPACE --service $RESOURCE_NAME
        exit 0
    else
        echo "  ✅ Service has endpoints: $ENDPOINTS"
    fi
fi

echo ""
echo "✅ Resource appears healthy. No issues detected."

