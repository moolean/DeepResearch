#!/bin/bash
# Standalone script to test API availability
# Can be run independently without starting inference

# Get the script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Check if .env file exists
ENV_FILE="$SCRIPT_DIR/.env"

if [ ! -f "$ENV_FILE" ]; then
    echo "Error: .env file not found at $ENV_FILE"
    echo "Please copy .env.example to .env and configure your settings:"
    echo "  cp .env.example .env"
    exit 1
fi

# Load environment variables from .env
echo "Loading environment variables from .env file..."
set -a  # automatically export all variables
source "$ENV_FILE"
set +a  # stop automatically exporting

# Run the test suite
echo ""
python -u "$SCRIPT_DIR/tests/run_api_tests.py"

exit_code=$?

if [ $exit_code -eq 0 ]; then
    echo ""
    echo "You can now run inference with: bash inference/run_react_infer.sh"
fi

exit $exit_code
