#!/bin/bash
# Vedic Astrology Calculator — quick setup (not generalized, just this repo)
set -euo pipefail

VENV=".venv"
PIP="$VENV/bin/pip"
PYTHON="$VENV/bin/python"

echo "==> Creating venv..."
python3 -m venv "$VENV" 2>/dev/null || true

echo "==> Installing essential pip packages (pyswisseph)..."
"$PIP" install --quiet pyswisseph>=2.10.3.2

echo "==> Checking tkinter..."
"$PYTHON" -c "import tkinter" || { echo "Install python3-tk"; exit 1; }

echo "==> Writing minimal Ollama Modelfile (local, small-footprint)..."
mkdir -p models
cat > models/Modelfile << 'EOF'
FROM phi3:latest
PARAMETER temperature 0.3
PARAMETER num_ctx 2048
EOF

echo "==> Setup complete. Launch with: ./run.sh  or  .venv/bin/python main.py"
echo "==> For AI tab: ollama create vedic:local -f models/Modelfile  &&  ollama serve"
