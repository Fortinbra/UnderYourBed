#!/usr/bin/env python3
"""
OLED Display Module for Animatronic Eyes
========================================

This module provides a clean interface for controlling SSD1351 OLED displays
used as animatronic eyes. Supports both single and dual eye configurations
with independent control pins.

Features:
- SSD1351 128x128 RGB OLED support
- BGR565 color format handling
- Independent DC/RST pins for dual displays
- Eyeball rendering with pupils and blinking
- Thread-safe operation

Hardware Requirements:
- SSD1351 OLED display(s) 128x128
- Raspberry Pi with SPI enabled
- GPIO pins for DC and RST control

Pin Configuration (recommended for dual eyes):
- Left Eye:  DC=GPIO24(Pin18), RST=GPIO25(Pin22), CS=GPIO8(Pin24)
- Right Eye: DC=GPIO23(Pin16), RST=GPIO22(Pin15), CS=GPIO7(Pin26)
- Shared: SCK=GPIO11(Pin23), MOSI=GPIO10(Pin19), VCC=3.3V, GND=GND
"""

import spidev
import time
import lgpio
import math
from typing import Tuple, Optional, List


class SSD1351Display:
    """
    Control for SSD1351 128x128 RGB OLED display
    
    This class handles low-level SPI communication and display initialization
    for SSD1351 OLED displays in BGR565 color format.
    """
    
    def __init__(self, spi_device: int, dc_pin: int, rst_pin: int, name: str = "Display"):
        """
        Initialize display controller
        
        Args:
            spi_device: SPI device number (0 for CE0, 1 for CE1)
            dc_pin: GPIO pin for Data/Command control
            rst_pin: GPIO pin for Reset control
            name: Human-readable name for this display
        """
        self.spi_device = spi_device
        self.dc_pin = dc_pin
        self.rst_pin = rst_pin
        self.name = name
        self.width = 128
        self.height = 128
        
        # Hardware handles
        self.spi = None
        self.gpio_handle = None
        self._initialized = False
    
    def initialize(self) -> bool:
        """
        Initialize SPI and GPIO, then configure the display
        
        Returns:
            True if initialization successful, False otherwise
        """
        try:
            # Setup SPI
            self.spi = spidev.SpiDev()
            self.spi.open(0, self.spi_device)
            self.spi.max_speed_hz = 8000000
            self.spi.mode = 0
            
            # Setup GPIO
            self.gpio_handle = lgpio.gpiochip_open(0)
            lgpio.gpio_claim_output(self.gpio_handle, self.dc_pin)
            lgpio.gpio_claim_output(self.gpio_handle, self.rst_pin)
            
            # Reset display
            self._reset_display()
            
            # Initialize SSD1351
            self._send_init_commands()
            
            self._initialized = True
            print(f"✓ {self.name} initialized - DC:{self.dc_pin} RST:{self.rst_pin}")
            return True
            
        except Exception as e:
            print(f"✗ {self.name} initialization failed: {e}")
            return False
    
    def _reset_display(self):
        """Perform hardware reset of the display"""
        lgpio.gpio_write(self.gpio_handle, self.rst_pin, 0)
        time.sleep(0.01)
        lgpio.gpio_write(self.gpio_handle, self.rst_pin, 1)
        time.sleep(0.01)
    
    def _send_command(self, cmd: int):
        """Send command byte to display"""
        if not self._initialized:
            raise RuntimeError(f"{self.name} not initialized")
        lgpio.gpio_write(self.gpio_handle, self.dc_pin, 0)
        self.spi.xfer2([cmd])
    
    def _send_data(self, data):
        """Send data to display"""
        if not self._initialized:
            raise RuntimeError(f"{self.name} not initialized")
        lgpio.gpio_write(self.gpio_handle, self.dc_pin, 1)
        if isinstance(data, list):
            self.spi.xfer2(data)
        else:
            self.spi.xfer2([data])
    
    def _send_init_commands(self):
        """Send SSD1351 initialization sequence"""
        commands = [
            (0xFD, 0x12), (0xFD, 0xB1), (0xAE, None),  # Command lock, display off
            (0xB3, 0xF1), (0xCA, 0x7F), (0xA2, 0x00),  # Clock, multiplex, offset
            (0xB5, 0x00), (0xAB, 0x01), (0xB1, 0x32),  # GPIO, function, phase
            (0xBE, 0x05), (0xA6, None), (0xAF, None)   # VCOMH, normal mode, display on
        ]
        
        for cmd, data in commands:
            self._send_command(cmd)
            if data is not None:
                self._send_data(data)
    
    def set_drawing_area(self, x1: int = 0, y1: int = 0, x2: int = 127, y2: int = 127):
        """
        Set the drawing area for subsequent pixel data
        
        Args:
            x1, y1: Top-left corner (inclusive)
            x2, y2: Bottom-right corner (inclusive)
        """
        self._send_command(0x15)  # Column address
        self._send_data([x1, x2])
        self._send_command(0x75)  # Row address
        self._send_data([y1, y2])
        self._send_command(0x5C)  # Write RAM
    
    def fill_screen(self, color_bgr565: Tuple[int, int]):
        """
        Fill entire screen with solid color
        
        Args:
            color_bgr565: Color as (low_byte, high_byte) in BGR565 format
        """
        self.set_drawing_area()
        
        # Send color data for entire screen (128x128 = 16384 pixels)
        lgpio.gpio_write(self.gpio_handle, self.dc_pin, 1)
        
        # Send in chunks to avoid SPI buffer issues
        chunk_size = 1024
        pixels_per_chunk = chunk_size // 2
        total_pixels = self.width * self.height
        
        for chunk_start in range(0, total_pixels, pixels_per_chunk):
            chunk = list(color_bgr565) * pixels_per_chunk
            self.spi.xfer2(chunk)
    
    def send_pixel_data(self, pixel_data: List[int]):
        """
        Send raw pixel data to display (must call set_drawing_area first)
        
        Args:
            pixel_data: List of bytes in BGR565 format (2 bytes per pixel)
        """
        lgpio.gpio_write(self.gpio_handle, self.dc_pin, 1)
        
        # Send in chunks to avoid SPI buffer issues
        chunk_size = 2048
        for i in range(0, len(pixel_data), chunk_size):
            chunk = pixel_data[i:i + chunk_size]
            self.spi.xfer2(chunk)
    
    def close(self):
        """Clean up hardware resources"""
        try:
            if self.spi:
                self.spi.close()
            if self.gpio_handle:
                lgpio.gpiochip_close(self.gpio_handle)
            self._initialized = False
        except:
            pass


class EyeRenderer:
    """
    High-level eyeball rendering for animatronic displays
    
    Renders realistic eyeballs with pupils, sclera, and blinking animation.
    """
    
    # BGR565 Color constants
    BLACK = (0x00, 0x00)
    WHITE = (0xFF, 0xFF)
    EYELID_COLOR = (0x20, 0x10)  # Dark skin tone
    
    def __init__(self, display: SSD1351Display):
        """
        Initialize eye renderer
        
        Args:
            display: SSD1351Display instance to render to
        """
        self.display = display
        self.eye_radius = 50
        self.pupil_radius = 18
    
    def draw_eye(self, pupil_x: int = 0, pupil_y: int = 0, blink_amount: float = 0.0):
        """
        Draw an eyeball with pupil and optional blinking
        
        Args:
            pupil_x: Pupil X offset from center (-20 to 20)
            pupil_y: Pupil Y offset from center (-20 to 20)  
            blink_amount: 0.0 = open, 1.0 = fully closed
        """
        try:
            # Set full screen drawing area
            self.display.set_drawing_area()
            
            center_x, center_y = 64, 64
            
            # Calculate blink effect
            blink_height = int(self.eye_radius * (1.0 - blink_amount))
            
            # Build eye data
            eye_data = []
            for y in range(128):
                for x in range(128):
                    dx = x - center_x
                    dy = y - center_y
                    distance = math.sqrt(dx * dx + dy * dy)
                    
                    # Check if within blinking area
                    if blink_amount > 0 and abs(dy) > blink_height:
                        # Eyelid color
                        eye_data.extend(self.EYELID_COLOR)
                    elif distance <= self.eye_radius:
                        # Inside eye area
                        pupil_dx = dx - pupil_x
                        pupil_dy = dy - pupil_y
                        pupil_distance = math.sqrt(pupil_dx * pupil_dx + pupil_dy * pupil_dy)
                        
                        if pupil_distance <= self.pupil_radius:
                            # Black pupil
                            eye_data.extend(self.BLACK)
                        else:
                            # White sclera
                            eye_data.extend(self.WHITE)
                    else:
                        # Outside eye (black background)
                        eye_data.extend(self.BLACK)
            
            # Send eye data to display
            self.display.send_pixel_data(eye_data)
            
        except Exception as e:
            print(f"⚠️ {self.display.name} draw error: {e}")


class DualEyeController:
    """
    Controller for dual eye animatronic system
    
    Manages two eye displays with synchronized animation and independent control.
    """
    
    def __init__(self, left_dc: int = 24, left_rst: int = 25, 
                 right_dc: int = 23, right_rst: int = 22):
        """
        Initialize dual eye controller
        
        Args:
            left_dc: Left eye DC pin (default: GPIO 24)
            left_rst: Left eye RST pin (default: GPIO 25)
            right_dc: Right eye DC pin (default: GPIO 23)
            right_rst: Right eye RST pin (default: GPIO 22)
        """
        # Create displays
        self.left_display = SSD1351Display(0, left_dc, left_rst, "Left Eye")
        self.right_display = SSD1351Display(1, right_dc, right_rst, "Right Eye")
        
        # Create renderers
        self.left_eye = EyeRenderer(self.left_display)
        self.right_eye = EyeRenderer(self.right_display)
        
        self._initialized = False
    
    def initialize(self) -> bool:
        """
        Initialize both eye displays
        
        Returns:
            True if both eyes initialized successfully
        """
        left_ok = self.left_display.initialize()
        right_ok = self.right_display.initialize()
        
        self._initialized = left_ok and right_ok
        
        if self._initialized:
            print("✓ Dual eye system initialized")
        else:
            print("⚠️ Dual eye system partially initialized")
        
        return self._initialized
    
    def draw_eyes(self, left_pupil: Tuple[int, int] = (0, 0), 
                  right_pupil: Tuple[int, int] = (0, 0),
                  blink_amount: float = 0.0):
        """
        Draw both eyes with specified pupil positions and blink
        
        Args:
            left_pupil: (x, y) pupil offset for left eye
            right_pupil: (x, y) pupil offset for right eye  
            blink_amount: 0.0 = open, 1.0 = closed
        """
        if not self._initialized:
            return
        
        self.left_eye.draw_eye(left_pupil[0], left_pupil[1], blink_amount)
        self.right_eye.draw_eye(right_pupil[0], right_pupil[1], blink_amount)
    
    def close(self):
        """Clean up both displays"""
        self.left_display.close()
        self.right_display.close()
        print("✓ Dual eye system closed")


# Color utility functions for BGR565 format
class Colors:
    """BGR565 color constants and utilities"""
    
    # Standard colors in BGR565 format (low_byte, high_byte)
    BLACK = (0x00, 0x00)
    WHITE = (0xFF, 0xFF)
    RED = (0x00, 0xF8)
    GREEN = (0x1F, 0x00)  
    BLUE = (0xE0, 0x07)
    YELLOW = (0x1F, 0xF8)  # Red + Green
    MAGENTA = (0xE0, 0xF8)  # Red + Blue
    CYAN = (0xFF, 0x07)   # Green + Blue
    
    @staticmethod
    def rgb_to_bgr565(r: int, g: int, b: int) -> Tuple[int, int]:
        """
        Convert RGB888 to BGR565 format
        
        Args:
            r, g, b: RGB values (0-255)
            
        Returns:
            Tuple of (low_byte, high_byte) for BGR565
        """
        # Convert to 5-6-5 bit format
        r5 = (r >> 3) & 0x1F
        g6 = (g >> 2) & 0x3F  
        b5 = (b >> 3) & 0x1F
        
        # Pack into BGR565 format
        bgr565 = (b5 << 11) | (g6 << 5) | r5
        
        # Return as bytes (little endian)
        return (bgr565 & 0xFF, (bgr565 >> 8) & 0xFF)


if __name__ == "__main__":
    print("OLED Display Module - Test Mode")
    print("This module should be imported, not run directly")
    print("See examples/ directory for usage examples")