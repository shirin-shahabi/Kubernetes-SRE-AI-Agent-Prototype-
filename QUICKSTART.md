# Quick Start Guide

This guide will help you get the Kubernetes SRE AI Agent up and running quickly.

## Prerequisites

- Python 3.8+
- kubectl configured with cluster access
- (Optional) OpenAI API key for enhanced AI analysis

## 1. Installation (5 minutes)

```bash
# Clone the repository
git clone https://github.com/shirin-shahabi/Kubernetes-SRE-AI-Agent-Prototype-.git
cd Kubernetes-SRE-AI-Agent-Prototype-

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Test the installation
python test_components.py
```

## 2. Deploy Test Scenarios (2 minutes)

```bash
# Deploy Scenario A: OOMKilled Pod
kubectl apply -f k8s-manifests/scenario-a-oom.yaml

# Deploy Scenario B: Broken Service
kubectl apply -f k8s-manifests/scenario-b-broken-service.yaml

# Verify deployments (wait ~30 seconds for OOM crashes to occur)
kubectl get pods
kubectl get svc broken-service
kubectl get endpoints broken-service
```

## 3. Run the Agent (CLI Method)

### Scenario A: Fix OOMKilled Pod

```bash
python cli.py --scenario oomkilled --namespace default --deployment oom-app
```

**What happens:**
1. Agent analyzes the pod and detects OOMKilled status
2. Shows root cause analysis
3. Proposes increasing memory limit from 50Mi to 150Mi
4. Asks for your approval
5. Applies the fix if approved
6. Shows verification commands

### Scenario B: Fix Broken Service

```bash
python cli.py --scenario broken-service --namespace default --service broken-service
```

**What happens:**
1. Agent checks service endpoints
2. Detects label mismatch (version: v2 vs v1)
3. Proposes correcting the service selector
4. Asks for your approval
5. Applies the fix if approved
6. Shows verification commands

## 4. Alternative: Web UI Method

```bash
# Start the web interface
python web_ui.py

# Open in browser: http://localhost:7860
```

Then:
1. Select a scenario from the dropdown
2. Enter namespace and resource name
3. Click "Run Diagnosis"
4. Review the AI analysis
5. Click "Approve & Execute" or "Reject"

## 5. Verify the Fixes

### Verify OOMKilled Fix:
```bash
kubectl get pods -l app=oom-app
kubectl describe deployment oom-app
# Pod should now be running without crashes
```

### Verify Service Fix:
```bash
kubectl get endpoints broken-service
kubectl describe service broken-service
# Endpoints should now be populated
```

## 6. Cleanup

```bash
kubectl delete -f k8s-manifests/scenario-a-oom.yaml
kubectl delete -f k8s-manifests/scenario-b-broken-service.yaml
```

## Optional: Enable AI-Enhanced Analysis

To get enhanced AI-powered explanations:

```bash
# Copy the example env file
cp .env.example .env

# Edit .env and add your OpenAI API key
echo "OPENAI_API_KEY=sk-your-key-here" >> .env

# Run the agent (it will now use AI for analysis)
python cli.py --scenario oomkilled --namespace default --deployment oom-app
```

Without an API key, the agent still works but uses rule-based analysis instead of LLM-powered explanations.

## Troubleshooting

### "Failed to load Kubernetes config"
- Ensure `kubectl cluster-info` works
- Check your kubeconfig is properly configured

### "No module named 'xxx'"
- Make sure you installed dependencies: `pip install -r requirements.txt`
- Activate your virtual environment

### "No OOMKilled issue detected"
- Wait 30-60 seconds after deploying for the pod to crash
- Check pod status: `kubectl get pods -l app=oom-app`

### "Service has no selector labels"
- Ensure you're targeting the correct service name
- Verify the service exists: `kubectl get svc broken-service`

## What's Next?

- Read the full [README.md](README.md) for architecture details
- Explore the code in `src/` directory
- Modify scenarios in `k8s-manifests/` to test different issues
- Try creating your own scenarios!
