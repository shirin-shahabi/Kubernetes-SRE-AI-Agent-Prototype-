# Quick Start Guide

## Complete Setup in 5 Steps

### 1. Prerequisites Check
```bash
# Check Docker
./scripts/check_docker.sh

# Check kubectl
kubectl version --client

# Check kind (optional, for local cluster)
kind version
```

### 2. Set API Key
```bash
source scripts/setup_env.sh
# Or manually:
export OPENROUTER_API_KEY="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"
```

### 3. Start Infrastructure
```bash
# Start Qdrant and RabbitMQ
docker-compose up -d

# Verify
docker-compose ps
```

### 4. Setup Kubernetes Cluster

**Option A: Local cluster (kind)**
```bash
# Create cluster
./scripts/setup_kind.sh

# Deploy test scenarios
./scripts/deploy_scenarios.sh
```

**Option B: Existing cluster**
```bash
# Verify access
kubectl cluster-info

# Deploy scenarios
./scripts/deploy_scenarios.sh
```

### 5. Install and Run

```bash
# Install dependencies
pip install -r requirements.txt

# Set up environment (sets PYTHONPATH and API key)
source scripts/activate_env.sh

# Run the agent - Web UI
python -m sre_agent.web
# Open http://localhost:7860

# Or use CLI with helper script (recommended):
./scripts/run_agent.sh diagnose --namespace default --deployment oom-app-v1

# Or manually:
export PYTHONPATH="${PYTHONPATH}:$(pwd)/src"
python -m sre_agent.cli diagnose --namespace default --deployment oom-app-v1
```

## Verify Everything Works

```bash
# 1. Check Kubernetes cluster
kubectl get nodes
kubectl get pods -A

# 2. Check test scenarios are deployed
kubectl get deployments | grep oom-app
kubectl get svc broken-service

# 3. Check pods are OOMKilled (wait a few seconds)
kubectl get pods | grep oom-app

# 4. Check service has no endpoints
kubectl get endpoints broken-service

# 5. Run agent diagnosis
source scripts/activate_env.sh
./scripts/run_agent.sh diagnose --namespace default --deployment oom-app-v1
```

## Troubleshooting

**If `pip install -e .` fails:**
```bash
pip install -r requirements.txt
source scripts/activate_env.sh  # Sets PYTHONPATH automatically
```

**If "No module named 'sre_agent'":**
```bash
# Use the helper script (easiest)
./scripts/run_agent.sh diagnose --namespace default --deployment oom-app-v1

# Or set PYTHONPATH manually
export PYTHONPATH="${PYTHONPATH}:$(pwd)/src"
python -m sre_agent.cli diagnose --namespace default --deployment oom-app-v1
```

**If kubectl can't connect:**
```bash
# For kind cluster
kubectl config use-context kind-sre-agent-cluster

# Check cluster
kubectl cluster-info
```

**If pods aren't OOMKilling:**
```bash
# Wait a bit longer (stress containers need time)
kubectl get pods -w

# Check events
kubectl describe pod <pod-name>
```

