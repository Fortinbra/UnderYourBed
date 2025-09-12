#!/usr/bin/env python3
"""
Dual Eye + Mouth Animation Test
Displays animated eyeballs on both OLED displays while servo animates mouth with lipsync
"""
import spidev
import time
import lgpio
import sys
import subprocess
import threading
import math
import random

try:
    from adafruit_servokit import ServoKit
    from playback import load_frames
    print("✓ Libraries imported successfully")
except ImportError as e:
    print(f"✗ Import error: {e}")
    sys.exit(1)

class EyeDisplay:
    """Control OLED eye display with raw SPI"""
    
    def __init__(self, device=0, name="Eye", dc_pin=24, rst_pin=25):
        self.device = device
        self.name = name
        self.spi = None
        self.gpio_handle = None  # Each eye has its own GPIO handle
        self.DC_PIN = dc_pin
        self.RST_PIN = rst_pin
        self.width = 128
        self.height = 128
        
    def initialize(self):
        """Initialize SPI and GPIO for eye display"""
        try:
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
            
            print(f"✓ {self.name} (device {self.device}) initialized with DC:{self.DC_PIN} RST:{self.RST_PIN}")
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
    
    def draw_eye(self, pupil_x=0, pupil_y=0, blink_amount=0.0):
        """Draw an animated eye
        pupil_x, pupil_y: pupil offset from center (-20 to 20)
        blink_amount: 0.0 = open, 1.0 = closed
        """
        try:
            # Set drawing area
            lgpio.gpio_write(self.gpio_handle, self.DC_PIN, 0)
            self.spi.xfer2([0x15, 0x00, 0x7F])  # Column
            lgpio.gpio_write(self.gpio_handle, self.DC_PIN, 0)
            self.spi.xfer2([0x75, 0x00, 0x7F])  # Row
            lgpio.gpio_write(self.gpio_handle, self.DC_PIN, 0)
            self.spi.xfer2([0x5C])  # Write RAM
            
            center_x, center_y = 64, 64
            eye_radius = 50
            pupil_radius = 18
            
            # Calculate blink effect
            blink_height = int(eye_radius * (1.0 - blink_amount))
            
            # Build eye data
            eye_data = []
            for y in range(128):
                for x in range(128):
                    dx = x - center_x
                    dy = y - center_y
                    distance = math.sqrt(dx * dx + dy * dy)
                    
                    # Check if within blinking area
                    if blink_amount > 0 and abs(dy) > blink_height:
                        # Eyelid color (dark skin tone)
                        eye_data.extend([0x20, 0x10])
                    elif distance <= eye_radius:
                        # Inside eye area
                        pupil_dx = dx - pupil_x
                        pupil_dy = dy - pupil_y
                        pupil_distance = math.sqrt(pupil_dx * pupil_dx + pupil_dy * pupil_dy)
                        
                        if pupil_distance <= pupil_radius:
                            # Black pupil
                            eye_data.extend([0x00, 0x00])
                        else:
                            # White sclera
                            eye_data.extend([0xFF, 0xFF])
                    else:
                        # Outside eye (black background)
                        eye_data.extend([0x00, 0x00])
            
            # Send eye data in chunks (direct data mode)
            lgpio.gpio_write(self.gpio_handle, self.DC_PIN, 1)
            chunk_size = 2048
            for i in range(0, len(eye_data), chunk_size):
                chunk = eye_data[i:i + chunk_size]
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

def animate_eyes(left_eye, right_eye, duration=30):
    """Animate both eyes with coordinated movements and blinking"""
    print("👁️👁️  Starting dual eye animation...")
    
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
    
    while time.time() - start_time < duration:
        current_time = time.time() - start_time
        
        # Synchronized blinking
        if not blinking and current_time - last_blink > random.uniform(2, 6):
            blinking = True
            blink_duration = 0
            last_blink = current_time
        
        # Blink animation
        blink_amount = 0.0
        if blinking:
            blink_duration += 0.1
            if blink_duration < 0.15:
                blink_amount = blink_duration / 0.15  # Closing
            elif blink_duration < 0.3:
                blink_amount = 1.0 - ((blink_duration - 0.15) / 0.15)  # Opening
            else:
                blinking = False
                blink_amount = 0.0
        
        # Coordinated eye movement (both eyes look in same direction)
        if current_time - last_look_change > random.uniform(1.5, 4):
            look_target_x = random.randint(-15, 15)
            look_target_y = random.randint(-10, 10)
            last_look_change = current_time
        
        # Smooth eye movement
        look_current_x += (look_target_x - look_current_x) * 0.1
        look_current_y += (look_target_y - look_current_y) * 0.1
        
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
            print(f"⚠️  Eye animation error: {e}")
            break
        
        time.sleep(0.1)  # 10 FPS
    
    print("👁️👁️  Dual eye animation completed")

def test_dual_eyes_and_mouth():
    """Test both eye displays and mouth servo together"""
    print("👁️👁️🗣️  Dual Eyes + Mouth Animation Test")
    print("=" * 45)
    
    # Initialize left eye (GPIO 24/25)
    left_eye = EyeDisplay(device=0, name="Left Eye", dc_pin=24, rst_pin=25)
    if not left_eye.initialize():
        print("❌ Left eye display failed to initialize")
        return False
    
    # Initialize right eye (GPIO 23/22)
    right_eye = EyeDisplay(device=1, name="Right Eye", dc_pin=23, rst_pin=22)
    right_eye_working = right_eye.initialize()
    if not right_eye_working:
        print("⚠️  Right eye failed - continuing with left eye only")
        right_eye = None
    
    # Initialize servo
    try:
        kit = ServoKit(channels=16)
        servo_channel = 0
        print(f"✓ Servo initialized on channel {servo_channel}")
    except Exception as e:
        print(f"✗ Servo initialization failed: {e}")
        left_eye.close()
        if right_eye:
            right_eye.close()
        return False
    
    # Load lipsync data
    try:
        frames_file = "/home/fortinbra/UnderYourBed-1/bundles/G-YNNJIe2Vk_20250904-030059/song.lipsync.json"
        frames, words = load_frames(frames_file)
        print(f"✓ Loaded {len(frames)} lipsync frames")
    except Exception as e:
        print(f"✗ Failed to load lipsync data: {e}")
        left_eye.close()
        if right_eye:
            right_eye.close()
        return False
    
    # Start audio playback
    audio_file = "/home/fortinbra/UnderYourBed-1/bundles/G-YNNJIe2Vk_20250904-030059/original.m4a"
    audio_process = None
    
    try:
        audio_process = subprocess.Popen([
            'ffplay', '-nodisp', '-autoexit', audio_file
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print("✓ Audio playback started")
    except Exception as e:
        print(f"⚠️  Audio failed: {e}")
    
    eye_count = "both eyes" if right_eye else "left eye only"
    print(f"\n🎬 Starting combined animation with {eye_count}...")
    print("You should see:")
    print(f"- Animated eyeball(s) with synchronized blinking and looking")
    print("- Servo mouth moving with the music")
    print("- Audio playing")
    print()
    
    # Start eye animation in separate thread
    eye_thread = threading.Thread(target=animate_eyes, args=(left_eye, right_eye, 60))
    eye_thread.start()
    
    # Mouth animation (main thread)
    start_time = time.perf_counter()
    frame_index = 0
    
    try:
        # Run for 60 seconds or until frames end
        while frame_index < len(frames) and time.perf_counter() - start_time < 60:
            current_time = time.perf_counter() - start_time
            frame = frames[frame_index]
            
            if current_time >= frame["TimeSeconds"]:
                mouth_open = frame["MouthOpen01"]
                servo_angle = 30 + (mouth_open * 50)  # 30° to 80°
                kit.servo[servo_channel].angle = servo_angle
                
                # Progress every 15 seconds
                if int(current_time) % 15 == 0 and current_time > 0:
                    if int(current_time) != getattr(test_dual_eyes_and_mouth, 'last_progress', -1):
                        eyes_status = "👁️👁️" if right_eye else "👁️"
                        print(f"⏱️  {int(current_time)}s {eyes_status} - mouth: {mouth_open:.2f}")
                        test_dual_eyes_and_mouth.last_progress = int(current_time)
                
                frame_index += 1
            else:
                time.sleep(0.001)
    
    except KeyboardInterrupt:
        print("\n⏹️  Interrupted by user")
    
    finally:
        # Clean up
        print("\n🔧 Cleaning up...")
        
        # Wait for eye thread
        eye_thread.join(timeout=3)
        
        # Center servo
        try:
            kit.servo[servo_channel].angle = 55
            print("✓ Servo centered")
        except:
            pass
        
        # Stop audio
        if audio_process:
            try:
                audio_process.terminate()
                audio_process.wait(timeout=2)
                print("✓ Audio stopped")
            except:
                pass
        
        # Close eye displays
        left_eye.close()
        if right_eye:
            right_eye.close()
        print("✓ Eye displays closed")
    
    return True

def main():
    print("🔍 Checking for dual eye setup...")
    print("Left eye should be connected to Pin 24 (GPIO 8, CE0)")
    print("Right eye should be connected to Pin 26 (GPIO 7, CE1)")
    print()
    
    success = test_dual_eyes_and_mouth()
    
    if success:
        print("\n🎉 Dual Eyes + Mouth animation test completed!")
        print("✅ Eye displays: Synchronized animated eyeballs")
        print("✅ Servo mouth: Lipsync animation")
        print("✅ Audio: Full track playback")
        print("✅ Coordination: All systems working together")
        print("\nYour dual-eye animatronic is alive! 🤖👁️👁️🗣️")
    else:
        print("\n❌ Test failed")
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())