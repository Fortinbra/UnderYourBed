#!/usr/bin/env python3
"""
UnderYourBed Animatronic Controller
Main application that coordinates audio playback and servo movement for animatronic mouth
"""

import sys
import os
import time
import signal

# Add src directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from src.audio_player import AudioPlayer
from src.servo_controller import ServoController
# from src.oled_eyes import OLEDEyeController  # Disabled for now


class AnimatronicController:
    """Main controller for the UnderYourBed animatronic system"""
    
    def __init__(self, servo_channel=0, min_angle=0, max_angle=90, exaggeration=1.1, enable_eyes=False):
        """
        Initialize the animatronic controller
        
        Args:
            servo_channel (int): Servo channel for mouth movement
            min_angle (float): Servo angle when mouth is closed
            max_angle (float): Servo angle when mouth is fully open
            exaggeration (float): Movement exaggeration factor (1.1 = 10% more pronounced)
            enable_eyes (bool): Whether to initialize OLED eyes
        """
        # Initialize controllers
        self.audio_player = AudioPlayer()
        self.servo_controller = ServoController()
        self.eye_controller = None  # Eyes disabled for now
        self.enable_eyes = enable_eyes
        
        # OLED eyes are disabled - can be re-enabled later
        # if enable_eyes:
        #     self.eye_controller = OLEDEyeController()
        #     self.eye_controller.initialize()
        
        self.is_running = False
        
        # Set up signal handlers for clean shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        print("UnderYourBed Animatronic Controller initialized")
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully"""
        print(f"\nReceived signal {signum}, shutting down...")
        self.stop()
        sys.exit(0)
    
    def load_content(self, audio_file_path, lipsync_file_path):
        """Load audio and lipsync data"""
        print("Loading content...")
        self.audio_player.load_audio_file(audio_file_path)
        self.servo_controller.load_lipsync_data(lipsync_file_path)
        print("Content loaded successfully")
    
    def play(self, start_time=0.0):
        """
        Start synchronized audio and servo playback
        
        Args:
            start_time (float): Time offset to start from (seconds)
        """
        if self.is_running:
            print("Already playing")
            return
        
        print(f"Starting playback from {start_time:.1f}s...")
        print("Press Ctrl+C to stop")
        
        self.is_running = True
        
        try:
            # Start servo animation (non-blocking)
            self.servo_controller.play_lipsync(start_time=start_time)
            
            # Start eye animation if available (non-blocking)
            if self.eye_controller:
                # Calculate duration from audio file (default to 60 seconds if unknown)
                duration = 60.0  # Could be extracted from audio metadata
                self.eye_controller.animate_idle(duration=duration)
            
            # Start audio playback (blocking)
            self.audio_player.play(blocking=True)
            
            # Wait for servo to finish if audio ends first
            while self.servo_controller.is_playing and self.is_running:
                time.sleep(0.1)
            
            # Stop eye animation
            if self.eye_controller:
                self.eye_controller.stop_animation()
                
        except KeyboardInterrupt:
            print("\nPlayback interrupted by user")
        except Exception as e:
            print(f"Error during playback: {e}")
        finally:
            self.is_running = False
            print("Playback finished")
    
    def stop(self):
        """Stop all playback"""
        if self.is_running:
            print("Stopping playback...")
            self.is_running = False
            self.servo_controller.stop_lipsync()
            self.audio_player.stop()
            if self.eye_controller:
                self.eye_controller.stop_animation()
    
    def cleanup(self):
        """Clean up all resources"""
        self.stop()
        self.audio_player.cleanup()
        self.servo_controller.cleanup()
        if self.eye_controller:
            self.eye_controller.cleanup()
        print("Cleanup complete")


def main():
    """Main application entry point"""
    # Default content paths
    audio_file = "/home/fortinbra/UnderYourBed-1/bundles/G-YNNJIe2Vk_20250904-030059/original.m4a"
    lipsync_file = "/home/fortinbra/UnderYourBed-1/bundles/G-YNNJIe2Vk_20250904-030059/song.lipsync.json"
    
    try:
        # Initialize controller with servo, eyes, and 10% mouth exaggeration
        controller = AnimatronicController(
            servo_channel=0, min_angle=0, max_angle=90, 
            exaggeration=1.1, enable_eyes=True
        )
        
        # Load content
        controller.load_content(audio_file, lipsync_file)
        
        # Start playback
        controller.play(start_time=0.0)
        
    except Exception as e:
        print(f"Error: {e}")
        return 1
    finally:
        if 'controller' in locals():
            controller.cleanup()
    
    return 0


if __name__ == "__main__":
    sys.exit(main())