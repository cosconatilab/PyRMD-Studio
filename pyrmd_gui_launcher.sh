#!/bin/bash
# PyRMD-GUI Robust Launcher Script
# This script reliably activates the Conda environment and launches PyRMD-GUI

# Enable error handling
set -e

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Function to log messages
log_message() {
    echo "[PyRMD-GUI] $1"
}

# Function to handle errors
handle_error() {
    echo "[ERROR] $1" >&2
    echo ""
    echo "Troubleshooting steps:"
    echo "1. Ensure Conda is properly installed"
    echo "2. Try running: conda activate pyrmd_gui"
    echo "3. Reinstall PyRMD-GUI if the problem persists"
    echo ""
    exit 1
}

# Find conda installation
CONDA_BASE_PATH=""

# Method 1: Use conda info if conda is in PATH
if command -v conda &> /dev/null; then
    CONDA_BASE_PATH=$(conda info --base 2>/dev/null)
    if [[ -n "$CONDA_BASE_PATH" && -f "$CONDA_BASE_PATH/etc/profile.d/conda.sh" ]]; then
        log_message "Found Conda via PATH: $CONDA_BASE_PATH"
    else
        CONDA_BASE_PATH=""
    fi
fi

# Method 2: Check common conda locations if not found via PATH
if [[ -z "$CONDA_BASE_PATH" ]]; then
    for conda_dir in "$HOME/miniconda3" "$HOME/anaconda3" "/opt/miniconda3" "/opt/anaconda3" "/usr/local/miniconda3" "/usr/local/anaconda3"; do
        if [[ -f "$conda_dir/etc/profile.d/conda.sh" ]]; then
            CONDA_BASE_PATH="$conda_dir"
            log_message "Found Conda at: $CONDA_BASE_PATH"
            break
        fi
    done
fi

# Validate conda installation
if [[ -z "$CONDA_BASE_PATH" ]]; then
    handle_error "Could not find Conda installation. Please ensure Conda is properly installed."
fi

if [[ ! -f "$CONDA_BASE_PATH/etc/profile.d/conda.sh" ]]; then
    handle_error "Conda installation appears to be incomplete. Missing conda.sh script."
fi

# Source conda
log_message "Initializing Conda..."
source "$CONDA_BASE_PATH/etc/profile.d/conda.sh"

# Verify conda is available
if ! command -v conda &> /dev/null; then
    handle_error "Failed to initialize Conda. Please check your Conda installation."
fi

# Check if environment exists
if ! conda env list | grep -q "^pyrmd_gui "; then
    handle_error "Conda environment 'pyrmd_gui' not found. Please reinstall PyRMD-GUI."
fi

# Activate the pyrmd_gui environment
log_message "Activating environment 'pyrmd_gui'..."
if ! conda activate pyrmd_gui; then
    handle_error "Failed to activate Conda environment 'pyrmd_gui'."
fi

# Verify critical packages are available
log_message "Verifying installation..."
python -c "import PyQt5; import rdkit; import pandas; import numpy" 2>/dev/null || {
    handle_error "Critical packages are missing. Please reinstall PyRMD-GUI."
}

# Check for useful_rdkit_utils (optional)
if python -c "import useful_rdkit_utils" 2>/dev/null; then
    log_message "useful_rdkit_utils available"
else
    log_message "useful_rdkit_utils not available (some features may be limited)"
fi

# Change to the installation directory
cd "$SCRIPT_DIR"

# Launch PyRMD-GUI
log_message "Starting PyRMD-GUI..."
python homepage.py "$@"

