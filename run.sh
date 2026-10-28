#!/usr/bin/env bash
# Vedic Astrology Calculator v6.0 - Run Script
# Usage: ./run.sh [--install] [--test] [--run] [--help]

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_ROOT"

VENV_DIR="$PROJECT_ROOT/.venv"
PYTHON_BIN="$VENV_DIR/bin/python"
PIP_BIN="$VENV_DIR/bin/pip"

ensure_venv() {
    if [[ ! -f "$PYTHON_BIN" ]]; then
        echo "Creating virtual environment at $VENV_DIR..."
        python3 -m venv "$VENV_DIR"
    fi
}

check_tkinter() {
    if ! "$PYTHON_BIN" -c "import tkinter" &>/dev/null; then
        echo ""
        echo "=================================================================="
        echo " Error: Tkinter runtime library (libtk8.6.so) is not found!"
        echo "=================================================================="
        echo " Tkinter is required for the desktop GUI."
        echo " Please install the Tk package using your system package manager:"
        echo ""
        echo "   Arch Linux / Manjaro:   sudo pacman -S tk"
        echo "   Ubuntu / Debian / Mint: sudo apt install python3-tk"
        echo "   Fedora / RHEL:          sudo dnf install python3-tkinter"
        echo "   openSUSE:               sudo zypper in python3-tk tk"
        echo "=================================================================="
        echo ""
        exit 1
    fi
}

show_help() {
    cat <<EOF
Vedic Astrology Calculator v6.0 — Run Script

Usage: ./run.sh [OPTION]

Options:
    --install     Setup venv, install Python dependencies (pyswisseph)
    --test        Run unit test suite
    --run         Launch the application (default)
    --help        Show this help

Examples:
    ./run.sh              # Launch the app (auto-initializes .venv if needed)
    ./run.sh --install    # Install/update dependencies then launch
    ./run.sh --test       # Run unit tests
EOF
}

install_deps() {
    ensure_venv
    echo "Installing Python dependencies into virtual environment..."
    "$PIP_BIN" install -r requirements.txt
    echo "Dependencies successfully installed."
}

run_tests() {
    ensure_venv
    echo "Running unit test suite..."
    "$PYTHON_BIN" -m unittest discover tests -v
}

run_app() {
    ensure_venv
    check_tkinter
    echo "Starting Vedic Astrology Calculator..."
    "$PYTHON_BIN" main.py
}

# Main
case "${1:-}" in
    --install)
        install_deps
        run_app
        ;;
    --test)
        run_tests
        ;;
    --run|"")
        run_app
        ;;
    --help|-h)
        show_help
        ;;
    *)
        echo "Unknown option: $1"
        show_help
        exit 1
        ;;
esac
