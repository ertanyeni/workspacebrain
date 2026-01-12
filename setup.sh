#!/bin/bash
# Setup script for WorkspaceBrain development environment

set -e

echo "🚀 Setting up WorkspaceBrain development environment..."

# Check Python version
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3.9 or higher."
    exit 1
fi

PYTHON_VERSION=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2)
echo "✓ Found Python $PYTHON_VERSION"

# Create virtual environment if it doesn't exist
if [ ! -d ".venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv .venv
    echo "✓ Virtual environment created"
else
    echo "✓ Virtual environment already exists"
fi

# Activate virtual environment
echo "🔌 Activating virtual environment..."
source .venv/bin/activate

# Upgrade pip
echo "⬆️  Upgrading pip..."
pip install --upgrade pip --quiet

# Install project in development mode
echo "📥 Installing WorkspaceBrain in development mode..."
pip install -e ".[dev]" --quiet

# Verify installation
echo "✅ Verifying installation..."
if wbrain --version &> /dev/null; then
    echo "✓ WorkspaceBrain installed successfully!"
    echo ""
    echo "You can now use:"
    echo "  wbrain --help"
    echo "  wbrain --version"
    echo ""
    echo "To activate the virtual environment in the future:"
    echo "  source .venv/bin/activate"
else
    echo "❌ Installation verification failed"
    exit 1
fi
