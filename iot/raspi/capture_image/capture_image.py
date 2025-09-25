#!/usr/bin/env python3
"""
Raspberry Pi Camera Image Capture Script (Python)
This script provides more control over camera settings and image capture
using the modern picamera2 library.
"""

import os
import sys
from datetime import datetime
from pathlib import Path

try:
    from picamera2 import Picamera2
    from libcamera import Transform
except ImportError:
    print("Error: picamera2 not installed!")
    print("Install with: sudo apt install python3-picamera2")
    sys.exit(1)

# Configuration
INCOMING_DIR = Path("/home/paulsczurek/code/fasttracktocleartracks/iot/raspi/image/incoming")
TIMESTAMP = datetime.now().strftime("%Y%m%d_%H%M%S")
FILENAME = f"captured_{TIMESTAMP}.jpg"
FILEPATH = INCOMING_DIR / FILENAME

# Camera settings
IMAGE_WIDTH = 1920
IMAGE_HEIGHT = 1080
QUALITY = 85

def capture_image():
    """Capture an image using picamera2"""
    
    # Create incoming directory if it doesn't exist
    INCOMING_DIR.mkdir(parents=True, exist_ok=True)
    
    try:
        # Initialize camera
        print("Initializing camera...")
        picam2 = Picamera2()
        
        # Configure camera
        config = picam2.create_still_configuration(
            main={"size": (IMAGE_WIDTH, IMAGE_HEIGHT)},
            transform=Transform()  # You can add rotation here if needed: Transform(hflip=1, vflip=1)
        )
        picam2.configure(config)
        
        # Start camera
        print("Starting camera preview...")
        picam2.start()
        
        # Allow camera to warm up
        import time
        time.sleep(2)
        
        # Capture image
        print(f"Capturing image: {FILENAME}")
        picam2.capture_file(str(FILEPATH))
        
        # Stop camera
        picam2.stop()
        
        # Verify capture
        if FILEPATH.exists():
            file_size = FILEPATH.stat().st_size
            print(f"Image captured successfully: {FILENAME}")
            print(f"Saved to: {FILEPATH}")
            print(f"File size: {file_size / 1024:.1f} KB")
            return True
        else:
            print("Error: Image file not created!")
            return False
            
    except Exception as e:
        print(f"Error capturing image: {e}")
        return False
    
    finally:
        # Ensure camera is properly closed
        try:
            picam2.stop()
        except:
            pass

def main():
    """Main function"""
    print("Raspberry Pi Camera Capture (Python)")
    print("=" * 40)
    
    success = capture_image()
    
    if success:
        print("Image capture completed successfully!")
        sys.exit(0)
    else:
        print("Image capture failed!")
        sys.exit(1)

if __name__ == "__main__":
    main()