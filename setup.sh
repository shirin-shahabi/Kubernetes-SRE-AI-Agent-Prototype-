#!/bin/bash
# Setup script for Kubernetes SRE AI Agent

set -e

echo "========================================="
echo "Kubernetes SRE AI Agent Setup"
echo "========================================="
echo ""

# Check Python version
echo "Checking Python version..."
python_version=$(python3 --version 2>&1 | awk '{print $2}')
echo "Found Python $python_version"

if ! python3 -c 'import sys; assert sys.version_info >= (3,8)' 2>/dev/null; then
    echo "Error: Python 3.8 or higher is required"
    exit 1
fi

# Check if kubectl is available
echo ""
echo "Checking kubectl..."
if command -v kubectl &> /dev/null; then
    echo "kubectl is available"
    kubectl cluster-info --request-timeout=5s &> /dev/null && echo "Kubernetes cluster is accessible" || echo "Warning: Cannot access Kubernetes cluster"
else
    echo "Warning: kubectl not found. You'll need it to use the agent."
fi

# Create virtual environment (optional but recommended)
echo ""
read -p "Create Python virtual environment? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
    source venv/bin/activate
    echo "Virtual environment activated"
fi

# Install dependencies
echo ""
echo "Installing Python dependencies..."
pip install -r requirements.txt

# Setup .env file
echo ""
if [ ! -f .env ]; then
    echo "Creating .env file..."
    cp .env.example .env
    echo ".env file created"
    echo ""
    echo "⚠️  IMPORTANT: Edit .env and add your OpenAI API key!"
    echo ""
else
    echo ".env file already exists"
fi

# Create examples
echo ""
echo "Generating test scenarios..."
python examples/create_test_scenarios.py

echo ""
echo "========================================="
echo "Setup Complete!"
echo "========================================="
echo ""
echo "Next steps:"
echo "1. Edit .env and add your OpenAI API key"
echo "2. (Optional) Test with: python main.py --namespace default --mode once --dry-run"
echo "3. Read QUICKSTART.md for detailed instructions"
echo ""
echo "If you created a virtual environment, activate it with:"
echo "  source venv/bin/activate"
echo ""
