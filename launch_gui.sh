#!/bin/bash
# PyRMD-GUI Application Launcher
# This script is specifically for launching the GUI application

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Execute the main launcher
exec "$SCRIPT_DIR/pyrmd_gui_launcher.sh" "$@"

