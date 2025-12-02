# End-to-End Pipeline: Complete Workflow with Human Feedback

This guide shows the **complete pipeline** for both scenarios, including all steps from detection to human feedback to execution.

---

## Pipeline Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    COMPLETE PIPELINE                        │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  1. SETUP      → Deploy failing scenario                    │
│  2. DETECT     → Agent detects failure                      │
│  3. DIAGNOSE   → Agent analyzes root cause                  │
│  4. PLAN       → Agent proposes fix                         │
│  5. APPROVE    → 🔵 HUMAN FEEDBACK REQUIRED 🔵              │
│  6. EXECUTE    → Agent applies fix (if approved)           │
│  7. EVALUATE   → Agent verifies fix worked                  │
│  8. LEARN      → Store pattern in knowledge base            │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## Scenario A: OOMKilled Pod - Complete Pipeline

### Step 1: Setup - Deploy Failing Scenario

```bash
# Terminal 1: Setup
cd ~/SREAgent/k8s-sre-agent
source .venv/bin/activate

# Start Qdrant (if not running)
docker-compose up -d qdrant

# Deploy the OOMKilled scenario
kubectl apply -f tests/scenarios/oom_killed/memory_limit_low.yaml

# Wait for pod to fail (10-15 seconds)
sleep 10

# Verify the failure
kubectl get pods -l app=oom-test-app
# Expected: STATUS: CrashLoopBackOff

# Check it's OOMKilled
kubectl describe pod -l app=oom-test-app | grep -A5 "Last State"
# Expected: Reason: OOMKilled, Exit Code: 137
```

**Expected State:**
- Deployment exists: `oom-test-app`
- Pod status: `CrashLoopBackOff`
- Last termination reason: `OOMKilled`
- Memory limit: `64Mi` (too low)

---

### Step 2: Detect - Agent Detects Failure

```bash
# Terminal 2: Start UI
cd ~/SREAgent/k8s-sre-agent
source .venv/bin/activate
export OPENROUTER_API_KEY="YOUR_API_KEY_HERE"

k8s-sre-agent ui
```

**In Browser (http://localhost:7860):**

1. Go to **"Diagnose"** tab
2. Fill form:
   - Namespace: `default`
   - Resource Type: `Deployment`
   - Resource Name: `oom-test-app`
3. Click **"Diagnose"**

**Agent Action:**
- Queries Kubernetes API
- Checks pod status
- Detects `OOMKilled` termination reason
- Sets `detected: true`, `failure_type: "OOMKilled"`

**Expected Output:**
```
## Failure: OOMKilled

### Root Cause
Container memory limit (64Mi) is insufficient for application workload (150Mi required)

### Confidence: 85%

### Workflow ID
abc123-def456-7890-ghij-klmnopqrstuv

⚠️ Copy this Workflow ID to use in the "Approve & Execute" tab!
```

**Copy the Workflow ID!** (e.g., `abc123-def456-7890-ghij-klmnopqrstuv`)

---

### Step 3: Diagnose - Agent Analyzes Root Cause

**Agent Action (Automatic):**
- Uses DSPy Chain-of-Thought reasoning
- Searches Qdrant for similar patterns
- Analyzes memory limits vs actual usage
- Generates root cause analysis

**Expected Diagnosis:**
- Root Cause: "Memory limit insufficient"
- Confidence: 85%
- Similar patterns found in knowledge base (if seeded)

---

### Step 4: Plan - Agent Proposes Fix

**Agent Action (Automatic):**
- Generates remediation plan
- Creates kubectl command
- Assesses risk level: `safe`
- Provides rollback command

**Expected Plan:**
```
Proposed Fix:
kubectl patch deployment oom-test-app -n default --type=json \
  -p='[{"op":"replace","path":"/spec/template/spec/containers/0/resources/limits/memory","value":"512Mi"}]'

Risk Level: safe
Rollback: kubectl rollout undo deployment/oom-test-app -n default
```

---

### Step 5: 🔵 APPROVE - Human Feedback Required 🔵

**This is where YOU provide feedback!**

**In Browser - "Approve & Execute" tab:**

1. **Paste Workflow ID** (from Step 2)
   ```
   abc123-def456-7890-ghij-klmnopqrstuv
   ```

2. **Add Your Feedback:**
   ```
   Memory increase from 64Mi to 512Mi looks safe.
   The application needs 150Mi, so 512Mi provides good headroom.
   Proceed with the fix.
   ```

3. **Decision:**
   - ☑ **Check "Execute Fix"** → Approve AND execute
   - ⬜ **Uncheck "Execute Fix"** → Approve only (no execution)

4. Click **"Submit Approval"**

**Human Feedback Options:**

| Action | Checkbox | Result |
|--------|----------|--------|
| **Approve & Execute** | ☑ Checked | Fix is applied immediately |
| **Approve Only** | ⬜ Unchecked | Approved but not executed (manual fix needed) |
| **Reject** | Don't submit | No action taken |

**Expected Output:**
```
✅ FIX APPLIED SUCCESSFULLY

Status: healthy
Pattern stored in knowledge base for future reference.

Your feedback: Memory increase from 64Mi to 512Mi looks safe...
```

**Feedback History Table Updates:**
```
| Time | Workflow | Action | Failure | Result |
| 10:30| abc123  | approved_and_executed | OOMKilled | success |
```

---

### Step 6: Execute - Agent Applies Fix

**Agent Action (Automatic, after approval):**

1. **Dry-run first** (safety check):
   ```bash
   kubectl patch deployment oom-test-app -n default --type=json \
     -p='[{"op":"replace",...}]' --dry-run=client
   ```

2. **If dry-run succeeds, execute:**
   ```bash
   kubectl patch deployment oom-test-app -n default --type=json \
     -p='[{"op":"replace","path":"/spec/template/spec/containers/0/resources/limits/memory","value":"512Mi"}]'
   ```

**Expected Result:**
- Command executes successfully
- Deployment updated
- New pod created with higher memory limit

---

### Step 7: Evaluate - Agent Verifies Fix

**Agent Action (Automatic):**

1. Waits for pod restart (5-10 seconds)
2. Checks pod status
3. Verifies no more OOMKilled events
4. Confirms pod is Running

**Verification:**
```bash
# In terminal
kubectl get pods -l app=oom-test-app
# Expected: STATUS: Running (was CrashLoopBackOff)

kubectl get deployment oom-test-app -o jsonpath='{.spec.template.spec.containers[0].resources.limits.memory}'
# Expected: 512Mi (was 64Mi)
```

**Expected Evaluation:**
- Status: `healthy`
- Fixed: `true`
- No more OOMKilled events

---

### Step 8: Learn - Store Pattern

**Agent Action (Automatic):**

Stores successful pattern in Qdrant:
```json
{
  "failure_type": "OOMKilled",
  "root_cause": "Container memory limit insufficient",
  "fix": "kubectl patch deployment ... --value='512Mi'",
  "scenario": "memory_limit_low",
  "timestamp": "2025-11-28T10:30:00Z"
}
```

**Verify Pattern Stored:**
```bash
curl http://localhost:6333/collections/k8s_failure_patterns | jq '.result.points_count'
# Should show: 1 (or more if patterns were seeded)
```

---

## Scenario B: Broken Service - Complete Pipeline

### Step 1: Setup - Deploy Broken Service

```bash
# Terminal 1: Setup
kubectl apply -f tests/scenarios/broken_service/label_mismatch.yaml

# Verify service has no endpoints
kubectl get endpoints broken-svc-app
# Expected: ENDPOINTS: <none>

# Verify pods are running (but not connected)
kubectl get pods -l app=broken-svc-app
# Expected: STATUS: Running

# Check service selector
kubectl get svc broken-svc-app -o jsonpath='{.spec.selector}'
# Expected: {"app":"wrong-label"}

# Check pod labels
kubectl get pods -l app=broken-svc-app --show-labels
# Expected: app=broken-svc-app (not wrong-label)
```

**Expected State:**
- Service exists: `broken-svc-app`
- Endpoints: `<none>`
- Pods: Running but not connected
- Selector mismatch: Service selector `app: wrong-label` doesn't match pod labels `app: broken-svc-app`

---

### Step 2: Detect - Agent Detects Failure

**In Browser - "Diagnose" tab:**

1. Fill form:
   - Namespace: `default`
   - Resource Type: `Service`
   - Resource Name: `broken-svc-app`
2. Click **"Diagnose"**

**Agent Action:**
- Queries Kubernetes API
- Checks service endpoints
- Finds empty endpoints list
- Compares service selector with pod labels
- Sets `detected: true`, `failure_type: "ServiceMisconfigured"`

**Expected Output:**
```
## Failure: ServiceMisconfigured

### Root Cause
Service selector does not match any pod labels - label mismatch between service and pods

### Confidence: 100%

### Workflow ID
xyz789-abc123-def456-ghij-klmnopqrstuv

⚠️ Copy this Workflow ID!
```

---

### Step 3: Diagnose - Agent Analyzes Root Cause

**Agent Action:**
- Uses DSPy to analyze service configuration
- Compares selector with available pod labels
- Identifies exact mismatch

**Expected Diagnosis:**
- Root Cause: "Service selector `app: wrong-label` doesn't match pod labels `app: broken-svc-app`"
- Confidence: 100%

---

### Step 4: Plan - Agent Proposes Fix

**Expected Plan:**
```
Proposed Fix:
kubectl patch svc broken-svc-app -n default \
  -p '{"spec":{"selector":{"app":"broken-svc-app"}}}'

Risk Level: safe
Rollback: kubectl patch svc broken-svc-app -n default \
  -p '{"spec":{"selector":{"app":"wrong-label"}}}'
```

---

### Step 5: 🔵 APPROVE - Human Feedback Required 🔵

**In Browser - "Approve & Execute" tab:**

1. **Paste Workflow ID** (from Step 2)
   ```
   xyz789-abc123-def456-ghij-klmnopqrstuv
   ```

2. **Add Your Feedback:**
   ```
   Selector fix looks correct. The service should match pod labels.
   This is a safe change. Proceed.
   ```

3. **Decision:**
   - ☑ Check "Execute Fix"

4. Click **"Submit Approval"**

**Expected Output:**
```
✅ FIX APPLIED SUCCESSFULLY

Status: healthy
Pattern stored in knowledge base.

Your feedback: Selector fix looks correct...
```

---

### Step 6: Execute - Agent Applies Fix

**Agent Action:**
- Patches service selector to match pod labels
- Updates from `app: wrong-label` to `app: broken-svc-app`

**Expected Result:**
- Service updated successfully
- Endpoints automatically populated

---

### Step 7: Evaluate - Agent Verifies Fix

**Verification:**
```bash
# Check endpoints are now populated
kubectl get endpoints broken-svc-app
# Expected: ENDPOINTS: 10.244.x.x:80 (was <none>)

# Check service selector
kubectl get svc broken-svc-app -o jsonpath='{.spec.selector}'
# Expected: {"app":"broken-svc-app"}
```

**Expected Evaluation:**
- Status: `healthy`
- Fixed: `true`
- Endpoints: Populated

---

### Step 8: Learn - Store Pattern

Pattern stored in Qdrant for future similar issues.

---

## Complete Pipeline Summary

### Scenario A: OOMKilled Pod

| Step | Action | Who | Status |
|------|--------|-----|--------|
| 1. Setup | Deploy failing deployment | Human | ✅ Manual |
| 2. Detect | Detect OOMKilled status | Agent | ✅ Automatic |
| 3. Diagnose | Analyze root cause | Agent | ✅ Automatic |
| 4. Plan | Propose memory increase | Agent | ✅ Automatic |
| 5. **Approve** | **Review and provide feedback** | **Human** | **🔵 Required** |
| 6. Execute | Patch deployment | Agent | ✅ After approval |
| 7. Evaluate | Verify pod running | Agent | ✅ Automatic |
| 8. Learn | Store pattern | Agent | ✅ Automatic |

### Scenario B: Broken Service

| Step | Action | Who | Status |
|------|--------|-----|--------|
| 1. Setup | Deploy broken service | Human | ✅ Manual |
| 2. Detect | Detect empty endpoints | Agent | ✅ Automatic |
| 3. Diagnose | Analyze label mismatch | Agent | ✅ Automatic |
| 4. Plan | Propose selector fix | Agent | ✅ Automatic |
| 5. **Approve** | **Review and provide feedback** | **Human** | **🔵 Required** |
| 6. Execute | Patch service selector | Agent | ✅ After approval |
| 7. Evaluate | Verify endpoints populated | Agent | ✅ Automatic |
| 8. Learn | Store pattern | Agent | ✅ Automatic |

---

## Human Feedback Examples

### Example 1: Approve with Notes
```
Feedback: "Memory increase is safe. Application needs 150Mi, 
512Mi provides good headroom. Proceed."
Action: ☑ Execute Fix
Result: ✅ Fix applied successfully
```

### Example 2: Approve but Don't Execute
```
Feedback: "Fix looks correct but need to coordinate with team first."
Action: ⬜ Execute Fix (unchecked)
Result: ✅ Approved but not executed (manual intervention needed)
```

### Example 3: Reject (Don't Submit)
```
Feedback: "Need to investigate further before applying fix."
Action: Don't click Submit
Result: No action taken, can re-run diagnosis later
```

---

## Quick Test Commands

### Test Scenario A (OOMKilled)
```bash
# Setup
kubectl apply -f tests/scenarios/oom_killed/memory_limit_low.yaml
sleep 10

# Start UI
export OPENROUTER_API_KEY="YOUR_API_KEY_HERE"
k8s-sre-agent ui

# In browser: Diagnose → Get Workflow ID → Approve & Execute → Provide feedback
```

### Test Scenario B (Broken Service)
```bash
# Setup
kubectl apply -f tests/scenarios/broken_service/label_mismatch.yaml

# Start UI (if not running)
k8s-sre-agent ui

# In browser: Diagnose → Get Workflow ID → Approve & Execute → Provide feedback
```

---

## Verification Checklist

After completing the pipeline:

- [ ] Failure detected by agent
- [ ] Root cause identified
- [ ] Fix proposed with risk assessment
- [ ] **Human provided feedback** (approve/reject/modify)
- [ ] Fix executed (if approved)
- [ ] Fix verified (pod running / endpoints populated)
- [ ] Pattern stored in knowledge base
- [ ] Feedback history shows your decision

---

## Next Steps

1. **Test both scenarios** end-to-end
2. **Try different feedback** (approve, approve-only, reject)
3. **Check feedback history** in UI
4. **Verify patterns** in Qdrant: `curl http://localhost:6333/collections/k8s_failure_patterns`
5. **Test pattern matching** - Deploy similar issue, see if agent finds stored pattern

