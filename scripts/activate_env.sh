#!/bin/bash
# Activate environment and set up paths

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"

# Add src to PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:${PROJECT_ROOT}/src"

# Load OpenRouter API key if setup_env.sh exists
if [ -f "$SCRIPT_DIR/setup_env.sh" ]; then
    source "$SCRIPT_DIR/setup_env.sh"
fi

echo "✅ Environment activated"
echo "   PYTHONPATH includes: $PROJECT_ROOT/src"
echo "   OPENROUTER_API_KEY: ${OPENROUTER_API_KEY:0:20}..."

