#!/usr/bin/env python3
"""
Servo Controller for UnderYourBed Animatronic Project
Controls servos using lipsync data from JSON files via Adafruit Servo HAT
"""

import json
import time
import threading
from typing import List, Dict, Optional
from adafruit_servokit import ServoKit


class LipsyncFrame:
    """Represents a single frame of lipsync data"""
    def __init__(self, time_seconds: float, mouth_open: float):
        self.time_seconds = time_seconds
        self.mouth_open = mouth_open  # 0.0 to 1.0


class ServoController:
    """Controls servos for animatronic mouth movement using lipsync data"""
    
    def __init__(self, servo_channel: int = 0, min_angle: float = 0, max_angle: float = 180, exaggeration: float = 1.1):
        """
        Initialize servo controller
        
        Args:
            servo_channel (int): Servo channel on the Adafruit HAT (0-15)
            min_angle (float): Minimum servo angle (mouth closed)
            max_angle (float): Maximum servo angle (mouth fully open)
            exaggeration (float): Movement exaggeration factor (1.0 = normal, 1.1 = 10% more pronounced)
        """
        self.servo_channel = servo_channel
        self.min_angle = min_angle
        self.max_angle = max_angle
        self.exaggeration = exaggeration
        self.lipsync_data: List[LipsyncFrame] = []
        self.is_playing = False
        self.playback_thread: Optional[threading.Thread] = None
        
        try:
            # Initialize the Servo HAT (supports 16 servos)
            self.kit = ServoKit(channels=16)
            self.simulation_mode = False
            print(f"Servo controller initialized - Channel: {servo_channel}, Range: {min_angle}°-{max_angle}°, Exaggeration: {exaggeration:.1f}x")
            
            # Set initial position (mouth closed)
            self.set_mouth_position(0.0)
            
        except Exception as e:
            print(f"Warning: Could not initialize servo hardware: {e}")
            print("Running in simulation mode - servo commands will be shown")
            self.kit = None
            self.simulation_mode = True
    
    def load_lipsync_data(self, json_file_path: str):
        """Load lipsync data from JSON file"""
        try:
            with open(json_file_path, 'r') as f:
                data = json.load(f)
            
            self.lipsync_data = []
            
            # Parse the frame-based lipsync data
            if 'frames' in data:
                for frame in data['frames']:
                    time_sec = frame.get('TimeSeconds', 0.0)
                    mouth_open = frame.get('MouthOpen01', 0.0)
                    self.lipsync_data.append(LipsyncFrame(time_sec, mouth_open))
                    
                print(f"Loaded {len(self.lipsync_data)} lipsync frames from {json_file_path}")
                
                # Print some stats
                max_mouth = max(frame.mouth_open for frame in self.lipsync_data)
                duration = self.lipsync_data[-1].time_seconds if self.lipsync_data else 0
                print(f"Duration: {duration:.2f}s, Max mouth opening: {max_mouth:.2f}")
                
            else:
                raise ValueError("JSON file must contain 'frames' array with TimeSeconds and MouthOpen01")
                
        except Exception as e:
            print(f"Error loading lipsync data: {e}")
            raise
    
    def set_mouth_position(self, mouth_open_ratio: float):
        """
        Set servo position based on mouth opening ratio
        
        Args:
            mouth_open_ratio (float): 0.0 (closed) to 1.0 (fully open)
        """
        # Clamp the ratio to valid range first
        mouth_open_ratio = max(0.0, min(1.0, mouth_open_ratio))
        
        # Apply configurable exaggeration to make movements more pronounced
        # This helps compensate for having only one servo vs multiple mouth actuators
        exaggerated_ratio = mouth_open_ratio * self.exaggeration
        
        # Ensure we don't exceed the valid range after exaggeration
        exaggerated_ratio = min(1.0, exaggerated_ratio)
        
        # Map ratio to servo angle
        angle = self.min_angle + (exaggerated_ratio * (self.max_angle - self.min_angle))
        
        if self.kit:
            try:
                self.kit.servo[self.servo_channel].angle = angle
            except Exception as e:
                print(f"Error setting servo angle: {e}")
        else:
            # Simulation mode - only show significant changes
            if not hasattr(self, '_last_angle') or abs(angle - self._last_angle) > 2:
                print(f"SERVO: Channel {self.servo_channel} -> {angle:.1f}° (mouth: {mouth_open_ratio:.2f} -> {exaggerated_ratio:.2f})")
                self._last_angle = angle
    
    def play_lipsync(self, start_time: float = 0.0):
        """
        Play the loaded lipsync animation
        
        Args:
            start_time (float): Time offset to start from (useful for synchronization)
        """
        if not self.lipsync_data:
            raise ValueError("No lipsync data loaded")
        
        if self.is_playing:
            print("Lipsync already playing")
            return
        
        self.is_playing = True
        
        def playback_loop():
            try:
                print(f"Starting lipsync playback from {start_time:.2f}s")
                playback_start_time = time.time()
                
                for frame in self.lipsync_data:
                    if not self.is_playing:
                        break
                    
                    # Calculate when this frame should be displayed
                    target_time = playback_start_time + frame.time_seconds - start_time
                    current_time = time.time()
                    
                    # Wait if we're ahead of schedule
                    if target_time > current_time:
                        time.sleep(target_time - current_time)
                    
                    # Update servo position
                    self.set_mouth_position(frame.mouth_open)
                
                # Return to closed position
                self.set_mouth_position(0.0)
                print("Lipsync playback completed")
                
            except Exception as e:
                print(f"Error during lipsync playback: {e}")
            finally:
                self.is_playing = False
        
        # Start playback in separate thread for non-blocking operation
        self.playback_thread = threading.Thread(target=playback_loop, daemon=True)
        self.playback_thread.start()
    
    def stop_lipsync(self):
        """Stop lipsync playback"""
        if self.is_playing:
            self.is_playing = False
            print("Stopping lipsync playback")
            
            # Wait for thread to finish
            if self.playback_thread and self.playback_thread.is_alive():
                self.playback_thread.join(timeout=1.0)
            
            # Return to closed position
            self.set_mouth_position(0.0)
    
    def cleanup(self):
        """Clean up servo controller"""
        self.stop_lipsync()
        self.set_mouth_position(0.0)  # Ensure mouth is closed


def main():
    """Basic test for development - can be removed in production"""
    lipsync_file = "/home/fortinbra/UnderYourBed-1/bundles/G-YNNJIe2Vk_20250904-030059/song.lipsync.json"
    
    try:
        servo_controller = ServoController(servo_channel=0, min_angle=0, max_angle=90)
        servo_controller.load_lipsync_data(lipsync_file)
        
        print("Testing servo movement for 10 seconds...")
        servo_controller.play_lipsync(start_time=5.5)
        time.sleep(10)
        servo_controller.stop_lipsync()
        servo_controller.cleanup()
        
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    main()