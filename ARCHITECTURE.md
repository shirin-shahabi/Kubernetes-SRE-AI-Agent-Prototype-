# Architecture Documentation

## System Architecture

The Kubernetes SRE AI Agent follows a modular architecture with clear separation of concerns:

```
┌───────────────────────────────────────────────────────────────┐
│                        Main Entry Point                        │
│                          (main.py)                             │
└────────────────────────────────┬──────────────────────────────┘
                                 │
                                 ▼
┌───────────────────────────────────────────────────────────────┐
│                         SRE Agent                              │
│                       (agent.py)                               │
│                                                                │
│  Orchestrates the detection → diagnosis → remediation flow    │
└───┬────────────────────┬────────────────────┬─────────────────┘
    │                    │                    │
    │                    │                    │
    ▼                    ▼                    ▼
┌──────────┐      ┌──────────────┐     ┌────────────┐
│ Detector │      │ Diagnostician│     │ Remediator │
│          │      │              │     │            │
│ Scans    │      │ Uses LLM to  │     │ Executes   │
│ cluster  │──────▶ analyze and  │─────▶ fixes with │
│ for      │      │ explain      │     │ safety     │
│ issues   │      │ issues       │     │ checks     │
└────┬─────┘      └──────┬───────┘     └─────┬──────┘
     │                   │                   │
     │                   │                   │
     ▼                   ▼                   ▼
┌──────────────────┐  ┌────────────────┐  ┌──────────────────┐
│ Kubernetes Client│  │ LangChain/     │  │ Kubernetes Client│
│                  │  │ OpenAI API     │  │                  │
│ - List pods      │  │                │  │ - Delete pods    │
│ - Get events     │  │ GPT-3.5-turbo  │  │ - Restart deploy │
│ - Get logs       │  │ for reasoning  │  │ - Scale deploy   │
└────────┬─────────┘  └────────────────┘  └─────────┬────────┘
         │                                           │
         ▼                                           ▼
┌────────────────────────────────────────────────────────────┐
│                   Kubernetes Cluster                       │
└────────────────────────────────────────────────────────────┘
```

## Component Details

### 1. Configuration Layer (`config.py`)

**Purpose**: Centralized configuration management

**Key Features**:
- Environment variable loading
- Validation using Pydantic
- Default values for all settings
- Type-safe configuration access

**Key Configuration Options**:
- `openai_api_key`: API key for LLM access
- `dry_run`: Safety mode (default: true)
- `require_approval`: Human-in-the-loop control
- `max_remediation_attempts`: Prevent infinite loops
- `check_interval_seconds`: Monitoring frequency

### 2. Kubernetes Client (`kubernetes_client.py`)

**Purpose**: Abstract Kubernetes API interactions

**Capabilities**:
- **Read Operations**:
  - Get all pods in a namespace
  - Get pod logs (with tail limit)
  - Get Kubernetes events
  - Get deployments and their status
  
- **Write Operations** (with dry-run support):
  - Delete pods
  - Restart deployments
  - Scale deployments

**Safety Features**:
- All write operations support dry-run mode
- Comprehensive error handling
- Detailed logging of all operations

### 3. Detector (`detector.py`)

**Purpose**: Identify issues in the Kubernetes cluster

**Detection Capabilities**:

| Issue Type | Detection Method | Key Indicators |
|-----------|------------------|----------------|
| CrashLoopBackOff | Container state | waiting.reason == "CrashLoopBackOff" |
| ImagePullBackOff | Container state | waiting.reason in ["ImagePullBackOff", "ErrImagePull"] |
| OOMKilled | Container state | terminated.reason == "OOMKilled" |
| Pending Pods | Pod phase | status == "Pending" + PodScheduled == False |
| High Restart Count | Container stats | restart_count > 5 |
| Deployment Unavailable | Deployment status | available_replicas < desired_replicas |

**Output**:
- List of `Issue` objects
- Each issue contains:
  - Failure type
  - Resource information
  - Severity (high/medium/low)
  - Detailed context

### 4. Diagnostician (`diagnostician.py`)

**Purpose**: Use AI to analyze and explain issues

**Workflow**:
1. Receive detected issue + context (logs, events)
2. Prepare detailed prompt for LLM
3. Query GPT-3.5-turbo via LangChain
4. Parse response into structured diagnosis

**Diagnosis Output**:
- Root cause explanation
- Detailed reasoning
- Actionable recommendations
- Confidence level (high/medium/low)

**Example LLM Interaction**:
```
Input: Pod crashloop-test in CrashLoopBackOff
Context: Container exits with code 1
Logs: "sh: exit 1"

Output:
ROOT_CAUSE: Container command exits with error code 1
EXPLANATION: The container is configured to run "sh -c exit 1" 
which immediately exits with failure...
RECOMMENDATIONS:
- Check the container command and ensure it's correct
- Review application logs for startup errors
- Verify configuration and environment variables
CONFIDENCE: high
```

### 5. Remediator (`remediator.py`)

**Purpose**: Safely execute fixes for detected issues

**Remediation Strategies**:

| Issue Type | Action | Risk Level |
|-----------|--------|-----------|
| CrashLoopBackOff | Delete pod | Low |
| ImagePullBackOff | Manual intervention | Low |
| OOMKilled | Manual intervention | Medium |
| Pending Pod | Manual intervention | Low |
| High Restart Count | Delete pod (if <10) or Manual | Low/Medium |
| Deployment Unavailable | Restart deployment | Medium |

**Safety Mechanisms**:
1. **Risk Assessment**: Each plan has a risk level
2. **Approval Gate**: High-risk actions can require approval
3. **Retry Limiting**: Max attempts per resource per hour
4. **Dry-Run Mode**: Test without actual changes
5. **Audit Trail**: All actions logged to history

**Remediation Plan Structure**:
```python
{
  "issue": {...},
  "action": "delete_pod",
  "parameters": {"pod_name": "...", "namespace": "..."},
  "justification": "Pod in CrashLoopBackOff...",
  "risk_level": "low"
}
```

### 6. SRE Agent (`agent.py`)

**Purpose**: Orchestrate the complete remediation pipeline

**Main Loop**:
```python
1. Detect issues (detector.detect_issues())
2. For each issue:
   a. Gather context (logs, events)
   b. Diagnose (diagnostician.diagnose())
   c. Create plan (remediator.create_remediation_plan())
   d. Check safety (should_remediate())
   e. Execute (remediator.execute_plan())
   f. Record history
3. Return summary
```

**Operating Modes**:
- **Once**: Single check and remediation cycle
- **Continuous**: Ongoing monitoring with configurable interval

## Data Flow

### Detection Phase
```
Kubernetes Cluster
    ↓ (API calls)
Kubernetes Client
    ↓ (pod/deployment data)
Detector
    ↓ (Issue objects)
Agent
```

### Diagnosis Phase
```
Issue + Context
    ↓
Diagnostician
    ↓ (format prompt)
LangChain
    ↓ (API call)
OpenAI GPT-3.5
    ↓ (AI response)
LangChain
    ↓ (parse response)
Diagnostician
    ↓ (structured diagnosis)
Agent
```

### Remediation Phase
```
Issue + Diagnosis
    ↓
Remediator (create plan)
    ↓
Agent (safety checks)
    ↓ (if approved)
Remediator (execute)
    ↓
Kubernetes Client
    ↓ (API calls)
Kubernetes Cluster
```

## Security Considerations

### 1. Kubernetes Access
- Uses standard kubeconfig authentication
- Respects RBAC permissions
- Requires appropriate service account in cluster deployments

### 2. API Key Management
- OpenAI key stored in environment/secrets
- Never logged or committed to version control
- Can be rotated without code changes

### 3. Safety Defaults
- Dry-run mode enabled by default
- Approval required for high-risk actions
- Comprehensive audit logging

### 4. Least Privilege
- Only requests necessary Kubernetes permissions
- No cluster-admin required
- Namespace-scoped operations

## Scalability Considerations

### Current Limitations
- Single namespace per run
- Sequential issue processing
- In-memory history storage
- Synchronous LLM calls

### Future Improvements
- Multi-namespace monitoring
- Parallel issue processing
- Persistent history database
- Async LLM calls
- Horizontal scaling via multiple agents

## Error Handling

### Kubernetes API Errors
- Graceful degradation
- Retry with exponential backoff
- Fallback to manual intervention

### LLM Errors
- Timeout handling
- Fallback to heuristic diagnosis
- Error logging and alerting

### Remediation Errors
- Rollback capability (where applicable)
- Error reporting
- Prevention of retry loops

## Testing Strategy

### Unit Tests
- Each component tested in isolation
- Mock Kubernetes API responses
- Mock LLM responses

### Integration Tests
- End-to-end flow testing
- Real cluster (test namespace)
- Dry-run mode validation

### Chaos Testing
- Inject various failure types
- Verify detection accuracy
- Validate remediation effectiveness

## Monitoring and Observability

### Logs
- Structured logging (timestamps, levels, context)
- File-based (`sre_agent.log`)
- Console output for real-time monitoring

### Metrics (Future)
- Issues detected per hour
- Remediation success rate
- Time to detection
- Time to remediation
- LLM response time

### Reports
- JSON report per run
- Historical data in remediation history
- Exportable for dashboards
