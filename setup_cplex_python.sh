#!/bin/bash
# setup_cplex_python.sh - Runtime setup for CPLEX Python API

set -e

echo "=== CPLEX Python API Runtime Setup ==="

# Check if already installed
if python3 -c "import cplex" 2>/dev/null; then
    echo "✓ CPLEX Python API already installed"
    exit 0
fi

echo "Setting up CPLEX Python API..."

# Find CPLEX installation
CPLEX_STUDIO_DIR="${CPLEX_STUDIO_DIR:-/opt/ibm/CPLEX_Studio2211}"

if [ ! -d "$CPLEX_STUDIO_DIR" ]; then
    echo "❌ CPLEX Studio not found at: $CPLEX_STUDIO_DIR"
    echo "Looking for CPLEX installation..."
    CPLEX_STUDIO_DIR=$(find /opt -name "*CPLEX_Studio*" -type d 2>/dev/null | head -1)
    if [ -z "$CPLEX_STUDIO_DIR" ]; then
        echo "❌ CPLEX installation not found!"
        exit 1
    fi
    echo "✓ Found CPLEX at: $CPLEX_STUDIO_DIR"
fi

# Navigate to Python API directory
PYTHON_API_DIR="$CPLEX_STUDIO_DIR/cplex/python"
if [ ! -d "$PYTHON_API_DIR" ]; then
    echo "❌ Python API directory not found: $PYTHON_API_DIR"
    exit 1
fi

cd "$PYTHON_API_DIR"
echo "📂 Changed to: $PYTHON_API_DIR"

# Detect Python version
PYTHON_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
echo "🐍 Python version: $PYTHON_VERSION"

# Find matching Python version directory
PYTHON_DIR=""
for dir in *; do
    if [[ -d "$dir" && "$dir" == *"$PYTHON_VERSION"* ]]; then
        PYTHON_DIR="$dir"
        break
    fi
done

# If no exact match, try any available version
if [ -z "$PYTHON_DIR" ]; then
    echo "⚠️  No exact Python version match, trying available versions..."
    for dir in */; do
        if [ -f "$dir/setup.py" ]; then
            PYTHON_DIR="$dir"
            echo "📁 Using: $PYTHON_DIR"
            break
        fi
    done
fi

if [ -z "$PYTHON_DIR" ] || [ ! -d "$PYTHON_DIR" ]; then
    echo "❌ No compatible Python directory found"
    echo "Available directories:"
    ls -la
    exit 1
fi

# Navigate to the Python version directory
cd "$PYTHON_DIR"
echo "📂 Using Python API directory: $PYTHON_DIR"

# Check for setup.py
if [ ! -f "setup.py" ]; then
    echo "❌ setup.py not found in $PWD"
    exit 1
fi

# Install CPLEX Python API
echo "🔧 Installing CPLEX Python API..."
python3 setup.py install

# Verify installation
echo "✅ Testing CPLEX installation..."
if python3 -c "import cplex; print('CPLEX version:', cplex.Cplex().get_version())" 2>/dev/null; then
    echo "🎉 CPLEX Python API successfully installed!"
else
    echo "❌ CPLEX Python API installation failed!"
    exit 1
fi

# Test with Pyomo if available
if python3 -c "import pyomo" 2>/dev/null; then
    echo "🔧 Testing Pyomo integration..."
    if python3 -c "from pyomo.opt import SolverFactory; print('CPLEX available in Pyomo:', SolverFactory('cplex').available())" 2>/dev/null; then
        echo "🎉 Pyomo-CPLEX integration working!"
    else
        echo "⚠️  Pyomo-CPLEX integration may need configuration"
    fi
fi

echo "=== Setup Complete ==="