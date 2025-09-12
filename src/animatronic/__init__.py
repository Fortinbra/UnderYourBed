"""
Animatronic Control System
=========================

A modular Python library for controlling animatronic systems with synchronized
audio, servo movement, and OLED eye displays.

Modules:
- display: OLED eye display control (SSD1351)
- servo: Servo motor control for mouth movement
- audio: Audio playback and lip-sync data processing
- controller: High-level system orchestration

Example usage:
    from animatronic import AnimatronicController
    
    robot = AnimatronicController()
    robot.initialize()
    robot.play_performance("bundle/song.lipsync.json", "bundle/audio.wav")
    robot.close()
"""

from .display import SSD1351Display, EyeRenderer, DualEyeController, Colors
from .servo import ServoController, LipSyncController
from .audio import AudioPlayer, LipSyncData
from .controller import AnimatronicController

__version__ = "1.0.0"
__author__ = "UnderYourBed Project"

__all__ = [
    "SSD1351Display",
    "EyeRenderer", 
    "DualEyeController",
    "Colors",
    "ServoController",
    "LipSyncController", 
    "AudioPlayer",
    "LipSyncData",
    "AnimatronicController"
]