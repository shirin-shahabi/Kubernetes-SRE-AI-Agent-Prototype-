# Development Guide

This guide is for developers who want to understand, modify, or extend the Kubernetes SRE AI Agent.

## Project Structure

```
Kubernetes-SRE-AI-Agent-Prototype-/
├── sre_agent/                  # Main package
│   ├── __init__.py            # Package initialization
│   ├── config.py              # Configuration management
│   ├── kubernetes_client.py   # Kubernetes API wrapper
│   ├── detector.py            # Issue detection logic
│   ├── diagnostician.py       # AI-powered diagnosis
│   ├── remediator.py          # Remediation actions
│   └── agent.py               # Main orchestration
├── examples/                   # Example scripts
│   ├── simple_usage.py        # Basic usage example
│   ├── create_test_scenarios.py  # Generate test manifests
│   └── k8s/                   # Test Kubernetes manifests
├── tests/                      # Unit tests
│   └── test_agent.py          # Basic tests
├── main.py                     # CLI entry point
├── demo.py                     # Standalone demo (no cluster needed)
├── setup.sh                    # Setup script
├── requirements.txt            # Python dependencies
├── .env.example               # Environment template
├── README.md                   # Main documentation
├── QUICKSTART.md              # Quick start guide
├── ARCHITECTURE.md            # Architecture details
└── DEVELOPMENT.md             # This file
```

## Development Setup

### 1. Clone and Setup

```bash
git clone https://github.com/shirin-shahabi/Kubernetes-SRE-AI-Agent-Prototype-.git
cd Kubernetes-SRE-AI-Agent-Prototype-
```

### 2. Create Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Install Development Tools

```bash
pip install pytest pytest-cov black flake8 mypy
```

## Running Tests

### Unit Tests

```bash
# Run all tests
python -m unittest discover tests

# Run specific test file
python -m unittest tests.test_agent

# Run with pytest (if installed)
pytest tests/ -v
```

### Code Coverage

```bash
pytest tests/ --cov=sre_agent --cov-report=html
```

## Code Style

### Formatting with Black

```bash
black sre_agent/ tests/ examples/
```

### Linting with Flake8

```bash
flake8 sre_agent/ tests/ examples/ --max-line-length=100
```

### Type Checking with MyPy

```bash
mypy sre_agent/
```

## Adding New Failure Types

### 1. Add to FailureType Enum

In `sre_agent/detector.py`:

```python
class FailureType(Enum):
    # Existing types...
    NEW_FAILURE = "new_failure"
```

### 2. Implement Detection Logic

In `sre_agent/detector.py`, add detection in appropriate method:

```python
def _detect_pod_issues(self, namespace: str) -> List[Issue]:
    # Existing detection...
    
    # New detection
    if some_condition:
        issues.append(Issue(
            failure_type=FailureType.NEW_FAILURE,
            resource_type="Pod",
            resource_name=pod["name"],
            namespace=namespace,
            details={"key": "value"}
        ))
```

### 3. Add Remediation Strategy

In `sre_agent/remediator.py`:

```python
def __init__(self, k8s_client, dry_run: bool = True):
    # Existing strategies...
    self.remediation_strategies[FailureType.NEW_FAILURE] = self._handle_new_failure

def _handle_new_failure(self, issue: Issue, diagnosis: Dict[str, Any]) -> RemediationPlan:
    return RemediationPlan(
        issue=issue,
        action=RemediationAction.SOME_ACTION,
        parameters={...},
        justification="...",
        risk_level="low"
    )
```

### 4. Write Tests

In `tests/test_agent.py`:

```python
def test_detect_new_failure(self):
    """Test new failure detection"""
    # Setup mock data
    # Run detector
    # Assert expected behavior
```

## Adding New Remediation Actions

### 1. Add to RemediationAction Enum

In `sre_agent/remediator.py`:

```python
class RemediationAction(Enum):
    # Existing actions...
    NEW_ACTION = "new_action"
```

### 2. Implement in Kubernetes Client

In `sre_agent/kubernetes_client.py`:

```python
def perform_new_action(self, params, dry_run: bool = True) -> bool:
    """Perform new remediation action"""
    try:
        if dry_run:
            logger.info(f"DRY RUN: Would perform new action with {params}")
            return True
        
        # Actual implementation
        # ...
        
        logger.info("New action executed successfully")
        return True
    except Exception as e:
        logger.error(f"Failed to execute new action: {e}")
        return False
```

### 3. Add Execution Logic

In `sre_agent/remediator.py`, update `execute_plan`:

```python
def execute_plan(self, plan: RemediationPlan) -> Dict[str, Any]:
    # Existing actions...
    
    elif plan.action == RemediationAction.NEW_ACTION:
        success = self.k8s_client.perform_new_action(
            params=plan.parameters,
            dry_run=self.dry_run
        )
```

## Extending the Diagnostician

### Using Different LLMs

Replace in `sre_agent/diagnostician.py`:

```python
# Instead of ChatOpenAI
from langchain_community.llms import HuggingFaceHub

self.llm = HuggingFaceHub(
    repo_id="google/flan-t5-xxl",
    model_kwargs={"temperature": 0.3}
)
```

### Customizing Prompts

Modify `_create_diagnosis_prompt` in `diagnostician.py`:

```python
def _create_diagnosis_prompt(self, context: str) -> str:
    return f"""
    Custom prompt template...
    {context}
    ...
    """
```

## Configuration Options

### Environment Variables

All configuration can be set via environment variables:

```bash
export OPENAI_API_KEY=sk-...
export KUBECONFIG=/path/to/config
export LOG_LEVEL=DEBUG
export DRY_RUN=false
```

### Programmatic Configuration

```python
from sre_agent.config import AgentConfig

config = AgentConfig(
    openai_api_key="sk-...",
    dry_run=False,
    require_approval=True,
    max_remediation_attempts=5
)
```

## Debugging

### Enable Debug Logging

```bash
python main.py --log-level DEBUG
```

### Inspect Issues

```python
from sre_agent.agent import SREAgent
from sre_agent.config import AgentConfig

config = AgentConfig(dry_run=True)
agent = SREAgent(config)

# Run and inspect
summary = agent.run_once("default")

# Examine issues
for action in summary['actions']:
    print(action['issue'])
    print(action.get('diagnosis'))
    print(action.get('remediation_plan'))
```

### Mock Kubernetes API

For testing without a cluster:

```python
from unittest.mock import Mock

mock_k8s = Mock()
mock_k8s.get_all_pods.return_value = [...]
mock_k8s.get_deployments.return_value = [...]

detector = FailureDetector(mock_k8s)
issues = detector.detect_issues("default")
```

## Performance Optimization

### Reduce LLM Calls

- Cache diagnoses for similar issues
- Batch diagnoses when possible
- Use cheaper models for simple cases

### Optimize Kubernetes API Calls

- Use field selectors to filter results
- Implement caching for static data
- Use watches for real-time updates

## Security Considerations

### API Key Protection

- Never commit API keys
- Use secrets management systems
- Rotate keys regularly

### Kubernetes RBAC

Minimum required permissions:

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: sre-agent
rules:
- apiGroups: [""]
  resources: ["pods", "pods/log", "events"]
  verbs: ["get", "list", "delete"]
- apiGroups: ["apps"]
  resources: ["deployments"]
  verbs: ["get", "list", "patch"]
```

### Safety Checks

Always:
1. Test in dry-run mode first
2. Use approval requirements in production
3. Set appropriate retry limits
4. Monitor remediation actions

## Contributing

### Coding Standards

- Follow PEP 8 style guide
- Use type hints
- Write docstrings for all functions
- Keep functions focused and small

### Pull Request Process

1. Fork the repository
2. Create a feature branch
3. Make changes with tests
4. Run linters and tests
5. Submit PR with description

### Testing Requirements

- All new code must have tests
- Maintain >80% code coverage
- Tests should be fast and independent

## Troubleshooting

### Common Issues

**Import errors**: Make sure you're in the virtual environment and dependencies are installed.

```bash
source venv/bin/activate
pip install -r requirements.txt
```

**Kubernetes connection errors**: Verify kubectl works:

```bash
kubectl cluster-info
kubectl auth can-i get pods
```

**OpenAI API errors**: Check API key and quota:

```python
import openai
openai.api_key = "your-key"
# Test with a simple call
```

## Resources

- [LangChain Documentation](https://python.langchain.com/)
- [Kubernetes Python Client](https://github.com/kubernetes-client/python)
- [OpenAI API Reference](https://platform.openai.com/docs)
- [Pydantic Documentation](https://docs.pydantic.dev/)

## Getting Help

- Check existing issues
- Review documentation files
- Run the demo: `python demo.py`
- Ask in discussions
