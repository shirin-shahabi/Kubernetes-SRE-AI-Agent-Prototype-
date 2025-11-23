# Kubernetes SRE AI Agent Prototype

An intelligent SRE (Site Reliability Engineering) AI agent that automatically detects, diagnoses, and remediates common Kubernetes failures using LangChain and the Kubernetes Python client.

## Overview

This prototype demonstrates a complete pipeline from problem detection to resolution, emphasizing:
- **Safety**: Dry-run mode, approval requirements, and risk assessment
- **Reasoning**: LLM-powered diagnosis with detailed explanations
- **Modern Tools**: LangChain for AI orchestration, Kubernetes Python client for cluster interaction

## Features

### Detection
The agent monitors Kubernetes clusters and detects:
- Pod crashes and CrashLoopBackOff
- ImagePullBackOff and image pull errors
- OOMKilled containers
- Pending pods (scheduling issues)
- High pod restart counts
- Deployment unavailability

### Diagnosis
Uses GPT-3.5-turbo via LangChain to:
- Analyze detected issues with context (logs, events)
- Determine root causes
- Provide detailed explanations
- Suggest specific remediation steps
- Assign confidence levels

### Remediation
Safely executes remediation actions:
- Pod deletion (for crash loops)
- Deployment restarts
- Deployment scaling
- Manual intervention recommendations for complex issues

### Safety Features
- **Dry-run mode**: Test without making actual changes
- **Approval requirements**: Control automatic vs. manual remediation
- **Risk assessment**: Each remediation has a risk level
- **Retry limits**: Prevents remediation loops
- **Comprehensive logging**: Full audit trail of actions

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    SRE AI Agent                         │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ┌──────────────┐      ┌───────────────┐              │
│  │   Detector   │─────▶│ Diagnostician │              │
│  └──────────────┘      └───────────────┘              │
│         │                      │                        │
│         │                      ▼                        │
│         │              ┌───────────────┐               │
│         └─────────────▶│  Remediator   │               │
│                        └───────────────┘               │
│                                                         │
├─────────────────────────────────────────────────────────┤
│          Kubernetes Client     │    LangChain/OpenAI   │
└────────────────────────────────┴───────────────────────┘
                 │                          │
                 ▼                          ▼
         Kubernetes Cluster            OpenAI API
```

## Installation

### Prerequisites
- Python 3.8+
- Access to a Kubernetes cluster
- OpenAI API key
- kubectl configured (optional but recommended)

### Setup

1. Clone the repository:
```bash
git clone https://github.com/shirin-shahabi/Kubernetes-SRE-AI-Agent-Prototype-.git
cd Kubernetes-SRE-AI-Agent-Prototype-
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Configure environment:
```bash
cp .env.example .env
# Edit .env and add your OpenAI API key
```

## Usage

### Command Line Interface

Basic usage:
```bash
# Single check with dry-run (safe - no changes)
python main.py --namespace default --mode once --dry-run

# Single check with actual remediation
python main.py --namespace default --mode once

# Continuous monitoring
python main.py --namespace default --mode continuous --interval 60

# Disable approval requirement (use with caution!)
python main.py --namespace default --mode once --no-approval
```

### Command Line Options

```
--namespace NAMESPACE     Kubernetes namespace to monitor (default: default)
--mode {once,continuous}  Run mode (default: once)
--interval SECONDS        Check interval for continuous mode (default: 60)
--dry-run                 Run without making actual changes
--no-approval            Skip approval for remediations
--log-level LEVEL        Logging level: DEBUG, INFO, WARNING, ERROR
--kubeconfig PATH        Path to kubeconfig file
```

### Programmatic Usage

```python
from sre_agent.config import AgentConfig
from sre_agent.agent import SREAgent

# Create configuration
config = AgentConfig(
    dry_run=True,
    require_approval=True
)

# Initialize agent
agent = SREAgent(config)

# Run single check
summary = agent.run_once(namespace="default")

# Display results
print(f"Issues detected: {summary['issues_detected']}")
print(f"Remediations successful: {summary['remediations_successful']}")
```

See `examples/simple_usage.py` for a complete example.

## Testing

### Create Test Scenarios

Generate problematic Kubernetes resources for testing:

```bash
python examples/create_test_scenarios.py
```

This creates example manifests in `examples/k8s/` that simulate common failures.

### Apply Test Scenarios

```bash
# Apply all test scenarios
kubectl apply -f examples/k8s/

# Wait a moment for issues to appear
sleep 10

# Run the agent
python main.py --namespace default --mode once --dry-run
```

### Cleanup

```bash
kubectl delete -f examples/k8s/
```

## Configuration

### Environment Variables

Create a `.env` file with:

```env
# Required
OPENAI_API_KEY=your-api-key-here

# Optional
KUBECONFIG=/path/to/kubeconfig
LOG_LEVEL=INFO
DRY_RUN=true
```

### Agent Configuration

Modify `sre_agent/config.py` or set via environment:

- `openai_api_key`: OpenAI API key for LLM
- `kubeconfig_path`: Path to kubeconfig file
- `dry_run`: Whether to run in dry-run mode (default: true)
- `log_level`: Logging level (default: INFO)
- `check_interval_seconds`: Interval between checks (default: 60)
- `max_remediation_attempts`: Max remediation attempts per issue (default: 3)
- `require_approval`: Require approval before remediation (default: true)

## Output

### Console Output

The agent provides detailed console output:
```
Namespace: default
Issues Detected: 3
Issues Diagnosed: 3
Remediations Attempted: 2
Remediations Successful: 2

Detailed Results:

1. Pod/crashloop-test
   Type: pod_crash_loop
   Severity: medium
   Root Cause: Container failing to start due to exit code 1
   Confidence: high
   Planned Action: delete_pod
   Risk Level: low
   Result: ✓ SUCCESS - Action executed successfully
```

### JSON Report

Detailed results are saved to `sre_agent_report.json`:
```json
{
  "timestamp": 1234567890,
  "namespace": "default",
  "issues_detected": 3,
  "issues_diagnosed": 3,
  "remediations_attempted": 2,
  "remediations_successful": 2,
  "actions": [...]
}
```

### Logs

Comprehensive logs are written to `sre_agent.log`.

## Supported Failure Types

| Failure Type | Detection | Diagnosis | Remediation |
|-------------|-----------|-----------|-------------|
| CrashLoopBackOff | ✓ | LLM-powered | Delete pod |
| ImagePullBackOff | ✓ | LLM-powered | Manual intervention |
| OOMKilled | ✓ | LLM-powered | Manual intervention |
| Pending Pods | ✓ | LLM-powered | Manual intervention |
| High Restart Count | ✓ | LLM-powered | Delete pod |
| Deployment Unavailable | ✓ | LLM-powered | Restart deployment |

## Safety Considerations

1. **Always start with dry-run mode** to understand what the agent would do
2. **Review remediation plans** before enabling automatic remediation
3. **Use approval requirements** for production environments
4. **Monitor remediation history** to detect issues
5. **Set appropriate retry limits** to prevent loops
6. **Test in non-production** environments first

## Limitations

- Currently focuses on common failure patterns
- Requires OpenAI API access (costs apply)
- Limited to namespace-scoped resources
- Does not handle cluster-wide issues
- Manual intervention required for complex issues

## Future Enhancements

- [ ] Support for more failure types
- [ ] Integration with alerting systems (PagerDuty, Slack)
- [ ] Custom remediation playbooks
- [ ] Multi-cluster support
- [ ] Web UI for monitoring and control
- [ ] Metrics and dashboards
- [ ] Integration with GitOps workflows
- [ ] Support for local/open-source LLMs

## Contributing

Contributions are welcome! Please feel free to submit issues or pull requests.

## License

MIT License - see LICENSE file for details.

## Acknowledgments

- Built with [LangChain](https://github.com/langchain-ai/langchain)
- Uses [Kubernetes Python Client](https://github.com/kubernetes-client/python)
- Powered by [OpenAI GPT](https://openai.com/)
