#!/usr/bin/env bash
# Build script for Render - installs Stockfish

set -e

# Install Python dependencies
pip install -r requirements.txt

# Download and install Stockfish
echo "Installing Stockfish..."

# Create bin directory
mkdir -p $HOME/bin

# Download Stockfish Linux binary
STOCKFISH_URL="https://github.com/official-stockfish/Stockfish/releases/download/sf_16.1/stockfish-ubuntu-x86-64-avx2.tar"

curl -L $STOCKFISH_URL -o stockfish.tar
tar -xvf stockfish.tar

# Find and move the stockfish binary (handles different archive structures)
find . -name "stockfish*" -type f -executable -exec mv {} $HOME/bin/stockfish \; 2>/dev/null || \
find . -name "stockfish*" -type f ! -name "*.tar" -exec mv {} $HOME/bin/stockfish \; 2>/dev/null || \
mv stockfish-ubuntu-x86-64-avx2/stockfish-ubuntu-x86-64-avx2 $HOME/bin/stockfish 2>/dev/null || \
mv stockfish-ubuntu-x86-64-avx2/stockfish $HOME/bin/stockfish 2>/dev/null || \
mv stockfish $HOME/bin/stockfish 2>/dev/null

chmod +x $HOME/bin/stockfish

# Cleanup
rm -rf stockfish.tar stockfish-*

echo "Stockfish installed at $HOME/bin/stockfish"
ls -la $HOME/bin/

