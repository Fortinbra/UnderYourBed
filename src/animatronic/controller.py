#!/usr/bin/env python3
"""
Animatronic Controller - Main System Orchestration
==================================================

This module provides the main controller class that orchestrates all
animatronic subsystems (eyes, mouth, audio) for synchronized performances.

Features:
- Unified interface for all animatronic components
- Synchronized audio and animation playback
- Graceful degradation when hardware unavailable
- Performance recording and playback
- Real-time animation control

Usage:
    from animatronic import AnimatronicController
    
    # Basic setup
    robot = AnimatronicController()
    robot.initialize()
    
    # Play a complete performance
    robot.play_performance("data/song.lipsync.json", "data/audio.wav")
    
    # Manual control
    robot.set_mouth_position(0.5)
    robot.set_eye_positions((5, -2), (-3, 1))
    robot.blink()
    
    robot.close()
"""

import time
import threading
import random
import math
from typing import Optional, Tuple, Union
from pathlib import Path

from .display import DualEyeController
from .servo import ServoController, LipSyncController
from .audio import AudioPlayer, LipSyncData


class AnimatronicController:
    """
    Main controller for complete animatronic system
    
    Coordinates all subsystems (eyes, mouth, audio) to create
    lifelike animated performances with synchronized lip-sync.
    """
    
    def __init__(self, servo_channel: int = 0, 
                 left_eye_pins: Tuple[int, int] = (24, 25),
                 right_eye_pins: Tuple[int, int] = (23, 22),
                 enable_eyes: bool = True,
                 enable_servo: bool = True,
                 enable_audio: bool = True):
        """
        Initialize animatronic controller
        
        Args:
            servo_channel: Servo channel on PCA9685 board
            left_eye_pins: (DC pin, RST pin) for left eye display
            right_eye_pins: (DC pin, RST pin) for right eye display
            enable_eyes: Enable eye displays
            enable_servo: Enable servo mouth control
            enable_audio: Enable audio playback
        """
        self.enable_eyes = enable_eyes
        self.enable_servo = enable_servo
        self.enable_audio = enable_audio
        
        # Initialize subsystem controllers
        self.eyes = None
        self.servo = None
        self.lipsync = None
        self.audio = None
        
        # Create controllers based on enabled features
        if self.enable_eyes:
            self.eyes = DualEyeController(
                left_dc=left_eye_pins[0], left_rst=left_eye_pins[1],
                right_dc=right_eye_pins[0], right_rst=right_eye_pins[1]
            )
        
        if self.enable_servo:
            self.servo = ServoController(channel=servo_channel)
            self.lipsync = LipSyncController(self.servo)
        
        if self.enable_audio:
            self.audio = AudioPlayer()
        
        # Animation state
        self._animation_thread = None
        self._animation_active = False
        self._performance_active = False
        
        # Eye animation parameters
        self._blink_timer = 0.0
        self._next_blink = self._random_blink_time()
        self._look_timer = 0.0
        self._next_look_change = self._random_look_time()
        self._current_look = (0, 0)
        self._target_look = (0, 0)
        
        print("🤖 Animatronic controller created")
        print(f"   Eyes: {'✓' if enable_eyes else '✗'}")
        print(f"   Servo: {'✓' if enable_servo else '✗'}")  
        print(f"   Audio: {'✓' if enable_audio else '✗'}")
    
    def initialize(self) -> bool:
        """
        Initialize all enabled subsystems
        
        Returns:
            True if all enabled systems initialized successfully
        """
        success = True
        
        print("🔧 Initializing animatronic systems...")
        
        # Initialize eyes
        if self.enable_eyes and self.eyes:
            if not self.eyes.initialize():
                print("⚠️ Eye displays failed to initialize")
                success = False
        
        # Initialize servo
        if self.enable_servo and self.servo:
            if not self.servo.initialize():
                print("⚠️ Servo failed to initialize") 
                success = False
        
        # Audio doesn't need initialization
        
        if success:
            print("✅ All systems initialized successfully")
            self._start_background_animation()
        else:
            print("⚠️ Some systems failed to initialize")
        
        return success
    
    def _start_background_animation(self):
        """Start background eye animation thread"""
        if not self.enable_eyes or not self.eyes:
            return
        
        self._animation_active = True
        self._animation_thread = threading.Thread(target=self._background_animation, daemon=True)
        self._animation_thread.start()
        print("👁️ Background eye animation started")
    
    def _background_animation(self):
        """Background thread for autonomous eye movement and blinking"""
        while self._animation_active:
            try:
                current_time = time.perf_counter()
                
                # Handle blinking
                blink_amount = 0.0
                if current_time >= self._next_blink:
                    # Calculate blink animation (quick close, slower open)
                    blink_progress = (current_time - self._next_blink) / 0.3  # 300ms blink
                    if blink_progress <= 0.33:  # Close phase
                        blink_amount = blink_progress * 3.0
                    elif blink_progress <= 1.0:  # Open phase
                        blink_amount = 1.0 - ((blink_progress - 0.33) / 0.67)
                    else:
                        # Blink finished, schedule next one
                        self._next_blink = current_time + self._random_blink_time()
                
                # Handle looking around
                if current_time >= self._next_look_change:
                    self._target_look = (random.randint(-15, 15), random.randint(-10, 10))
                    self._next_look_change = current_time + self._random_look_time()
                
                # Smoothly interpolate to target look position
                look_speed = 0.05
                self._current_look = (
                    self._current_look[0] + (self._target_look[0] - self._current_look[0]) * look_speed,
                    self._current_look[1] + (self._target_look[1] - self._current_look[1]) * look_speed
                )
                
                # Update eyes (if not in performance mode)
                if not self._performance_active:
                    self.eyes.draw_eyes(
                        left_pupil=self._current_look,
                        right_pupil=self._current_look,
                        blink_amount=blink_amount
                    )
                
                time.sleep(1/30)  # 30 FPS animation
                
            except Exception as e:
                print(f"⚠️ Background animation error: {e}")
                time.sleep(0.1)
    
    def _random_blink_time(self) -> float:
        """Generate random time until next blink (2-8 seconds)"""
        return random.uniform(2.0, 8.0)
    
    def _random_look_time(self) -> float:
        """Generate random time until next look change (1-4 seconds)"""
        return random.uniform(1.0, 4.0)
    
    def play_performance(self, lipsync_file: Union[str, Path], 
                        audio_file: Union[str, Path],
                        audio_delay_ms: int = 0) -> bool:
        """
        Play complete synchronized performance
        
        Args:
            lipsync_file: Path to lip-sync JSON data
            audio_file: Path to audio file
            audio_delay_ms: Audio delay adjustment in milliseconds
            
        Returns:
            True if performance completed successfully
        """
        print("🎭 Starting animatronic performance...")
        
        # Load lip-sync data
        lipsync_data = LipSyncData()
        if not lipsync_data.load_from_file(lipsync_file):
            print("✗ Failed to load lip-sync data")
            return False
        
        # Start audio playback
        if self.enable_audio and self.audio:
            if not self.audio.play_file(audio_file, delay_ms=audio_delay_ms):
                print("⚠️ Audio playback failed - continuing without audio")
        
        # Start synchronized animation
        self._performance_active = True
        
        try:
            frames = lipsync_data.get_frames()
            frame_rate = lipsync_data.get_frame_rate()
            frame_duration = 1.0 / frame_rate
            
            print(f"🎬 Playing {len(frames)} frames at {frame_rate:.1f} FPS")
            
            start_time = time.perf_counter()
            
            for i, frame in enumerate(frames):
                if not self._performance_active:
                    break
                
                # Extract mouth position
                mouth_position = frame.get("MouthOpen01", 0.0)
                frame_time = frame.get("TimeSeconds", i * frame_duration)
                
                # Set servo position
                if self.enable_servo and self.servo:
                    self.servo.set_position(mouth_position)
                
                # Add some eye movement during performance
                if self.enable_eyes and self.eyes:
                    # Subtle eye movement based on mouth intensity
                    eye_intensity = mouth_position * 5  # Scale for subtle movement
                    look_x = math.sin(frame_time * 0.3) * eye_intensity
                    look_y = math.cos(frame_time * 0.5) * eye_intensity * 0.5
                    
                    self.eyes.draw_eyes(
                        left_pupil=(int(look_x), int(look_y)),
                        right_pupil=(int(look_x), int(look_y)),
                        blink_amount=0.0
                    )
                
                # Progress indicator (every 30 frames = ~1 second)
                if i % 30 == 0:
                    print(f"⏱️  {i//30}s 🗣️ - mouth: {mouth_position:.2f}")
                
                # Frame timing
                target_time = start_time + frame_time
                sleep_time = target_time - time.perf_counter()
                if sleep_time > 0:
                    time.sleep(sleep_time)
            
            print("✓ Performance completed")
            return True
            
        except KeyboardInterrupt:
            print("⏸️ Performance interrupted by user")
            return False
        except Exception as e:
            print(f"✗ Performance error: {e}")
            return False
        finally:
            self._performance_active = False
            
            # Stop audio and center servo
            if self.audio:
                self.audio.stop()
            if self.servo:
                self.servo.center()
    
    def set_mouth_position(self, position: float):
        """
        Set mouth position manually
        
        Args:
            position: Mouth position (0.0 = closed, 1.0 = open)
        """
        if self.enable_servo and self.servo:
            self.servo.set_position(position)
    
    def set_eye_positions(self, left_pupil: Tuple[int, int], 
                         right_pupil: Tuple[int, int],
                         blink_amount: float = 0.0):
        """
        Set eye pupil positions manually
        
        Args:
            left_pupil: (x, y) position for left pupil
            right_pupil: (x, y) position for right pupil
            blink_amount: Blink amount (0.0 = open, 1.0 = closed)
        """
        if self.enable_eyes and self.eyes:
            self._performance_active = True  # Disable background animation
            self.eyes.draw_eyes(left_pupil, right_pupil, blink_amount)
            self._performance_active = False
    
    def blink(self, duration: float = 0.3):
        """
        Perform a single blink
        
        Args:
            duration: Blink duration in seconds
        """
        if not self.enable_eyes or not self.eyes:
            return
        
        self._performance_active = True
        
        steps = int(duration * 30)  # 30 FPS
        
        for i in range(steps):
            # Blink animation curve (quick close, slower open)
            progress = i / steps
            if progress <= 0.33:
                blink_amount = progress * 3.0
            else:
                blink_amount = 1.0 - ((progress - 0.33) / 0.67)
            
            self.eyes.draw_eyes(
                left_pupil=self._current_look,
                right_pupil=self._current_look,
                blink_amount=blink_amount
            )
            
            time.sleep(duration / steps)
        
        self._performance_active = False
    
    def test_systems(self):
        """Test all enabled systems"""
        print("🔧 Testing animatronic systems...")
        
        if self.enable_eyes and self.eyes:
            print("👁️ Testing eyes...")
            # Test eye colors
            colors = [("red", (0x00, 0xF8)), ("green", (0x1F, 0x00)), 
                     ("blue", (0xE0, 0x07)), ("white", (0xFF, 0xFF))]
            
            for color_name, color_value in colors:
                print(f"   {color_name}...")
                self.eyes.left_display.fill_screen(color_value)
                self.eyes.right_display.fill_screen(color_value)
                time.sleep(1)
            
            # Test eye movement
            print("   Eye movement...")
            for angle in range(0, 360, 30):
                x = int(math.cos(math.radians(angle)) * 10)
                y = int(math.sin(math.radians(angle)) * 8)
                self.set_eye_positions((x, y), (x, y))
                time.sleep(0.2)
            
            # Test blinking
            print("   Blinking...")
            for _ in range(3):
                self.blink()
                time.sleep(0.5)
        
        if self.enable_servo and self.lipsync:
            print("🗣️ Testing servo...")
            self.lipsync.test_movement()
        
        print("✅ System test completed")
    
    def stop_performance(self):
        """Stop current performance"""
        self._performance_active = False
        if self.audio:
            self.audio.stop()
        if self.servo:
            self.servo.center()
        print("⏹️ Performance stopped")
    
    def close(self):
        """Clean up all resources"""
        print("🔧 Shutting down animatronic systems...")
        
        # Stop background animation
        self._animation_active = False
        if self._animation_thread:
            self._animation_thread.join(timeout=1)
        
        # Stop any active performance
        self.stop_performance()
        
        # Close subsystems
        if self.eyes:
            self.eyes.close()
        
        if self.servo:
            self.servo.close()
        
        if self.audio:
            self.audio.close()
        
        print("✅ Animatronic system shutdown complete")


if __name__ == "__main__":
    print("Animatronic Controller - Test Mode")
    print("This module should be imported, not run directly")
    print("See examples/ directory for usage examples")