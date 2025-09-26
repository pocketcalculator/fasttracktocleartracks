#!/bin/bash

# Raspberry Pi Camera Image Capture Script
# This script captures an image using rpicam-still and saves it to the incoming directory

# Function to auto-detect incoming directory
get_incoming_dir() {
    # Get the directory where this script is located
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    
    # Try ../image/incoming relative to script
    AUTO_INCOMING="${SCRIPT_DIR}/../image/incoming"
    
    if [ -d "$AUTO_INCOMING" ]; then
        echo "$AUTO_INCOMING"
    else
        # Fallback to script_dir/incoming
        FALLBACK_DIR="${SCRIPT_DIR}/incoming"
        echo "Warning: Using fallback directory: $FALLBACK_DIR" >&2
        echo "$FALLBACK_DIR"
    fi
}

# Configuration
INCOMING_DIR="${1:-$(get_incoming_dir)}"  # Use first argument or auto-detect
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
FILENAME="captured_${TIMESTAMP}.jpg"
FILEPATH="${INCOMING_DIR}/${FILENAME}"

# Create incoming directory if it doesn't exist
mkdir -p "$INCOMING_DIR"

# Check if rpicam-still is available (modern tool)
if command -v rpicam-still &> /dev/null; then
    echo "Using rpicam-still to capture image..."
    rpicam-still -o "$FILEPATH" --width 1920 --height 1080 --quality 85 --timeout 2000
elif command -v raspistill &> /dev/null; then
    echo "Using legacy raspistill to capture image..."
    raspistill -o "$FILEPATH" -w 1920 -h 1080 -q 85 -t 2000
else
    echo "Error: Neither rpicam-still nor raspistill found!"
    echo "Please install camera tools: sudo apt update && sudo apt install rpicam-apps"
    exit 1
fi

# Check if image was captured successfully
if [ -f "$FILEPATH" ]; then
    echo "Image captured successfully: $FILENAME"
    echo "Saved to: $FILEPATH"
    echo "File size: $(du -h "$FILEPATH" | cut -f1)"
else
    echo "Error: Failed to capture image!"
    exit 1
fi
