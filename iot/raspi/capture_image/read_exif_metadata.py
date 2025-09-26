#!/usr/bin/env python3
"""
Simple utility to read and display metadata from captured images
Supports both EXIF-embedded metadata and separate JSON files
"""

import sys
import json
import argparse
from pathlib import Path

try:
    from PIL import Image
    from PIL.ExifTags import TAGS
    import piexif
except ImportError as e:
    print(f"Error: Required library not installed - {e}")
    print("Install with: sudo apt install python3-pil python3-piexif")
    sys.exit(1)

def read_exif_metadata(image_path):
    """Read metadata from EXIF UserComment field"""
    try:
        image_path = Path(image_path)
        if not image_path.exists():
            print(f"Error: Image file not found: {image_path}")
            return None
        
        # Load EXIF data
        exif_dict = piexif.load(str(image_path))
        
        print(f"Image: {image_path.name}")
        print("=" * 50)
        
        # Read standard EXIF data
        print("\nStandard EXIF Data:")
        print("-" * 20)
        
        # Image description
        if piexif.ImageIFD.ImageDescription in exif_dict.get('0th', {}):
            desc = exif_dict['0th'][piexif.ImageIFD.ImageDescription]
            if isinstance(desc, bytes):
                desc = desc.decode('utf-8')
            print(f"Description: {desc}")
        
        # Software info
        if piexif.ImageIFD.Software in exif_dict.get('0th', {}):
            software = exif_dict['0th'][piexif.ImageIFD.Software]
            if isinstance(software, bytes):
                software = software.decode('utf-8')
            print(f"Software: {software}")
        
        # Camera settings from EXIF
        if 'Exif' in exif_dict:
            exif_data = exif_dict['Exif']
            
            if piexif.ExifIFD.ExposureTime in exif_data:
                exp_time = exif_data[piexif.ExifIFD.ExposureTime]
                if isinstance(exp_time, tuple) and len(exp_time) == 2:
                    exp_sec = exp_time[0] / exp_time[1]
                    if exp_sec < 1:
                        print(f"Exposure: 1/{int(1/exp_sec)}s")
                    else:
                        print(f"Exposure: {exp_sec}s")
            
            if piexif.ExifIFD.ISOSpeedRatings in exif_data:
                iso = exif_data[piexif.ExifIFD.ISOSpeedRatings]
                print(f"ISO: {iso}")
        
        # Read embedded JSON metadata from UserComment
        if piexif.ExifIFD.UserComment in exif_dict.get('Exif', {}):
            user_comment = exif_dict['Exif'][piexif.ExifIFD.UserComment]
            
            if user_comment.startswith(b"JPEG\x00\x00\x00\x00"):
                # Extract JSON data after the encoding header
                json_data = user_comment[8:].decode('utf-8')
                try:
                    metadata = json.loads(json_data)
                    
                    print("\nEmbedded Metadata:")
                    print("-" * 20)
                    
                    # Display key information
                    if 'timestamp' in metadata:
                        print(f"Timestamp: {metadata['timestamp']}")
                    
                    if 'settings' in metadata:
                        settings = metadata['settings']
                        print(f"Resolution: {settings.get('width')}x{settings.get('height')}")
                        print(f"Quality: {settings.get('quality')}")
                        print(f"Adaptive Exposure: {settings.get('adaptive_exposure')}")
                    
                    if 'lighting_analysis' in metadata:
                        lighting = metadata['lighting_analysis']
                        print(f"Lighting: {lighting.get('description')} (brightness: {lighting.get('brightness', 0):.1f})")
                        print(f"Dark pixels: {lighting.get('dark_pixels_percent', 0):.1f}%")
                        print(f"Bright pixels: {lighting.get('bright_pixels_percent', 0):.1f}%")
                    
                    if 'camera_metadata' in metadata:
                        camera = metadata['camera_metadata']
                        print(f"Camera exposure: {camera.get('ExposureTime', 'N/A')} μs")
                        print(f"Analogue gain: {camera.get('AnalogueGain', 'N/A')}")
                        print(f"Color temperature: {camera.get('ColourTemperature', 'N/A')}K")
                        print(f"Lux: {camera.get('Lux', 'N/A')}")
                    
                    return metadata
                    
                except json.JSONDecodeError as e:
                    print(f"Error: Could not parse embedded JSON metadata: {e}")
                    return None
            else:
                print("No embedded JSON metadata found in EXIF UserComment")
                return None
        else:
            print("No UserComment field found in EXIF data")
            return None
            
    except Exception as e:
        print(f"Error reading EXIF data: {e}")
        return None

def read_json_metadata(image_path):
    """Read metadata from separate JSON file"""
    image_path = Path(image_path)
    json_path = image_path.parent / f"{image_path.stem}_metadata.json"
    
    if json_path.exists():
        print(f"JSON Metadata: {json_path.name}")
        print("=" * 50)
        
        try:
            with open(json_path, 'r') as f:
                metadata = json.load(f)
            
            print(json.dumps(metadata, indent=2))
            return metadata
            
        except Exception as e:
            print(f"Error reading JSON metadata: {e}")
            return None
    else:
        print(f"No JSON metadata file found: {json_path.name}")
        return None

def main():
    parser = argparse.ArgumentParser(description="Read metadata from captured images")
    parser.add_argument("image_path", help="Path to the image file")
    parser.add_argument("--json-only", action='store_true', help="Only read JSON metadata file")
    parser.add_argument("--exif-only", action='store_true', help="Only read EXIF metadata")
    parser.add_argument("--raw", action='store_true', help="Show raw JSON output")
    
    args = parser.parse_args()
    
    if args.json_only:
        metadata = read_json_metadata(args.image_path)
    elif args.exif_only:
        metadata = read_exif_metadata(args.image_path)
    else:
        # Try EXIF first, then JSON as fallback
        metadata = read_exif_metadata(args.image_path)
        if not metadata:
            print("\nTrying JSON metadata...")
            metadata = read_json_metadata(args.image_path)
    
    if metadata and args.raw:
        print("\nRaw JSON output:")
        print("=" * 50)
        print(json.dumps(metadata, indent=2))

if __name__ == "__main__":
    main()