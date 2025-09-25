#!/usr/bin/env python3
"""
Advanced Raspberry Pi Camera Image Capture Script with Adaptive Exposure
This script provides extensive control over camera settings and includes
intelligent exposure adaptation for outdoor photography in varying lighting conditions.
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
    print("  pip3 install pillow numpy")
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
            try:
                controls_dict[controls.AeExposureMode] = controls.AeExposureModeEnum.Long
            except AttributeError:
                # Fallback if enum not available
                pass
        elif exposure_mode == "short":
            # For bright conditions, prefer shorter exposures
            try:
                controls_dict[controls.AeExposureMode] = controls.AeExposureModeEnum.Short
            except AttributeError:
                pass
        
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
                     rotation=0, flip_h=False, flip_v=False, preview_time=2,
                     adaptive_exposure=True, exposure_bracketing=False):
        """
        Capture an image with advanced settings and adaptive exposure
        
        Args:
            width, height: Image dimensions
            quality: JPEG quality (1-100)
            exposure_time: Manual exposure in microseconds (None for auto)
            iso: ISO value (100-1600, None for auto)
            white_balance: White balance mode ('auto', 'daylight', 'cloudy', etc.)
            rotation: Rotation in degrees (0, 90, 180, 270)
            flip_h, flip_v: Horizontal and vertical flip
            preview_time: Preview time in seconds before capture
            adaptive_exposure: Enable intelligent exposure adaptation
            exposure_bracketing: Take multiple shots with different exposures
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
            
            # Allow camera to stabilize
            import time
            time.sleep(1)
            
            # Analyze lighting conditions if adaptive exposure is enabled
            lighting_info = None
            if adaptive_exposure:
                print("Analyzing lighting conditions...")
                lighting_info = self.analyze_lighting_conditions()
                print(f"Detected lighting: {lighting_info['description']} (brightness: {lighting_info['brightness']:.1f})")
                
                # Apply adaptive settings
                adaptive_controls = self.apply_adaptive_settings(lighting_info, base_iso=iso or 400)
                self.picam2.set_controls(adaptive_controls)
                print(f"Applied adaptive controls for {lighting_info['condition']} conditions")
                
                # Additional stabilization time after applying new settings
                time.sleep(1)
            
            # Set manual controls if specified (these override adaptive settings)
            controls_dict = {}
            if exposure_time:
                controls_dict[controls.ExposureTime] = exposure_time
                controls_dict[controls.AeEnable] = False  # Disable auto exposure
                print(f"Manual exposure: {exposure_time}μs")
            
            if iso and not adaptive_exposure:
                controls_dict[controls.AnalogueGain] = iso / 100.0
                print(f"Manual ISO: {iso}")
            
            if white_balance and white_balance != 'auto':
                controls_dict[controls.AwbEnable] = False
                # Set color gains based on white balance mode
                wb_gains = {
                    'daylight': (1.5, 2.5),
                    'cloudy': (1.8, 2.2),
                    'tungsten': (2.5, 1.2),
                    'fluorescent': (2.0, 1.8)
                }
                if white_balance in wb_gains:
                    r_gain, b_gain = wb_gains[white_balance]
                    controls_dict[controls.ColourGains] = (r_gain, b_gain)
                    print(f"Manual white balance: {white_balance}")
            
            if controls_dict:
                self.picam2.set_controls(controls_dict)
            
            # Final preview time
            remaining_preview = max(0, preview_time - (2 if adaptive_exposure else 1))
            if remaining_preview > 0:
                print(f"Final preview for {remaining_preview} seconds...")
                time.sleep(remaining_preview)
            
            # Capture metadata before taking the photo
            metadata = self.picam2.capture_metadata()
            
            if exposure_bracketing and not exposure_time:
                # Take multiple shots with different exposure compensations
                print("Capturing bracketed exposures...")
                exposures = [-1.0, 0.0, 1.0]  # Under, normal, over exposed
                best_filepath = None
                best_score = -1
                
                for i, exp_compensation in enumerate(exposures):
                    bracket_filename = f"captured_{timestamp}_bracket_{i}.jpg"
                    bracket_filepath = self.incoming_dir / bracket_filename
                    
                    # Set exposure compensation
                    self.picam2.set_controls({controls.ExposureValue: exp_compensation})
                    time.sleep(0.5)  # Brief stabilization
                    
                    print(f"  Capturing exposure {i+1}/3 (compensation: {exp_compensation:+.1f})")
                    self.picam2.capture_file(str(bracket_filepath))
                    
                    # Analyze this exposure to find the best one
                    try:
                        with Image.open(bracket_filepath) as img:
                            stat = ImageStat.Stat(img)
                            brightness = sum(stat.mean) / len(stat.mean)
                            
                            # Score based on how close to ideal brightness (128) and avoid over/under exposure
                            histogram = img.histogram()
                            total_pixels = img.size[0] * img.size[1]
                            clipped_highlights = histogram[255] / total_pixels
                            clipped_shadows = histogram[0] / total_pixels
                            
                            # Penalty for clipped pixels, preference for good brightness
                            score = 100 - abs(brightness - 128) - (clipped_highlights * 100) - (clipped_shadows * 100)
                            
                            if score > best_score:
                                best_score = score
                                best_filepath = bracket_filepath
                                
                    except Exception as e:
                        print(f"    Warning: Could not analyze bracket {i}: {e}")
                
                # Copy the best exposure to the main filename
                if best_filepath:
                    import shutil
                    shutil.copy2(best_filepath, filepath)
                    print(f"Selected best exposure: {best_filepath.name} (score: {best_score:.1f})")
                    
                    # Clean up bracket files
                    for i in range(len(exposures)):
                        bracket_filename = f"captured_{timestamp}_bracket_{i}.jpg"
                        bracket_filepath = self.incoming_dir / bracket_filename
                        if bracket_filepath.exists():
                            bracket_filepath.unlink()
            else:
                # Single capture
                print(f"Capturing image: {filename}")
                self.picam2.capture_file(str(filepath))
            
            # Stop camera
            self.picam2.stop()
            
            # Enhanced metadata
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
                    "flip_vertical": flip_v,
                    "adaptive_exposure": adaptive_exposure,
                    "exposure_bracketing": exposure_bracketing
                },
                "lighting_analysis": lighting_info,
                "camera_metadata": {k: str(v) for k, v in metadata.items()}
            }
            
            # Add final image analysis
            if filepath.exists():
                try:
                    with Image.open(filepath) as img:
                        stat = ImageStat.Stat(img)
                        final_brightness = sum(stat.mean) / len(stat.mean)
                        capture_metadata["final_image_analysis"] = {
                            "brightness": final_brightness,
                            "dimensions": img.size,
                            "mode": img.mode
                        }
                except:
                    pass
            
            with open(metadata_file, 'w') as f:
                json.dump(capture_metadata, f, indent=2)
            
            # Verify and report
            if filepath.exists():
                file_size = filepath.stat().st_size
                print(f"✓ Image captured successfully: {filename}")
                print(f"✓ Saved to: {filepath}")
                print(f"✓ File size: {file_size / 1024:.1f} KB")
                
                if lighting_info:
                    print(f"✓ Lighting condition: {lighting_info['description']}")
                    final_brightness = capture_metadata.get("final_image_analysis", {}).get("brightness", "N/A")
                    if final_brightness != "N/A":
                        print(f"✓ Final image brightness: {final_brightness:.1f}")
                
                print(f"✓ Metadata saved: {metadata_file.name}")
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
    parser = argparse.ArgumentParser(description="Advanced Raspberry Pi Camera Capture with Adaptive Exposure")
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
    parser.add_argument("--no-adaptive", action='store_true', 
                       help="Disable adaptive exposure (use standard auto-exposure)")
    parser.add_argument("--bracket", action='store_true', 
                       help="Enable exposure bracketing (takes best of 3 exposures)")
    parser.add_argument("--list-props", action='store_true', help="List camera properties")
    
    args = parser.parse_args()
    
    incoming_dir = "/home/paulsczurek/code/fasttracktocleartracks/iot/raspi/image/incoming"
    camera = RaspberryPiCamera(incoming_dir)
    
    if args.list_props:
        camera.list_camera_properties()
        return
    
    print("Advanced Raspberry Pi Camera Capture with Adaptive Exposure")
    print("=" * 60)
    print(f"Resolution: {args.width}x{args.height}")
    print(f"Quality: {args.quality}")
    print(f"Adaptive exposure: {'Disabled' if args.no_adaptive else 'Enabled'}")
    print(f"Exposure bracketing: {'Enabled' if args.bracket else 'Disabled'}")
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
        preview_time=args.preview,
        adaptive_exposure=not args.no_adaptive,
        exposure_bracketing=args.bracket
    )
    
    if success:
        print("\n✓ Image capture completed successfully!")
        sys.exit(0)
    else:
        print("\n✗ Image capture failed!")
        sys.exit(1)

if __name__ == "__main__":
    main()