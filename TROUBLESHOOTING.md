# Troubleshooting: Diagnose Errors

## Common Diagnose Errors and Solutions

### Error 1: "OPENROUTER_API_KEY not set"

**What you see:**
```
❌ OPENROUTER_API_KEY not set! Please export it:
export OPENROUTER_API_KEY='your-key'
```

**Solution:**
```bash
# In the terminal where you run k8s-sre-agent ui
export OPENROUTER_API_KEY="YOUR_API_KEY_HERE"

# Verify it's set
echo $OPENROUTER_API_KEY

# Restart UI
k8s-sre-agent ui
```

### Error 2: "Resource Not Found"

**What you see:**
```
❌ Resource Not Found: deployments.apps "my-app" not found
```

**Solution:**
```bash
# Check if resource exists
kubectl get deployment oom-test-app -n default

# If it doesn't exist, deploy it
kubectl apply -f tests/scenarios/oom_killed/memory_limit_low.yaml

# Wait for it to be created
kubectl get pods -l app=oom-test-app
```

### Error 3: "Connection Error" or "Timeout"

**What you see:**
```
❌ Connection Error: ...
```

**Solution:**
```bash
# Test kubectl connection
kubectl get nodes

# If that fails, check your kubeconfig
kubectl config current-context

# For kind clusters
kind get clusters

# For minikube
minikube status
```

### Error 4: "No workflow ID returned"

**What you see:**
```
❌ Error: No workflow ID returned. Check logs for details.
```

**Solution:**
- Check the terminal where UI is running for detailed error logs
- Make sure API key is set correctly
- Try running diagnosis again

## How to Get Workflow ID

### Step-by-Step:

1. **Make sure everything is set up:**
   ```bash
   # API key is set
   echo $OPENROUTER_API_KEY
   
   # Resource exists
   kubectl get deployment oom-test-app
   ```

2. **In the UI Diagnose tab:**
   - Namespace: `default`
   - Resource Type: `Deployment`
   - Resource Name: `oom-test-app`
   - Click **"Diagnose"**

3. **After diagnosis completes:**
   - Look for the **"Workflow ID"** field
   - It will show something like: `abc123-def456-7890-ghij-klmnopqrstuv`
   - **Copy this complete ID**

4. **If you see an error:**
   - The error message will tell you what's wrong
   - Fix the issue (see errors above)
   - Try diagnosis again

## Example: Successful Diagnosis

**What you should see:**

```
## Failure: OOMKilled

### Root Cause
Container memory limit (64Mi) is insufficient for application workload

### Confidence: 85%

### Workflow ID
abc123-def456-7890-ghij-klmnopqrstuv

⚠️ Copy this Workflow ID to use in the "Approve & Execute" tab!
```

**Then copy:** `abc123-def456-7890-ghij-klmnopqrstuv`

## Quick Test

```bash
# 1. Set API key
export OPENROUTER_API_KEY="YOUR_API_KEY_HERE"

# 2. Deploy test scenario
kubectl apply -f tests/scenarios/oom_killed/memory_limit_low.yaml

# 3. Wait for failure
sleep 10

# 4. Verify it exists
kubectl get deployment oom-test-app

# 5. Start UI
k8s-sre-agent ui

# 6. In browser: Diagnose tab → Fill form → Click Diagnose → Copy Workflow ID
```

## Still Having Issues?

1. **Check UI terminal logs** - Look for detailed error messages
2. **Test CLI directly:**
   ```bash
   export OPENROUTER_API_KEY="sk-or-v1-..."
   k8s-sre-agent diagnose -t Deployment -r oom-test-app
   ```
3. **Check kubectl works:**
   ```bash
   kubectl get pods
   kubectl get deployment oom-test-app
   ```

