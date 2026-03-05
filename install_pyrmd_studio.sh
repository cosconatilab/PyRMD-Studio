#!/bin/bash

# ==============================================================================
# PyRMD-Studio Ultimate Installer (Final Version)
# ==============================================================================
set -e  # Exit on any error

# --- Color Codes ---
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# --- Configuration ---
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTALL_DIR="$HOME/.local/share/pyrmd-studio"
GLOBAL_BIN_DIR="$HOME/.local/bin"
CONDA_ENV_NAME="pyrmd_studio"
APP_NAME="PyRMD Studio"
DESKTOP_FILE_NAME="pyrmd-studio.desktop"
ICON_NAME="pyrmd_logo.png"

# --- Helper Functions ---
log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

echo -e "${BLUE}======================================================${NC}"
echo -e "${BLUE}       PyRMD Studio Installer (Complete Package)      ${NC}"
echo -e "${BLUE}======================================================${NC}"

# ----------------------------------------------------------------------
# STEP 1: GENERATE OPTIMIZED ENVIRONMENT FILE
# ----------------------------------------------------------------------
log_info "Generating optimized environment configuration..."

cat > fast_environment_temp.yml <<EOL
name: $CONDA_ENV_NAME
channels:
  - conda-forge
dependencies:
  - python=3.11
  - pandas
  - numpy
  - matplotlib
  - scikit-learn
  - rdkit
  - openpyxl
  - pyqt=5.15
  - openbabel
  - scipy
  - joblib
  - pillow
  - patsy
  - statsmodels
  - pip
  - pip:
    - configparser
    - psutil
    - tqdm
    - requests
    - useful_rdkit_utils
EOL

# ----------------------------------------------------------------------
# STEP 2: AUTO-DETECT OR INSTALL CONDA/MAMBA
# ----------------------------------------------------------------------
log_info "Checking package manager..."

HAS_CONDA=false
HAS_MAMBA=false
CONDA_EXE=""
LOCAL_MAMBA_DIR="$HOME/.local/share/pyrmd-miniforge"

# 1. Check existing Mamba
if command -v mamba &> /dev/null; then
    log_success "Mamba detected on system."
    HAS_MAMBA=true
    CONDA_EXE=$(command -v mamba)
# 2. Check existing Conda
elif command -v conda &> /dev/null; then
    log_success "Conda detected on system."
    HAS_CONDA=true
    CONDA_EXE=$(command -v conda)
fi

# 3. If NEITHER, install local Miniforge
if [ "$HAS_CONDA" = false ] && [ "$HAS_MAMBA" = false ]; then
    log_warning "No Conda/Mamba found. Downloading standalone Mamba (Miniforge)..."

    mkdir -p "$LOCAL_MAMBA_DIR"
    wget -O Miniforge3.sh "https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-Linux-x86_64.sh"

    log_info "Installing Miniforge..."
    bash Miniforge3.sh -b -u -p "$LOCAL_MAMBA_DIR"
    rm Miniforge3.sh

    # Activate local mamba
    source "$LOCAL_MAMBA_DIR/etc/profile.d/conda.sh"
    source "$LOCAL_MAMBA_DIR/etc/profile.d/mamba.sh"

    HAS_MAMBA=true
    CONDA_EXE="mamba"
    log_success "Miniforge installed locally."
fi

# ----------------------------------------------------------------------
# STEP 3: CREATE/UPDATE ENVIRONMENT
# ----------------------------------------------------------------------
log_info "Setting up Conda environment '$CONDA_ENV_NAME'..."

if conda info --envs | grep -q "$CONDA_ENV_NAME"; then
    log_info "Environment exists. Updating..."
    if [ "$HAS_MAMBA" = true ]; then
        mamba env update -f fast_environment_temp.yml --prune
    else
        conda env update -f fast_environment_temp.yml --solver=libmamba --prune || \
        conda env update -f fast_environment_temp.yml
    fi
else
    log_info "Creating new environment (using fast solver)..."
    if [ "$HAS_MAMBA" = true ]; then
        mamba env create -f fast_environment_temp.yml
    else
        conda env create -f fast_environment_temp.yml --solver=libmamba || \
        conda env create -f fast_environment_temp.yml
    fi
fi

rm fast_environment_temp.yml

# ----------------------------------------------------------------------
# STEP 4: INSTALL APPLICATION FILES & FOLDERS
# ----------------------------------------------------------------------
log_info "Installing application files to $INSTALL_DIR..."

mkdir -p "$INSTALL_DIR"

# 1. List of individual files to copy
FILES_TO_COPY=(
    "Benchmark_1.py"
    "Benchmark_2.py"
    "Fetch_chEMBL.py"
    "PyRMD_v2.0_noplot_vect_butina.py"
    "Screening.py"
    "Screening_2.py"
    "compound_analyzer_modal.py"
    "configuration_benchmark.ini"
    "configuration_screening.ini"
    "dock_prep.py"
    "environment.yml"
    "homepage.py"
    "icon.ico"
    "icon.png"
    "install_pyrmd_studio.sh"
    "launch.sh"
    "launch_gui.sh"
    "logo_2.png"
    "pyrmd-gui.png"
    "pyrmd_gui_launcher.sh"
    "pyrmd_logo.png"
    "pyrmd_logos.png"
    "rmd_analysis.py"
    "tc_actives.txt"
    "tc_inactives.txt"
    "uninstall_pyrmd_studio.sh"
)

# Copy files loop
for file in "${FILES_TO_COPY[@]}"; do
    if [ -f "$SCRIPT_DIR/$file" ]; then
        cp "$SCRIPT_DIR/$file" "$INSTALL_DIR/"
    else
        log_warning "File not found (skipping): $file"
    fi
done

# 2. List of FOLDERS to copy (Added Tutorial here)
FOLDERS_TO_COPY=("Tutorial")

for folder in "${FOLDERS_TO_COPY[@]}"; do
    if [ -d "$SCRIPT_DIR/$folder" ]; then
        # Copy folder recursively
        cp -r "$SCRIPT_DIR/$folder" "$INSTALL_DIR/"
        log_success "Copied directory: $folder"
    else
        log_warning "Directory not found (skipping): $folder"
    fi
done

# Make scripts executable
chmod +x "$INSTALL_DIR/launch.sh"
chmod +x "$INSTALL_DIR/launch_gui.sh"
chmod +x "$INSTALL_DIR/pyrmd_gui_launcher.sh"

# ----------------------------------------------------------------------
# STEP 5: CREATE LAUNCHER & GLOBAL COMMAND
# ----------------------------------------------------------------------
log_info "Creating global launcher command..."

# Determine Conda Source robustly
if [ -d "$LOCAL_MAMBA_DIR" ]; then
    CONDA_SOURCE="$LOCAL_MAMBA_DIR/etc/profile.d/conda.sh"
elif [ -f "$HOME/miniconda3/etc/profile.d/conda.sh" ]; then
    CONDA_SOURCE="$HOME/miniconda3/etc/profile.d/conda.sh"
elif [ -f "$HOME/anaconda3/etc/profile.d/conda.sh" ]; then
    CONDA_SOURCE="$HOME/anaconda3/etc/profile.d/conda.sh"
else
    # Fallback attempt to find conda
    CONDA_BASE=$(conda info --base 2>/dev/null || echo "")
    if [ -n "$CONDA_BASE" ] && [ -f "$CONDA_BASE/etc/profile.d/conda.sh" ]; then
        CONDA_SOURCE="$CONDA_BASE/etc/profile.d/conda.sh"
    else
        log_warning "Could not auto-detect Conda profile script. Wrapper might require manual adjustment."
        CONDA_SOURCE=""
    fi
fi

# 1. Create wrapper script with MESA/GL FIX
# This wrapper handles the environment AND the graphics fix
cat > "$INSTALL_DIR/pyrmd_studio" <<EOL
#!/bin/bash
# Force software rendering to fix MESA/ZINK errors
export LIBGL_ALWAYS_SOFTWARE=1

# Initialize Conda
if [ -f "$CONDA_SOURCE" ]; then
    source "$CONDA_SOURCE"
fi

# Activate Environment
conda activate $CONDA_ENV_NAME

# Launch Application
cd "$INSTALL_DIR"
python homepage.py
EOL

chmod +x "$INSTALL_DIR/pyrmd_studio"

# 2. Link to ~/.local/bin (Standard user bin)
mkdir -p "$GLOBAL_BIN_DIR"
ln -sf "$INSTALL_DIR/pyrmd_studio" "$GLOBAL_BIN_DIR/pyrmd_studio"
log_success "Global command 'pyrmd_studio' created."

# ----------------------------------------------------------------------
# STEP 6: DESKTOP INTEGRATION
# ----------------------------------------------------------------------
log_info "Creating Desktop shortcut..."

# Try finding the best icon
ICON_PATH="$INSTALL_DIR/$ICON_NAME"
if [ ! -f "$ICON_PATH" ]; then
    if [ -f "$INSTALL_DIR/icon.png" ]; then
        ICON_PATH="$INSTALL_DIR/icon.png"
    else
        ICON_PATH="utilities-terminal"
    fi
fi

mkdir -p "$HOME/.local/share/applications"

# Create the .desktop file
cat > "$HOME/.local/share/applications/$DESKTOP_FILE_NAME" <<EOL
[Desktop Entry]
Version=1.0
Type=Application
Name=PyRMD Studio
Comment=Computational Drug Discovery Platform
Exec=$INSTALL_DIR/pyrmd_studio
Icon=$ICON_PATH
Terminal=false
Categories=Science;Education;Chemistry;
StartupNotify=true
EOL

chmod +x "$HOME/.local/share/applications/$DESKTOP_FILE_NAME"
update-desktop-database "$HOME/.local/share/applications" &> /dev/null || true

# ALSO copy to Desktop surface if it exists (for easy clicking)
if [ -d "$HOME/Desktop" ]; then
    cp "$HOME/.local/share/applications/$DESKTOP_FILE_NAME" "$HOME/Desktop/"
    chmod +x "$HOME/Desktop/$DESKTOP_FILE_NAME"
    log_success "Shortcut added to Desktop."
fi

log_success "Shortcut added to Applications Menu."

# ----------------------------------------------------------------------
# STEP 7: FINISH & PATH CHECK
# ----------------------------------------------------------------------
echo ""
echo -e "${BLUE}======================================================${NC}"
echo -e "${GREEN}   INSTALLATION COMPLETE!   ${NC}"
echo -e "${BLUE}======================================================${NC}"
echo ""
echo "Installation Summary:"
echo "---------------------"
echo "- Location: $INSTALL_DIR"
echo "- Command:  pyrmd_studio"
echo ""

# Check PATH and auto-fix if necessary
if [[ ":$PATH:" != *":$GLOBAL_BIN_DIR:"* ]]; then
    log_warning "Your ~/.local/bin folder is not in your PATH."
    
    SHELL_CONFIG=""
    if [ -f "$HOME/.bashrc" ]; then SHELL_CONFIG="$HOME/.bashrc"; fi
    if [ -f "$HOME/.zshrc" ]; then SHELL_CONFIG="$HOME/.zshrc"; fi

    if [ -n "$SHELL_CONFIG" ]; then
        echo "Appending export PATH to $SHELL_CONFIG..."
        echo '' >> "$SHELL_CONFIG"
        echo '# Added by PyRMD Studio Installer' >> "$SHELL_CONFIG"
        echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$SHELL_CONFIG"
        log_success "Path added! Please restart your terminal or run: source $SHELL_CONFIG"
    else
        echo "Could not find .bashrc or .zshrc. Please run manually:"
        echo "  export PATH=\"\$HOME/.local/bin:\$PATH\""
    fi
else
    echo "You can now type 'pyrmd_studio' in any terminal to start."
fi

echo "You can also launch 'PyRMD Studio' from your Applications Menu."
echo ""