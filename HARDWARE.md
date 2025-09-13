# Hardware Setup Guide

## Required Hardware

### Core Components
- **Raspberry Pi 4** (or newer) with Raspberry Pi OS
- **Adafruit 16-Channel PWM/Servo HAT** for Raspberry Pi
- **USB Audio Device** (for high-quality audio output)
- **Servo Motor** (standard 180° servo for mouth movement)
- **MicroSD Card** (32GB+ recommended)

### Optional Components (for future expansion)
- **2x SPI OLED Displays** (for eyes)
- **Speakers/Amplifier** (if not using USB audio device)

## Hardware Connections

### Servo HAT Setup
1. **Mount the HAT**: Stack the Adafruit Servo HAT on top of your Raspberry Pi
2. **I2C Connection**: The HAT uses I2C interface (automatically connected when stacked)
3. **Power the HAT**: Connect 5V power supply to the HAT's power terminals
   - **Red wire**: +5V (center terminal)
   - **Black wire**: Ground (outer terminal)
   - **Recommended**: 5V 4A power supply for reliable servo operation

### Servo Connection
1. **Servo Channel**: Connect your mouth servo to **Channel 0** on the HAT
2. **Servo Wiring**:
   - **Red wire**: Power (connects to servo HAT power rail)
   - **Brown/Black wire**: Ground (connects to servo HAT ground rail)
   - **Orange/Yellow wire**: Signal (connects to Channel 0 signal pin)

### USB Audio Device
1. **USB Port**: Connect USB audio device to any available USB port
2. **Audio Output**: Connect speakers or headphones to the USB audio device
3. **Verification**: The device should appear as "USB Audio Device" in `aplay -l`

## I2C Configuration

### Enable I2C
```bash
sudo raspi-config
# Navigate to: Interface Options > I2C > Enable
```

### Verify I2C Connection
```bash
# Check if Servo HAT is detected (should show device at address 0x40)
i2cdetect -y 1
```

Expected output:
```
     0  1  2  3  4  5  6  7  8  9  a  b  c  d  e  f
00:          -- -- -- -- -- -- -- -- -- -- -- -- --
10: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
20: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
30: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
40: 40 -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
50: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
60: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
70: 70 -- -- -- -- -- -- --
```

## Power Requirements

### Servo HAT Power
- **Voltage**: 5V DC
- **Current**: 4A minimum (for multiple servos)
- **Important**: The Raspberry Pi's 5V pin cannot provide enough current for servos

### Raspberry Pi Power
- **Standard**: Use official Raspberry Pi power supply (5V 3A)
- **Alternative**: Power through GPIO if using high-current 5V supply

## Troubleshooting

### Common Issues

**Servo not moving**:
- Check 5V power supply to servo HAT
- Verify I2C is enabled: `sudo raspi-config`
- Check I2C connection: `i2cdetect -y 1`

**Audio not working**:
- Check USB audio device: `aplay -l`
- Test audio: `speaker-test -D hw:0,0 -t wav`

**I2C errors**:
- Enable I2C interface in raspi-config
- Check physical connections
- Reboot after enabling I2C

## Safety Notes

⚠️ **Important Safety Information**:
- Always connect servo HAT power supply before connecting servos
- Use appropriate power supply (5V 4A) for servo HAT
- Never connect servo power directly to Raspberry Pi GPIO pins
- Double-check wiring before powering on

## Testing Hardware

### Test Servo Movement
```bash
# Run the servo controller test
cd /home/fortinbra/UnderYourBed-1
source .venv/bin/activate
python src/servo_controller.py
```

### Test Audio Playback
```bash
# Test USB audio device
aplay -D hw:0,0 /usr/share/sounds/alsa/Front_Left.wav
```