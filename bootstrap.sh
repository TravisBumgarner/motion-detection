#!/bin/bash
#
# Bootstrap script for motion-cam
# Sets up a motion-activated camera system on Raspberry Pi
#
# Usage: sudo ./bootstrap.sh
#
# This script is idempotent - safe to run multiple times.

set -e

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_DIR="/etc/motion-cam"
ENV_FILE="${CONFIG_DIR}/.env"
ENV_EXAMPLE="${SCRIPT_DIR}/config/.env.example"
SERVICE_TEMPLATE="${SCRIPT_DIR}/systemd/motion-cam.service"
SERVICE_FILE="/etc/systemd/system/motion-cam.service"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if running as root
check_root() {
    if [[ $EUID -ne 0 ]]; then
        log_error "This script must be run as root (use sudo)"
        echo "  Usage: sudo ./bootstrap.sh"
        exit 1
    fi
}

# Install system dependencies
install_system_deps() {
    log_info "Installing system dependencies..."
    apt-get update -qq
    apt-get install -y python3 python3-pip python3-venv ffmpeg
    log_info "System dependencies installed"
}

# Create virtual environment and install Python dependencies
setup_venv() {
    log_info "Setting up Python virtual environment..."

    if [[ ! -d "${SCRIPT_DIR}/.venv" ]]; then
        python3 -m venv "${SCRIPT_DIR}/.venv"
        log_info "Virtual environment created"
    else
        log_info "Virtual environment already exists"
    fi

    "${SCRIPT_DIR}/.venv/bin/pip" install --upgrade pip -q
    "${SCRIPT_DIR}/.venv/bin/pip" install -r "${SCRIPT_DIR}/requirements.txt" -q

    log_info "Python dependencies installed"
}

# Create config directory and .env file
setup_config() {
    log_info "Setting up configuration..."

    mkdir -p "${CONFIG_DIR}"
    chmod 755 "${CONFIG_DIR}"

    if [[ -f "${ENV_FILE}" ]]; then
        log_info "Config file already exists at ${ENV_FILE}, skipping"
        return
    fi

    if [[ -t 0 ]]; then
        # Interactive mode: prompt for each variable
        log_info "Interactive configuration (press Enter to accept defaults)"
        echo ""

        local tmp_env
        tmp_env=$(mktemp)

        while IFS= read -r line; do
            # Pass through comments and blank lines
            if [[ "$line" =~ ^#.*$ ]] || [[ -z "$line" ]]; then
                echo "$line" >> "$tmp_env"
                continue
            fi

            # Parse KEY=VALUE
            local key="${line%%=*}"
            local default_val="${line#*=}"

            read -r -p "  ${key} [${default_val}]: " user_val
            if [[ -n "$user_val" ]]; then
                echo "${key}=${user_val}" >> "$tmp_env"
            else
                echo "${key}=${default_val}" >> "$tmp_env"
            fi
        done < "${ENV_EXAMPLE}"

        mv "$tmp_env" "${ENV_FILE}"
        echo ""
        log_info "Configuration saved to ${ENV_FILE}"
    else
        # Non-interactive: copy example and warn
        cp "${ENV_EXAMPLE}" "${ENV_FILE}"
        log_warn "Non-interactive mode: copied .env.example to ${ENV_FILE}"
        log_warn "Edit ${ENV_FILE} to customize settings"
    fi

    chmod 600 "${ENV_FILE}"
}

# Ensure invoking user is in the video group for camera access
setup_video_group() {
    if [[ -n "${SUDO_USER}" ]]; then
        if id -nG "${SUDO_USER}" | grep -qw video; then
            log_info "User ${SUDO_USER} is already in the video group"
        else
            usermod -aG video "${SUDO_USER}"
            log_info "Added ${SUDO_USER} to the video group"
        fi
    else
        log_warn "SUDO_USER not set, skipping video group setup"
    fi
}

# Create data directory
setup_data_dir() {
    # Read data dir from config, or use default
    local data_dir
    if [[ -f "${ENV_FILE}" ]]; then
        data_dir=$(grep -E "^STORAGE_DATA_DIR=" "${ENV_FILE}" | cut -d'=' -f2-)
    fi

    if [[ -z "${data_dir}" ]]; then
        data_dir="/home/${SUDO_USER:-pi}/motion-cam-data"
    fi

    if [[ ! -d "${data_dir}" ]]; then
        mkdir -p "${data_dir}"
        if [[ -n "${SUDO_USER}" ]]; then
            chown "${SUDO_USER}:${SUDO_USER}" "${data_dir}"
        fi
        log_info "Data directory created at ${data_dir}"
    else
        log_info "Data directory already exists at ${data_dir}"
    fi
}

# Install systemd service
setup_systemd() {
    log_info "Installing systemd service..."

    sed "s|{{INSTALL_DIR}}|${SCRIPT_DIR}|g" "${SERVICE_TEMPLATE}" > "${SERVICE_FILE}"

    systemctl daemon-reload
    systemctl enable motion-cam

    log_info "Systemd service installed and enabled"
}

# Print completion message
print_success() {
    local hostname
    hostname=$(hostname 2>/dev/null || echo "raspberrypi")
    local port
    if [[ -f "${ENV_FILE}" ]]; then
        port=$(grep -E "^WEB_PORT=" "${ENV_FILE}" | cut -d'=' -f2-)
    fi
    port="${port:-8080}"

    echo ""
    echo "=========================================="
    log_info "Bootstrap complete!"
    echo "=========================================="
    echo ""
    echo "Next steps:"
    echo "  Start the service:"
    echo "    sudo systemctl start motion-cam"
    echo ""
    echo "  View logs:"
    echo "    sudo journalctl -u motion-cam -f"
    echo ""
    echo "  Web portal:"
    echo "    http://${hostname}:${port}"
    echo ""
    echo "  Edit config:"
    echo "    sudo nano ${ENV_FILE}"
    echo "    sudo systemctl restart motion-cam"
    echo ""
}

# Main
main() {
    echo ""
    echo "=========================================="
    echo "  motion-cam Bootstrap Script"
    echo "=========================================="
    echo ""
    log_info "Installing from: ${SCRIPT_DIR}"
    echo ""

    check_root
    install_system_deps
    setup_venv
    setup_config
    setup_video_group
    setup_data_dir
    setup_systemd
    print_success
}

main "$@"
