#!/bin/bash
# UnderYourBed Animatronic - Environment Verification Script
# Run this to verify your setup is working correctly

echo "=== UnderYourBed Environment Verification ==="

# Check Python virtual environment
if [ ! -d ".venv" ]; then
    echo "❌ Python virtual environment not found"
    echo "   Run: ./setup_python.sh"
    exit 1
else
    echo "✅ Python virtual environment found"
fi

# Check if virtual environment is activated
if [[ "$VIRTUAL_ENV" != *"UnderYourBed-1/.venv" ]]; then
    echo "⚠️  Virtual environment not activated"
    echo "   Run: source .venv/bin/activate"
else
    echo "✅ Virtual environment activated"
fi

# Check required Python packages
echo ""
echo "Checking Python packages..."
source .venv/bin/activate

packages=("pygame" "sounddevice" "adafruit_servokit")
for package in "${packages[@]}"; do
    if python -c "import ${package}" 2>/dev/null; then
        echo "✅ $package installed"
    else
        echo "❌ $package missing"
        echo "   Run: pip install -r requirements-minimal.txt"
    fi
done

# Check system dependencies
echo ""
echo "Checking system dependencies..."

commands=("ffmpeg" "aplay" "i2cdetect")
for cmd in "${commands[@]}"; do
    if command -v $cmd &> /dev/null; then
        echo "✅ $cmd available"
    else
        echo "❌ $cmd missing"
        echo "   Run: ./setup_system.sh"
    fi
done

# Check I2C interface
echo ""
echo "Checking I2C interface..."
if [ -e "/dev/i2c-1" ]; then
    echo "✅ I2C interface enabled"
    
    # Check for Servo HAT (optional)
    if i2cdetect -y 1 2>/dev/null | grep -q "40"; then
        echo "✅ Servo HAT detected at address 0x40"
    else
        echo "⚠️  Servo HAT not detected (may be running in simulation mode)"
    fi
else
    echo "❌ I2C interface disabled"
    echo "   Run: sudo raspi-config -> Interface Options -> I2C -> Enable"
    echo "   Then reboot"
fi

# Check USB audio device
echo ""
echo "Checking USB audio device..."
if aplay -l 2>/dev/null | grep -q "USB Audio"; then
    echo "✅ USB Audio Device detected"
else
    echo "⚠️  USB Audio Device not found"
    echo "   Connect USB audio device to continue"
fi

# Check content files
echo ""
echo "Checking content files..."
if [ -f "bundles/G-YNNJIe2Vk_20250904-030059/original.m4a" ]; then
    echo "✅ Audio file found"
else
    echo "❌ Audio file missing"
fi

if [ -f "bundles/G-YNNJIe2Vk_20250904-030059/song.lipsync.json" ]; then
    echo "✅ Lipsync data found"
else
    echo "❌ Lipsync data missing"
fi

echo ""
echo "=== Verification Complete ==="
echo ""
echo "To run the animatronic:"
echo "  source .venv/bin/activate"
echo "  python main.py"
echo ""