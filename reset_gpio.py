#!/usr/bin/env python3
"""
GPIO Reset Script for OLED Eyes

Resets GPIO pins used by the OLED displays to clear any "GPIO busy" state.
Run this before starting the main animatronic system if you get GPIO errors.
"""

import time
import board
import digitalio

def reset_gpio():
    """Reset all GPIO pins used by the OLED displays"""
    
    # Define all pins used by the OLED displays
    pin_numbers = [
        board.D8,   # Left CS (GPIO8/Pin24)
        board.D24,  # Left DC (GPIO24/Pin18)
        board.D25,  # Left RST (GPIO25/Pin22)
        board.D7,   # Right CS (GPIO7/Pin26)
        board.D23,  # Right DC (GPIO23/Pin16)
        board.D22,  # Right RST (GPIO22/Pin15)
    ]
    
    pin_names = [
        "Left CS (GPIO8/Pin24)",
        "Left DC (GPIO24/Pin18)",
        "Left RST (GPIO25/Pin22)",
        "Right CS (GPIO7/Pin26)",
        "Right DC (GPIO23/Pin16)",
        "Right RST (GPIO22/Pin15)",
    ]
    
    print("Resetting OLED GPIO pins...")
    
    for pin, name in zip(pin_numbers, pin_names):
        try:
            # Initialize pin
            gpio_pin = digitalio.DigitalInOut(pin)
            print(f"  Resetting {name}...")
            
            # Set as output and toggle to reset state
            gpio_pin.direction = digitalio.Direction.OUTPUT
            gpio_pin.value = False
            time.sleep(0.01)
            gpio_pin.value = True
            time.sleep(0.01)
            
            # Deinitialize to release
            gpio_pin.deinit()
            print(f"  ✓ {name} reset successfully")
            
        except Exception as e:
            print(f"  ⚠ Could not reset {name}: {e}")
    
    print("GPIO reset complete!")
    print("You can now run the main animatronic system.")

if __name__ == "__main__":
    reset_gpio()