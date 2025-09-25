#!/bin/bash

# Raspberry Pi Camera Image Capture Script with Adaptive Exposure
# Optimized for outdoor photography with varying lighting conditions

# Configuration
INCOMING_DIR="/home/paulsczurek/code/fasttracktocleartracks/iot/raspi/image/incoming"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
FILENAME="captured_${TIMESTAMP}.jpg"
FILEPATH="${INCOMING_DIR}/${FILENAME}"
LOG_FILE="${INCOMING_DIR}/capture_log.txt"

# Camera settings optimized for outdoor conditions
WIDTH=1920
HEIGHT=1080
QUALITY=85

# Create incoming directory if it doesn't exist
mkdir -p "$INCOMING_DIR"

# Function to log messages
log_message() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# Function to get current hour (0-23)
get_hour() {
    date +%H
}

# Function to determine lighting conditions and camera settings
get_camera_settings() {
    local hour=$(get_hour)
    local month=$(date +%m)
    
    # Determine approximate lighting based on time and season
    # This is a simplified approach - you could enhance with light sensors
    
    if [ $hour -ge 6 ] && [ $hour -le 8 ]; then
        # Dawn - moderate low light
        echo "--ev 0.3 --ISO 400 --shutter 8000 --awb auto"
        log_message "Dawn lighting detected - using moderate exposure boost"
    elif [ $hour -ge 9 ] && [ $hour -le 16 ]; then
        # Daylight - normal to bright
        echo "--ev 0 --ISO 100 --shutter 2000 --awb daylight"
        log_message "Daylight detected - using standard exposure"
    elif [ $hour -ge 17 ] && [ $hour -le 19 ]; then
        # Dusk - moderate low light
        echo "--ev 0.3 --ISO 400 --shutter 8000 --awb auto"
        log_message "Dusk lighting detected - using moderate exposure boost"
    else
        # Night - very low light
        echo "--ev 0.5 --ISO 800 --shutter 30000 --awb auto"
        log_message "Night lighting detected - using high exposure boost"
    fi
}

# Function to capture image with adaptive settings
capture_with_rpicam() {
    local settings=$(get_camera_settings)
    log_message "Using rpicam-still with adaptive settings: $settings"
    
    rpicam-still \
        -o "$FILEPATH" \
        --width $WIDTH \
        --height $HEIGHT \
        --quality $QUALITY \
        --timeout 3000 \
        --immediate \
        $settings
}

# Function to capture image with legacy tool
capture_with_raspistill() {
    local hour=$(get_hour)
    local settings=""
    
    # Convert settings to raspistill format
    if [ $hour -ge 6 ] && [ $hour -le 8 ]; then
        settings="-ev 3 -ISO 400 -ss 8000 -awb auto"
        log_message "Dawn lighting - using raspistill with moderate exposure"
    elif [ $hour -ge 9 ] && [ $hour -le 16 ]; then
        settings="-ev 0 -ISO 100 -ss 2000 -awb sun"
        log_message "Daylight - using raspistill standard exposure"
    elif [ $hour -ge 17 ] && [ $hour -le 19 ]; then
        settings="-ev 3 -ISO 400 -ss 8000 -awb auto"
        log_message "Dusk lighting - using raspistill moderate exposure"
    else
        settings="-ev 5 -ISO 800 -ss 30000 -awb auto"
        log_message "Night lighting - using raspistill high exposure"
    fi
    
    raspistill \
        -o "$FILEPATH" \
        -w $WIDTH \
        -h $HEIGHT \
        -q $QUALITY \
        -t 3000 \
        $settings
}

# Main execution
log_message "Starting adaptive image capture for outdoor conditions"
log_message "Time: $(date), Hour: $(get_hour)"

# Check which camera tool is available and capture
if command -v rpicam-still &> /dev/null; then
    capture_with_rpicam
elif command -v raspistill &> /dev/null; then
    capture_with_raspistill
else
    log_message "ERROR: Neither rpicam-still nor raspistill found!"
    echo "Error: No camera tools available!"
    echo "Install with: sudo apt update && sudo apt install rpicam-apps"
    exit 1
fi

# Check if image was captured successfully
if [ -f "$FILEPATH" ]; then
    FILE_SIZE=$(du -h "$FILEPATH" | cut -f1)
    log_message "SUCCESS: Image captured - $FILENAME ($FILE_SIZE)"
    echo "✓ Image captured successfully: $FILENAME"
    echo "✓ Saved to: $FILEPATH"
    echo "✓ File size: $FILE_SIZE"
    echo "✓ Log: $LOG_FILE"
    
    # Optional: Basic image analysis using ImageMagick (if available)
    if command -v identify &> /dev/null; then
        IMAGE_INFO=$(identify -ping -format "%wx%h %[mean] %[standard-deviation]" "$FILEPATH" 2>/dev/null)
        if [ $? -eq 0 ]; then
            log_message "Image analysis: $IMAGE_INFO"
            echo "✓ Image info: $IMAGE_INFO"
        fi
    fi
    
    exit 0
else
    log_message "ERROR: Failed to capture image"
    echo "✗ Error: Failed to capture image!"
    exit 1
fi