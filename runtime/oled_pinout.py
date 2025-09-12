#!/usr/bin/env python3
"""
SSD1351 OLED Display Connection Guide for Raspberry Pi 5

This guide shows how to connect 128x128 RGB OLED displays (SSD1351) to your Raspberry Pi 5.
The displays use SPI communication and each needs a separate Chip Select (CS) pin.

OLED Display Pinout (typical SSD1351 module):
- VCC/3V3: 3.3V power
- GND: Ground  
- SCL/SCK: SPI Clock
- SDA/MOSI: SPI Data (Master Out Slave In)
- RES/RST: Reset pin
- DC: Data/Command pin  
- CS: Chip Select (different for each display)

Raspberry Pi 5 SPI Pins:
- Pin 1:  3.3V Power
- Pin 6:  Ground
- Pin 19: GPIO 10 (MOSI/SDA) 
- Pin 23: GPIO 11 (SCLK/SCL)
- Pin 24: GPIO 8 (CE0) - First CS pin
- Pin 26: GPIO 7 (CE1) - Second CS pin  
- Pin 22: GPIO 25 - Can use for Reset
- Pin 18: GPIO 24 - Can use for DC

CONNECTION DIAGRAM:

First OLED (Left Eye):
OLED Pin    -> Raspberry Pi Pin
VCC/3V3     -> Pin 1 (3.3V)
GND         -> Pin 6 (Ground)  
SCL/SCK     -> Pin 23 (GPIO 11, SCLK)
SDA/MOSI    -> Pin 19 (GPIO 10, MOSI)
RES/RST     -> Pin 22 (GPIO 25)
DC          -> Pin 18 (GPIO 24) 
CS          -> Pin 24 (GPIO 8, CE0) <- This is CS device 0

Second OLED (Right Eye):  
OLED Pin    -> Raspberry Pi Pin
VCC/3V3     -> Pin 1 (3.3V)
GND         -> Pin 6 (Ground)
SCL/SCK     -> Pin 23 (GPIO 11, SCLK) 
SDA/MOSI    -> Pin 19 (GPIO 10, MOSI)
RES/RST     -> Pin 22 (GPIO 25) [shared]
DC          -> Pin 18 (GPIO 24) [shared]
CS          -> Pin 26 (GPIO 7, CE1) <- This is CS device 1

IMPORTANT NOTES:
1. Both displays share the same SPI bus (SCK, MOSI, RST, DC)
2. Each display needs its own CS (Chip Select) pin
3. The code uses device=0 for left eye (CE0/GPIO 8) and device=1 for right eye (CE1/GPIO 7)
4. Make sure SPI is enabled: sudo raspi-config -> Interface Options -> SPI -> Enable

POWER REQUIREMENTS:
- Each SSD1351 display typically draws 20-50mA
- Pi 5's 3.3V rail can handle both displays easily
- Use short wires for stable connections

TESTING COMMAND:
python3 playback.py --frames ../bundles/G-YNNJIe2Vk_20250904-030059/song.lipsync.json --audio /dev/null --servo-channel 0 --eyes --left-cs 0 --right-cs 1
"""

def print_pinout():
    print("🔌 SSD1351 OLED Connection Guide for Raspberry Pi 5")
    print("=" * 60)
    print()
    print("📋 First OLED (Left Eye) - CS Device 0:")
    print("  VCC/3V3  -> Pin 1  (3.3V)")
    print("  GND      -> Pin 6  (Ground)")
    print("  SCL/SCK  -> Pin 23 (GPIO 11, SCLK)")
    print("  SDA/MOSI -> Pin 19 (GPIO 10, MOSI)")
    print("  RES/RST  -> Pin 22 (GPIO 25)")
    print("  DC       -> Pin 18 (GPIO 24)")
    print("  CS       -> Pin 24 (GPIO 8, CE0)  ⚠️  DEVICE 0")
    print()
    print("📋 Second OLED (Right Eye) - CS Device 1:")
    print("  VCC/3V3  -> Pin 1  (3.3V)")
    print("  GND      -> Pin 6  (Ground)")
    print("  SCL/SCK  -> Pin 23 (GPIO 11, SCLK)")
    print("  SDA/MOSI -> Pin 19 (GPIO 10, MOSI)")
    print("  RES/RST  -> Pin 22 (GPIO 25) [shared]")
    print("  DC       -> Pin 18 (GPIO 24) [shared]")
    print("  CS       -> Pin 26 (GPIO 7, CE1)   ⚠️  DEVICE 1")
    print()
    print("⚙️  Setup Requirements:")
    print("  1. Enable SPI: sudo raspi-config -> Interface Options -> SPI")
    print("  2. Install luma.oled: pip install luma.oled")
    print("  3. Connect displays as shown above")
    print()
    print("🧪 Test Command:")
    print("  python3 oled_test.py")
    

if __name__ == "__main__":
    print_pinout()
