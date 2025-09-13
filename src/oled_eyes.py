#!/usr/bin/env python3
"""
OLED Eyes Controller for Animatronic Project

Controls dual SSD1351 128x128 RGB OLED displays as animated eyes

Hardware Setup:
| Signal | Left Eye      | Right Eye     | Shared        |
|--------|---------------|---------------|---------------|
| VCC    | Pin 1 (3.3V)  | Pin 1 (3.3V)  |               |
| GND    | Pin 6 (GND)   | Pin 6 (GND)   |               |
| SCK    |               |               | Pin 23 (GPIO11) |
| MOSI   |               |               | Pin 19 (GPIO10) |
| DC     | Pin 18 (GPIO24) | Pin 16 (GPIO23) |           |
| RST    | Pin 22 (GPIO25) | Pin 15 (GPIO22) |           |
| CS     | Pin 24 (CE0)    | Pin 26 (CE1)    |           |

Features:
- Realistic eye movements with pupil tracking
- Natural blinking animations
- Coordinated dual-eye control
- Simulation mode for development without hardware
"""

import time
import math
import threading
from typing import Tuple, Optional
from PIL import Image, ImageDraw
import digitalio
import board
import busio
import adafruit_ssd1351


class EyeGraphics:
    """Helper class for generating eye graphics"""
    
    @staticmethod
    def draw_eye(size: Tuple[int, int], pupil_pos: Tuple[int, int], pupil_size: int = 20, 
                 iris_color: Tuple[int, int, int] = (0, 100, 255), 
                 pupil_color: Tuple[int, int, int] = (0, 0, 0),
                 sclera_color: Tuple[int, int, int] = (255, 255, 255)) -> Image.Image:
        """
        Draw a single eye
        
        Args:
            size: (width, height) of the display
            pupil_pos: (x, y) position of the pupil center
            pupil_size: Size of the pupil
            iris_color: RGB color of the iris
            pupil_color: RGB color of the pupil
            sclera_color: RGB color of the sclera (white part)
        """
        img = Image.new('RGB', size, sclera_color)
        draw = ImageDraw.Draw(img)
        
        # Calculate eye dimensions
        eye_width, eye_height = size
        center_x, center_y = eye_width // 2, eye_height // 2
        
        # Draw iris (larger circle around pupil)
        iris_size = pupil_size * 2
        iris_x, iris_y = pupil_pos
        
        # Ensure iris stays within bounds
        iris_radius = iris_size // 2
        iris_x = max(iris_radius, min(eye_width - iris_radius, iris_x))
        iris_y = max(iris_radius, min(eye_height - iris_radius, iris_y))
        
        # Draw iris
        draw.ellipse([
            iris_x - iris_radius, iris_y - iris_radius,
            iris_x + iris_radius, iris_y + iris_radius
        ], fill=iris_color)
        
        # Draw pupil
        pupil_radius = pupil_size // 2
        draw.ellipse([
            iris_x - pupil_radius, iris_y - pupil_radius,
            iris_x + pupil_radius, iris_y + pupil_radius
        ], fill=pupil_color)
        
        return img
    
    @staticmethod
    def draw_blink(size: Tuple[int, int], blink_amount: float) -> Image.Image:
        """
        Draw a blinking eye (partial closure)
        
        Args:
            size: (width, height) of the display
            blink_amount: 0.0 (fully open) to 1.0 (fully closed)
        """
        img = Image.new('RGB', size, (0, 0, 0))  # Black for closed portions
        
        if blink_amount >= 1.0:
            return img  # Fully closed
        
        # Calculate visible portion
        eye_height = int(size[1] * (1.0 - blink_amount))
        if eye_height <= 0:
            return img
        
        # Create normal eye for visible portion
        eye_img = EyeGraphics.draw_eye(size, (size[0]//2, size[1]//2))
        
        # Crop to show only the middle portion (simulate eyelid closure)
        y_offset = (size[1] - eye_height) // 2
        visible_portion = eye_img.crop((0, y_offset, size[0], y_offset + eye_height))
        
        # Paste visible portion back
        img.paste(visible_portion, (0, y_offset))
        
        return img


class OLEDEyeController:
    """Controller for dual SSD1351 OLED displays as animated eyes"""
    
    def __init__(self, 
                 # SPI pins (shared)
                 spi_sclk=board.SCK, spi_mosi=board.MOSI,
                 # Left eye pins
                 left_cs=board.D8, left_dc=board.D24, left_rst=board.D25,
                 # Right eye pins  
                 right_cs=board.D7, right_dc=board.D23, right_rst=board.D22,
                 # Display settings
                 width=128, height=128):
        """
        Initialize dual OLED eye controller
        
        Args:
            spi_sclk, spi_mosi: Shared SPI pins (GPIO11/Pin23, GPIO10/Pin19)
            left_cs, left_dc, left_rst: Left display control pins (CE0/Pin24, GPIO24/Pin18, GPIO25/Pin22)
            right_cs, right_dc, right_rst: Right display control pins (CE1/Pin26, GPIO23/Pin16, GPIO22/Pin15)
            width, height: Display dimensions
        """
        self.width = width
        self.height = height
        self.left_display = None
        self.right_display = None
        self.is_initialized = False
        self.animation_thread = None
        self.is_animating = False
        
        # Store pin configurations
        self.spi_sclk = spi_sclk
        self.spi_mosi = spi_mosi
        self.left_pins = (left_cs, left_dc, left_rst)
        self.right_pins = (right_cs, right_dc, right_rst)
        
        print("OLED Eye Controller created - waiting for initialization")
    
    def initialize(self):
        """Initialize the dual OLED displays"""
        try:
            # Create shared SPI bus
            spi = busio.SPI(self.spi_sclk, MOSI=self.spi_mosi)
            
            # Initialize left eye display
            left_cs = digitalio.DigitalInOut(self.left_pins[0])
            left_dc = digitalio.DigitalInOut(self.left_pins[1])
            left_rst = digitalio.DigitalInOut(self.left_pins[2])
            
            self.left_display = adafruit_ssd1351.SSD1351(
                spi, cs=left_cs, dc=left_dc, rst=left_rst,
                width=self.width, height=self.height, baudrate=16000000
            )
            
            # Initialize right eye display
            right_cs = digitalio.DigitalInOut(self.right_pins[0])
            right_dc = digitalio.DigitalInOut(self.right_pins[1])
            right_rst = digitalio.DigitalInOut(self.right_pins[2])
            
            self.right_display = adafruit_ssd1351.SSD1351(
                spi, cs=right_cs, dc=right_dc, rst=right_rst,
                width=self.width, height=self.height, baudrate=16000000
            )
            
            # Clear both displays
            self.clear_displays()
            
            self.is_initialized = True
            print(f"Dual OLED eyes initialized - {self.width}x{self.height} SSD1351 displays")
            
        except Exception as e:
            print(f"Warning: Could not initialize OLED displays: {e}")
            print("Running in simulation mode - eye commands will be printed")
            self.is_initialized = False
    
    def clear_displays(self):
        """Clear both eye displays"""
        if self.is_initialized:
            self.left_display.fill(0x0000)  # Black
            self.right_display.fill(0x0000)
        else:
            print("EYES: Clearing displays")
    
    def draw_eyes(self, left_pupil_pos: Tuple[int, int], right_pupil_pos: Tuple[int, int], 
                  blink_amount: float = 0.0):
        """
        Draw both eyes with specified pupil positions
        
        Args:
            left_pupil_pos: (x, y) position for left eye pupil
            right_pupil_pos: (x, y) position for right eye pupil  
            blink_amount: 0.0 (open) to 1.0 (closed)
        """
        size = (self.width, self.height)
        
        if blink_amount > 0.0:
            # Draw blinking eyes
            left_img = EyeGraphics.draw_blink(size, blink_amount)
            right_img = EyeGraphics.draw_blink(size, blink_amount)
        else:
            # Draw normal eyes
            left_img = EyeGraphics.draw_eye(size, left_pupil_pos)
            right_img = EyeGraphics.draw_eye(size, right_pupil_pos)
        
        if self.is_initialized:
            # Display on hardware
            self.left_display.image(left_img)
            self.right_display.image(right_img)
        else:
            # Simulation mode
            print(f"EYES: Left pupil {left_pupil_pos}, Right pupil {right_pupil_pos}, Blink {blink_amount:.2f}")
    
    def look_at(self, target_x: float, target_y: float, eye_separation: float = 20):
        """
        Make both eyes look at a target point
        
        Args:
            target_x: X coordinate to look at (0-127)
            target_y: Y coordinate to look at (0-127)
            eye_separation: Distance between eye centers for parallax effect
        """
        center_x, center_y = self.width // 2, self.height // 2
        
        # Calculate pupil positions with slight parallax for each eye
        left_pupil_x = int(center_x + (target_x - center_x) * 0.3 - eye_separation//2)
        left_pupil_y = int(center_y + (target_y - center_y) * 0.3)
        
        right_pupil_x = int(center_x + (target_x - center_x) * 0.3 + eye_separation//2)
        right_pupil_y = int(center_y + (target_y - center_y) * 0.3)
        
        # Clamp to display bounds
        left_pupil_x = max(20, min(self.width-20, left_pupil_x))
        left_pupil_y = max(20, min(self.height-20, left_pupil_y))
        right_pupil_x = max(20, min(self.width-20, right_pupil_x))
        right_pupil_y = max(20, min(self.height-20, right_pupil_y))
        
        self.draw_eyes((left_pupil_x, left_pupil_y), (right_pupil_x, right_pupil_y))
    
    def animate_idle(self, duration: float = 10.0):
        """
        Start idle eye animation (looking around, blinking)
        
        Args:
            duration: How long to animate (seconds)
        """
        if self.is_animating:
            return
        
        def animation_loop():
            self.is_animating = True
            start_time = time.time()
            
            try:
                while time.time() - start_time < duration and self.is_animating:
                    current_time = time.time() - start_time
                    
                    # Gentle eye movement (figure-8 pattern)
                    x = self.width//2 + int(15 * math.sin(current_time * 0.5))
                    y = self.height//2 + int(10 * math.sin(current_time * 1.0))
                    
                    # Occasional blink
                    blink = 0.0
                    if current_time % 3.0 < 0.2:  # Blink every 3 seconds for 0.2 seconds
                        blink_progress = (current_time % 3.0) / 0.2
                        blink = math.sin(blink_progress * math.pi)  # Smooth blink curve
                    
                    self.draw_eyes((x, y), (x, y), blink_amount=blink)
                    time.sleep(0.05)  # 20fps animation
                    
            except Exception as e:
                print(f"Error in eye animation: {e}")
            finally:
                self.is_animating = False
                # Return to center position
                self.draw_eyes((self.width//2, self.height//2), (self.width//2, self.height//2))
        
        self.animation_thread = threading.Thread(target=animation_loop, daemon=True)
        self.animation_thread.start()
        print(f"Started idle eye animation for {duration:.1f} seconds")
    
    def stop_animation(self):
        """Stop any running eye animation"""
        if self.is_animating:
            self.is_animating = False
            print("Stopping eye animation")
            if self.animation_thread and self.animation_thread.is_alive():
                self.animation_thread.join(timeout=1.0)
    
    def cleanup(self):
        """Clean up eye controller resources"""
        self.stop_animation()
        self.clear_displays()


def main():
    """Test the OLED eye controller"""
    try:
        # Create eye controller with Waveshare 1.5inch RGB OLED pin configuration
        eyes = OLEDEyeController()
        
        # Initialize displays
        eyes.initialize()
        
        print("Testing OLED eyes...")
        
        # Test basic eye drawing
        print("Drawing centered eyes...")
        eyes.draw_eyes((64, 64), (64, 64))
        time.sleep(2)
        
        # Test eye movement
        print("Testing eye movement...")
        for i in range(20):
            x = 64 + int(20 * math.sin(i * 0.3))
            y = 64 + int(15 * math.cos(i * 0.3))
            eyes.look_at(x, y)
            time.sleep(0.1)
        
        # Test blinking
        print("Testing blink animation...")
        for i in range(10):
            blink_amount = abs(math.sin(i * 0.8))
            eyes.draw_eyes((64, 64), (64, 64), blink_amount=blink_amount)
            time.sleep(0.2)
        
        # Test idle animation
        print("Testing idle animation...")
        eyes.animate_idle(duration=5.0)
        time.sleep(5.5)
        
        # Cleanup
        eyes.cleanup()
        
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    main()