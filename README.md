# Kubernetes SRE AI Agent Prototype

An intelligent AI-powered agent that automatically detects, diagnoses, and remediates common Kubernetes failures using LangGraph, DSPy, and OpenRouter. The agent provides human-in-the-loop approval for safety and demonstrates a complete pipeline from problem detection to resolution.

## 📋 Table of Contents

- [What is This Project?](#what-is-this-project)
- [Architecture Overview](#architecture-overview)
- [Design Overview](#design-overview)
- [Technology Stack](#technology-stack)
- [Project Structure](#project-structure)
- [Quick Start](#quick-start)
- [Setup Instructions](#setup-instructions)
- [Usage Examples](#usage-examples)
- [Output Examples](#output-examples)
- [Security](#security)
- [Future Work](#future-work)

## What is This Project?

This project is a **prototype SRE AI agent** designed to automate Kubernetes failure detection and remediation. It demonstrates how AI can assist Site Reliability Engineers by:

1. **Detecting** common Kubernetes failures (OOMKilled pods, broken services)
2. **Diagnosing** root causes using AI reasoning
3. **Proposing** safe remediation fixes
4. **Requiring** human approval before execution (safety-first approach)
5. **Evaluating** fix effectiveness

The agent handles two core scenarios:
- **Scenario A**: OOMKilled Pod - Deployment with pods repeatedly killed due to memory limits
- **Scenario B**: Broken Service - Service with no endpoints due to label mismatch

## Architecture Overview

```
                    ┌─────────────────────┐
                    │   User Interface    │
                    │  ┌─────┐ ┌──────┐  │
                    │  │ CLI │ │ Web  │  │
                    │  └──┬──┘ └──┬───┘  │
                    └─────┼───────┼──────┘
                          │       │
                    ┌─────▼───────▼──────┐
                    │   SRE Agent Core   │
                    │   (LangGraph)      │
                    └─────┬──────────────┘
                          │
        ┌─────────────────┼─────────────────┐
        │                 │                 │
   ┌────▼────┐      ┌─────▼─────┐    ┌─────▼────┐
   │K8s SDK  │      │ OpenRouter │    │  Qdrant  │
   │kubectl  │      │  (LLM)    │    │(Optional) │
   └─────────┘      └───────────┘    └───────────┘
```

### Component Interaction

```
User Request
    │
    ▼
┌─────────────┐
│   CLI/Web   │
└──────┬──────┘
       │
       ▼
┌─────────────────┐
│  LangGraph      │
│  Workflow       │
└──────┬──────────┘
       │
       ├──► Detect ──────► kubectl get pods/deployments
       │
       ├──► Diagnose ─────► DSPy + OpenRouter API
       │
       ├──► Propose ──────► DSPy + OpenRouter API
       │
       ├──► Approve ──────► Human Review (CLI/Web)
       │
       ├──► Execute ──────► kubectl patch/apply
       │
       └──► Evaluate ─────► kubectl get (verify fix)
```

## Design Overview

### Workflow Pipeline

The agent follows a **6-step LangGraph workflow**:

```
┌─────────┐     ┌──────────┐     ┌─────────────┐     ┌──────────────┐
│ Detect  │────▶│ Diagnose │────▶│ Propose Fix │────▶│ Await Approval│
└─────────┘     └──────────┘     └─────────────┘     └──────┬───────┘
                                                             │
                                                             ▼
┌─────────┐     ┌──────────┐     ┌─────────────┐     ┌──────────────┐
│Evaluate │◀────│ Execute  │◀────│   Approved  │◀────│ Human Review │
└─────────┘     └──────────┘     └─────────────┘     └──────────────┘
```

### Key Design Decisions

1. **LangGraph for Workflow**: Provides explicit state management and conditional routing
2. **DSPy for Structured Outputs**: Ensures consistent, typed responses from LLM
3. **Rule-based Fallbacks**: Works even if LLM fails, ensuring reliability
4. **Human-in-the-Loop**: All fixes require explicit approval for safety
5. **kubectl Integration**: Uses standard Kubernetes tools for execution
6. **Caching**: Reduces redundant LLM calls and improves performance

### Safety Features

- **Dry-run validation**: All commands validated before execution
- **Human approval required**: No automatic execution
- **Command timeout**: 30-second limit on all kubectl commands
- **Error handling**: Graceful degradation with meaningful error messages
- **Audit logging**: All actions logged for compliance

## Technology Stack

| Component | Technology | Justification |
|-----------|------------|--------------|
| **AI Framework** | LangGraph + DSPy | LangGraph provides workflow orchestration; DSPy ensures structured LLM outputs with type safety |
| **LLM Provider** | OpenRouter | OpenAI-compatible API, free tier available, no local model setup required |
| **K8s Interaction** | Kubernetes Python SDK + kubectl | Direct cluster access via SDK; kubectl for command execution |
| **Vector DB** | Qdrant | Optional knowledge base for failure pattern matching |
| **Cache** | DiskCache | Persistent caching for diagnosis results |
| **CLI** | Typer | Modern, type-safe CLI framework |
| **Web UI** | Gradio | Rapid prototyping for human-in-the-loop |
| **API** | FastAPI | Async, type-safe REST API |

### Why LangGraph + DSPy?

- **LangGraph**: Explicit state machine makes the workflow transparent and debuggable
- **DSPy**: Structured signatures ensure consistent outputs, reducing hallucinations
- **Chain-of-Thought**: DSPy's CoT provides transparent reasoning for diagnosis steps
- **Fallback Support**: Rule-based fallbacks ensure the agent works even if LLM fails

## Project Structure

```
kubernetes-sre-agent/
├── src/
│   └── sre_agent/              # Main package
│       ├── agent.py            # LangGraph workflow + DSPy integration
│       ├── dspy_modules.py     # DSPy signatures and modules
│       ├── k8s_client.py       # Kubernetes client wrapper
│       ├── cache.py            # DiskCache manager
│       ├── cli.py              # CLI interface (Typer)
│       ├── web.py              # Gradio web UI
│       ├── api.py              # FastAPI REST API
│       └── utils.py            # Logging, config loading
├── config/
│   └── config.yaml             # Configuration file
├── tests/
│   ├── unit/                   # Unit tests
│   ├── integration/            # Integration tests
│   └── scenarios/              # Test scenarios (K8s YAML)
│       ├── scenario_a_oom/     # OOMKilled variants
│       └── scenario_b_service/ # Broken service
├── scripts/
│   ├── setup_kind.sh          # Create local K8s cluster
│   ├── deploy_scenarios.sh    # Deploy test scenarios
│   ├── test_scenario_a.sh     # Test Scenario A
│   ├── test_scenario_b.sh     # Test Scenario B
│   ├── run_agent.sh           # Run agent CLI
│   └── setup_env.sh           # Environment setup
├── docker-compose.yaml        # Qdrant + RabbitMQ
├── pyproject.toml             # Dependencies
├── requirements.txt           # Pip dependencies
├── README.md                  # This file
└── SECURITY.md                # Security guidelines
```

## Quick Start

### Prerequisites

- **Python 3.11+**
- **Docker Desktop** (for Qdrant/RabbitMQ)
- **kubectl** configured with cluster access
- **kind** (optional, for local cluster: `brew install kind`)
- **OpenRouter API Key** (free tier available at [openrouter.ai](https://openrouter.ai))

### Step 1: Clone and Setup

```bash
# Clone repository
git clone <repository-url>
cd kubernetes-sre-agent

# Set up environment (sets API key and PYTHONPATH)
source scripts/setup_env.sh

# Start infrastructure (Qdrant + RabbitMQ)
docker-compose up -d

# Install dependencies
pip install -r requirements.txt
export PYTHONPATH="${PYTHONPATH}:$(pwd)/src"
```

### Step 2: Setup Kubernetes Cluster

**Option A: Local cluster with kind (Recommended for testing)**
```bash
# Create local Kubernetes cluster
./scripts/setup_kind.sh

# Deploy test scenarios
./scripts/deploy_scenarios.sh
```

**Option B: Use existing cluster**
```bash
# Verify kubectl access
kubectl cluster-info

# Deploy test scenarios
./scripts/deploy_scenarios.sh
```

### Step 3: Run Agent

**Simple kubectl-based diagnosis:**
```bash
./scripts/simple_diagnose.sh default Deployment oom-app-v1
./scripts/simple_diagnose.sh default Service broken-service
```

**Full AI agent diagnosis:**
```bash
# Test Scenario A: OOMKilled Pod
./scripts/test_scenario_a.sh

# Test Scenario B: Broken Service
./scripts/test_scenario_b.sh

# Or use directly
./scripts/run_agent.sh diagnose --namespace default --deployment oom-app-v1
./scripts/run_agent.sh diagnose --namespace default --service broken-service
```

**Execute a fix (after approval):**
```bash
./scripts/run_agent.sh execute --namespace default --deployment oom-app-v1
```

## Setup Instructions

### Detailed Setup

1. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   # Or: pip install -e .
   ```

2. **Configure**
   - Edit `config/config.yaml` (optional - defaults work)
   - Set `OPENROUTER_API_KEY` environment variable

3. **Start Infrastructure**
   ```bash
   docker-compose up -d
   ```

4. **Deploy Test Scenarios**
   ```bash
   ./scripts/deploy_scenarios.sh
   ```

5. **Verify Setup**
   ```bash
   kubectl get pods -n default
   kubectl get svc broken-service -n default
   ```

See [QUICK_TEST.md](QUICK_TEST.md) for detailed testing guide.

## Usage Examples

### Simple kubectl-Based Diagnosis

The simplest way to diagnose issues using kubectl:

```bash
# Diagnose OOMKilled pod
./scripts/simple_diagnose.sh default Deployment oom-app-v1

# Diagnose broken service
./scripts/simple_diagnose.sh default Service broken-service
```

This script shows:
- Current kubectl status
- Detected issues
- Runs AI agent if issues found

### Full AI Agent Usage

```bash
# Diagnose a deployment
./scripts/run_agent.sh diagnose --namespace default --deployment oom-app-v1

# Diagnose a service
./scripts/run_agent.sh diagnose --namespace default --service broken-service

# Execute a fix (after approval)
./scripts/run_agent.sh execute --namespace default --deployment oom-app-v1
```

### Manual kubectl Verification

You can verify everything with kubectl:

```bash
# Check OOMKilled pods
kubectl get pods -n default | grep oom-app
kubectl describe pod <pod-name> -n default | grep -A 5 "Last State"

# Check pod events
kubectl get events -n default --sort-by='.lastTimestamp' | grep oom-app

# Check service endpoints
kubectl get endpoints broken-service -n default

# Check service selector vs pod labels
kubectl get svc broken-service -n default -o jsonpath='{.spec.selector}' | jq .
kubectl get pods -n default -l app=healthy-app -o json | jq '.items[].metadata.labels'
```

## Output Examples

### Scenario A: OOMKilled Pod

**Input:**
```bash
./scripts/run_agent.sh diagnose --namespace default --deployment oom-app-v1
```

**Output:**
```
======================================================================
KUBERNETES RESOURCE STATUS
======================================================================

📊 Deployment: oom-app-v1
NAME         READY   UP-TO-DATE   AVAILABLE   AGE
oom-app-v1   0/1     1            0           5m

📊 Pods:
NAME                      READY   STATUS             RESTARTS   AGE
oom-app-v1-xxx-yyy        0/1     CrashLoopBackOff   3          5m

======================================================================
AI AGENT DIAGNOSIS
======================================================================

🔴 Failure Detected: OOMKilled

📋 Root Cause Analysis:
   Pod is being OOMKilled due to insufficient memory limits.
   Current limits: 64Mi. The container is exceeding these
   limits and being terminated by Kubernetes.

📝 Contributing Factors:
   • Memory limit too low: 64Mi
   • Container memory usage exceeds configured limit
   • Kubernetes OOMKiller is terminating the pod

📊 Confidence: 90%

======================================================================
PROPOSED FIX
======================================================================

🔧 kubectl Command:
   kubectl patch deployment oom-app-v1 -n default --type='json'
   -p='[{"op": "replace", "path":
   "/spec/template/spec/containers/0/resources/limits/memory",
   "value": "512Mi"}]'

💡 To execute manually:
   kubectl patch deployment oom-app-v1 -n default --type='json' -p='[{"op": "replace", "path": "/spec/template/spec/containers/0/resources/limits/memory", "value": "512Mi"}]'

⚠️  Risk Level: MEDIUM

↩️  Rollback Plan:
   kubectl rollout undo deployment/oom-app-v1 -n default

✅ Expected Outcome:
   Pod should have sufficient memory and stop being OOMKilled

======================================================================
EXECUTE FIX
======================================================================

   ./scripts/run_agent.sh execute --namespace default --deployment oom-app-v1
```

### Scenario B: Broken Service

**Input:**
```bash
./scripts/run_agent.sh diagnose --namespace default --service broken-service
```

**Output:**
```
======================================================================
KUBERNETES RESOURCE STATUS
======================================================================

📊 Service: broken-service
NAME             TYPE        CLUSTER-IP      EXTERNAL-IP   PORT(S)   AGE
broken-service   ClusterIP   10.96.170.139   <none>        80/TCP    10m

📊 Endpoints:
NAME             ENDPOINTS   AGE
broken-service   <none>      10m

======================================================================
AI AGENT DIAGNOSIS
======================================================================

🔴 Failure Detected: ServiceMisconfigured

📋 Root Cause Analysis:
   Service has no endpoints due to label mismatch. Service
   selector: {"app":"healthy-app","tier":"frontend"}.
   Available pod labels show tier=backend, causing mismatch.

📝 Contributing Factors:
   • Service selector: {"app":"healthy-app","tier":"frontend"}
   • Available pods: 2 (with tier=backend)
   • Label mismatch prevents service from finding pods

📊 Confidence: 95%

======================================================================
PROPOSED FIX
======================================================================

🔧 kubectl Command:
   kubectl patch service broken-service -n default --type='json'
   -p='[{"op": "replace", "path": "/spec/selector", "value":
   {"app":"healthy-app","tier":"backend"}}]'

⚠️  Risk Level: LOW

✅ Expected Outcome:
   Service should now have endpoints and route traffic to pods
```

## Security

This project follows security best practices. See **[SECURITY.md](SECURITY.md)** for detailed security guidelines.

**Key Security Features:**
- **Access Control**: RBAC for Kubernetes operations
- **Audit Logging**: All actions logged with timestamps
- **Dry-run Validation**: Commands validated before execution
- **Human Approval**: Required for all remediation actions
- **Timeout Protection**: Commands timeout after 30s
- **Error Handling**: Graceful failure without exposing sensitive data
- **API Key Management**: Environment variables, never committed

## Future Work

### Short-term Improvements
- [ ] **More Failure Scenarios**: ImagePullBackOff, CrashLoopBackOff, PodDisruptionBudget violations
- [ ] **Enhanced kubectl Integration**: Better error parsing and status reporting
- [ ] **Qdrant Knowledge Base**: Vector embeddings for similarity search
- [ ] **Prometheus Metrics**: Integration for monitoring agent performance
- [ ] **Better Error Messages**: Include kubectl output in error messages
- [ ] **Multi-cluster Support**: Handle multiple Kubernetes clusters

### Long-term Enhancements
- [ ] **RLHF Integration**: Learn from human feedback to improve diagnosis
- [ ] **CI/CD Integration**: Automated testing and deployment pipelines
- [ ] **Helm Charts**: Production-ready deployment manifests
- [ ] **Grafana Dashboards**: Visual monitoring of agent operations
- [ ] **Kubernetes MCP Server**: Native integration with MCP protocol
- [ ] **Custom Failure Patterns**: User-defined failure detection rules
- [ ] **Multi-tenant Support**: Namespace isolation and RBAC

### Scalability & Cost Efficiency
- [ ] **Horizontal Scaling**: Agent workers scale independently
- [ ] **LLM Cost Optimization**: Batch requests, smarter caching
- [ ] **Large Cluster Support**: Efficient processing for 1000+ pods
- [ ] **Batch Processing**: Diagnose multiple resources in parallel

### Research & Development
- [ ] **Advanced RCA**: Multi-factor root cause analysis
- [ ] **Predictive Failure Detection**: ML models for failure prediction
- [ ] **Auto-remediation**: Low-risk automatic fixes with approval workflow
- [ ] **Knowledge Graph**: Build failure pattern relationships

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## License

See [LICENSE](LICENSE) file.

## Acknowledgments

- Built with [LangGraph](https://github.com/langchain-ai/langgraph)
- Uses [DSPy](https://github.com/stanfordnlp/dspy) for structured LLM outputs
- Kubernetes client via [kubernetes-python](https://github.com/kubernetes-client/python)
