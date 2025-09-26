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
    from PIL.ExifTags import GPSTAGS
    import piexif
    import numpy as np
except ImportError as e:
    print(f"Error: Required library not installed - {e}")
    print("Install with:")
    print("  sudo apt install python3-picamera2")
    print("  pip3 install pillow numpy piexif")
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
        
        try:
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
            
            # Set exposure mode preferences (skip this for now to avoid compatibility issues)
            # exposure_mode = recommended.get("exposure_mode", "normal")
            # if exposure_mode == "long":
            #     # For dark conditions, allow longer exposures
            #     try:
            #         controls_dict[controls.AeExposureMode] = controls.AeExposureModeEnum.Long
            #     except AttributeError:
            #         # Fallback if enum not available
            #         pass
            # elif exposure_mode == "short":
            #     # For bright conditions, prefer shorter exposures
            #     try:
            #         controls_dict[controls.AeExposureMode] = controls.AeExposureModeEnum.Short
            #     except AttributeError:
            #         pass
        
        except Exception as e:
            print(f"Warning: Error setting adaptive controls: {e}")
            # Return minimal safe controls
            return {controls.AeEnable: True}
        
        return controls_dict
        
    def _convert_metadata_safely(self, metadata):
        """
        Safely convert camera metadata to a JSON-serializable format
        Handles libcamera ControlId objects and other non-serializable types
        """
        converted = {}
        for key, value in metadata.items():
            try:
                # Convert key to string, handling ControlId objects
                if hasattr(key, '__str__'):
                    str_key = str(key)
                else:
                    str_key = repr(key)
                
                # Convert value to serializable format
                if value is None:
                    converted[str_key] = None
                elif isinstance(value, (int, float, str, bool)):
                    converted[str_key] = value
                elif isinstance(value, (list, tuple)):
                    # Handle arrays/tuples
                    converted[str_key] = [str(item) if not isinstance(item, (int, float, str, bool)) else item for item in value]
                else:
                    # For complex objects, convert to string representation
                    converted[str_key] = str(value)
            except Exception as e:
                # If conversion fails, store the error info
                converted[f"conversion_error_{repr(key)}"] = f"Failed to convert: {str(e)}"
        
        return converted
        
    def _embed_metadata_in_exif(self, filepath, capture_metadata):
        """
        Embed capture metadata into JPEG EXIF data
        """
        try:
            # Load the existing EXIF data
            exif_dict = piexif.load(str(filepath))
            
            # Add our custom metadata to the UserComment field (allows longer text)
            metadata_json = json.dumps(capture_metadata, separators=(',', ':'))
            
            # EXIF UserComment format: encoding + actual comment
            # We'll use ASCII encoding (0x41534349 = "ASCI")
            user_comment = b"JPEG\x00\x00\x00\x00" + metadata_json.encode('utf-8')
            exif_dict['Exif'][piexif.ExifIFD.UserComment] = user_comment
            
            # Also add some key information to standard EXIF fields
            settings = capture_metadata.get('settings', {})
            lighting = capture_metadata.get('lighting_analysis', {})
            
            # Image description with lighting condition
            if lighting.get('description'):
                description = f"Adaptive capture: {lighting['description']} (brightness: {lighting.get('brightness', 'N/A'):.1f})"
                exif_dict['0th'][piexif.ImageIFD.ImageDescription] = description.encode('utf-8')
            
            # Software/processing info
            software_info = f"RaspberryPi Adaptive Camera - Quality:{settings.get('quality', 85)}"
            if settings.get('adaptive_exposure'):
                software_info += " - Adaptive"
            if settings.get('exposure_bracketing'):
                software_info += " - Bracketed"
            exif_dict['0th'][piexif.ImageIFD.Software] = software_info.encode('utf-8')
            
            # Camera settings in maker note area if available
            camera_meta = capture_metadata.get('camera_metadata', {})
            if 'ExposureTime' in camera_meta:
                # Convert microseconds to rational (1/shutter_speed format)
                exposure_us = camera_meta['ExposureTime']
                if isinstance(exposure_us, (int, float)) and exposure_us > 0:
                    # Convert to standard EXIF format (seconds as rational)
                    exposure_sec = exposure_us / 1000000.0
                    if exposure_sec < 1:
                        # Express as 1/X for fast shutter speeds
                        denominator = int(1 / exposure_sec)
                        exif_dict['Exif'][piexif.ExifIFD.ExposureTime] = (1, denominator)
                    else:
                        # Express as rational for longer exposures
                        numerator = int(exposure_sec * 1000)
                        exif_dict['Exif'][piexif.ExifIFD.ExposureTime] = (numerator, 1000)
            
            # ISO setting
            if 'AnalogueGain' in camera_meta:
                analogue_gain = camera_meta['AnalogueGain']
                if isinstance(analogue_gain, (int, float)):
                    iso_equivalent = int(analogue_gain * 100)
                    exif_dict['Exif'][piexif.ExifIFD.ISOSpeedRatings] = iso_equivalent
            
            # Color temperature
            if 'ColourTemperature' in camera_meta:
                color_temp = camera_meta['ColourTemperature']
                if isinstance(color_temp, (int, float)):
                    exif_dict['Exif'][piexif.ExifIFD.WhiteBalance] = 1  # Manual white balance
                    exif_dict['Exif'][piexif.ExifIFD.ColorSpace] = 1    # sRGB
            
            # Convert back to bytes and save
            exif_bytes = piexif.dump(exif_dict)
            
            # Re-save the image with new EXIF data
            img = Image.open(filepath)
            img.save(filepath, "JPEG", quality=settings.get('quality', 85), exif=exif_bytes)
            
            return True
            
        except Exception as e:
            print(f"Warning: Could not embed metadata in EXIF: {e}")
            return False
        
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
                     adaptive_exposure=True, exposure_bracketing=False, use_json_metadata=False):
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
            use_json_metadata: Save metadata to JSON file instead of EXIF (default: False)
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
                try:
                    self.picam2.set_controls(adaptive_controls)
                    print(f"Applied adaptive controls for {lighting_info['condition']} conditions")
                except Exception as e:
                    print(f"Warning: Could not apply adaptive controls, using defaults: {e}")
                
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
            try:
                safe_metadata = self._convert_metadata_safely(metadata)
            except Exception as e:
                print(f"Warning: Could not convert camera metadata: {e}")
                safe_metadata = {"error": f"Metadata conversion failed: {e}"}
            
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
                "camera_metadata": safe_metadata
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
            
            # Store metadata based on user preference
            if use_json_metadata:
                # Save to separate JSON file (legacy method)
                with open(metadata_file, 'w') as f:
                    json.dump(capture_metadata, f, indent=2)
                metadata_saved_msg = f"✓ Metadata saved: {metadata_file.name}"
            else:
                # Embed metadata into EXIF data (default method)
                metadata_embedded = False
                if filepath.exists():
                    print("Embedding metadata into EXIF...")
                    metadata_embedded = self._embed_metadata_in_exif(filepath, capture_metadata)
                
                if metadata_embedded:
                    metadata_saved_msg = "✓ Metadata embedded in EXIF data"
                else:
                    metadata_saved_msg = "⚠ Metadata could not be embedded (image still captured)"
            
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
                
                print(metadata_saved_msg)
                
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
    parser.add_argument("--json-metadata", action='store_true', 
                       help="Save metadata to separate JSON file instead of embedding in EXIF")
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
        exposure_bracketing=args.bracket,
        use_json_metadata=args.json_metadata
    )
    
    if success:
        print("\n✓ Image capture completed successfully!")
        sys.exit(0)
    else:
        print("\n✗ Image capture failed!")
        sys.exit(1)

if __name__ == "__main__":
    main()