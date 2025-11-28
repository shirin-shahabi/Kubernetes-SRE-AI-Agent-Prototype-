#!/bin/bash
# Run the SRE agent web UI with proper Python path

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"

# Add src to PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:${PROJECT_ROOT}/src"

# Check if OPENROUTER_API_KEY is set
if [ -z "$OPENROUTER_API_KEY" ]; then
    echo "⚠️  OPENROUTER_API_KEY not set"
    echo "   Run: source scripts/setup_env.sh"
    exit 1
fi

# Run the web UI
cd "$PROJECT_ROOT"
python -m sre_agent.web

