#!/usr/bin/env bash

# ----------------------------------------------------------------------
# PyRMD Launch Script with Conda Environment and Output Directory Management
# This script handles benchmarking runs with proper conda activation
# ----------------------------------------------------------------------

# Enable error handling
set -e

# User-configurable: how many CPU cores (OpenBLAS threads) each job may use
NUM_CORES=${NUM_CORES:-1}
export OPENBLAS_NUM_THREADS=$NUM_CORES
export OMP_NUM_THREADS=$NUM_CORES
export NUMBA_NUM_THREADS=$NUM_CORES

# Function to log messages with timestamps
log_message() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1"
}

# Function to handle errors
handle_error() {
    echo "[ERROR] $1" >&2
    echo ""
    echo "Troubleshooting steps:"
    echo "1. Ensure Conda is properly installed"
    echo "2. Try running: conda activate pyrmd_studio"
    echo "3. Check that all required files are present"
    echo "4. Verify output directory permissions"
    echo ""
    exit 1
}

# ----------------------------------------------------------------------
# Conda Environment Setup
# ----------------------------------------------------------------------
log_message "Initializing Conda environment for PyRMD computational tasks..."

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
if ! conda env list | grep -q "^pyrmd_studio "; then
    handle_error "Conda environment 'pyrmd_studio' not found. Please install PyRMD-Studio first."
fi

# Activate the pyrmd_studio environment
log_message "Activating environment 'pyrmd_studio'..."
if ! conda activate pyrmd_studio; then
    handle_error "Failed to activate Conda environment 'pyrmd_studio'."
fi

# Verify critical packages are available
log_message "Verifying computational packages..."
python -c "import pandas; import numpy; import rdkit" 2>/dev/null || {
    handle_error "Critical computational packages are missing. Please reinstall PyRMD-GUI."
}

log_message "Conda environment activated successfully."

# ----------------------------------------------------------------------
# Determine configuration template (benchmark or screening)
# ----------------------------------------------------------------------
CONFIG_TEMPLATE=""
if [ -f "configuration_benchmark.ini" ] && [ -f "configuration_screening.ini" ]; then
    if [ "configuration_benchmark.ini" -nt "configuration_screening.ini" ]; then
        CONFIG_TEMPLATE="configuration_benchmark.ini"
        MODE="benchmark"
    else
        CONFIG_TEMPLATE="configuration_screening.ini"
        MODE="screening"
    fi
elif [ -f "configuration_benchmark.ini" ]; then
    CONFIG_TEMPLATE="configuration_benchmark.ini"
    MODE="benchmark"
elif [ -f "configuration_screening.ini" ]; then
    CONFIG_TEMPLATE="configuration_screening.ini"
    MODE="screening"
else
    handle_error "No configuration file found (configuration_benchmark.ini or configuration_screening.ini)."
fi

log_message "Using configuration template: $CONFIG_TEMPLATE (mode: $MODE)"

# ----------------------------------------------------------------------
# Validate required input files
# ----------------------------------------------------------------------
for file in "tc_actives.txt" "tc_inactives.txt" "PyRMD_v2.0_noplot_vect_butina.py"; do
    if [ ! -f "$file" ]; then
        handle_error "Required file '$file' not found in current directory."
    fi
    if [ ! -s "$file" ]; then
        handle_error "Required file '$file' is empty."
    fi
done

# ----------------------------------------------------------------------
# Extract and setup output directory from configuration
# ----------------------------------------------------------------------
log_message "Setting up output directory structure..."

# Read the first combination to determine output directory
first_a=$(head -n 1 tc_actives.txt | tr -d '[:space:]')
first_i=$(head -n 1 tc_inactives.txt | tr -d '[:space:]')

# Create temporary config to extract output directory
TEMP_CFG="temp_${first_a}_${first_i}.ini"
sed "s/XXXX/${first_a}/g; s/YYYY/${first_i}/g" "$CONFIG_TEMPLATE" > "$TEMP_CFG"

# Extract output directory from benchmark_file or screening_output
if [ "$MODE" = "benchmark" ]; then
    OUTPUT_FILE=$(grep "^benchmark_file" "$TEMP_CFG" | cut -d '=' -f2- | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')

    if [ -z "$OUTPUT_FILE" ]; then
        OUTPUT_FILE="./PyRMD_benchmark_results.csv"
        log_message "No benchmark_file specified, using default: $OUTPUT_FILE"
    fi
else
    OUTPUT_FILE=$(grep "^screening_output" "$TEMP_CFG" | cut -d '=' -f2- | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')

    if [ -z "$OUTPUT_FILE" ]; then
        OUTPUT_FILE="./PyRMD_screening_results.csv"
        log_message "No screening_output specified, using default: $OUTPUT_FILE"
    fi
fi

# Determine output directory
if [[ "$OUTPUT_FILE" == /* ]]; then
    # Absolute path
    OUTPUT_DIR=$(dirname "$OUTPUT_FILE")
else
    # Relative path
    OUTPUT_DIR=$(dirname "$OUTPUT_FILE")
    if [ "$OUTPUT_DIR" = "." ]; then
        OUTPUT_DIR="./PyRMD_Results_$(date +%Y%m%d_%H%M%S)"
        log_message "Using timestamped output directory: $OUTPUT_DIR"
        
        # Update the output file path in the template
        if [ "$MODE" = "benchmark" ]; then
            sed -i "s|^benchmark_file.*|benchmark_file = $OUTPUT_DIR/$(basename "$OUTPUT_FILE")|" "$CONFIG_TEMPLATE"
        else
            sed -i "s|^screening_output.*|screening_output = $OUTPUT_DIR/$(basename "$OUTPUT_FILE")|" "$CONFIG_TEMPLATE"
        fi
    fi
fi

# Clean up temporary config
rm -f "$TEMP_CFG"

# Create output directory structure
log_message "Creating output directory structure: $OUTPUT_DIR"
mkdir -p "$OUTPUT_DIR"
mkdir -p "$OUTPUT_DIR/configs"
mkdir -p "$OUTPUT_DIR/logs"
mkdir -p "$OUTPUT_DIR/models"
mkdir -p "$OUTPUT_DIR/temp"

# Verify output directory is writable
if [ ! -w "$OUTPUT_DIR" ]; then
    handle_error "Output directory '$OUTPUT_DIR' is not writable. Please check permissions."
fi

log_message "Output directory structure created successfully."

# ----------------------------------------------------------------------
# Count total combinations
# ----------------------------------------------------------------------
TOTAL_ACTIVES=$(wc -l < tc_actives.txt)
TOTAL_INACTIVES=$(wc -l < tc_inactives.txt)
TOTAL_COMBINATIONS=$((TOTAL_ACTIVES * TOTAL_INACTIVES))

log_message "Found $TOTAL_ACTIVES active and $TOTAL_INACTIVES inactive epsilon values"
log_message "Total combinations to process: $TOTAL_COMBINATIONS"
log_message "Using $NUM_CORES CPU cores per job"
log_message "All outputs will be saved to: $OUTPUT_DIR"
echo ""

# ----------------------------------------------------------------------
# First combination setup with output directory
# ----------------------------------------------------------------------
first_a=$(head -n 1 tc_actives.txt | tr -d '[:space:]')
first_i=$(head -n 1 tc_inactives.txt | tr -d '[:space:]')

log_message "Starting with first combination: active=$first_a, inactive=$first_i"

# Create config with proper output directory paths
TEMP_CFG="temp_${first_a}_${first_i}.ini"
sed "s/XXXX/${first_a}/g; s/YYYY/${first_i}/g" "$CONFIG_TEMPLATE" > "$TEMP_CFG"

# Update output paths in the config to use the output directory
if [ "$MODE" = "benchmark" ]; then
    sed -i "s|^benchmark_file.*|benchmark_file = $OUTPUT_DIR/$(basename "$(grep "^benchmark_file" "$TEMP_CFG" | cut -d '=' -f2- | xargs)")|" "$TEMP_CFG"
else
    sed -i "s|^screening_output.*|screening_output = $OUTPUT_DIR/$(basename "$(grep "^screening_output" "$TEMP_CFG" | cut -d '=' -f2- | xargs)")|" "$TEMP_CFG"
fi

# Move config to configs directory
cfg_path="$OUTPUT_DIR/configs/${first_a}_${first_i}.ini"
mv "$TEMP_CFG" "$cfg_path"

# Set wait file in temp directory
WAIT_FILE="$OUTPUT_DIR/temp/temp_y_training.pkl"

# Launch first job with output redirection
log_message "Launching first job using config: $cfg_path"
python -u PyRMD_v2.0_noplot_vect_butina.py "$cfg_path" &> "$OUTPUT_DIR/logs/${first_a}_${first_i}.log" &
FIRST_PID=$!

log_message "First job PID: $FIRST_PID"
log_message "Waiting for training data file: $WAIT_FILE"

# ----------------------------------------------------------------------
# Wait for training file
# ----------------------------------------------------------------------
WAIT_COUNT=0
while [ ! -f "$WAIT_FILE" ]; do
    sleep 5
    WAIT_COUNT=$((WAIT_COUNT + 1))
    if [ $((WAIT_COUNT % 12)) -eq 0 ]; then
        log_message "Still waiting for $WAIT_FILE... ($((WAIT_COUNT * 5)) seconds elapsed)"
    fi
    if ! kill -0 $FIRST_PID 2>/dev/null; then
        log_message "WARNING: First job has terminated but $WAIT_FILE not found"
        break
    fi
done

if [ -f "$WAIT_FILE" ]; then
    log_message "Training data file found: $WAIT_FILE"
else
    log_message "WARNING: Proceeding without finding $WAIT_FILE"
fi

# ----------------------------------------------------------------------
# Launch remaining jobs with proper output directory management
# ----------------------------------------------------------------------
CURRENT_COMBINATION=1
MAX_PARALLEL_JOBS=50

for a in $(cat tc_actives.txt); do
    a=$(echo "$a" | tr -d '[:space:]')
    for i in $(cat tc_inactives.txt); do
        i=$(echo "$i" | tr -d '[:space:]')

        if [ "$a" = "$first_a" ] && [ "$i" = "$first_i" ]; then
            continue
        fi

        CURRENT_COMBINATION=$((CURRENT_COMBINATION + 1))
        log_message "[$CURRENT_COMBINATION/$TOTAL_COMBINATIONS] active=$a, inactive=$i"

        # Create config with proper output directory paths
        TEMP_CFG="temp_${a}_${i}.ini"
        sed "s/XXXX/${a}/g; s/YYYY/${i}/g" "$CONFIG_TEMPLATE" > "$TEMP_CFG"

        # Update output paths in the config
        if [ "$MODE" = "benchmark" ]; then
            sed -i "s|^benchmark_file.*|benchmark_file = $OUTPUT_DIR/$(basename "$(grep "^benchmark_file" "$TEMP_CFG" | cut -d '=' -f2- | xargs)")|" "$TEMP_CFG"
        else
            sed -i "s|^screening_output.*|screening_output = $OUTPUT_DIR/$(basename "$(grep "^screening_output" "$TEMP_CFG" | cut -d '=' -f2- | xargs)")|" "$TEMP_CFG"
        fi

        # Move config to configs directory
        cfg_path="$OUTPUT_DIR/configs/${a}_${i}.ini"
        mv "$TEMP_CFG" "$cfg_path"

        # Throttle parallel jobs
        CURRENT_JOBS=$(pgrep -f "python.*PyRMD_v2.0_noplot_vect_butina.py" | wc -l)
        while [ "$CURRENT_JOBS" -ge "$MAX_PARALLEL_JOBS" ]; do
            log_message "  Throttling: $CURRENT_JOBS jobs running, waiting..."
            sleep 10
            CURRENT_JOBS=$(pgrep -f "python.*PyRMD_v2.0_noplot_vect_butina.py" | wc -l)
        done

        log_message "  Starting job: $cfg_path"
        python -u PyRMD_v2.0_noplot_vect_butina.py "$cfg_path" &> "$OUTPUT_DIR/logs/${a}_${i}.log" &

        sleep 2
    done
done

# ----------------------------------------------------------------------
# Done launching
# ----------------------------------------------------------------------
echo ""
log_message "All combinations launched."
log_message "Output directory: $OUTPUT_DIR"
log_message "Configuration files: $OUTPUT_DIR/configs/"
log_message "Log files: $OUTPUT_DIR/logs/"
log_message "Models and results: $OUTPUT_DIR/"
log_message "To monitor jobs: pgrep -f 'python.*PyRMD_v2.0_noplot_vect_butina.py'"
log_message "To check logs: ls -la $OUTPUT_DIR/logs/ | wc -l"
log_message "Expected log files: $TOTAL_COMBINATIONS"

# ----------------------------------------------------------------------
# Optional wait for all jobs
# ----------------------------------------------------------------------
if [ "$1" = "--wait" ]; then
    log_message "Waiting for all jobs to complete..."
    while [ "$(pgrep -f 'python.*PyRMD_v2.0_noplot_vect_butina.py' | wc -l)" -gt 0 ]; do
        RUNNING=$(pgrep -f "python.*PyRMD_v2.0_noplot_vect_butina.py" | wc -l)
        COMPLETED=$(find "$OUTPUT_DIR/logs" -name '*.log' | wc -l)
        log_message "Status: $RUNNING jobs running, $COMPLETED/$TOTAL_COMBINATIONS logs created"
        sleep 30
    done
    log_message "All jobs completed!"
    log_message "Results available in: $OUTPUT_DIR"
fi

# Deactivate conda environment when done
conda deactivate
log_message "Conda environment deactivated."
log_message "PyRMD launch script completed successfully."

