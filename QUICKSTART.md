# Quick Start Guide

This guide will help you get the Kubernetes SRE AI Agent up and running quickly.

## Prerequisites

1. **Python 3.8+** installed
2. **Access to a Kubernetes cluster** (minikube, kind, or cloud cluster)
3. **OpenAI API Key** ([Get one here](https://platform.openai.com/api-keys))
4. **kubectl** configured to access your cluster

## Setup (5 minutes)

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure API Key

Create a `.env` file:

```bash
cp .env.example .env
```

Edit `.env` and add your OpenAI API key:
```
OPENAI_API_KEY=sk-your-actual-key-here
```

### 3. Verify Kubernetes Access

```bash
kubectl cluster-info
kubectl get nodes
```

## First Run (Safe Mode)

Test the agent in dry-run mode (no actual changes):

```bash
python main.py --namespace default --mode once --dry-run
```

This will:
1. Connect to your Kubernetes cluster
2. Scan for issues in the `default` namespace
3. Diagnose any problems using AI
4. Show what it *would* do (but won't actually do it)

## Testing with Sample Issues

### 1. Create Test Problems

```bash
python examples/create_test_scenarios.py
kubectl apply -f examples/k8s/
```

### 2. Wait for Issues to Appear

```bash
sleep 15
kubectl get pods  # You should see some failing pods
```

### 3. Run the Agent

```bash
python main.py --namespace default --mode once --dry-run
```

You should see output like:

```
SRE AGENT SUMMARY
====================================
Namespace: default
Issues Detected: 3
Issues Diagnosed: 3
Remediations Attempted: 2
Remediations Successful: 2
====================================
```

### 4. Review the Report

Check `sre_agent_report.json` for detailed results.

### 5. Cleanup

```bash
kubectl delete -f examples/k8s/
```

## Next Steps

### Run with Actual Remediation

⚠️ **Warning**: This will make actual changes to your cluster!

```bash
python main.py --namespace default --mode once
```

### Continuous Monitoring

Monitor your cluster continuously:

```bash
python main.py --namespace default --mode continuous --interval 60
```

Press Ctrl+C to stop.

### Customize Behavior

Edit `.env` or use command-line flags:

```bash
# Disable approval requirement (not recommended for production)
python main.py --namespace default --mode once --no-approval

# Change log level
python main.py --namespace default --mode once --log-level DEBUG

# Use different namespace
python main.py --namespace kube-system --mode once --dry-run
```

## Troubleshooting

### "OpenAI API key not found"

Make sure you've set `OPENAI_API_KEY` in your `.env` file.

### "Failed to initialize Kubernetes client"

Check that:
- kubectl is configured: `kubectl cluster-info`
- You have permissions: `kubectl auth can-i get pods`

### "No issues detected"

Good! Your cluster is healthy. Try applying test scenarios to see the agent in action.

## Safety Reminders

1. **Always test in dry-run mode first**
2. **Review the report before enabling actual remediation**
3. **Start with non-production clusters**
4. **Monitor the logs** in `sre_agent.log`

## Need Help?

- Check the full [README.md](README.md) for detailed documentation
- Review example code in `examples/`
- Check logs in `sre_agent.log`
