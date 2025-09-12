#!/usr/bin/env python3
"""
Basic Animatronic Usage Example
==============================

This example demonstrates basic usage of the animatronic system
with a simple performance playback.

Requirements:
- Lip-sync JSON file
- Audio file (WAV, MP3, M4A)
- Hardware setup (eyes, servo, audio)
"""

import sys
from pathlib import Path

# Add src directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from animatronic import AnimatronicController


def main():
    """Run basic animatronic example"""
    print("🤖 Basic Animatronic Example")
    print("=" * 30)
    
    # Create controller with all systems enabled
    robot = AnimatronicController(
        servo_channel=0,           # Servo on channel 0
        left_eye_pins=(24, 25),    # Left eye DC=GPIO24, RST=GPIO25
        right_eye_pins=(23, 22),   # Right eye DC=GPIO23, RST=GPIO22
        enable_eyes=True,
        enable_servo=True,
        enable_audio=True
    )
    
    try:
        # Initialize all systems
        if not robot.initialize():
            print("❌ Failed to initialize robot systems")
            return 1
        
        # Test all systems
        print("\n🔧 Testing systems...")
        robot.test_systems()
        
        # Look for performance files in bundles directory
        bundle_dir = Path("bundles")
        if bundle_dir.exists():
            # Find first available bundle
            for bundle_path in bundle_dir.iterdir():
                if bundle_path.is_dir():
                    lipsync_file = bundle_path / "song.lipsync.json"
                    audio_files = list(bundle_path.glob("*.wav")) + list(bundle_path.glob("*.m4a"))
                    
                    if lipsync_file.exists() and audio_files:
                        print(f"\n🎭 Playing performance from {bundle_path.name}")
                        
                        # Play the performance
                        robot.play_performance(lipsync_file, audio_files[0])
                        break
            else:
                print("\n⚠️ No performance bundles found in bundles/ directory")
                print("   Demonstrating manual control instead...")
                
                # Manual control demonstration
                import time
                import math
                
                print("📱 Manual control demo - 10 seconds")
                start_time = time.perf_counter()
                
                while time.perf_counter() - start_time < 10:
                    t = time.perf_counter() - start_time
                    
                    # Animate mouth with sine wave
                    mouth_pos = (math.sin(t * 2) + 1) / 4  # 0.0 to 0.5
                    robot.set_mouth_position(mouth_pos)
                    
                    # Move eyes in figure-8 pattern
                    eye_x = int(math.sin(t) * 10)
                    eye_y = int(math.sin(t * 2) * 5)
                    robot.set_eye_positions((eye_x, eye_y), (eye_x, eye_y))
                    
                    time.sleep(1/30)  # 30 FPS
                
                print("✓ Manual control demo completed")
        
        else:
            print("⚠️ bundles/ directory not found")
        
        print("\n✅ Example completed successfully!")
        return 0
        
    except KeyboardInterrupt:
        print("\n⏸️ Example interrupted by user")
        return 1
    except Exception as e:
        print(f"\n❌ Example failed: {e}")
        return 1
    finally:
        # Always clean up
        robot.close()


if __name__ == "__main__":
    exit(main())