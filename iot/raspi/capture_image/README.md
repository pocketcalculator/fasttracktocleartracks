# Raspberry Pi Camera Capture Scripts

This directory contains several camera capture scripts for Raspberry Pi with different features and capabilities.

## Scripts Overview

### 1. `capture_image_adaptive.py` (Recommended)
Advanced Python script with intelligent lighting analysis and adaptive exposure settings.

**Features:**
- ✅ Adaptive exposure based on lighting conditions
- ✅ EXIF metadata embedding (default) or JSON files
- ✅ Exposure bracketing
- ✅ Configurable output directory
- ✅ Comprehensive camera controls

**Usage:**
```bash
# Basic usage (auto-detects output directory)
python ./capture_image_adaptive.py

# With custom output directory
python ./capture_image_adaptive.py --output-dir /path/to/your/images

# High quality with manual settings
python ./capture_image_adaptive.py --quality 95 --width 3280 --height 2464

# Use JSON metadata instead of EXIF
python ./capture_image_adaptive.py --json-metadata

# See all options
python ./capture_image_adaptive.py --help
```

### 2. `capture_image_advanced_manual.py`
Python script with full manual control over camera settings.

**Features:**
- ✅ Manual exposure, ISO, white balance controls
- ✅ Configurable output directory
- ✅ Camera properties listing

**Usage:**
```bash
# Auto-detect output directory
python ./capture_image_advanced_manual.py

# Custom directory with manual settings
python ./capture_image_advanced_manual.py --output-dir /tmp/photos --exposure 10000 --iso 800
```

### 3. `capture_image.py`
Simple Python script for basic image capture.

**Features:**
- ✅ Simple and lightweight
- ✅ Auto-detects output directory
- ✅ Basic camera controls

### 4. `capture_image.sh`
Shell script using rpicam-still/raspistill for basic captures.

**Usage:**
```bash
# Auto-detect output directory
./capture_image.sh

# Custom output directory
./capture_image.sh /path/to/output
```

### 5. `capture_image_smart.sh`
Advanced shell script with time-based adaptive settings.

**Features:**
- ✅ Time-based exposure adaptation
- ✅ Logging
- ✅ Configurable output directory

**Usage:**
```bash
# Auto-detect output directory
./capture_image_smart.sh

# Custom output directory
./capture_image_smart.sh /path/to/output
```

## Output Directory Auto-Detection

All scripts now automatically detect the output directory in this order:

1. **Custom directory** (if specified with `--output-dir` or as first argument)
2. **Auto-detected** `../image/incoming` relative to the script location
3. **Fallback** `./incoming` in the same directory as the script

This makes the scripts portable and eliminates hard-coded paths!

## Directory Structure

The expected directory structure is:
```
iot/raspi/
├── capture_image/          # Scripts location
│   ├── capture_image_adaptive.py
│   ├── capture_image.sh
│   └── ...
└── image/
    ├── incoming/           # Auto-detected output directory
    ├── processing/
    └── archived/
```

## Metadata Storage

The `capture_image_adaptive.py` script stores rich metadata about each capture:

### EXIF Embedding (Default)
- Metadata is embedded directly in JPEG EXIF data
- Single file - no separate JSON files needed
- Standard EXIF fields + complete JSON in UserComment
- Portable - metadata travels with the image

### JSON Files (Optional)
Use `--json-metadata` flag to save metadata to separate JSON files alongside images.

## Reading Metadata

Use the included `read_exif_metadata.py` utility:

```bash
# Read EXIF-embedded metadata
python ./read_exif_metadata.py /path/to/image.jpg

# Read JSON metadata file
python ./read_exif_metadata.py /path/to/image.jpg --json-only

# Show raw JSON output
python ./read_exif_metadata.py /path/to/image.jpg --raw
```

## Examples

```bash
# Capture with adaptive settings to default location
python ./capture_image_adaptive.py

# High-resolution capture to custom directory
python ./capture_image_adaptive.py \
    --width 3280 --height 2464 \
    --quality 95 \
    --output-dir /media/usb/photos

# Night photography with bracketing
python ./capture_image_adaptive.py \
    --bracket \
    --preview 5 \
    --output-dir /tmp/night_photos

# Manual control for specific conditions
python ./capture_image_advanced_manual.py \
    --exposure 50000 \
    --iso 400 \
    --wb daylight \
    --output-dir /home/user/captures
```

## Requirements

- Raspberry Pi with camera module
- Python 3.7+ with picamera2, PIL, piexif, numpy
- rpicam-apps or legacy camera tools

Install dependencies:
```bash
sudo apt update
sudo apt install python3-picamera2 python3-pil python3-piexif python3-numpy rpicam-apps
```