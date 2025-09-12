#!/usr/bin/env python3
"""
Servo Control Module for Animatronic Mouth
==========================================

This module provides servo control for animatronic mouth movement,
typically used for lip-sync animation. Supports PCA9685 servo drivers
and direct PWM control.

Features:
- PCA9685 servo driver support via Adafruit ServoKit
- Configurable servo channels and ranges
- Smooth position interpolation
- Safe positioning with limits
- Graceful degradation when hardware unavailable

Hardware Requirements:
- Adafruit PCA9685 servo driver board
- Standard servo motor (SG90, MG996R, etc.)
- I2C connection to Raspberry Pi

Usage:
    from animatronic.servo import ServoController
    
    servo = ServoController(channel=0)
    servo.initialize()
    servo.set_position(0.5)  # 50% open
    servo.close()
"""

import time
from typing import Optional


class ServoController:
    """
    Servo motor controller for animatronic mouth movement
    
    Provides high-level interface for controlling servo position with
    safety limits and smooth movement capabilities.
    """
    
    def __init__(self, channel: int = 0, min_angle: float = 0, max_angle: float = 180,
                 min_position: float = 0.0, max_position: float = 1.0):
        """
        Initialize servo controller
        
        Args:
            channel: Servo channel on PCA9685 board (0-15)
            min_angle: Minimum servo angle in degrees
            max_angle: Maximum servo angle in degrees  
            min_position: Logical minimum position (0.0 = closed mouth)
            max_position: Logical maximum position (1.0 = open mouth)
        """
        self.channel = channel
        self.min_angle = min_angle
        self.max_angle = max_angle
        self.min_position = min_position
        self.max_position = max_position
        
        # Hardware handles
        self.kit = None
        self.servo = None
        self._initialized = False
        self._current_position = 0.0
        
        print(f"Servo controller created - Channel: {channel}, Range: {min_angle}°-{max_angle}°")
    
    def initialize(self) -> bool:
        """
        Initialize servo hardware
        
        Returns:
            True if initialization successful, False otherwise
        """
        try:
            from adafruit_servokit import ServoKit
            
            # Initialize PCA9685 board
            self.kit = ServoKit(channels=16)
            self.servo = self.kit.servo[self.channel]
            
            # Configure servo range
            self.servo.set_pulse_width_range(500, 2500)  # Standard servo range
            
            # Set to center position
            self.set_position(0.0)
            
            self._initialized = True
            print(f"✓ Servo initialized on channel {self.channel}")
            return True
            
        except ImportError:
            print("⚠️ ServoKit library not available (install adafruit-circuitpython-pca9685)")
            return False
        except Exception as e:
            print(f"✗ Servo initialization failed: {e}")
            return False
    
    def set_position(self, position: float):
        """
        Set servo to specific position
        
        Args:
            position: Target position (0.0 = closed, 1.0 = fully open)
        """
        if not self._initialized:
            return
        
        # Clamp position to valid range
        position = max(self.min_position, min(self.max_position, position))
        
        try:
            # Convert logical position to servo angle
            angle_range = self.max_angle - self.min_angle
            target_angle = self.min_angle + (position * angle_range)
            
            # Set servo angle
            self.servo.angle = target_angle
            self._current_position = position
            
        except Exception as e:
            print(f"⚠️ Servo position error: {e}")
    
    def get_position(self) -> float:
        """
        Get current servo position
        
        Returns:
            Current position (0.0 to 1.0)
        """
        return self._current_position
    
    def move_to(self, target_position: float, duration: float = 1.0, steps: int = 20):
        """
        Smoothly move servo to target position over time
        
        Args:
            target_position: Target position (0.0 to 1.0)
            duration: Movement duration in seconds
            steps: Number of intermediate steps
        """
        if not self._initialized:
            return
        
        start_position = self._current_position
        step_delay = duration / steps
        
        for i in range(steps + 1):
            # Calculate intermediate position
            progress = i / steps
            current_pos = start_position + (target_position - start_position) * progress
            
            self.set_position(current_pos)
            
            if i < steps:  # Don't sleep after final step
                time.sleep(step_delay)
    
    def center(self):
        """Move servo to center position (50% open)"""
        self.set_position(0.5)
    
    def close_mouth(self):
        """Move servo to closed position"""
        self.set_position(0.0)
    
    def open_mouth(self):
        """Move servo to fully open position"""
        self.set_position(1.0)
    
    def is_initialized(self) -> bool:
        """Check if servo is properly initialized"""
        return self._initialized
    
    def close(self):
        """
        Clean up servo resources and center position
        """
        if self._initialized:
            try:
                # Center servo before shutdown
                self.center()
                time.sleep(0.5)  # Allow time for movement
                print(f"✓ Servo channel {self.channel} centered and closed")
            except:
                pass
        
        self._initialized = False


class LipSyncController:
    """
    High-level lip-sync animation controller
    
    Coordinates servo movement with audio playback timing for realistic
    lip-sync animation based on phoneme or volume data.
    """
    
    def __init__(self, servo_controller: ServoController):
        """
        Initialize lip-sync controller
        
        Args:
            servo_controller: ServoController instance to control
        """
        self.servo = servo_controller
        self.is_playing = False
    
    def play_lipsync_data(self, frames: list, frame_rate: float = 30.0):
        """
        Play back lip-sync animation data
        
        Args:
            frames: List of mouth positions (0.0 to 1.0) or frame objects
            frame_rate: Playback frame rate (frames per second)
        """
        if not self.servo.is_initialized():
            print("⚠️ Servo not initialized - cannot play lip-sync")
            return
        
        frame_duration = 1.0 / frame_rate
        self.is_playing = True
        
        try:
            print(f"🎬 Playing {len(frames)} lip-sync frames at {frame_rate} FPS")
            
            for i, frame in enumerate(frames):
                if not self.is_playing:
                    break
                
                # Extract position value from frame
                if isinstance(frame, dict):
                    position = frame.get('mouth', 0.0)
                elif isinstance(frame, (list, tuple)):
                    position = frame[0] if frame else 0.0
                else:
                    position = float(frame)
                
                # Set servo position
                self.servo.set_position(position)
                
                # Progress indicator (every 15 frames = ~0.5 seconds at 30fps)
                if i % 15 == 0:
                    print(f"⏱️  {i//30}s 🗣️ - mouth: {position:.2f}")
                
                time.sleep(frame_duration)
            
            print("✓ Lip-sync playback completed")
            
        except KeyboardInterrupt:
            print("⏸️ Lip-sync interrupted by user")
        except Exception as e:
            print(f"✗ Lip-sync playback error: {e}")
        finally:
            self.is_playing = False
            self.servo.center()
    
    def stop(self):
        """Stop lip-sync playback"""
        self.is_playing = False
        self.servo.center()
        print("⏹️ Lip-sync stopped")
    
    def test_movement(self):
        """Test servo movement with a simple animation"""
        if not self.servo.is_initialized():
            print("⚠️ Servo not initialized - cannot test")
            return
        
        print("🔧 Testing servo movement...")
        
        # Test sequence: closed -> open -> closed
        positions = [0.0, 0.3, 0.7, 1.0, 0.7, 0.3, 0.0]
        
        for position in positions:
            print(f"   Position: {position:.1f}")
            self.servo.set_position(position)
            time.sleep(0.5)
        
        print("✓ Servo test completed")


if __name__ == "__main__":
    print("Servo Control Module - Test Mode")
    print("This module should be imported, not run directly")
    print("See examples/ directory for usage examples")