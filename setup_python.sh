#!/bin/bash
# UnderYourBed Animatronic Project - Python Environment Setup
# Run this script after system setup to create Python environment

set -e

echo "=== Python Environment Setup ==="

# Create virtual environment
echo "Creating Python virtual environment..."
python3 -m venv .venv

# Activate virtual environment
echo "Activating virtual environment..."
source .venv/bin/activate

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip

# Install Python dependencies
echo "Installing Python dependencies..."
pip install -r requirements-minimal.txt

echo ""
echo "=== Python Setup Complete ==="
echo ""
echo "To activate the environment:"
echo "  source .venv/bin/activate"
echo ""
echo "To run the animatronic:"
echo "  python main.py"
echo ""
echo "To deactivate when done:"
echo "  deactivate"
echo ""