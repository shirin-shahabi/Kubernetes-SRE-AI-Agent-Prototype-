# Design Document: Kubernetes SRE AI Agent

## Executive Summary

This document provides a detailed design overview of the Kubernetes SRE AI Agent prototype, explaining architectural decisions, implementation details, and rationale for technology choices.

## Problem Statement

Site Reliability Engineers frequently deal with common Kubernetes failures that follow predictable patterns. Manual diagnosis and remediation is time-consuming and error-prone. This prototype demonstrates an AI-powered agent that can:

1. Automatically detect common Kubernetes issues
2. Perform root cause analysis
3. Propose safe remediation actions
4. Execute fixes with human approval
5. Verify the results

## Design Goals

### Primary Goals
1. **Safety**: Never modify cluster resources without explicit human approval
2. **Reliability**: Accurate diagnosis with minimal false positives
3. **Clarity**: Clear explanation of issues and proposed fixes
4. **Extensibility**: Easy to add new scenarios and diagnostic logic

### Non-Goals
1. Autonomous remediation without human oversight
2. Comprehensive coverage of all possible Kubernetes issues
3. Production-ready monitoring integration (prototype focuses on core workflow)

## Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     User Interface Layer                    │
│  ┌──────────────┐              ┌──────────────┐            │
│  │   CLI Tool   │              │  Web UI      │            │
│  │  (cli.py)    │              │  (Gradio)    │            │
│  └──────────────┘              └──────────────┘            │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                    Orchestration Layer                      │
│  ┌────────────────────────────────────────────────────┐    │
│  │            SREOrchestrator                         │    │
│  │  - Coordinates workflow                            │    │
│  │  - Manages diagnosis and remediation              │    │
│  └────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
           │                │                 │
           ▼                ▼                 ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│  K8s Client  │  │ Diagnostics  │  │  AI Agent    │
│              │  │              │  │  (LangChain) │
│ - API calls  │  │ - RCA logic  │  │ - Analysis   │
│ - Patching   │  │ - Fix gen    │  │ - Reasoning  │
└──────────────┘  └──────────────┘  └──────────────┘
```

### Component Breakdown

#### 1. Kubernetes Client (`src/k8s_client.py`)

**Purpose**: Abstraction layer for Kubernetes API interactions

**Responsibilities**:
- Load kubeconfig or in-cluster configuration
- Retrieve pod, deployment, service, and endpoint information
- Apply patches to cluster resources
- Handle API exceptions gracefully

**Design Decisions**:
- Uses official `kubernetes` Python client for reliability
- Provides typed responses for type safety
- Implements defensive programming with comprehensive error handling
- Extracts structured data from Kubernetes objects for easier analysis

#### 2. Diagnostics Engine (`src/diagnostics.py`)

**Purpose**: Rule-based diagnostic logic for common Kubernetes issues

**Responsibilities**:
- Analyze pod status for OOMKilled conditions
- Detect service endpoint issues
- Identify label mismatches
- Generate remediation patches

**Design Decisions**:
- Pure functions for testability
- Deterministic logic for predictable behavior
- Conservative fix suggestions (3x memory increase)
- Resource requests set to 70% of limits for better scheduling

**Supported Scenarios**:

##### Scenario A: OOMKilled Pod
- **Detection**: Checks `last_state.reason == 'OOMKilled'`
- **RCA**: Identifies memory limit vs. actual usage
- **Fix**: Increases memory limit by 3x
- **Rationale**: 3x provides buffer while avoiding wasteful over-provisioning

##### Scenario B: Broken Service
- **Detection**: Service has no endpoints but pods exist
- **RCA**: Compares service selector labels with pod labels
- **Fix**: Updates service selector to match pod labels
- **Rationale**: Assumes pods are correct and service misconfigured

#### 3. AI Agent (`src/agent.py`)

**Purpose**: LLM-powered analysis and explanation generation

**Responsibilities**:
- Provide detailed explanations of diagnoses
- Generate human-readable recommendations
- Enhance rule-based output with contextual understanding

**Design Decisions**:
- Uses LangChain for LLM integration
- ChatGPT-3.5-turbo for cost-effectiveness
- Low temperature (0.2) for consistent, factual responses
- Graceful degradation when API key not available
- Structured prompts for reliable output

#### 4. Orchestrator (`src/orchestrator.py`)

**Purpose**: Coordinate the complete workflow

**Responsibilities**:
- Execute diagnosis → analysis → remediation workflow
- Handle scenario-specific logic
- Manage error conditions
- Apply fixes to cluster

**Design Decisions**:
- Single entry point for each scenario
- Consistent response format
- Separation of diagnosis and execution phases
- Explicit success/failure states

#### 5. User Interfaces

##### CLI (`cli.py`)
**Features**:
- Command-line argument parsing
- Interactive approval prompts
- Colored output for better UX
- Step-by-step progress indicators

**Advantages**:
- Scriptable and automatable
- No GUI dependencies
- Suitable for CI/CD integration

##### Web UI (`web_ui.py`)
**Features**:
- Gradio-based interface
- Visual scenario selection
- Thread-safe state management
- Clear approval workflow

**Advantages**:
- User-friendly
- No local setup required
- Better for demos and exploration

## Technology Choices

### LangChain for AI Framework

**Why LangChain?**

1. **Maturity**: Battle-tested framework with extensive documentation
2. **Flexibility**: Easy to integrate different LLMs
3. **Prompt Management**: Built-in templates and chains
4. **Community**: Large ecosystem and active development

**Alternatives Considered**:
- **CrewAI**: Better for multi-agent systems; overkill for our use case
- **LlamaIndex**: Optimized for RAG; we need reasoning not retrieval
- **Raw OpenAI API**: Less abstraction, more code to maintain

### Kubernetes Python Client

**Why official Python client?**

1. **Official Support**: Maintained by Kubernetes community
2. **Completeness**: Full API coverage
3. **Type Safety**: Strong typing support
4. **Documentation**: Extensive examples and guides

**Alternatives Considered**:
- **kubectl CLI**: Less programmatic, harder to parse output
- **Custom REST API calls**: More error-prone, requires manual serialization
- **Kubernetes MCP**: Newer, less mature tooling

### Gradio for Web UI

**Why Gradio?**

1. **Simplicity**: Minimal code for functional UI
2. **Speed**: Rapid prototyping
3. **Built-in Features**: State management, themes, components
4. **Python-Native**: No separate frontend stack needed

**Alternatives Considered**:
- **Flask/FastAPI**: More code, requires frontend development
- **Streamlit**: Similar benefits, but Gradio has better component library
- **React/Vue**: Overkill for prototype, requires separate stack

## Safety Mechanisms

### 1. Human-in-the-Loop Approval
- All remediations require explicit approval
- Clear presentation of proposed changes
- Reject option always available

### 2. Read-Only Diagnosis
- Diagnosis phase never modifies cluster
- Safe to run repeatedly
- No side effects

### 3. Explicit Patches
- Shows exact changes before applying
- Uses Kubernetes strategic merge patches
- Version-controlled changes

### 4. Error Handling
- Comprehensive exception catching
- Clear error messages
- Graceful degradation

### 5. Logging
- All operations logged
- Audit trail for troubleshooting
- Structured logging format

## Testing Strategy

### Component Tests (`test_components.py`)
- Unit tests for diagnostic logic
- Mock data for deterministic testing
- No cluster required
- Fast feedback loop

### Integration Testing
- Manual testing with real cluster
- Test scenarios in `k8s-manifests/`
- Verification commands provided
- End-to-end workflow validation

### Future Testing Enhancements
- Automated integration tests with kind/minikube
- Property-based testing for edge cases
- Load testing for performance
- Chaos testing for reliability

## Extensibility

### Adding New Scenarios

To add a new scenario:

1. **Add diagnostic logic** in `src/diagnostics.py`:
```python
@staticmethod
def diagnose_new_scenario(resource_info: Dict) -> Dict:
    # Detection logic
    # RCA logic
    # Fix generation
    return diagnosis
```

2. **Add orchestrator method** in `src/orchestrator.py`:
```python
def diagnose_new_scenario(self, namespace: str, resource: str) -> Dict:
    # Gather info
    # Run diagnostics
    # Get AI analysis
    return result
```

3. **Add UI handlers** in `cli.py` and `web_ui.py`

4. **Create test manifests** in `k8s-manifests/`

### Configuration

All configurable values should be:
- Environment variables (for secrets)
- Function parameters (for runtime config)
- Constants at module level (for defaults)

## Performance Considerations

### Current State
- Synchronous operations
- Single-threaded execution
- LLM calls add latency (~1-3 seconds)

### Future Optimizations
- Async API calls for parallel data gathering
- Caching of cluster information
- Background diagnosis with notifications
- Batch processing for multiple issues

## Security Considerations

### Current Mitigations
1. **No secrets in code**: Uses environment variables
2. **RBAC-aware**: Respects Kubernetes permissions
3. **Input validation**: Validates all user inputs
4. **Safe defaults**: Conservative patch generation
5. **CodeQL verified**: No security vulnerabilities detected

### Future Enhancements
1. **Audit logging**: Comprehensive change tracking
2. **Rate limiting**: Prevent API abuse
3. **Authentication**: Multi-user support
4. **Authorization**: Role-based access control
5. **Encryption**: Secure API key storage

## Limitations

### Known Limitations
1. **Two scenarios only**: Prototype scope limited to OOMKilled and broken services
2. **No monitoring integration**: Manual trigger required
3. **Single namespace**: No multi-cluster support
4. **No rollback**: Manual revert if needed
5. **LLM dependency**: Enhanced analysis requires API key

### Future Work
1. More scenarios (ImagePullBackOff, CrashLoopBackOff, etc.)
2. Monitoring system integration (Prometheus, Datadog)
3. Multi-cluster support
4. Automated rollback mechanisms
5. Historical analysis and pattern detection
6. GitOps integration
7. Slack/Teams notifications
8. Custom remediation strategies

## Conclusion

This prototype demonstrates a viable approach to AI-powered SRE automation for Kubernetes. The architecture is modular, safe, and extensible. The choice of LangChain, Kubernetes Python client, and Gradio provides a solid foundation for future enhancements while keeping the codebase maintainable and understandable.

The human-in-the-loop design ensures safety while the AI analysis provides valuable insights that can reduce MTTR (Mean Time To Resolution) for common issues.
