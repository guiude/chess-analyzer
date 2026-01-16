#!/usr/bin/env bash
# Build script for Render - installs Stockfish

set -e

# Install Python dependencies
pip install -r requirements.txt

# Download and install Stockfish
echo "=== Installing Stockfish ==="

# Create bin directory in the project (persists between builds)
mkdir -p ./bin

# Download Stockfish Linux binary (non-AVX2 version for compatibility)
echo "Downloading Stockfish..."
curl -L "https://github.com/official-stockfish/Stockfish/releases/download/sf_16.1/stockfish-ubuntu-x86-64.tar" -o stockfish.tar

echo "Extracting..."
tar -xvf stockfish.tar

echo "Contents after extraction:"
ls -la
ls -la stockfish-ubuntu-x86-64/ || true

# Move the binary
cp stockfish-ubuntu-x86-64/stockfish-ubuntu-x86-64 ./bin/stockfish
chmod +x ./bin/stockfish

# Also copy to home bin
mkdir -p $HOME/bin
cp ./bin/stockfish $HOME/bin/stockfish
chmod +x $HOME/bin/stockfish

# Cleanup
rm -rf stockfish.tar stockfish-ubuntu-x86-64

echo "=== Stockfish Installation Complete ==="
echo "Checking ./bin/stockfish:"
ls -la ./bin/
echo "Checking ~/bin/stockfish:"
ls -la $HOME/bin/

# Test stockfish
echo "Testing Stockfish..."
./bin/stockfish quit || echo "Stockfish test completed"

