# Quick Start - UI Testing

## ⚠️ CRITICAL: Set API Key First!

```bash
export OPENROUTER_API_KEY="YOUR_API_KEY_HERE"
```

**Verify:** `echo $OPENROUTER_API_KEY` (should show your key, not empty)

## 🚀 Easiest Way: Use the Launcher

```bash
cd ~/SREAgent/k8s-sre-agent
source .venv/bin/activate
export OPENROUTER_API_KEY="YOUR_API_KEY_HERE"

# This script checks everything and starts UI
./scripts/start_ui.sh
```

## 📋 Manual Steps (3 Terminals)

### Terminal 1: Setup

```bash
cd ~/SREAgent/k8s-sre-agent
source .venv/bin/activate

# Start Qdrant
docker-compose up -d qdrant

# Deploy failing scenario
kubectl apply -f tests/scenarios/oom_killed/memory_limit_low.yaml

# Wait for failure
sleep 10
kubectl get pods -l app=oom-test-app
# Should show: CrashLoopBackOff
```

### Terminal 2: Start UI (IMPORTANT: Set API key here!)

```bash
cd ~/SREAgent/k8s-sre-agent
source .venv/bin/activate

# ⚠️ SET API KEY IN THIS TERMINAL!
export OPENROUTER_API_KEY="YOUR_API_KEY_HERE"

# Verify it's set
echo $OPENROUTER_API_KEY

# Start UI
k8s-sre-agent ui
```

**Open browser:** http://localhost:7860

### Browser: Test Flow

#### Step 1: Diagnose
1. Go to **"Diagnose"** tab
2. Fill:
   - Namespace: `default`
   - Resource Type: `Deployment`
   - Resource Name: `oom-test-app`
3. Click **"Diagnose"**
4. **Copy the Workflow ID** (full ID, e.g., `abc123-def456-7890-...`)

#### Step 2: Human Feedback
1. Go to **"Approve & Execute"** tab
2. Fill:
   - Workflow ID: `[paste full ID from Step 1]`
   - Your Feedback: `"Memory increase looks safe, proceed"`
   - ☑ **Execute Fix** (check this!)
3. Click **"Submit Approval"**

#### Step 3: Verify
- See success message: "✅ FIX APPLIED SUCCESSFULLY"
- Check feedback history table
- Verify in terminal:
  ```bash
  kubectl get pods -l app=oom-test-app
  # Should show: Running (was CrashLoopBackOff)
  ```

## 🐛 Troubleshooting

| Problem | Solution |
|---------|----------|
| **UI shows "API key not set"** | Export API key in the terminal where you run `k8s-sre-agent ui` |
| **UI won't start** | Check port: `lsof -i :7860` |
| **"Workflow not found"** | Make sure you copied the complete Workflow ID |
| **Qdrant error** | Restart: `docker-compose restart qdrant` |

## ✅ Quick Test Checklist

- [ ] API key exported: `echo $OPENROUTER_API_KEY`
- [ ] Qdrant running: `curl http://localhost:6333/readyz`
- [ ] Scenario deployed: `kubectl get pods -l app=oom-test-app`
- [ ] UI started: `k8s-sre-agent ui` (shows URL)
- [ ] Browser opened: http://localhost:7860
- [ ] Diagnosis ran: Got Workflow ID
- [ ] Approval submitted: Checked "Execute Fix"
- [ ] Fix verified: Pod is Running

## 📚 Full Guide

See `UI_TESTING_GUIDE.md` for detailed instructions.
