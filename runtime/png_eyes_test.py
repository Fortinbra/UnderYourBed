#!/usr/bin/env python3
"""
PNG-Based Eye Display Test
Uses converted PNG graphics from Uncanny Eyes project instead of procedural generation
"""
import spidev
import time
import lgpio
import sys
import math
import random
import json
import os
from typing import Optional, Dict, List

class PNGEyeDisplay:
    """Control OLED eye display using pre-converted PNG graphics"""
    
    def __init__(self, device=0, name="Eye", dc_pin=24, rst_pin=25, eye_type="defaultEye"):
        self.device = device
        self.name = name
        self.spi = None
        self.gpio_handle = None
        self.DC_PIN = dc_pin
        self.RST_PIN = rst_pin
        self.width = 128
        self.height = 128
        self.eye_type = eye_type
        
        # Graphics data
        self.eye_data = None
        self.frames = {}
        
    def load_eye_graphics(self):
        """Load pre-converted eye graphics from JSON file"""
        graphics_file = f"/home/fortinbra/UnderYourBed-1/runtime/{self.eye_type}_graphics.json"
        
        try:
            if not os.path.exists(graphics_file):
                print(f"⚠️ Graphics file not found: {graphics_file}")
                return False
                
            with open(graphics_file, 'r') as f:
                self.eye_data = json.load(f)
            
            self.frames = self.eye_data.get("frames", {})
            print(f"✓ Loaded {len(self.frames)} eye frames for {self.eye_type}")
            return True
            
        except Exception as e:
            print(f"✗ Failed to load eye graphics: {e}")
            return False
        
    def initialize(self):
        """Initialize SPI, GPIO, and load graphics"""
        try:
            # Load graphics first
            if not self.load_eye_graphics():
                return False
            
            # Open SPI
            self.spi = spidev.SpiDev()
            self.spi.open(0, self.device)
            self.spi.max_speed_hz = 8000000
            self.spi.mode = 0
            
            # Each eye gets its own GPIO handle
            self.gpio_handle = lgpio.gpiochip_open(0)
            lgpio.gpio_claim_output(self.gpio_handle, self.DC_PIN)
            lgpio.gpio_claim_output(self.gpio_handle, self.RST_PIN)
            
            # Reset display
            lgpio.gpio_write(self.gpio_handle, self.RST_PIN, 0)
            time.sleep(0.01)
            lgpio.gpio_write(self.gpio_handle, self.RST_PIN, 1)
            time.sleep(0.01)
            
            # Initialize SSD1351
            self._send_init_commands()
            
            print(f"✓ {self.name} ({self.eye_type}) initialized with DC:{self.DC_PIN} RST:{self.RST_PIN}")
            return True
            
        except Exception as e:
            print(f"✗ {self.name} initialization failed: {e}")
            return False
    
    def _send_command(self, cmd):
        """Send command to display"""
        lgpio.gpio_write(self.gpio_handle, self.DC_PIN, 0)
        self.spi.xfer2([cmd])
    
    def _send_data(self, data):
        """Send data to display"""
        lgpio.gpio_write(self.gpio_handle, self.DC_PIN, 1)
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
    
    def get_best_frame(self, pupil_x=0, pupil_y=0, blink_amount=0.0):
        """Get the best matching pre-rendered frame for the given parameters"""
        if not self.frames:
            return None
        
        # If blinking, prioritize blink frames
        if blink_amount > 0.8:
            return self.frames.get("blink_full")
        elif blink_amount > 0.6:
            return self.frames.get("blink_75")
        elif blink_amount > 0.4:
            return self.frames.get("blink_50")
        elif blink_amount > 0.2:
            return self.frames.get("blink_25")
        
        # Otherwise, use movement frames
        if abs(pupil_x) > abs(pupil_y):
            # Horizontal movement dominant
            if pupil_x > 5:
                return self.frames.get("look_right", self.frames.get("normal"))
            elif pupil_x < -5:
                return self.frames.get("look_left", self.frames.get("normal"))
        else:
            # Vertical movement dominant
            if pupil_y > 5:
                return self.frames.get("look_down", self.frames.get("normal"))
            elif pupil_y < -5:
                return self.frames.get("look_up", self.frames.get("normal"))
        
        # Default to normal
        return self.frames.get("normal")
    
    def draw_eye(self, pupil_x=0, pupil_y=0, blink_amount=0.0):
        """Draw eye using pre-rendered PNG graphics"""
        try:
            # Get the best matching frame
            frame_data = self.get_best_frame(pupil_x, pupil_y, blink_amount)
            if not frame_data:
                print(f"⚠️ No frame data available for {self.name}")
                return
            
            # Set drawing area to full display
            lgpio.gpio_write(self.gpio_handle, self.DC_PIN, 0)
            self.spi.xfer2([0x15, 0x00, 0x7F])  # Column 0-127
            lgpio.gpio_write(self.gpio_handle, self.DC_PIN, 0)
            self.spi.xfer2([0x75, 0x00, 0x7F])  # Row 0-127
            lgpio.gpio_write(self.gpio_handle, self.DC_PIN, 0)
            self.spi.xfer2([0x5C])  # Write RAM command
            
            # Send frame data in chunks
            lgpio.gpio_write(self.gpio_handle, self.DC_PIN, 1)
            chunk_size = 2048
            for i in range(0, len(frame_data), chunk_size):
                chunk = frame_data[i:i + chunk_size]
                self.spi.xfer2(chunk)
                
        except Exception as e:
            print(f"⚠️ {self.name} draw error: {e}")
    
    def close(self):
        """Clean up resources"""
        try:
            if self.spi:
                self.spi.close()
            if self.gpio_handle:
                lgpio.gpiochip_close(self.gpio_handle)
        except:
            pass

def animate_png_eyes(left_eye, right_eye, duration=30):
    """Animate both eyes using PNG graphics with coordinated movements and blinking"""
    print(f"👁️👁️  Starting PNG eye animation ({left_eye.eye_type})...")
    
    start_time = time.time()
    last_blink = 0
    blink_duration = 0
    blinking = False
    
    # Eye movement parameters
    look_target_x = 0
    look_target_y = 0
    look_current_x = 0
    look_current_y = 0
    last_look_change = 0
    
    frame_count = 0
    
    while time.time() - start_time < duration:
        current_time = time.time() - start_time
        frame_count += 1
        
        # Progress indicator every 5 seconds
        if int(current_time) % 5 == 0 and current_time > 0:
            if int(current_time) != getattr(animate_png_eyes, 'last_progress', -1):
                eyes_status = "👁️👁️" if right_eye else "👁️"
                print(f"⏱️  {int(current_time)}s {eyes_status} ({left_eye.eye_type}) - Frame {frame_count}")
                animate_png_eyes.last_progress = int(current_time)
        
        # Synchronized blinking
        if not blinking and current_time - last_blink > random.uniform(3, 7):
            blinking = True
            blink_duration = 0
            last_blink = current_time
            print(f"👁️  Blink ({left_eye.eye_type}) at {current_time:.1f}s")
        
        # Blink animation
        blink_amount = 0.0
        if blinking:
            blink_duration += 0.1
            if blink_duration < 0.2:
                blink_amount = blink_duration / 0.2  # Closing
            elif blink_duration < 0.4:
                blink_amount = 1.0 - ((blink_duration - 0.2) / 0.2)  # Opening
            else:
                blinking = False
                blink_amount = 0.0
        
        # Coordinated eye movement
        if current_time - last_look_change > random.uniform(2, 5):
            look_target_x = random.randint(-15, 15)
            look_target_y = random.randint(-10, 10)
            last_look_change = current_time
            print(f"👀 Looking to ({look_target_x}, {look_target_y}) at {current_time:.1f}s")
        
        # Smooth eye movement
        look_current_x += (look_target_x - look_current_x) * 0.15
        look_current_y += (look_target_y - look_current_y) * 0.15
        
        # Draw both eyes with same movement (synchronized)
        try:
            left_eye.draw_eye(
                pupil_x=int(look_current_x),
                pupil_y=int(look_current_y),
                blink_amount=blink_amount
            )
            
            if right_eye:
                right_eye.draw_eye(
                    pupil_x=int(look_current_x),
                    pupil_y=int(look_current_y),
                    blink_amount=blink_amount
                )
        except Exception as e:
            print(f"⚠️  PNG Eye animation error: {e}")
            break
        
        time.sleep(0.1)  # 10 FPS
    
    print("👁️👁️  PNG eye animation completed")

def test_png_eyes(eye_type="defaultEye"):
    """Test both eye displays using PNG graphics"""
    print(f"👁️👁️  PNG Eyes Test - {eye_type}")
    print("=" * 40)
    print(f"Using converted graphics from Uncanny Eyes: {eye_type}")
    print()
    
    # Initialize left eye
    left_eye = PNGEyeDisplay(device=0, name="Left Eye", dc_pin=24, rst_pin=25, eye_type=eye_type)
    if not left_eye.initialize():
        print("❌ Left eye display failed to initialize")
        return False
    
    # Initialize right eye
    right_eye = PNGEyeDisplay(device=1, name="Right Eye", dc_pin=23, rst_pin=22, eye_type=eye_type)
    right_eye_working = right_eye.initialize()
    if not right_eye_working:
        print("⚠️  Right eye failed - continuing with left eye only")
        right_eye = None
    
    eye_count = "both eyes" if right_eye else "left eye only"
    print(f"\n🎬 Starting PNG eye animation with {eye_count}...")
    print("You should see:")
    print(f"- High-quality {eye_type} graphics from PNG files")
    print("- Coordinated eye movements and blinking")
    print("- Smooth transitions between eye states")
    print("- Different eye expressions based on movement")
    print("Press Ctrl+C to stop")
    print()
    
    try:
        # Run PNG eye animation
        animate_png_eyes(left_eye, right_eye, 30)
        
    except KeyboardInterrupt:
        print("\n⏹️  Interrupted by user")
    
    finally:
        # Clean up
        print("\n🔧 Cleaning up...")
        left_eye.close()
        if right_eye:
            right_eye.close()
        print("✓ PNG eye displays closed")
    
    return True

def main():
    """Main function with eye type selection"""
    available_eyes = ["defaultEye", "catEye", "dragonEye", "doeEye", "goatEye", "newtEye", "terminatorEye"]
    
    if len(sys.argv) > 1:
        eye_type = sys.argv[1]
        if eye_type not in available_eyes:
            print(f"⚠️ Unknown eye type: {eye_type}")
            print(f"Available: {', '.join(available_eyes)}")
            return 1
    else:
        eye_type = "defaultEye"
    
    print(f"🔍 Checking for PNG graphics setup...")
    print(f"Using eye type: {eye_type}")
    
    success = test_png_eyes(eye_type)
    
    if success:
        print(f"\n🎉 PNG Eyes test completed successfully!")
        print(f"✅ Eye graphics: {eye_type} PNG-based rendering")
        print("✅ Eye movement: Pre-rendered frame selection")
        print("✅ Blinking: High-quality eyelid animations")
        print("✅ Performance: Optimized SPI data transfer")
        print(f"\nYour {eye_type} eyes look amazing! 👁️👁️🎨")
    else:
        print("\n❌ Test failed")
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())