# Contributing to Kubernetes SRE AI Agent

Thank you for your interest in contributing to this project! This guide will help you get started.

## Development Setup

1. **Fork and clone the repository**:
```bash
git clone https://github.com/YOUR_USERNAME/Kubernetes-SRE-AI-Agent-Prototype-.git
cd Kubernetes-SRE-AI-Agent-Prototype-
```

2. **Set up development environment**:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

3. **Run tests**:
```bash
python test_components.py
```

## Project Structure

```
.
├── src/                    # Core implementation
│   ├── k8s_client.py      # Kubernetes API wrapper
│   ├── diagnostics.py     # Diagnostic logic
│   ├── agent.py           # LangChain AI agent
│   └── orchestrator.py    # Workflow coordinator
├── cli.py                  # CLI interface
├── web_ui.py              # Gradio web UI
├── test_components.py     # Component tests
├── k8s-manifests/         # Test scenarios
├── README.md              # Main documentation
├── QUICKSTART.md          # Quick start guide
├── DESIGN.md              # Design document
└── CONTRIBUTING.md        # This file
```

## Adding New Scenarios

To add support for a new Kubernetes failure scenario:

### 1. Create Test Manifests

Add YAML files in `k8s-manifests/`:
- `scenario-X-problem.yaml` - Manifest that creates the problem
- `scenario-X-problem-fixed.yaml` - Fixed version for reference

### 2. Add Diagnostic Logic

In `src/diagnostics.py`:
```python
@staticmethod
def diagnose_your_scenario(resource_info: Dict[str, Any], 
                           related_info: Dict[str, Any]) -> Dict[str, Any]:
    """
    Diagnose your specific scenario.
    
    Returns:
        Dictionary with diagnosis results.
    """
    diagnosis = {
        'issue_detected': False,
        'issue_type': 'YourScenarioType',
        'root_cause': '',
        'details': {},
        'suggested_fix': {}
    }
    
    # Your detection logic here
    if condition_met:
        diagnosis['issue_detected'] = True
        diagnosis['root_cause'] = "Explanation of what went wrong"
        diagnosis['suggested_fix'] = {
            'action': 'your_action_type',
            'patch': your_patch_object
        }
    
    return diagnosis
```

### 3. Add Orchestrator Method

In `src/orchestrator.py`:
```python
def diagnose_your_scenario(self, namespace: str, resource_name: str) -> Dict[str, Any]:
    """Diagnose your scenario."""
    logger.info(f"Diagnosing scenario for {resource_name}")
    
    # Gather necessary information
    resource_info = self.k8s_client.get_resource(namespace, resource_name)
    
    # Run diagnostics
    diagnosis = self.diagnostics.diagnose_your_scenario(resource_info)
    
    if not diagnosis['issue_detected']:
        return {'success': False, 'error': 'Issue not detected'}
    
    # Get AI analysis
    ai_analysis = self.agent.analyze_diagnosis(diagnosis)
    
    return {
        'success': True,
        'scenario': 'Your Scenario Name',
        'resource': resource_name,
        'namespace': namespace,
        'diagnosis': diagnosis,
        'ai_analysis': ai_analysis,
        'remediation_ready': True
    }
```

### 4. Update User Interfaces

Add handlers in both `cli.py` and `web_ui.py` to support the new scenario.

### 5. Add Tests

Add test cases in `test_components.py`:
```python
def test_your_scenario():
    """Test your scenario diagnosis logic."""
    # Mock data
    resource_info = {...}
    
    # Run diagnosis
    diagnostics = Diagnostics()
    result = diagnostics.diagnose_your_scenario(resource_info)
    
    # Validate
    assert result['issue_detected'], "Issue should be detected"
    # More assertions...
    
    print("✅ Your scenario test passed!")
```

### 6. Update Documentation

- Add scenario description to README.md
- Update QUICKSTART.md with usage examples
- Add design notes to DESIGN.md if needed

## Code Style Guidelines

### Python Style
- Follow PEP 8 conventions
- Use type hints for function signatures
- Write docstrings for all public functions
- Maximum line length: 100 characters

### Naming Conventions
- Classes: `PascalCase`
- Functions/methods: `snake_case`
- Constants: `UPPER_SNAKE_CASE`
- Private methods: `_leading_underscore`

### Error Handling
- Use try-except blocks for external calls
- Log errors with appropriate severity
- Return structured error responses
- Never silently fail

### Documentation
- Document all public APIs
- Include examples in docstrings
- Update README for user-facing changes
- Add comments for complex logic only

## Testing Guidelines

### Component Tests
- Test individual functions in isolation
- Use mock data, not real clusters
- Cover happy path and edge cases
- Keep tests fast and deterministic

### Integration Tests
- Test against real/local Kubernetes cluster
- Use kind or minikube for local testing
- Document setup requirements
- Clean up resources after tests

### Manual Testing
- Test both CLI and Web UI
- Verify all scenarios work end-to-end
- Check error messages are clear
- Validate documentation accuracy

## Submitting Changes

### Before Submitting
1. Run all tests: `python test_components.py`
2. Test manually with both interfaces
3. Update documentation
4. Check code style
5. Verify no security issues

### Pull Request Process
1. Create a feature branch from main
2. Make your changes with clear commits
3. Update CHANGELOG.md (if it exists)
4. Submit PR with description of changes
5. Respond to review comments
6. Ensure CI passes

### PR Description Template
```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Documentation update
- [ ] Performance improvement

## Testing
- [ ] Component tests pass
- [ ] Manual testing completed
- [ ] Documentation updated

## Checklist
- [ ] Code follows style guidelines
- [ ] Self-review completed
- [ ] Comments added for complex logic
- [ ] Documentation updated
- [ ] No new warnings
```

## Questions or Issues?

- **Bug Reports**: Open an issue with reproduction steps
- **Feature Requests**: Open an issue with use case description
- **Questions**: Start a discussion in GitHub Discussions
- **Security Issues**: Email maintainers directly (do not open public issue)

## Code of Conduct

- Be respectful and inclusive
- Provide constructive feedback
- Focus on the code, not the person
- Help newcomers get started

## Recognition

All contributors will be recognized in the project README. Thank you for helping make this project better!
