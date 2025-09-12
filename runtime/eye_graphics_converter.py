#!/usr/bin/env python3
"""
PNG Eye Graphics Converter for SSD1351 128x128 OLED Displays
Converts Uncanny Eyes PNG graphics to texture maps for proper eye rendering
Based on the original Uncanny Eyes texture mapping approach
"""

import sys
import os
import math
import json
from PIL import Image

class EyeTextureConverter:
    """Convert PNG eye graphics to texture maps for realistic eye rendering"""
    
    def __init__(self, eye_type="defaultEye"):
        self.eye_type = eye_type
        self.base_path = "/home/fortinbra/UnderYourBed-1/lib/Uncanny_Eyes/convert"
        self.eye_path = os.path.join(self.base_path, eye_type)
        self.display_size = (128, 128)
        
        # Loaded texture maps
        self.sclera_texture = None      # White of the eye texture
        self.iris_texture = None        # Colored iris texture  
        self.pupil_map = None           # Pupil shape map
        self.lid_upper_map = None       # Upper eyelid threshold map
        self.lid_lower_map = None       # Lower eyelid threshold map
        
        # Generated lookup tables
        self.polar_map = None           # Polar coordinate mapping for iris
        
    def load_textures(self):
        """Load all PNG texture maps for the eye type"""
        try:
            # Load sclera texture (white of the eye)
            sclera_path = os.path.join(self.eye_path, "sclera.png")
            if os.path.exists(sclera_path):
                self.sclera_texture = Image.open(sclera_path).convert('RGB')
                print(f"✓ Loaded sclera texture: {self.sclera_texture.size}")
            
            # Load iris texture (colored part)
            iris_path = os.path.join(self.eye_path, "iris.png")
            if os.path.exists(iris_path):
                self.iris_texture = Image.open(iris_path).convert('RGB')
                print(f"✓ Loaded iris texture: {self.iris_texture.size}")
            
            # Load pupil map (for non-round pupils)
            pupil_path = os.path.join(self.eye_path, "pupilMap.png")
            if os.path.exists(pupil_path):
                self.pupil_map = Image.open(pupil_path).convert('L')
                print(f"✓ Loaded pupil map: {self.pupil_map.size}")
            
            # Load eyelid threshold maps
            lid_upper_path = os.path.join(self.eye_path, "lid-upper.png")
            if os.path.exists(lid_upper_path):
                self.lid_upper_map = Image.open(lid_upper_path).convert('L')
                print(f"✓ Loaded upper lid map: {self.lid_upper_map.size}")
                
            lid_lower_path = os.path.join(self.eye_path, "lid-lower.png")
            if os.path.exists(lid_lower_path):
                self.lid_lower_map = Image.open(lid_lower_path).convert('L')
                print(f"✓ Loaded lower lid map: {self.lid_lower_map.size}")
                
            return True
            
        except Exception as e:
            print(f"✗ Failed to load textures: {e}")
            return False
    
    def generate_polar_map(self, iris_size=80):
        """Generate polar coordinate mapping for iris texture sampling"""
        print(f"🔄 Generating polar coordinate map for iris size {iris_size}...")
        
        radius = iris_size / 2.0
        polar_data = []
        
        for y in range(iris_size):
            row = []
            dy = y - radius + 0.5
            for x in range(iris_size):
                dx = x - radius + 0.5
                distance = math.sqrt(dx * dx + dy * dy)
                
                if distance >= radius:
                    # Outside circle
                    row.append((0, 127))  # angle=0, distance=127 (outside)
                else:
                    if self.pupil_map:
                        # Use pupil map for custom pupil shapes
                        pupil_pixels = self.pupil_map.load()
                        pupil_size = self.pupil_map.size[0]
                        px = int(x * pupil_size / iris_size)
                        py = int(y * pupil_size / iris_size)
                        if px < pupil_size and py < pupil_size:
                            distance = pupil_pixels[px, py] / 255.0
                        else:
                            distance = distance / radius
                    else:
                        # Standard circular pupil
                        distance = distance / radius
                    
                    # Calculate angle
                    angle = math.atan2(dy, dx)  # -pi to +pi
                    angle += math.pi            # 0 to 2*pi
                    angle /= (2.0 * math.pi)    # 0 to 1
                    
                    # Convert to fixed point
                    angle_fixed = int(angle * 512.0) & 0x1FF  # 0-511
                    dist_fixed = int((1.0 - distance) * 127.0)  # 127-0
                    if dist_fixed < 0:
                        dist_fixed = 0
                    if dist_fixed > 127:
                        dist_fixed = 127
                        
                    row.append((angle_fixed, dist_fixed))
            polar_data.append(row)
        
        self.polar_map = polar_data
        print(f"✓ Generated {len(polar_data)}x{len(polar_data[0])} polar map")
        
    def rgb888_to_rgb565(self, r, g, b):
        """Convert 24-bit RGB to 16-bit RGB565 format for SSD1351"""
        return ((r & 0b11111000) << 8) | ((g & 0b11111100) << 3) | (b >> 3)
    
    def sample_texture(self, texture, u, v):
        """Sample texture at normalized coordinates (0-1, 0-1)"""
        if not texture:
            return (255, 255, 255)  # Default white
            
        width, height = texture.size
        x = int(u * width) % width
        y = int(v * height) % height
        
        pixels = texture.load()
        return pixels[x, y]
    
    def render_eye_frame(self, eye_offset_x=0, eye_offset_y=0, iris_scale=1.0, 
                        upper_lid=0, lower_lid=0):
        """Render a complete eye frame using texture mapping
        
        Args:
            eye_offset_x, eye_offset_y: Eye movement offset in pixels
            iris_scale: Iris size scale (0.5-1.5, 1.0 = normal)
            upper_lid, lower_lid: Eyelid closure amount (0-255, 0=open, 255=closed)
        """
        if not self.sclera_texture or not self.iris_texture:
            print("✗ Textures not loaded")
            return None
        
        # Resize textures if needed
        sclera = self.sclera_texture
        if sclera.size != self.display_size:
            sclera = sclera.resize(self.display_size, Image.Resampling.LANCZOS)
        
        # Generate polar map if not exists
        if not self.polar_map:
            self.generate_polar_map()
        
        # Calculate texture sampling offsets
        sclera_offset_x = eye_offset_x
        sclera_offset_y = eye_offset_y
        
        # Calculate iris position and scale
        iris_size = int(80 * iris_scale)  # Base iris size
        iris_threshold = int(128 * (1.0 - iris_scale * 0.5))
        
        frame_data = []
        sclera_pixels = sclera.load()
        iris_pixels = self.iris_texture.load()
        iris_width, iris_height = self.iris_texture.size
        
        # Get eyelid maps
        upper_pixels = None
        lower_pixels = None
        if self.lid_upper_map:
            upper_pixels = self.lid_upper_map.load()
        if self.lid_lower_map:
            lower_pixels = self.lid_lower_map.load()
        
        for screen_y in range(128):
            for screen_x in range(128):
                # Check eyelid occlusion
                covered_by_lid = False
                
                if upper_pixels and screen_y < 64:  # Upper half
                    if upper_pixels[screen_x, screen_y] <= upper_lid:
                        covered_by_lid = True
                        
                if lower_pixels and screen_y >= 64:  # Lower half
                    if lower_pixels[screen_x, screen_y] <= lower_lid:
                        covered_by_lid = True
                
                if covered_by_lid:
                    # Eyelid color (dark skin tone)
                    rgb565 = self.rgb888_to_rgb565(64, 32, 16)
                else:
                    # Calculate iris position
                    iris_y = screen_y + eye_offset_y - (128 - iris_size) // 2
                    iris_x = screen_x + eye_offset_x - (128 - iris_size) // 2
                    
                    # Check if in iris area and get polar coordinates
                    if (0 <= iris_y < len(self.polar_map) and 
                        0 <= iris_x < len(self.polar_map[0])):
                        
                        angle, distance = self.polar_map[iris_y][iris_x]
                        
                        if distance < iris_threshold:
                            # Sample iris texture using polar coordinates
                            u = angle / 512.0  # Angle as U coordinate
                            v = distance / 127.0  # Distance as V coordinate
                            
                            # Sample iris texture
                            tex_x = int(u * iris_width) % iris_width
                            tex_y = int(v * iris_height) % iris_height
                            r, g, b = iris_pixels[tex_x, tex_y]
                            rgb565 = self.rgb888_to_rgb565(r, g, b)
                        else:
                            # Sample sclera texture
                            sclera_x = (screen_x + sclera_offset_x) % 128
                            sclera_y = (screen_y + sclera_offset_y) % 128
                            r, g, b = sclera_pixels[sclera_x, sclera_y]
                            rgb565 = self.rgb888_to_rgb565(r, g, b)
                    else:
                        # Sample sclera texture
                        sclera_x = (screen_x + sclera_offset_x) % 128
                        sclera_y = (screen_y + sclera_offset_y) % 128
                        r, g, b = sclera_pixels[sclera_x, sclera_y]
                        rgb565 = self.rgb888_to_rgb565(r, g, b)
                
                # Convert to SPI data (big-endian 16-bit)
                frame_data.extend([rgb565 >> 8, rgb565 & 0xFF])
        
        return frame_data
    
    def generate_eye_states(self):
        """Generate pre-rendered eye states for common movements and expressions"""
        if not self.load_textures():
            return None
        
        print(f"🎨 Generating eye states for {self.eye_type}...")
        
        eye_states = {
            "eye_type": self.eye_type,
            "display_size": self.display_size,
            "states": {}
        }
        
        # Define eye states with parameters
        states = [
            # Basic positions
            ("center", 0, 0, 1.0, 0, 0),
            ("look_left", -15, 0, 1.0, 0, 0),
            ("look_right", 15, 0, 1.0, 0, 0),
            ("look_up", 0, -10, 1.0, 0, 0),
            ("look_down", 0, 10, 1.0, 0, 0),
            ("look_up_left", -10, -8, 1.0, 0, 0),
            ("look_up_right", 10, -8, 1.0, 0, 0),
            ("look_down_left", -10, 8, 1.0, 0, 0),
            ("look_down_right", 10, 8, 1.0, 0, 0),
            
            # Blink states
            ("blink_25", 0, 0, 1.0, 64, 64),
            ("blink_50", 0, 0, 1.0, 128, 128),
            ("blink_75", 0, 0, 1.0, 192, 192),
            ("blink_closed", 0, 0, 1.0, 255, 255),
            
            # Size variations
            ("dilated", 0, 0, 1.3, 0, 0),
            ("constricted", 0, 0, 0.7, 0, 0),
        ]
        
        for state_name, offset_x, offset_y, iris_scale, upper_lid, lower_lid in states:
            print(f"  Rendering {state_name}...")
            frame_data = self.render_eye_frame(offset_x, offset_y, iris_scale, upper_lid, lower_lid)
            if frame_data:
                eye_states["states"][state_name] = frame_data
        
        return eye_states
    
    def save_eye_textures(self, output_file=None):
        """Generate and save textured eye data"""
        if output_file is None:
            output_file = f"{self.eye_type}_textures.json"
        
        eye_data = self.generate_eye_states()
        if not eye_data:
            return False
        
        output_path = os.path.join("/home/fortinbra/UnderYourBed-1/runtime", output_file)
        with open(output_path, 'w') as f:
            json.dump(eye_data, f, indent=2)
        
        print(f"✓ Saved textured eye data to {output_path}")
        return True

def main():
    """Convert eye graphics for different eye types"""
    eye_types = ["defaultEye", "catEye", "dragonEye", "doeEye", "goatEye", "newtEye", "terminatorEye"]
    
    if len(sys.argv) > 1:
        eye_types = [sys.argv[1]]
    
    for eye_type in eye_types:
        print(f"\n🎨 Converting {eye_type}...")
        converter = EyeGraphicsConverter(eye_type)
        
        # Check if eye type exists
        if not os.path.exists(converter.eye_path):
            print(f"✗ Eye type {eye_type} not found at {converter.eye_path}")
            continue
        
        # Convert and save
        output_file = f"{eye_type}_graphics.json"
        if converter.save_eye_data(output_file):
            print(f"✅ {eye_type} converted successfully")
        else:
            print(f"❌ {eye_type} conversion failed")

if __name__ == "__main__":
    main()