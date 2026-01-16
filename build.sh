#!/usr/bin/env bash
# Build script for Render - installs Stockfish

set -e

# Install Python dependencies
pip install -r requirements.txt

# Download and install Stockfish
echo "Installing Stockfish..."
STOCKFISH_VERSION="stockfish-ubuntu-x86-64-avx2"
STOCKFISH_URL="https://github.com/official-stockfish/Stockfish/releases/download/sf_17/${STOCKFISH_VERSION}.tar"

# Create bin directory
mkdir -p $HOME/bin

# Download and extract Stockfish
curl -L $STOCKFISH_URL -o stockfish.tar
tar -xf stockfish.tar
mv ${STOCKFISH_VERSION}/stockfish-ubuntu-x86-64-avx2 $HOME/bin/stockfish
chmod +x $HOME/bin/stockfish
rm -rf stockfish.tar ${STOCKFISH_VERSION}

echo "Stockfish installed at $HOME/bin/stockfish"
$HOME/bin/stockfish --version || echo "Stockfish ready"

