# End-to-End UI Testing Guide

Complete guide to test the K8s SRE Agent UI with human feedback processing.

## ⚠️ IMPORTANT: Set API Key First!

```bash
export OPENROUTER_API_KEY="YOUR_API_KEY_HERE"
```

**Verify it's set:**
```bash
echo $OPENROUTER_API_KEY
```

## Quick Start (Easiest Method)

```bash
cd ~/SREAgent/k8s-sre-agent
source .venv/bin/activate
export OPENROUTER_API_KEY="YOUR_API_KEY_HERE"

# Use the launcher script (checks everything)
./scripts/start_ui.sh
```

## Step-by-Step Manual Setup

### Step 1: Prerequisites Check

```bash
# 1. Navigate to project
cd ~/SREAgent/k8s-sre-agent

# 2. Activate virtual environment
source .venv/bin/activate

# 3. SET API KEY (REQUIRED!)
export OPENROUTER_API_KEY="YOUR_API_KEY_HERE"

# 4. Verify API key is set
echo $OPENROUTER_API_KEY
# Should show your key, not empty

# 5. Verify kubectl access
kubectl get nodes
```

### Step 2: Start Qdrant (Vector Database)

```bash
# Start Qdrant in Docker
docker-compose up -d qdrant

# Wait a few seconds, then verify
sleep 3
curl http://localhost:6333/readyz
# Should return: "all shards are ready"

# (Optional) Seed knowledge base
python scripts/seed_patterns.py
```

### Step 3: Deploy Test Scenario

**Option A: OOMKilled Pod (Recommended)**

```bash
# Deploy the failing deployment
kubectl apply -f tests/scenarios/oom_killed/memory_limit_low.yaml

# Wait for pod to fail (about 10-15 seconds)
sleep 10

# Verify it's failing
kubectl get pods -l app=oom-test-app
# Should show: STATUS: CrashLoopBackOff

# Check it's OOMKilled
kubectl describe pod -l app=oom-test-app | grep -A5 "Last State"
# Should show: Reason: OOMKilled
```

**Option B: Broken Service**

```bash
# Deploy the broken service
kubectl apply -f tests/scenarios/broken_service/label_mismatch.yaml

# Verify service has no endpoints
kubectl get endpoints broken-svc-app
# Should show: ENDPOINTS: <none>
```

### Step 4: Start the UI

**IMPORTANT: Make sure API key is set in THIS terminal!**

```bash
# In a NEW terminal window
cd ~/SREAgent/k8s-sre-agent
source .venv/bin/activate

# SET API KEY (MUST DO THIS!)
export OPENROUTER_API_KEY="YOUR_API_KEY_HERE"

# Verify it's set
echo $OPENROUTER_API_KEY

# Start UI
k8s-sre-agent ui
```

**Expected output:**
```
✅ Starting UI on http://0.0.0.0:7860
Press Ctrl+C to stop
Running on local URL:  http://127.0.0.1:7860
```

**Open browser:** http://localhost:7860

**If you see an error about API key:**
- The UI will show a warning at the top
- Make sure you exported the API key in the terminal where you ran `k8s-sre-agent ui`
- Check with: `echo $OPENROUTER_API_KEY`

## Step 5: Test Human Feedback Flow

### 5.1 Diagnose the Issue

1. **Go to "Diagnose" tab** in the browser
2. Fill in the form:
   - **Namespace**: `default`
   - **Resource Type**: 
     - `Deployment` (for OOMKilled scenario)
     - `Service` (for Broken Service scenario)
   - **Resource Name**: 
     - `oom-test-app` (for OOMKilled)
     - `broken-svc-app` (for Broken Service)
3. Click **"Diagnose"** button

**Expected Result:**
- If API key is missing: You'll see an error message at the top
- If API key is set: You'll see:
  - Failure type (OOMKilled or ServiceMisconfigured)
  - Root cause analysis
  - Confidence score
  - Proposed fix command
  - **Workflow ID** (copy this!)

**Troubleshooting:**
- If you see "OPENROUTER_API_KEY not set": 
  - Close the UI (Ctrl+C)
  - Export the API key: `export OPENROUTER_API_KEY="YOUR_API_KEY_HERE"`
  - Restart: `k8s-sre-agent ui`

### 5.2 Provide Human Feedback

1. **Go to "Approve & Execute" tab**
2. Fill in the form:
   - **Workflow ID**: Paste the ID from Step 5.1 (the full ID, e.g., `abc123-def456-7890`)
   - **Your Feedback**: Type something like:
     ```
     Looks good. Memory limit increase is safe.
     Proceed with fix.
     ```
   - **Execute Fix**: 
     - ✅ **Check the box** to approve AND execute
     - ⬜ Leave unchecked to approve only (no execution)
3. Click **"Submit Approval"** button

**Expected Result:**
- If Workflow ID is wrong: Error message explaining what to check
- If "Execute Fix" is checked:
  - ✅ Success message: "FIX APPLIED SUCCESSFULLY"
  - Status shows the fix was applied
  - Pattern stored in knowledge base
- Feedback History table updates with your decision

### 5.3 Verify the Fix

**In a terminal:**

```bash
# For OOMKilled scenario
kubectl get pods -l app=oom-test-app
# Should show: STATUS: Running (was CrashLoopBackOff)

kubectl get deployment oom-test-app -o jsonpath='{.spec.template.spec.containers[0].resources.limits.memory}'
# Should show: 512Mi (was 64Mi)

# For Broken Service scenario
kubectl get endpoints broken-svc-app
# Should show: ENDPOINTS: 10.244.x.x:80 (was <none>)
```

### 5.4 Check Feedback History

1. **Go back to "Approve & Execute" tab**
2. Scroll down to **"Feedback History"** section
3. You should see a table with:
   - Timestamp
   - Workflow ID (shortened)
   - Action taken (approved_and_executed, etc.)
   - Failure type
   - Result (success/partial/error)

## Step 6: Test Rejection Flow

To test rejection (approve but don't execute):

1. Deploy another failing scenario:
   ```bash
   kubectl delete deployment oom-test-app  # Clean up first
   kubectl apply -f tests/scenarios/oom_killed/memory_limit_low.yaml
   ```

2. Run diagnosis again in UI (get new Workflow ID)

3. In "Approve & Execute" tab:
   - Paste workflow ID
   - **Leave "Execute Fix" UNCHECKED**
   - Add feedback: "Need to review with team first"
   - Click "Submit Approval"

**Expected Result:**
- Message: "Action approved but NOT executed"
- Feedback History shows: `approved_no_execute`

## Troubleshooting

### UI won't start / API key error

```bash
# Check if API key is set
echo $OPENROUTER_API_KEY

# If empty, set it:
export OPENROUTER_API_KEY="YOUR_API_KEY_HERE"

# Verify
echo $OPENROUTER_API_KEY

# Restart UI
k8s-sre-agent ui
```

### UI shows "OPENROUTER_API_KEY not set" warning

- The API key must be set in the **same terminal** where you run `k8s-sre-agent ui`
- Check: `echo $OPENROUTER_API_KEY` in that terminal
- If empty, export it and restart the UI

### Port 7860 already in use

```bash
# Check what's using the port
lsof -i :7860

# Kill the process
kill -9 <PID>

# Or use a different port
k8s-sre-agent ui --port 7861
```

### Diagnosis fails / "Workflow not found"

- Make sure you copied the **complete** Workflow ID from Diagnose tab
- Workflow IDs look like: `abc123-def456-7890-ghij-klmnopqrstuv`
- Don't copy just part of it

### Qdrant connection error

```bash
# Restart Qdrant
docker-compose restart qdrant

# Check logs
docker-compose logs qdrant

# Verify it's running
curl http://localhost:6333/readyz
```

### kubectl connection error

```bash
# Test connection
kubectl get nodes

# Check kubeconfig
kubectl config current-context

# If using kind/minikube, make sure cluster is running
kind get clusters  # or: minikube status
```

## Complete Test Flow Summary

```
1. Set API key        → export OPENROUTER_API_KEY="YOUR_API_KEY_HERE"
2. Start Qdrant      → docker-compose up -d qdrant
3. Deploy scenario    → kubectl apply -f tests/scenarios/...
4. Start UI          → k8s-sre-agent ui (in terminal with API key!)
5. Open browser       → http://localhost:7860
6. Diagnose           → Fill form, click "Diagnose"
7. Copy Workflow ID   → From diagnosis result
8. Approve & Execute  → Paste ID, add feedback, check "Execute Fix"
9. Verify fix         → kubectl get pods/services
10. Check history     → See table in "Approve & Execute" tab
```

## Expected UI Screenshots Flow

### Tab 1: Diagnose
```
┌─────────────────────────────────────┐
│ ✅ API key configured               │
├─────────────────────────────────────┤
│ Namespace: default                  │
│ Resource Type: [Deployment ▼]       │
│ Resource Name: oom-test-app         │
│ [Diagnose]                          │
├─────────────────────────────────────┤
│ ## Failure: OOMKilled              │
│ ### Root Cause                      │
│ Memory limit insufficient...        │
│ ### Confidence: 85%                │
│                                     │
│ Proposed Fix:                       │
│ kubectl patch deployment...         │
│                                     │
│ Workflow ID: abc123-def456-7890     │
└─────────────────────────────────────┘
```

### Tab 2: Approve & Execute
```
┌─────────────────────────────────────┐
│ Workflow ID: [abc123-def456-7890]  │
│ ☑ Execute Fix                       │
│ Feedback: [Looks good, proceed]    │
│ [Submit Approval]                   │
├─────────────────────────────────────┤
│ ✅ FIX APPLIED SUCCESSFULLY         │
│ Status: healthy                     │
│ Pattern stored in knowledge base   │
│                                     │
│ Your feedback: Looks good, proceed │
├─────────────────────────────────────┤
│ ### Feedback History                │
│ | Time | Workflow | Action | Result │
│ | 10:30| abc123  | execute| success│
└─────────────────────────────────────┘
```

## Quick Reference Commands

```bash
# Set API key (DO THIS FIRST!)
export OPENROUTER_API_KEY="YOUR_API_KEY_HERE"

# Start everything
docker-compose up -d qdrant
kubectl apply -f tests/scenarios/oom_killed/memory_limit_low.yaml
k8s-sre-agent ui

# Or use the launcher
./scripts/start_ui.sh
```

## Next Steps

After testing:
- Try different scenarios
- Test rejection flow
- Check Qdrant for stored patterns: `curl http://localhost:6333/collections/k8s_failure_patterns`
- Review logs: Check terminal where UI is running
