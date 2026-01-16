#!/usr/bin/env bash
# Build script for Render - installs Stockfish

set -e

# Install Python dependencies
pip install -r requirements.txt

# Download and install Stockfish
echo "=== Installing Stockfish ==="

# Create bin directories
mkdir -p ./bin
mkdir -p $HOME/bin

# Download Stockfish Linux binary
echo "Downloading Stockfish..."
curl -L "https://github.com/official-stockfish/Stockfish/releases/download/sf_16.1/stockfish-ubuntu-x86-64.tar" -o stockfish.tar

echo "Extracting..."
tar -xvf stockfish.tar

echo "=== Finding Stockfish binary ==="
echo "All files extracted:"
find . -name "*stockfish*" -type f 2>/dev/null

# Find the actual binary (it's the large executable file)
STOCKFISH_BIN=$(find . -name "*stockfish*" -type f ! -name "*.tar" ! -name "*.sh" ! -name "*.py" ! -name "*.txt" 2>/dev/null | head -1)

echo "Found binary at: $STOCKFISH_BIN"

if [ -n "$STOCKFISH_BIN" ] && [ -f "$STOCKFISH_BIN" ]; then
    cp "$STOCKFISH_BIN" ./bin/stockfish
    chmod +x ./bin/stockfish
    cp "$STOCKFISH_BIN" $HOME/bin/stockfish
    chmod +x $HOME/bin/stockfish
    echo "=== Stockfish installed successfully ==="
else
    echo "=== ERROR: Could not find Stockfish binary ==="
    echo "Trying alternative: fairy-stockfish from pip..."
    pip install fairy-stockfish
    FAIRY_PATH=$(python -c "import fairy_stockfish; print(fairy_stockfish.STOCKFISH_PATH)" 2>/dev/null || echo "")
    if [ -n "$FAIRY_PATH" ]; then
        cp "$FAIRY_PATH" ./bin/stockfish
        chmod +x ./bin/stockfish
    fi
fi

# Cleanup
rm -rf stockfish.tar stockfish-*/ 2>/dev/null || true

echo "=== Final check ==="
ls -la ./bin/
./bin/stockfish quit 2>/dev/null && echo "Stockfish is working!" || echo "Warning: Stockfish test failed"

