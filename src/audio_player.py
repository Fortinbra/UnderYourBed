#!/usr/bin/env python3
"""
Audio Player for UnderYourBed Animatronic Project
Plays audio files through USB audio device using ffmpeg
"""

import os
import sys
import subprocess
from pathlib import Path


class AudioPlayer:
    def __init__(self):
        self.audio_file = None
        self.usb_device = "hw:0,0"  # USB Audio Device is card 0
        self.ffmpeg_process = None
        self.aplay_process = None
        print(f"Audio player initialized - Target device: {self.usb_device}")
        
    def load_audio_file(self, file_path):
        """Load audio file for playback"""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Audio file not found: {file_path}")
            
        self.audio_file = file_path
        print(f"Loaded audio file: {file_path}")
        
    def play(self, blocking=True):
        """Play the loaded audio file through USB audio device
        
        Args:
            blocking (bool): If True, wait for playback to complete. If False, return immediately.
        """
        if not self.audio_file:
            raise ValueError("No audio file loaded")
            
        try:
            print("Starting audio playback through USB audio device...")
            
            # Use ffmpeg to decode and aplay to output to specific device
            # Convert to stereo and proper sample rate for USB device compatibility
            cmd = [
                'ffmpeg', '-i', self.audio_file,
                '-f', 'wav',
                '-acodec', 'pcm_s16le',
                '-ar', '44100',
                '-ac', '2',  # Force stereo output
                '-'
            ]
            
            aplay_cmd = [
                'aplay', '-D', self.usb_device,
                '-f', 'S16_LE',
                '-r', '44100',
                '-c', '2'
            ]
            
            # Pipe ffmpeg output to aplay
            self.ffmpeg_process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
            self.aplay_process = subprocess.Popen(aplay_cmd, stdin=self.ffmpeg_process.stdout, stderr=subprocess.DEVNULL)
            
            # Close ffmpeg stdout in parent to allow ffmpeg to receive SIGPIPE if aplay exits
            self.ffmpeg_process.stdout.close()
            
            if blocking:
                # Wait for playback to complete
                self.aplay_process.wait()
                self.ffmpeg_process.wait()
                
                if self.aplay_process.returncode == 0:
                    print("Playback completed successfully")
                else:
                    print(f"Playback failed with return code: {self.aplay_process.returncode}")
            else:
                print("Audio playback started in background")
                
        except Exception as e:
            print(f"Error during playback: {e}")
            raise
            
    def stop(self):
        """Stop audio playback"""
        try:
            if self.aplay_process and self.aplay_process.poll() is None:
                self.aplay_process.terminate()
                self.aplay_process.wait(timeout=2)
                
            if self.ffmpeg_process and self.ffmpeg_process.poll() is None:
                self.ffmpeg_process.terminate()
                self.ffmpeg_process.wait(timeout=2)
                
            print("Audio playback stopped")
        except Exception as e:
            print(f"Error stopping playback: {e}")
            # Force kill if needed
            subprocess.run(['pkill', '-f', 'ffmpeg.*original.m4a'], check=False)
            subprocess.run(['pkill', '-f', 'aplay.*hw:0,0'], check=False)
        
    def cleanup(self):
        """Clean up any remaining processes"""
        self.stop()


def main():
    """Main function to play the bundled audio file"""
    # Path to the audio file
    audio_file_path = "/home/fortinbra/UnderYourBed-1/bundles/G-YNNJIe2Vk_20250904-030059/original.m4a"
    
    try:
        # Create audio player
        player = AudioPlayer()
        
        # Load and play the audio file
        player.load_audio_file(audio_file_path)
        player.play()
        
        # Cleanup
        player.cleanup()
        
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()