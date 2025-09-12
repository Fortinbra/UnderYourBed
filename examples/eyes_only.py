#!/usr/bin/env python3
"""
Eyes Only Example
================

Demonstrates eye display control without servo or audio.
Good for testing eye displays independently.
"""

import sys
import time
import math
from pathlib import Path

# Add src directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from animatronic.display import DualEyeController, Colors


def main():
    """Run eyes-only example"""
    print("👁️👁️ Eyes Only Example")
    print("=" * 25)
    
    # Create dual eye controller
    eyes = DualEyeController(
        left_dc=24, left_rst=25,    # Left eye pins
        right_dc=23, right_rst=22   # Right eye pins
    )
    
    try:
        # Initialize displays
        if not eyes.initialize():
            print("❌ Failed to initialize eye displays")
            return 1
        
        # Test solid colors
        print("🎨 Testing colors...")
        test_colors = [
            ("Red", Colors.RED),
            ("Green", Colors.GREEN), 
            ("Blue", Colors.BLUE),
            ("White", Colors.WHITE),
            ("Yellow", Colors.YELLOW),
            ("Magenta", Colors.MAGENTA),
            ("Cyan", Colors.CYAN)
        ]
        
        for color_name, color_value in test_colors:
            print(f"   {color_name}...")
            eyes.left_display.fill_screen(color_value)
            eyes.right_display.fill_screen(color_value)
            time.sleep(1)
        
        # Test eyeball animation
        print("👁️ Testing eyeball animation...")
        
        # Looking around in circle
        print("   Circle pattern...")
        for angle in range(0, 720, 5):  # Two full circles
            x = int(math.cos(math.radians(angle)) * 15)
            y = int(math.sin(math.radians(angle)) * 10)
            eyes.draw_eyes((x, y), (x, y))
            time.sleep(0.05)
        
        # Blinking test
        print("   Blink test...")
        for _ in range(5):
            # Blink animation
            for blink in [0.0, 0.3, 0.7, 1.0, 0.7, 0.3, 0.0]:
                eyes.draw_eyes((0, 0), (0, 0), blink_amount=blink)
                time.sleep(0.05)
            time.sleep(0.5)
        
        # Independent eye movement
        print("   Independent eye movement...")
        for i in range(60):  # 2 seconds at 30fps
            left_x = int(math.sin(i * 0.1) * 12)
            left_y = int(math.cos(i * 0.15) * 8)
            right_x = int(math.sin(i * 0.12) * 10)
            right_y = int(math.cos(i * 0.08) * 6)
            
            eyes.draw_eyes((left_x, left_y), (right_x, right_y))
            time.sleep(1/30)
        
        # Random movements
        print("   Random movements (5 seconds)...")
        import random
        start_time = time.perf_counter()
        
        while time.perf_counter() - start_time < 5:
            left_x = random.randint(-15, 15)
            left_y = random.randint(-10, 10)
            right_x = random.randint(-15, 15)
            right_y = random.randint(-10, 10)
            
            eyes.draw_eyes((left_x, left_y), (right_x, right_y))
            time.sleep(0.3)
        
        # Return to center
        eyes.draw_eyes((0, 0), (0, 0))
        
        print("✅ Eyes test completed!")
        return 0
        
    except KeyboardInterrupt:
        print("\n⏸️ Test interrupted by user")
        return 1
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        return 1
    finally:
        eyes.close()


if __name__ == "__main__":
    exit(main())