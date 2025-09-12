#!/usr/bin/env python3
"""
Audio Playback Module for Animatronic Systems
=============================================

This module handles audio playback for animatronic systems, supporting
various audio formats and providing timing synchronization for lip-sync
animation.

Features:
- Multiple audio backend support (ffplay, sounddevice)
- Audio file format support (WAV, MP3, M4A)
- Timing synchronization for animation
- Volume control and audio monitoring
- Graceful fallback when audio hardware unavailable

Requirements:
- ffmpeg (for ffplay backend): sudo apt-get install -y ffmpeg
- sounddevice (alternative): pip install sounddevice

Usage:
    from animatronic.audio import AudioPlayer
    
    player = AudioPlayer()
    player.play_file("audio.wav")
    player.wait_for_completion()
"""

import subprocess
import time
import threading
from pathlib import Path
from typing import Optional, Union


class AudioPlayer:
    """
    Audio playback controller with timing synchronization
    
    Supports multiple audio backends and provides precise timing
    information for coordinating with animatronic movements.
    """
    
    def __init__(self, backend: str = "auto", volume: float = 1.0):
        """
        Initialize audio player
        
        Args:
            backend: Audio backend ("ffplay", "sounddevice", "auto")
            volume: Volume level (0.0 to 1.0)
        """
        self.backend = backend
        self.volume = max(0.0, min(1.0, volume))
        self._process = None
        self._start_time = None
        self._duration = None
        self._playing = False
        
        # Auto-detect best available backend
        if backend == "auto":
            self.backend = self._detect_backend()
        
        print(f"Audio player initialized - Backend: {self.backend}, Volume: {self.volume}")
    
    def _detect_backend(self) -> str:
        """Detect best available audio backend"""
        # Try ffplay first (most reliable for file playback)
        try:
            result = subprocess.run(["ffplay", "-version"], 
                                  capture_output=True, timeout=5)
            if result.returncode == 0:
                return "ffplay"
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass
        
        # Try sounddevice as fallback
        try:
            import sounddevice
            return "sounddevice"
        except ImportError:
            pass
        
        print("⚠️ No audio backend available - audio will be disabled")
        return "none"
    
    def play_file(self, audio_path: Union[str, Path], delay_ms: int = 0) -> bool:
        """
        Start playing audio file
        
        Args:
            audio_path: Path to audio file
            delay_ms: Delay before starting playback (milliseconds)
            
        Returns:
            True if playback started successfully
        """
        audio_path = Path(audio_path)
        
        if not audio_path.exists():
            print(f"✗ Audio file not found: {audio_path}")
            return False
        
        if self.backend == "none":
            print("⚠️ Audio playback disabled - no backend available")
            return False
        
        # Apply startup delay if specified
        if delay_ms > 0:
            time.sleep(delay_ms / 1000.0)
        
        try:
            if self.backend == "ffplay":
                return self._play_with_ffplay(audio_path)
            elif self.backend == "sounddevice":
                return self._play_with_sounddevice(audio_path)
            else:
                print(f"✗ Unknown audio backend: {self.backend}")
                return False
                
        except Exception as e:
            print(f"✗ Audio playback failed: {e}")
            return False
    
    def _play_with_ffplay(self, audio_path: Path) -> bool:
        """Play audio using ffplay subprocess"""
        try:
            # Build ffplay command
            cmd = [
                "ffplay",
                "-nodisp",  # No video display
                "-autoexit",  # Exit when done
                "-loglevel", "quiet",  # Suppress output
                "-volume", str(int(self.volume * 100)),  # Volume (0-100)
                str(audio_path)
            ]
            
            # Start subprocess
            self._process = subprocess.Popen(cmd)
            self._start_time = time.perf_counter()
            self._playing = True
            
            print(f"✓ Audio playback started: {audio_path.name}")
            return True
            
        except Exception as e:
            print(f"✗ ffplay error: {e}")
            return False
    
    def _play_with_sounddevice(self, audio_path: Path) -> bool:
        """Play audio using sounddevice library"""
        try:
            import sounddevice as sd
            import soundfile as sf
            
            # Load audio file
            data, sample_rate = sf.read(str(audio_path))
            
            # Apply volume
            if self.volume != 1.0:
                data = data * self.volume
            
            # Start playback in separate thread
            def play_audio():
                sd.play(data, sample_rate)
                sd.wait()  # Wait for playback to complete
                self._playing = False
            
            threading.Thread(target=play_audio, daemon=True).start()
            
            self._start_time = time.perf_counter()
            self._playing = True
            self._duration = len(data) / sample_rate
            
            print(f"✓ Audio playback started: {audio_path.name}")
            return True
            
        except ImportError:
            print("✗ sounddevice/soundfile not available")
            return False
        except Exception as e:
            print(f"✗ sounddevice error: {e}")
            return False
    
    def stop(self):
        """Stop audio playback"""
        if self._process:
            try:
                self._process.terminate()
                self._process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                self._process.kill()
            except:
                pass
            finally:
                self._process = None
        
        if self.backend == "sounddevice":
            try:
                import sounddevice as sd
                sd.stop()
            except:
                pass
        
        self._playing = False
        print("⏹️ Audio playback stopped")
    
    def is_playing(self) -> bool:
        """Check if audio is currently playing"""
        if not self._playing:
            return False
        
        # Check if ffplay process is still running
        if self._process:
            poll = self._process.poll()
            if poll is not None:  # Process has finished
                self._playing = False
                return False
        
        return True
    
    def get_position(self) -> float:
        """
        Get current playback position in seconds
        
        Returns:
            Current position in seconds since playback started
        """
        if not self._start_time:
            return 0.0
        
        return time.perf_counter() - self._start_time
    
    def wait_for_completion(self, timeout: Optional[float] = None) -> bool:
        """
        Wait for audio playback to complete
        
        Args:
            timeout: Maximum wait time in seconds (None = infinite)
            
        Returns:
            True if completed normally, False if timed out
        """
        start_wait = time.perf_counter()
        
        while self.is_playing():
            if timeout and (time.perf_counter() - start_wait) > timeout:
                return False
            time.sleep(0.1)
        
        return True
    
    def get_volume(self) -> float:
        """Get current volume level"""
        return self.volume
    
    def set_volume(self, volume: float):
        """
        Set volume level (for future playback)
        
        Args:
            volume: Volume level (0.0 to 1.0)
        """
        self.volume = max(0.0, min(1.0, volume))
    
    def close(self):
        """Clean up audio resources"""
        self.stop()
        print("✓ Audio player closed")


class LipSyncData:
    """
    Lip-sync data loader and processor
    
    Handles loading and processing of lip-sync animation data from JSON files
    generated by the pipeline processing system.
    """
    
    def __init__(self):
        self.frames = []
        self.words = []
        self.duration = 0.0
        self.frame_rate = 30.0
    
    def load_from_file(self, json_path: Union[str, Path]) -> bool:
        """
        Load lip-sync data from JSON file
        
        Args:
            json_path: Path to lip-sync JSON file
            
        Returns:
            True if loaded successfully
        """
        try:
            import json
            
            json_path = Path(json_path)
            if not json_path.exists():
                print(f"✗ Lip-sync file not found: {json_path}")
                return False
            
            data = json.loads(json_path.read_text())
            
            # Handle both simple array and object format
            if isinstance(data, list):
                self.frames = data
                self.words = []
            else:
                self.frames = data.get("frames", [])
                self.words = data.get("words", [])
            
            # Validate frame format
            if not self.frames:
                print("✗ No frames found in lip-sync data")
                return False
            
            # Validate required fields
            for frame in self.frames:
                if not isinstance(frame, dict):
                    print("✗ Invalid frame format - expected dictionary")
                    return False
                
                if "TimeSeconds" not in frame or "MouthOpen01" not in frame:
                    print("✗ Invalid frame missing TimeSeconds/MouthOpen01")
                    return False
            
            # Calculate duration and frame rate
            if len(self.frames) > 1:
                self.duration = self.frames[-1]["TimeSeconds"]
                self.frame_rate = len(self.frames) / self.duration
            
            print(f"✓ Loaded {len(self.frames)} lip-sync frames")
            print(f"   Duration: {self.duration:.2f}s, Frame rate: {self.frame_rate:.1f} FPS")
            
            return True
            
        except Exception as e:
            print(f"✗ Failed to load lip-sync data: {e}")
            return False
    
    def get_frames(self) -> list:
        """Get list of lip-sync frames"""
        return self.frames
    
    def get_frame_count(self) -> int:
        """Get total number of frames"""
        return len(self.frames)
    
    def get_duration(self) -> float:
        """Get total duration in seconds"""
        return self.duration
    
    def get_frame_rate(self) -> float:
        """Get average frame rate"""
        return self.frame_rate
    
    def get_frame_at_time(self, time_seconds: float) -> Optional[dict]:
        """
        Get lip-sync frame at specific time
        
        Args:
            time_seconds: Time position in seconds
            
        Returns:
            Frame data dictionary or None if not found
        """
        if not self.frames:
            return None
        
        # Find closest frame by time
        best_frame = None
        best_diff = float('inf')
        
        for frame in self.frames:
            time_diff = abs(frame["TimeSeconds"] - time_seconds)
            if time_diff < best_diff:
                best_diff = time_diff
                best_frame = frame
        
        return best_frame
    
    def get_mouth_position_at_time(self, time_seconds: float) -> float:
        """
        Get mouth position at specific time
        
        Args:
            time_seconds: Time position in seconds
            
        Returns:
            Mouth position (0.0 to 1.0)
        """
        frame = self.get_frame_at_time(time_seconds)
        return frame["MouthOpen01"] if frame else 0.0


if __name__ == "__main__":
    print("Audio Module - Test Mode")
    print("This module should be imported, not run directly")
    print("See examples/ directory for usage examples")