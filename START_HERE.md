# 🚀 START HERE - Quick UI Test

## ✅ Qdrant is Already Running!

Your Qdrant is already running on port 6333. You can skip the `docker-compose up -d qdrant` step.

## Next Steps:

### 1. Set API Key (REQUIRED!)

```bash
export OPENROUTER_API_KEY="your-api-key-here"
```

**Verify:** `echo $OPENROUTER_API_KEY`

### 2. Deploy Test Scenario

```bash
kubectl apply -f tests/scenarios/oom_killed/memory_limit_low.yaml

# Wait 10 seconds for pod to fail
sleep 10

# Verify it's failing
kubectl get pods -l app=oom-test-app
# Should show: CrashLoopBackOff
```

### 3. Start UI

```bash
# Make sure API key is set in THIS terminal
export OPENROUTER_API_KEY="your-api-key-here"

# Start UI
k8s-sre-agent ui
```

**Open browser:** http://localhost:7860

### 4. Test in Browser

1. **Diagnose Tab:**
   - Namespace: `default`
   - Resource Type: `Deployment`
   - Resource Name: `oom-test-app`
   - Click "Diagnose"
   - **Copy the Workflow ID**

2. **Approve & Execute Tab:**
   - Paste Workflow ID
   - Add feedback: `"Looks good, proceed"`
   - ☑ Check "Execute Fix"
   - Click "Submit Approval"

3. **Verify:**
   ```bash
   kubectl get pods -l app=oom-test-app
   # Should show: Running (was CrashLoopBackOff)
   ```

## 🐛 If UI Shows "API Key Not Set"

- Make sure you exported the API key in the **same terminal** where you run `k8s-sre-agent ui`
- Check: `echo $OPENROUTER_API_KEY` in that terminal
- If empty, export it and restart the UI

## 📚 Full Guide

See `UI_TESTING_GUIDE.md` for detailed instructions.

