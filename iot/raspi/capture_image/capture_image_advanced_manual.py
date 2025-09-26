#!/usr/bin/env python3
"""
Advanced Raspberry Pi Camera Image Capture Script
This script provides extensive control over camera settings and includes
features like custom resolution, exposure, white balance, and metadata.
"""

import os
import sys
import json
import argparse
from datetime import datetime
from pathlib import Path

try:
    from picamera2 import Picamera2
    from libcamera import Transform, controls
    from PIL import Image, ImageStat
    from PIL.ExifTags import TAGS
    import numpy as np
except ImportError as e:
    print(f"Error: Required library not installed - {e}")
    print("Install with:")
    print("  sudo apt install python3-picamera2")
    print("  pip3 install pillow")
    sys.exit(1)

class RaspberryPiCamera:
    def __init__(self, incoming_dir):
        self.incoming_dir = Path(incoming_dir)
        self.incoming_dir.mkdir(parents=True, exist_ok=True)
        self.picam2 = None
        
    def analyze_lighting_conditions(self):
        """
        Analyze current lighting conditions by taking a quick preview capture
        Returns lighting assessment and recommended settings
        """
        try:
            # Take a small preview image for analysis
            preview_array = self.picam2.capture_array("main")
            
            # Convert to PIL for analysis
            preview_img = Image.fromarray(preview_array)
            
            # Calculate brightness statistics
            stat = ImageStat.Stat(preview_img)
            brightness = sum(stat.mean) / len(stat.mean)  # Average across RGB channels
            
            # Analyze histogram for exposure assessment
            histogram = preview_img.histogram()
            
            # Calculate percentage of pixels in different brightness ranges
            total_pixels = preview_img.size[0] * preview_img.size[1]
            dark_pixels = sum(histogram[0:85]) / total_pixels  # Very dark pixels (0-33% brightness)
            bright_pixels = sum(histogram[170:256]) / total_pixels  # Very bright pixels (67-100% brightness)
            
            # Determine lighting conditions and recommended settings
            if brightness < 50:
                condition = "very_dark"
                description = "Night/Very Dark"
                # Night settings: longer exposure, higher ISO
                recommended = {
                    "exposure_mode": "long",
                    "iso_boost": 2.0,
                    "brightness_compensation": 0.3
                }
            elif brightness < 100:
                condition = "dark"
                description = "Dawn/Dusk/Overcast"
                # Low light settings: moderate exposure boost
                recommended = {
                    "exposure_mode": "normal",
                    "iso_boost": 1.5,
                    "brightness_compensation": 0.2
                }
            elif brightness > 180:
                condition = "very_bright"
                description = "Direct Sunlight"
                # Bright conditions: reduce exposure to prevent overexposure
                recommended = {
                    "exposure_mode": "short",
                    "iso_boost": 0.8,
                    "brightness_compensation": -0.2
                }
            else:
                condition = "normal"
                description = "Good Lighting"
                # Normal conditions: standard auto settings
                recommended = {
                    "exposure_mode": "normal",
                    "iso_boost": 1.0,
                    "brightness_compensation": 0.0
                }
            
            lighting_info = {
                "condition": condition,
                "description": description,
                "brightness": brightness,
                "dark_pixels_percent": dark_pixels * 100,
                "bright_pixels_percent": bright_pixels * 100,
                "recommended_settings": recommended
            }
            
            return lighting_info
            
        except Exception as e:
            print(f"Warning: Could not analyze lighting conditions: {e}")
            # Return safe defaults
            return {
                "condition": "unknown",
                "description": "Auto",
                "brightness": 128,
                "dark_pixels_percent": 0,
                "bright_pixels_percent": 0,
                "recommended_settings": {
                    "exposure_mode": "normal",
                    "iso_boost": 1.0,
                    "brightness_compensation": 0.0
                }
            }
    
    def apply_adaptive_settings(self, lighting_info, base_exposure=None, base_iso=None):
        """
        Apply camera settings based on lighting analysis
        """
        recommended = lighting_info["recommended_settings"]
        controls_dict = {}
        
        # Enable auto-exposure but with compensation
        controls_dict[controls.AeEnable] = True
        
        # Apply exposure compensation based on lighting conditions
        if "brightness_compensation" in recommended:
            compensation = recommended["brightness_compensation"]
            controls_dict[controls.ExposureValue] = compensation
        
        # Adjust ISO sensitivity based on conditions
        if base_iso:
            iso_multiplier = recommended.get("iso_boost", 1.0)
            adjusted_iso = min(1600, int(base_iso * iso_multiplier))  # Cap at 1600
            controls_dict[controls.AnalogueGain] = adjusted_iso / 100.0
        
        # Set exposure mode preferences
        exposure_mode = recommended.get("exposure_mode", "normal")
        if exposure_mode == "long":
            # For dark conditions, allow longer exposures
            controls_dict[controls.AeExposureMode] = controls.AeExposureModeEnum.Long
        elif exposure_mode == "short":
            # For bright conditions, prefer shorter exposures
            controls_dict[controls.AeExposureMode] = controls.AeExposureModeEnum.Short
        else:
            # Normal auto-exposure
            controls_dict[controls.AeExposureMode] = controls.AeExposureModeEnum.Normal
        
        return controls_dict
        
    def list_camera_properties(self):
        """List available camera properties and controls"""
        try:
            self.picam2 = Picamera2()
            camera_properties = self.picam2.camera_properties
            print("Camera Properties:")
            for key, value in camera_properties.items():
                print(f"  {key}: {value}")
            return camera_properties
        except Exception as e:
            print(f"Error listing camera properties: {e}")
            return {}
        finally:
            if self.picam2:
                try:
                    self.picam2.close()
                except:
                    pass
    
    def capture_image(self, width=1920, height=1080, quality=85, 
                     exposure_time=None, iso=None, white_balance=None,
                     rotation=0, flip_h=False, flip_v=False, preview_time=2):
        """
        Capture an image with advanced settings
        
        Args:
            width, height: Image dimensions
            quality: JPEG quality (1-100)
            exposure_time: Manual exposure in microseconds (None for auto)
            iso: ISO value (100-1600, None for auto)
            white_balance: White balance mode ('auto', 'daylight', 'cloudy', etc.)
            rotation: Rotation in degrees (0, 90, 180, 270)
            flip_h, flip_v: Horizontal and vertical flip
            preview_time: Preview time in seconds before capture
        """
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"captured_{timestamp}.jpg"
        filepath = self.incoming_dir / filename
        metadata_file = self.incoming_dir / f"captured_{timestamp}_metadata.json"
        
        try:
            print("Initializing camera...")
            self.picam2 = Picamera2()
            
            # Set transform based on rotation and flip
            transform = Transform(
                hflip=flip_h,
                vflip=flip_v
            )
            
            # Configure camera
            config = self.picam2.create_still_configuration(
                main={"size": (width, height)},
                transform=transform
            )
            self.picam2.configure(config)
            
            print("Starting camera...")
            self.picam2.start()
            
            # Set manual controls if specified
            controls_dict = {}
            if exposure_time:
                controls_dict[controls.ExposureTime] = exposure_time
                controls_dict[controls.AeEnable] = False  # Disable auto exposure
            
            if iso:
                controls_dict[controls.AnalogueGain] = iso / 100.0
            
            if white_balance and white_balance != 'auto':
                controls_dict[controls.AwbEnable] = False
                # You would set specific color gains here based on white_balance mode
            
            if controls_dict:
                self.picam2.set_controls(controls_dict)
                print(f"Applied manual controls: {controls_dict}")
            
            # Preview time
            print(f"Camera preview for {preview_time} seconds...")
            import time
            time.sleep(preview_time)
            
            # Capture metadata before taking the photo
            metadata = self.picam2.capture_metadata()
            
            # Capture image
            print(f"Capturing image: {filename}")
            self.picam2.capture_file(str(filepath))
            
            # Save metadata
            capture_metadata = {
                "timestamp": timestamp,
                "filename": filename,
                "settings": {
                    "width": width,
                    "height": height,
                    "quality": quality,
                    "exposure_time": exposure_time,
                    "iso": iso,
                    "white_balance": white_balance,
                    "rotation": rotation,
                    "flip_horizontal": flip_h,
                    "flip_vertical": flip_v
                },
                "camera_metadata": {k: str(v) for k, v in metadata.items()}
            }
            
            with open(metadata_file, 'w') as f:
                json.dump(capture_metadata, f, indent=2)
            
            # Stop camera
            self.picam2.stop()
            
            # Verify and report
            if filepath.exists():
                file_size = filepath.stat().st_size
                print(f"✓ Image captured successfully: {filename}")
                print(f"✓ Saved to: {filepath}")
                print(f"✓ File size: {file_size / 1024:.1f} KB")
                print(f"✓ Metadata saved: {metadata_file.name}")
                
                # Display basic image info
                try:
                    with Image.open(filepath) as img:
                        print(f"✓ Image dimensions: {img.size[0]}x{img.size[1]}")
                        print(f"✓ Color mode: {img.mode}")
                except:
                    pass
                
                return True
            else:
                print("✗ Error: Image file not created!")
                return False
                
        except Exception as e:
            print(f"✗ Error capturing image: {e}")
            return False
            
        finally:
            if self.picam2:
                try:
                    self.picam2.stop()
                    self.picam2.close()
                except:
                    pass

def main():
    parser = argparse.ArgumentParser(description="Advanced Raspberry Pi Camera Capture")
    parser.add_argument("--width", type=int, default=1920, help="Image width")
    parser.add_argument("--height", type=int, default=1080, help="Image height")
    parser.add_argument("--quality", type=int, default=85, help="JPEG quality (1-100)")
    parser.add_argument("--exposure", type=int, help="Manual exposure time (microseconds)")
    parser.add_argument("--iso", type=int, help="ISO value (100-1600)")
    parser.add_argument("--wb", choices=['auto', 'daylight', 'cloudy', 'tungsten'], 
                       default='auto', help="White balance mode")
    parser.add_argument("--rotation", type=int, choices=[0, 90, 180, 270], 
                       default=0, help="Image rotation")
    parser.add_argument("--flip-h", action='store_true', help="Flip horizontally")
    parser.add_argument("--flip-v", action='store_true', help="Flip vertically")
    parser.add_argument("--preview", type=int, default=2, help="Preview time in seconds")
    parser.add_argument("--list-props", action='store_true', help="List camera properties")
    parser.add_argument("--output-dir", type=str, 
                       help="Output directory for captured images (default: auto-detect or use ../image/incoming)")
    
    args = parser.parse_args()
    
    # Determine output directory
    if args.output_dir:
        incoming_dir = args.output_dir
    else:
        # Try to auto-detect based on script location
        script_dir = Path(__file__).parent
        # Look for ../image/incoming relative to script
        auto_incoming = script_dir.parent / "image" / "incoming"
        if auto_incoming.exists():
            incoming_dir = str(auto_incoming)
        else:
            # Fallback to current directory + incoming
            incoming_dir = str(script_dir / "incoming")
            print(f"Warning: Using fallback directory: {incoming_dir}")
            print("Consider using --output-dir to specify the correct path")
    
    camera = RaspberryPiCamera(incoming_dir)
    
    if args.list_props:
        camera.list_camera_properties()
        return
    
    print("Advanced Raspberry Pi Camera Capture")
    print("=" * 50)
    print(f"Resolution: {args.width}x{args.height}")
    print(f"Quality: {args.quality}")
    print(f"Incoming directory: {incoming_dir}")
    print()
    
    success = camera.capture_image(
        width=args.width,
        height=args.height,
        quality=args.quality,
        exposure_time=args.exposure,
        iso=args.iso,
        white_balance=args.wb,
        rotation=args.rotation,
        flip_h=args.flip_h,
        flip_v=args.flip_v,
        preview_time=args.preview
    )
    
    if success:
        print("\n✓ Image capture completed successfully!")
        sys.exit(0)
    else:
        print("\n✗ Image capture failed!")
        sys.exit(1)

if __name__ == "__main__":
    main()