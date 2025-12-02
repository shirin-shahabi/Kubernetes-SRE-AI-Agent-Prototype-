# Quick CLI Test Guide

## Prerequisites

```bash
# 1. Set up environment
source scripts/activate_env.sh

# 2. Ensure scenarios are deployed
./scripts/deploy_scenarios.sh
```

## Test Scenario A: OOMKilled Pod

```bash
# Quick test script
./scripts/test_scenario_a.sh

# Or manually:
./scripts/run_agent.sh diagnose --namespace default --deployment oom-app-v1
```

**What you'll see:**
1. Current pod status (showing CrashLoopBackOff/OOMKilled)
2. Agent diagnosis with root cause
3. Proposed fix (kubectl command to increase memory limit)
4. Instructions to execute the fix

**Verify with kubectl:**
```bash
# Check pod status
kubectl get pods -n default | grep oom-app-v1

# Check for OOMKilled
kubectl describe pod <pod-name> -n default | grep -A 5 "Last State"

# Check events
kubectl get events -n default --sort-by='.lastTimestamp' | grep oom-app-v1
```

## Test Scenario B: Broken Service

```bash
# Quick test script
./scripts/test_scenario_b.sh

# Or manually:
./scripts/run_agent.sh diagnose --namespace default --service broken-service
```

**What you'll see:**
1. Service status (showing 0 endpoints)
2. Service selector vs pod labels mismatch
3. Agent diagnosis identifying label mismatch
4. Proposed fix (kubectl command to update service selector)

**Verify with kubectl:**
```bash
# Check service has no endpoints
kubectl get endpoints broken-service -n default

# Check service selector
kubectl get svc broken-service -n default -o jsonpath='{.spec.selector}' | jq .

# Check pod labels
kubectl get pods -n default -l app=healthy-app -o json | jq -r '.items[].metadata.labels'
```

## Interactive Demo

```bash
# Full interactive demo
./scripts/demo.sh
```

This will:
- Show current cluster status
- Let you choose a scenario
- Display kubectl output showing the problem
- Run the agent diagnosis
- Show proposed fixes

## Execute a Fix

After diagnosis, execute the fix:

```bash
# For Scenario A
./scripts/run_agent.sh execute --namespace default --deployment oom-app-v1

# For Scenario B
./scripts/run_agent.sh execute --namespace default --service broken-service
```

**Verify fix worked:**
```bash
# For OOMKilled - check pod is running
kubectl get pods -n default | grep oom-app-v1

# For Broken Service - check endpoints exist
kubectl get endpoints broken-service -n default
```

## Manual kubectl Verification

### Scenario A Verification:
```bash
# 1. Check deployment memory limits
kubectl get deployment oom-app-v1 -n default -o jsonpath='{.spec.template.spec.containers[0].resources.limits.memory}'

# 2. Check pod status
kubectl get pods -n default -l app=oom-app

# 3. Check for OOMKilled in pod events
kubectl describe pod <pod-name> -n default | grep -i oom
```

### Scenario B Verification:
```bash
# 1. Check service selector
kubectl get svc broken-service -n default -o yaml | grep -A 5 selector

# 2. Check endpoints
kubectl get endpoints broken-service -n default

# 3. Check pod labels
kubectl get pods -n default -o json | jq '.items[] | select(.status.phase=="Running") | {name: .metadata.name, labels: .metadata.labels}'
```

## Expected Output

### Scenario A Output:
```
DIAGNOSIS RESULTS
============================================================

🔴 Failure Detected: OOMKilled

📋 Root Cause Analysis:
   Pod is being OOMKilled due to insufficient memory limits...

📝 Contributing Factors:
   • Memory limit too low: 64Mi
   • Container memory usage exceeds configured limit
   • Kubernetes OOMKiller is terminating the pod

📊 Confidence: 90%

============================================================
PROPOSED FIX
============================================================

🔧 Fix Command:
   kubectl patch deployment oom-app-v1 -n default --type='json' -p='[{"op": "replace", "path": "/spec/template/spec/containers/0/resources/limits/memory", "value": "512Mi"}]'

⚠️  Risk Level: MEDIUM

↩️  Rollback Plan:
   kubectl rollout undo deployment/oom-app-v1 -n default

✅ Expected Outcome:
   Pod should have sufficient memory and stop being OOMKilled
```

### Scenario B Output:
```
DIAGNOSIS RESULTS
============================================================

🔴 Failure Detected: ServiceMisconfigured

📋 Root Cause Analysis:
   Service has no endpoints due to label mismatch...

📝 Contributing Factors:
   • Service selector: {"app":"healthy-app","tier":"frontend"}
   • Available pods: 2
   • Label mismatch prevents service from finding pods

📊 Confidence: 95%

============================================================
PROPOSED FIX
============================================================

🔧 Fix Command:
   kubectl patch service broken-service -n default --type='json' -p='[{"op": "replace", "path": "/spec/selector", "value": {"app":"healthy-app","tier":"backend"}}]'

⚠️  Risk Level: LOW

✅ Expected Outcome:
   Service should now have endpoints and route traffic to pods
```

