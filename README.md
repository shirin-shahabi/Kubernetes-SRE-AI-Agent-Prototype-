# Kubernetes SRE AI Agent Prototype

[![CI/CD Pipeline](https://github.com/shirin-shahabi/Kubernetes-SRE-AI-Agent-Prototype-/actions/workflows/ci.yml/badge.svg)](https://github.com/shirin-shahabi/Kubernetes-SRE-AI-Agent-Prototype-/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/shirin-shahabi/Kubernetes-SRE-AI-Agent-Prototype-/branch/main/graph/badge.svg)](https://codecov.io/gh/shirin-shahabi/Kubernetes-SRE-AI-Agent-Prototype-)
[![Python Version](https://img.shields.io/badge/python-3.9%20%7C%203.10%20%7C%203.11-blue)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A prototype SRE AI agent that can detect, diagnose, and remediate common Kubernetes failures automatically.

## 🎯 Features

- **Automated Failure Detection**: Identifies failed pods, CrashLoopBackOff, and unhealthy deployments
- **Intelligent Remediation**: Automatically restarts failed pods and scales deployments
- **Diagnostic Capabilities**: Retrieves pod logs and analyzes deployment health
- **Production-Ready Testing**: Comprehensive unit tests and E2E tests with real Kubernetes clusters
- **CI/CD Pipeline**: Automated testing, linting, and security scanning

## 📋 Prerequisites

- Python 3.9 or higher
- Kubernetes cluster (for E2E tests)
- kubectl configured with cluster access

## 🚀 Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/shirin-shahabi/Kubernetes-SRE-AI-Agent-Prototype-.git
cd Kubernetes-SRE-AI-Agent-Prototype-

# Create a virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Basic Usage

```python
from sre_agent import KubernetesSREAgent, setup_logging

# Configure logging
setup_logging(level="INFO")

# Initialize the agent
agent = KubernetesSREAgent()

# Detect failed pods
failed_pods = agent.detect_pod_failures(namespace="default")
print(f"Found {len(failed_pods)} failed pods")

# Check deployment health
health = agent.check_deployment_health("my-deployment", namespace="default")
print(f"Deployment health: {health}")

# Restart a failed pod
agent.restart_failed_pod("failed-pod-name", namespace="default")
```

## 🧪 Testing

### Running Unit Tests

```bash
# Run all unit tests
pytest test_sre_agent.py -v

# Run with coverage
pytest test_sre_agent.py -v --cov=sre_agent --cov-report=html

# View coverage report
open htmlcov/index.html
```

### Running E2E Tests

E2E tests require a running Kubernetes cluster. The easiest way is to use [kind](https://kind.sigs.k8s.io/):

```bash
# Install kind (if not already installed)
# On macOS:
brew install kind

# On Linux:
curl -Lo ./kind https://kind.sigs.k8s.io/dl/v0.20.0/kind-linux-amd64
chmod +x ./kind
sudo mv ./kind /usr/local/bin/kind

# Create a kind cluster
kind create cluster --name sre-test

# Run E2E tests
pytest test_e2e.py -v

# Cleanup
kind delete cluster --name sre-test
```

### Running All Tests

```bash
# Run all tests (unit + e2e)
pytest -v

# Run with coverage
pytest -v --cov=sre_agent --cov-report=term-missing
```

## 🔍 Code Quality

### Linting

```bash
# Run flake8
flake8 sre_agent.py test_sre_agent.py test_e2e.py --max-line-length=120

# Run black (code formatter)
black --check --line-length=120 sre_agent.py test_sre_agent.py test_e2e.py

# Auto-format with black
black --line-length=120 sre_agent.py test_sre_agent.py test_e2e.py

# Run mypy (type checking)
mypy sre_agent.py --ignore-missing-imports
```

### Security Scanning

```bash
# Check for vulnerable dependencies
safety check
```

## 🤖 CI/CD Pipeline

This project uses GitHub Actions for continuous integration and deployment. The pipeline includes:

### Pipeline Stages

1. **Code Quality & Linting**
   - flake8: Style and syntax checking
   - black: Code formatting verification
   - mypy: Static type checking

2. **Security Scanning**
   - Safety: Dependency vulnerability scanning
   - CodeQL: Static security analysis

3. **Unit Tests**
   - Tests across Python 3.9, 3.10, and 3.11
   - Coverage reporting to Codecov
   - Fast feedback (< 2 minutes)

4. **E2E Tests**
   - Tests with real Kubernetes cluster (kind)
   - Validates actual cluster interactions
   - End-to-end workflow verification

5. **Build Validation**
   - Syntax validation
   - Import verification
   - Integration smoke tests

### Running CI Locally

You can run the same checks locally before pushing:

```bash
# Run all quality checks
flake8 sre_agent.py test_sre_agent.py test_e2e.py --max-line-length=120
black --check --line-length=120 sre_agent.py test_sre_agent.py test_e2e.py
mypy sre_agent.py --ignore-missing-imports

# Run unit tests
pytest test_sre_agent.py -v --cov=sre_agent

# Run E2E tests (requires kind cluster)
kind create cluster
pytest test_e2e.py -v
kind delete cluster
```

## 📊 Project Structure

```
.
├── .github/
│   ├── workflows/
│   │   └── ci.yml              # CI/CD pipeline configuration
│   └── dependabot.yml          # Automated dependency updates
├── sre_agent.py                # Main SRE agent implementation
├── test_sre_agent.py           # Unit tests
├── test_e2e.py                 # End-to-end tests
├── requirements.txt            # Python dependencies
├── pytest.ini                  # Pytest configuration
├── .gitignore                  # Git ignore rules
├── JUSTIFICATION.md            # Technology choices justification
├── LICENSE                     # MIT License
└── README.md                   # This file
```

## 🎓 Why This Technology Stack?

For a detailed explanation of why we chose this specific technology stack and testing approach for this Kubernetes SRE AI Agent prototype, see [JUSTIFICATION.md](JUSTIFICATION.md).

**TL;DR:**
- **Python**: Best Kubernetes client support, AI/ML libraries, rapid prototyping
- **GitHub Actions**: Native GitHub integration, free for open source, Kubernetes support
- **pytest**: Industry standard, rich ecosystem, excellent mocking
- **kind**: Fast Kubernetes cluster in Docker, perfect for CI/CD
- **Unit + E2E Tests**: Comprehensive coverage from isolated components to real cluster interactions

## 🔒 Security

- All dependencies are scanned with `safety` for known vulnerabilities
- CodeQL performs static security analysis on every commit
- Dependabot automatically creates PRs for dependency updates
- Minimal external dependencies to reduce attack surface

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Run tests and linting (`pytest -v && flake8 . && black --check .`)
5. Commit your changes (`git commit -m 'Add amazing feature'`)
6. Push to the branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [Kubernetes Python Client](https://github.com/kubernetes-client/python)
- [kind (Kubernetes in Docker)](https://kind.sigs.k8s.io/)
- [pytest](https://pytest.org/)
- CNCF and Kubernetes SIG Testing community

## 📧 Contact

Shirin Shahabi - [@shirin-shahabi](https://github.com/shirin-shahabi)

Project Link: [https://github.com/shirin-shahabi/Kubernetes-SRE-AI-Agent-Prototype-](https://github.com/shirin-shahabi/Kubernetes-SRE-AI-Agent-Prototype-)

---

**Note**: This is a prototype for learning and demonstration purposes. For production use, additional features like proper error handling, logging aggregation, metrics collection, and alerting would be necessary.
