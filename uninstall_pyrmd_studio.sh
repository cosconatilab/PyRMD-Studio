#!/bin/bash

# ==============================================================================
# PyRMD-Studio Ultimate Uninstaller
# ==============================================================================
set -e  # Exit on any error

# --- Color Codes (matches installer) ---
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# --- Configuration (must mirror install_pyrmd_studio.sh exactly) ---
INSTALL_DIR="$HOME/.local/share/pyrmd-studio"
GLOBAL_BIN_DIR="$HOME/.local/bin"
CONDA_ENV_NAME="pyrmd_studio"
APP_NAME="PyRMD Studio"
DESKTOP_FILE_NAME="pyrmd-studio.desktop"
LOCAL_MAMBA_DIR="$HOME/.local/share/pyrmd-miniforge"

# --- Helper Functions (same names/style as installer) ---
log_info()    { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
log_error()   { echo -e "${RED}[ERROR]${NC} $1" >&2; }

# ==============================================================================
# STEP 1: HEADER & CONFIRMATION
# ==============================================================================
echo -e "${BLUE}======================================================${NC}"
echo -e "${BLUE}       PyRMD Studio Uninstaller                       ${NC}"
echo -e "${BLUE}======================================================${NC}"
echo ""

# Verify there is something to remove
if [[ ! -d "$INSTALL_DIR" ]]; then
    log_warning "$APP_NAME installation not found at: $INSTALL_DIR"
    echo "Nothing to uninstall."
    exit 0
fi

log_info "Found $APP_NAME installation:"
echo "  - Application files : $INSTALL_DIR"
echo "  - Global command    : $GLOBAL_BIN_DIR/pyrmd_studio"
echo "  - Conda environment : $CONDA_ENV_NAME"
echo "  - Desktop shortcut  : $DESKTOP_FILE_NAME"
if [[ -d "$LOCAL_MAMBA_DIR" ]]; then
    echo "  - Local Miniforge   : $LOCAL_MAMBA_DIR"
fi
echo ""

read -p "Proceed with full uninstallation? (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    log_info "Uninstallation cancelled by user."
    exit 0
fi

echo ""
log_info "Starting $APP_NAME uninstallation..."
echo ""

# ==============================================================================
# STEP 2: REMOVE DESKTOP INTEGRATION
# ==============================================================================
log_info "Removing desktop integration..."

# Remove application menu entry
APP_MENU_FILE="$HOME/.local/share/applications/$DESKTOP_FILE_NAME"
if [[ -f "$APP_MENU_FILE" ]]; then
    rm -f "$APP_MENU_FILE"
    log_success "Removed applications menu entry."
fi

# Remove desktop shortcut (if it was copied there by installer)
DESKTOP_SHORTCUT="$HOME/Desktop/$DESKTOP_FILE_NAME"
if [[ -f "$DESKTOP_SHORTCUT" ]]; then
    rm -f "$DESKTOP_SHORTCUT"
    log_success "Removed desktop shortcut."
fi

# Refresh desktop database
update-desktop-database "$HOME/.local/share/applications" &> /dev/null || true

# ==============================================================================
# STEP 3: REMOVE GLOBAL COMMAND & SYMLINK
# ==============================================================================
log_info "Removing global command 'pyrmd_studio'..."

SYMLINK_PATH="$GLOBAL_BIN_DIR/pyrmd_studio"
if [[ -L "$SYMLINK_PATH" || -f "$SYMLINK_PATH" ]]; then
    rm -f "$SYMLINK_PATH"
    log_success "Removed symlink: $SYMLINK_PATH"
else
    log_warning "Symlink not found (already removed?): $SYMLINK_PATH"
fi

# ==============================================================================
# STEP 4: REMOVE APPLICATION FILES
# ==============================================================================
log_info "Removing application directory: $INSTALL_DIR"

if [[ -d "$INSTALL_DIR" ]]; then
    rm -rf "$INSTALL_DIR"
    log_success "Removed application directory."
else
    log_warning "Application directory not found (already removed?)."
fi

# ==============================================================================
# STEP 5: REMOVE CONDA ENVIRONMENT
# ==============================================================================
log_info "Removing Conda environment '$CONDA_ENV_NAME'..."

# Source local Miniforge first if it exists (installed by this app's installer)
if [[ -f "$LOCAL_MAMBA_DIR/etc/profile.d/conda.sh" ]]; then
    source "$LOCAL_MAMBA_DIR/etc/profile.d/conda.sh"
    source "$LOCAL_MAMBA_DIR/etc/profile.d/mamba.sh" 2>/dev/null || true
fi

CONDA_REMOVED=false

# Prefer mamba for speed, fall back to conda
if command -v mamba &> /dev/null; then
    if conda info --envs 2>/dev/null | grep -q "$CONDA_ENV_NAME"; then
        mamba env remove -n "$CONDA_ENV_NAME" -y
        log_success "Conda environment '$CONDA_ENV_NAME' removed (via mamba)."
        CONDA_REMOVED=true
    fi
elif command -v conda &> /dev/null; then
    if conda info --envs 2>/dev/null | grep -q "$CONDA_ENV_NAME"; then
        conda env remove -n "$CONDA_ENV_NAME" -y
        log_success "Conda environment '$CONDA_ENV_NAME' removed (via conda)."
        CONDA_REMOVED=true
    fi
fi

if [[ "$CONDA_REMOVED" = false ]]; then
    log_warning "Conda environment '$CONDA_ENV_NAME' not found or conda unavailable. Skipping."
fi

# ==============================================================================
# STEP 6: REMOVE LOCAL MINIFORGE (if installed by this app's installer)
# ==============================================================================
if [[ -d "$LOCAL_MAMBA_DIR" ]]; then
    log_info "Removing locally installed Miniforge: $LOCAL_MAMBA_DIR"
    read -p "  Remove standalone Miniforge at '$LOCAL_MAMBA_DIR'? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        rm -rf "$LOCAL_MAMBA_DIR"
        log_success "Removed local Miniforge installation."
    else
        log_info "Keeping local Miniforge installation."
    fi
fi

# ==============================================================================
# STEP 7: CLEAN UP PATH ENTRY FROM SHELL CONFIG
# ==============================================================================
log_info "Cleaning up PATH entry from shell configuration..."

CLEANED_SHELL_CONFIG=false

for SHELL_CONFIG in "$HOME/.bashrc" "$HOME/.zshrc"; do
    if [[ -f "$SHELL_CONFIG" ]] && grep -q "Added by PyRMD Studio Installer" "$SHELL_CONFIG"; then
        # Remove the 3 lines added by the installer (blank line + comment + export)
        sed -i '/^$/N;/\n# Added by PyRMD Studio Installer/!P;D' "$SHELL_CONFIG" 2>/dev/null || \
        grep -v "Added by PyRMD Studio Installer" "$SHELL_CONFIG" | \
        grep -v 'export PATH="\$HOME/.local/bin:\$PATH"' > "${SHELL_CONFIG}.tmp" && \
        mv "${SHELL_CONFIG}.tmp" "$SHELL_CONFIG"
        log_success "Cleaned PATH entry from $SHELL_CONFIG"
        CLEANED_SHELL_CONFIG=true
    fi
done

if [[ "$CLEANED_SHELL_CONFIG" = false ]]; then
    log_info "No PATH entry found in shell configs (or already clean)."
fi

# ==============================================================================
# FINISH
# ==============================================================================
echo ""
echo -e "${BLUE}======================================================${NC}"
echo -e "${GREEN}   UNINSTALLATION COMPLETE!                           ${NC}"
echo -e "${BLUE}======================================================${NC}"
echo ""
echo "Removal Summary:"
echo "----------------"
echo "- Application files  : removed from $INSTALL_DIR"
echo "- Global command     : removed from $GLOBAL_BIN_DIR"
echo "- Desktop shortcut   : removed"
echo "- Conda environment  : $CONDA_ENV_NAME"
echo ""
log_success "$APP_NAME has been successfully removed."
echo "Please restart your terminal to apply PATH changes."
echo ""

# Run main block only when executed directly
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    :  # already running top-level, nothing extra needed
fi

