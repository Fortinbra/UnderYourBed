#!/bin/bash
# Setup script for servo testing on Raspberry Pi

echo "Setting up servo test environment..."

# Check if we're on a Raspberry Pi
if [ ! -f /proc/device-tree/model ] || ! grep -q "Raspberry Pi" /proc/device-tree/model; then
    echo "Warning: This doesn't appear to be a Raspberry Pi"
fi

# Enable I2C if not already enabled
if ! grep -q "dtparam=i2c_arm=on" /boot/firmware/config.txt 2>/dev/null && 
   ! grep -q "dtparam=i2c_arm=on" /boot/config.txt 2>/dev/null; then
    echo "I2C may not be enabled. Please run 'sudo raspi-config' and enable I2C under Interface Options."
fi

# Install Python dependencies in virtual environment
echo "Creating virtual environment..."
python3 -m venv servo_env

echo "Installing Python dependencies in virtual environment..."
source servo_env/bin/activate
pip install -r requirements-runtime.txt

# Check I2C devices
echo "Checking I2C devices..."
if command -v i2cdetect >/dev/null 2>&1; then
    echo "I2C devices detected:"
    i2cdetect -y 1
    
    # Check for servo HAT (usually at address 0x40)
    if i2cdetect -y 1 | grep -q "40"; then
        echo "✓ Servo HAT detected at address 0x40"
    else
        echo "⚠️  Servo HAT not detected at expected address 0x40"
        echo "   Check connections and power supply"
    fi
else
    echo "Installing i2c-tools..."
    sudo apt-get update
    sudo apt-get install -y i2c-tools
fi

echo ""
echo "Setup complete! You can now run:"
echo "  cd runtime && source servo_env/bin/activate"
echo "  python3 servo_test.py            # Test all channels"
echo "  python3 servo_test.py --quick    # Quick test"
echo "  python3 servo_test.py --help     # See all options"
