# K8s SRE Agent

AI-powered Kubernetes SRE Agent for detecting, diagnosing, and remediating cluster failures.

Built with LangGraph, DSPy, and Qdrant. Based on [KubeIntellect](https://arxiv.org/pdf/2509.02449) and [OpenDerisk](https://arxiv.org/pdf/2510.13561).

## Features

- **Failure Detection**: Identifies OOMKilled pods and misconfigured services
- **Root Cause Analysis**: Uses DSPy Chain-of-Thought for structured diagnosis
- **Action Planning**: Generates remediation steps ranked by probability
- **Human-in-the-Loop**: Approval gate before any cluster modifications
- **Knowledge Base**: Qdrant vector store for learning from past resolutions

## Architecture

```
User -> CLI/API/UI -> SREAgent -> LangGraph Workflow
                                      |
                    [Detect] -> [Diagnose] -> [Plan] -> [Approve] -> [Execute] -> [Evaluate]
                        |            |
                    K8sClient    DSPy + Qdrant
```

## Quick Start

### Prerequisites

- Python 3.11+
- Kubernetes cluster (kind/minikube/etc.)
- OpenRouter API key
- Qdrant (optional, for knowledge base)

### Installation

```bash
cd k8s-sre-agent
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

### Configuration

```bash
export OPENROUTER_API_KEY="your-key"
```

### Usage

**CLI:**
```bash
# Diagnose a deployment
k8s-sre-agent diagnose -t Deployment -r my-app -n default

# Auto-approve mode
k8s-sre-agent diagnose -t Deployment -r my-app --auto-approve
```

**Web UI:**
```bash
k8s-sre-agent ui
# Open http://localhost:7860
# Navigate to "Approve & Execute" tab to see human feedback processing
```

**REST API:**
```bash
k8s-sre-agent serve
# POST http://localhost:8000/diagnose
```

## Test Scenarios

### Scenario A: OOMKilled Pod

```bash
kubectl apply -f tests/scenarios/oom_killed/memory_limit_low.yaml
k8s-sre-agent diagnose -t Deployment -r oom-test-app
```

### Scenario B: Broken Service

```bash
kubectl apply -f tests/scenarios/broken_service/label_mismatch.yaml
k8s-sre-agent diagnose -t Service -r broken-svc-app
```

## Human-in-the-Loop

The agent **never executes changes without approval**:

1. **Diagnose** - Agent runs automatically, detects issues
2. **Plan** - Agent proposes fix with risk assessment
3. **Approve** - **Human reviews and provides feedback** (approve/reject/modify)
4. **Execute** - Only after approval, agent executes fix
5. **Learn** - Successful fixes stored in knowledge base

**Web UI Feedback Flow:**
- Go to "Diagnose" tab → Run diagnosis → Get workflow ID
- Go to "Approve & Execute" tab → Paste workflow ID → Add feedback → Approve
- See feedback history table showing all human decisions

## Design Choices

| Component | Choice | Reason |
|-----------|--------|--------|
| Orchestration | LangGraph | Structured workflow with conditional edges |
| Reasoning | DSPy | Typed prompts with Chain-of-Thought |
| LLM | OpenRouter | Access to GPT-4o and other models |
| Vector DB | Qdrant | Fast similarity search for patterns |
| UI | Gradio | Rapid prototyping with built-in components |
| K8s Client | kubectl + Python SDK | kubectl for writes (clean), SDK for reads |

## Project Structure

```
k8s-sre-agent/
├── src/k8s_sre_agent/
│   ├── core/           # LangGraph agent + state
│   ├── k8s/            # Kubernetes client (kubectl + SDK)
│   ├── knowledge/      # Qdrant vector store
│   ├── api/            # FastAPI endpoints
│   ├── ui/             # Gradio interface with feedback
│   └── utils/          # Config, logging, cache
├── tests/
│   ├── scenarios/      # K8s test manifests
│   └── unit/           # Unit tests
├── scripts/
│   └── seed_patterns.py # Seed knowledge base
└── config/             # Configuration files
```

## Security

See [SECURITY.md](SECURITY.md) for details.

- Human approval required for all changes
- Dry-run validation before execution
- Dangerous commands blocked (`delete`, `drain`, `cordon`)
- Minimal RBAC permissions recommended

## Future Work

Based on analysis of related projects and requirements:

- [ ] **MCP Integration** - Model Context Protocol for standardized tool integration ([k8s-observability-mcp](https://github.com/martinimarcello00/k8s-observability-mcp))
- [ ] **Prometheus/Metrics Integration** - Use metrics for anomaly detection ([k8sgpt](https://github.com/k8sgpt-ai/k8sgpt))
- [ ] **Slack/Teams Notifications** - Alert on-call when approval needed ([srenity](https://github.com/DevJadhav/srenity))
- [ ] **Multi-Cluster Support** - Manage multiple clusters from single agent
- [ ] **GitOps Integration** - Sync fixes to Git repositories
- [ ] **CI/CD Pipeline** - Automated testing and deployment workflows
- [ ] **More Failure Types** - CrashLoopBackOff, ImagePullBackOff, PVC issues, Network policies
- [ ] **Semantic Search Enhancement** - Domain-specific K8s embeddings for better pattern matching
- [ ] **Incident Management** - Track and correlate incidents over time ([srenity](https://github.com/DevJadhav/srenity))
- [ ] **Audit Dashboard** - Visualize all agent actions and decisions
- [ ] **Redis-Specific Agents** - Specialized agents for Redis failures ([redis-sre-agent](https://github.com/redis-applied-ai/redis-sre-agent))
- [ ] **Deployment Patterns** - Production deployment guides ([sre-agent-deployment](https://github.com/fuzzylabs/sre-agent-deployment))

## References

### Research Papers

- [KubeIntellect: LLM-Enhanced Kubernetes Troubleshooting](https://arxiv.org/pdf/2509.02449) - Foundation for K8s failure diagnosis using LLMs
- [OpenDerisk: An Industrial Framework for AI-Driven SRE](https://arxiv.org/pdf/2510.13561) - Multi-agent SRE architecture with MCP protocol

### Related Projects

- [k8sgpt-ai/k8sgpt](https://github.com/k8sgpt-ai/k8sgpt) - K8s diagnostics with AI analyzers and metrics integration
- [fuzzylabs/sre-agent-deployment](https://github.com/fuzzylabs/sre-agent-deployment) - SRE agent deployment patterns and best practices
- [redis-applied-ai/redis-sre-agent](https://github.com/redis-applied-ai/redis-sre-agent) - Redis-specific SRE automation
- [k8s-observability-mcp](https://github.com/martinimarcello00/k8s-observability-mcp) - K8s observability with Model Context Protocol
- [DevJadhav/srenity](https://github.com/DevJadhav/srenity) - SRE automation with incident management and notifications

## License

MIT
