#!/bin/bash
# Setup local Kubernetes cluster using kind for testing

set -e

echo "🔧 Setting up local Kubernetes cluster with kind..."

# Check if kind is installed
if ! command -v kind &> /dev/null; then
    echo "❌ kind is not installed"
    echo "Install it with:"
    echo "  macOS: brew install kind"
    echo "  Linux: See https://kind.sigs.k8s.io/docs/user/quick-start/"
    exit 1
fi

# Check if kubectl is installed
if ! command -v kubectl &> /dev/null; then
    echo "❌ kubectl is not installed"
    echo "Install it with:"
    echo "  macOS: brew install kubectl"
    echo "  Linux: See https://kubernetes.io/docs/tasks/tools/"
    exit 1
fi

# Check if cluster already exists
if kind get clusters | grep -q "^sre-agent-cluster$"; then
    echo "⚠️  Cluster 'sre-agent-cluster' already exists"
    read -p "Delete and recreate? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "🗑️  Deleting existing cluster..."
        kind delete cluster --name sre-agent-cluster
    else
        echo "✅ Using existing cluster"
        kubectl cluster-info --context kind-sre-agent-cluster
        exit 0
    fi
fi

# Create cluster
echo "📦 Creating kind cluster 'sre-agent-cluster'..."
cat <<EOF | kind create cluster --name sre-agent-cluster --config=-
kind: Cluster
apiVersion: kind.x-k8s.io/v1alpha4
nodes:
- role: control-plane
  kubeadmConfigPatches:
  - |
    kind: InitConfiguration
    nodeRegistration:
      kubeletExtraArgs:
        node-labels: "ingress-ready=true"
  extraPortMappings:
  - containerPort: 80
    hostPort: 80
    protocol: TCP
  - containerPort: 443
    hostPort: 443
    protocol: TCP
EOF

# Wait for cluster to be ready
echo "⏳ Waiting for cluster to be ready..."
kubectl wait --for=condition=Ready node --all --timeout=120s --context kind-sre-agent-cluster

# Set context
kubectl config use-context kind-sre-agent-cluster

echo ""
echo "✅ Cluster 'sre-agent-cluster' is ready!"
echo ""
echo "Next steps:"
echo "  1. Deploy test scenarios:"
echo "     kubectl apply -f tests/scenarios/scenario_a_oom/"
echo "     kubectl apply -f tests/scenarios/scenario_b_service/"
echo ""
echo "  2. Check cluster status:"
echo "     kubectl cluster-info"
echo "     kubectl get nodes"
echo ""
echo "  3. Run the SRE agent:"
echo "     python -m sre_agent.cli diagnose --namespace default --deployment oom-app-v1"

