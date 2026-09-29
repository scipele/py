#!/bin/bash

# Define absolute paths based on your new directory structure
PROJECT_DIR="/home/dev/py/financial_plan"
PYTHON="/home/dev/py/.venv/bin/python"
PYTHON_SCRIPT="$PROJECT_DIR/py/main.py"

# Verify that the Python virtual environment executable exists
if [ ! -x "$PYTHON" ]; then
    echo "ERROR: Python virtual environment not found at: $PYTHON"
    exit 1
fi

# Verify that the main program script exists
if [ ! -f "$PYTHON_SCRIPT" ]; then
    echo "ERROR: Python main script not found at: $PYTHON_SCRIPT"
    exit 1
fi

# Navigate to the script's directory so relative paths for modules and JSON files resolve correctly
cd "$PROJECT_DIR/py" || exit 1

# Run the program
echo "Starting retirement simulation..."
"$PYTHON" "main.py"
