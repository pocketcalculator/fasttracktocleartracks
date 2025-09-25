#!/bin/bash

# Raspberry Pi Camera Image Capture Script
# This script captures an image using rpicam-still and saves it to the incoming directory

# Configuration
INCOMING_DIR="/home/paulsczurek/code/fasttracktocleartracks/iot/raspi/image/incoming"
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