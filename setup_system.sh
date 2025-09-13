#!/bin/bash
# UnderYourBed Animatronic Project - System Setup Script
# Run this script to install all required system dependencies

set -e

echo "=== UnderYourBed Animatronic Setup ==="
echo "Installing system dependencies..."

# Update package list
echo "Updating package list..."
sudo apt-get update

# Install audio dependencies
echo "Installing audio dependencies..."
sudo apt-get install -y \
    portaudio19-dev \
    ffmpeg \
    alsa-utils

# Install I2C tools for servo HAT
echo "Installing I2C tools..."
sudo apt-get install -y \
    i2c-tools \
    python3-dev \
    python3-pip \
    python3-venv

# Enable I2C interface
echo "Enabling I2C interface..."
sudo raspi-config nonint do_i2c 0

# Install GPIO library dependencies
echo "Installing GPIO dependencies..."
sudo apt-get install -y \
    libgpiod-dev \
    gpiod

echo ""
echo "=== System Setup Complete ==="
echo ""
echo "Next steps:"
echo "1. Reboot your Raspberry Pi: sudo reboot"
echo "2. After reboot, run: ./setup_python.sh"
echo "3. Connect your hardware (USB audio, Servo HAT)"
echo "4. Run: python3 main.py"
echo ""

# Check if I2C is working
echo "Testing I2C interface..."
if command -v i2cdetect &> /dev/null; then
    echo "I2C tools installed successfully"
    echo "After reboot, you can check connected I2C devices with: i2cdetect -y 1"
else
    echo "Warning: I2C tools installation may have failed"
fi

echo "Setup script completed!"