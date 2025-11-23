# Kubernetes SRE AI Agent Prototype

An intelligent Site Reliability Engineering (SRE) agent that automatically detects, diagnoses, and remediates common Kubernetes failures using AI-powered analysis.

> **📖 New to this project?** Check out the [Quick Start Guide](QUICKSTART.md) to get running in 10 minutes!

## 🎯 Overview

This prototype demonstrates a complete pipeline from problem detection to resolution, with human-in-the-loop approval for safety. The agent handles two critical scenarios:

- **Scenario A: OOMKilled Pod** - Detects and fixes pods killed due to memory limits
- **Scenario B: Broken Service** - Identifies and resolves service endpoint issues due to label mismatches

## 🏗️ Architecture

### Design Principles

1. **Safety First**: Human-in-the-loop approval required before any cluster modifications
2. **AI-Powered Reasoning**: Uses LangChain with OpenAI for intelligent analysis
3. **Modular Design**: Separate components for diagnosis, reasoning, and remediation
4. **Clear Pipeline**: Diagnose → Analyze → Propose → Approve → Execute → Evaluate

### Component Architecture

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
       │
       ▼
┌─────────────────────────────────────────────────────────────┐
│                  Kubernetes Cluster                         │
└─────────────────────────────────────────────────────────────┘
```

### Technology Stack Justification

#### AI Agent Framework: LangChain

**Why LangChain?**

1. **Mature Ecosystem**: Well-established framework with extensive documentation
2. **LLM Integration**: Seamless integration with OpenAI and other LLM providers
3. **Flexibility**: Easy to extend with custom tools and chains
4. **Prompt Management**: Built-in prompt templates for structured reasoning
5. **Community Support**: Large community and regular updates

**Alternatives Considered**:
- **CrewAI**: More suited for multi-agent collaboration; overkill for this use case
- **LlamaIndex**: Better for RAG applications; our use case is more about reasoning than retrieval

#### Kubernetes Interaction: Official Python Client

**Why kubernetes Python client?**

1. **Official Support**: Maintained by Kubernetes community
2. **Type Safety**: Strong typing support with Python type hints
3. **Comprehensive**: Full API coverage
4. **Well-Documented**: Extensive documentation and examples

#### Human-in-the-Loop: CLI + Gradio Web UI

**Why both interfaces?**

1. **CLI**: Simple, scriptable, no dependencies for basic usage
2. **Gradio**: User-friendly web interface, visual feedback, easier for demos
3. **Flexibility**: Users can choose based on their preference

## 🚀 Setup Instructions

### Prerequisites

- Python 3.8 or higher
- Access to a Kubernetes cluster (local or remote)
- kubectl configured with valid kubeconfig
- OpenAI API key (optional, for enhanced AI analysis)

### Installation

1. **Clone the repository**:
```bash
git clone https://github.com/shirin-shahabi/Kubernetes-SRE-AI-Agent-Prototype-.git
cd Kubernetes-SRE-AI-Agent-Prototype-
```

2. **Create a virtual environment**:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**:
```bash
pip install -r requirements.txt
```

4. **Configure environment variables**:
```bash
cp .env.example .env
# Edit .env and add your OpenAI API key (optional)
```

5. **Verify Kubernetes access**:
```bash
kubectl cluster-info
kubectl get nodes
```

### Deploy Test Scenarios

Deploy the test scenarios to your Kubernetes cluster:

**Scenario A: OOMKilled Pod**
```bash
kubectl apply -f k8s-manifests/scenario-a-oom.yaml
```

**Scenario B: Broken Service**
```bash
kubectl apply -f k8s-manifests/scenario-b-broken-service.yaml
```

Wait a few moments for the OOMKilled pod to start crashing:
```bash
kubectl get pods -w  # Watch for OOMKilled status
```

## 📖 Usage

### Option 1: CLI Interface (Recommended for automation)

**Diagnose and fix OOMKilled pod**:
```bash
python cli.py --scenario oomkilled --namespace default --deployment oom-app
```

**Diagnose and fix broken service**:
```bash
python cli.py --scenario broken-service --namespace default --service broken-service
```

**With OpenAI API key**:
```bash
python cli.py --scenario oomkilled --namespace default --deployment oom-app --api-key sk-...
```

### Option 2: Web UI Interface (Recommended for interactive use)

1. **Start the web UI**:
```bash
python web_ui.py
```

2. **Open your browser**:
```
http://localhost:7860
```

3. **Use the interface**:
   - Select a scenario (OOMKilled Pod or Broken Service)
   - Enter namespace and resource name
   - Click "Run Diagnosis"
   - Review the AI analysis
   - Approve or reject the proposed fix
   - Verify the results

## 🔍 How It Works

### Workflow Steps

1. **Diagnose & RCA (Root Cause Analysis)**
   - Connects to Kubernetes cluster
   - Retrieves resource status and metadata
   - Analyzes container states, labels, and configurations
   - Identifies root cause using rule-based logic

2. **AI-Powered Analysis**
   - Sends diagnosis to LangChain agent
   - LLM provides detailed explanation and reasoning
   - Generates human-readable analysis

3. **Propose Fix**
   - Generates specific remediation actions
   - Creates Kubernetes patch objects
   - Presents changes for review

4. **Human-in-the-Loop Approval**
   - Displays proposed changes clearly
   - Waits for operator approval
   - Proceeds only with explicit consent

5. **Execute Remediation**
   - Applies Kubernetes patches
   - Updates cluster resources
   - Confirms successful application

6. **Evaluate**
   - Provides verification commands
   - Suggests monitoring steps
   - Documents the resolution

### Scenario A: OOMKilled Pod

**Problem**: Pod repeatedly crashes with OOMKilled status

**Detection**:
- Checks container termination states
- Identifies OOMKilled reason
- Counts restart attempts

**Root Cause**:
- Memory limit too low for workload
- Compares requested vs. actual usage

**Fix**:
- Increases memory limit by 3x (configurable)
- Updates both limits and requests
- Patches deployment

### Scenario B: Broken Service

**Problem**: Service has no endpoints despite healthy pods

**Detection**:
- Checks service endpoints
- Verifies pod health
- Compares labels

**Root Cause**:
- Service selector labels don't match pod labels
- Identifies mismatched keys/values

**Fix**:
- Updates service selector to match pod labels
- Patches service resource
- Restores connectivity

## 🔒 Safety Features

1. **Read-Only Diagnosis**: All diagnosis operations are read-only
2. **Human Approval**: No changes applied without explicit approval
3. **Clear Communication**: Detailed explanation of all proposed changes
4. **Audit Trail**: All actions logged
5. **Rollback Support**: Changes can be manually reverted if needed

## 🧪 Testing

### Manual Testing

1. **Deploy test scenarios**:
```bash
kubectl apply -f k8s-manifests/scenario-a-oom.yaml
kubectl apply -f k8s-manifests/scenario-b-broken-service.yaml
```

2. **Verify issues exist**:
```bash
# Check OOMKilled pod
kubectl get pods -l app=oom-app
kubectl describe pod -l app=oom-app

# Check service endpoints
kubectl get endpoints broken-service
```

3. **Run the agent**:
```bash
python cli.py --scenario oomkilled --namespace default --deployment oom-app
python cli.py --scenario broken-service --namespace default --service broken-service
```

4. **Verify fixes**:
```bash
# Verify OOM fix
kubectl get pods -l app=oom-app
kubectl describe deployment oom-app

# Verify service fix
kubectl get endpoints broken-service
kubectl describe service broken-service
```

### Cleanup

```bash
kubectl delete -f k8s-manifests/scenario-a-oom.yaml
kubectl delete -f k8s-manifests/scenario-b-broken-service.yaml
```

## 📁 Project Structure

```
.
├── cli.py                      # CLI interface with human-in-the-loop
├── web_ui.py                   # Gradio web interface
├── requirements.txt            # Python dependencies
├── .env.example               # Environment variables template
├── README.md                  # This file
├── src/
│   ├── k8s_client.py          # Kubernetes API wrapper
│   ├── diagnostics.py         # Diagnostic logic and RCA
│   ├── agent.py               # LangChain AI agent
│   └── orchestrator.py        # Main workflow orchestrator
└── k8s-manifests/
    ├── scenario-a-oom.yaml           # OOMKilled test deployment
    ├── scenario-a-oom-fixed.yaml     # Fixed version (reference)
    ├── scenario-b-broken-service.yaml # Broken service test
    └── scenario-b-broken-service-fixed.yaml # Fixed version (reference)
```

## 🛠️ Configuration

### Environment Variables

Create a `.env` file based on `.env.example`:

```bash
# OpenAI API Key (optional - agent works without it but with basic analysis)
OPENAI_API_KEY=sk-your-key-here

# Kubernetes Configuration (optional - uses default kubeconfig if not set)
KUBECONFIG=/path/to/kubeconfig
```

### Without OpenAI API Key

The agent works without an OpenAI API key by using rule-based diagnostics. AI-powered analysis will be replaced with formatted diagnostic output.

## 🔮 Future Enhancements

- [ ] Support for more scenarios (CrashLoopBackOff, ImagePullBackOff, etc.)
- [ ] Automated rollback on failed remediation
- [ ] Integration with monitoring/alerting systems
- [ ] Multi-cluster support
- [ ] Historical analysis and pattern recognition
- [ ] Custom remediation strategies
- [ ] Slack/Teams notifications
- [ ] GitOps integration for change tracking

## 📝 License

MIT License - see [LICENSE](LICENSE) file for details

## 🤝 Contributing

Contributions are welcome! Please read [CONTRIBUTING.md](CONTRIBUTING.md) for details on how to add new scenarios, submit pull requests, and contribute to the project.

## 📚 Additional Documentation

- [Quick Start Guide](QUICKSTART.md) - Get running in 10 minutes
- [Design Document](DESIGN.md) - Architecture and design decisions
- [Contributing Guide](CONTRIBUTING.md) - How to contribute

## 📧 Contact

For questions or feedback, please open an issue on GitHub.
