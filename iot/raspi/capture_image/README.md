# Raspberry Pi Camera Capture Scripts

This directory contains multiple approaches to capture images from your Raspberry Pi camera and save them to the `incoming` directory, **with special focus on outdoor photography with varying lighting conditions**.

## 📁 Directory Structure

```
iot/raspi/
├── capture_image_smart.sh              # Smart shell script (RECOMMENDED)
├── capture_image/                      # Camera capture scripts directory
│   ├── README.md                       # This documentation
│   ├── capture_image.py                # Basic Python script
│   ├── capture_image.sh                # Basic shell script
│   ├── capture_image_adaptive.py       # Advanced adaptive Python script
│   └── capture_image_advanced_manual.py # Advanced manual control Python script
└── image/
    ├── incoming/                       # Images saved here
    ├── processing/                     # For image processing
    └── archived/                       # For processed images
```

## 🌅 NEW: Adaptive Exposure for Outdoor Use

For outdoor installations that need to capture images throughout the day and night, we now have **intelligent adaptive exposure** scripts that automatically adjust camera settings based on lighting conditions.

## Prerequisites

### For Shell Scripts
```bash
# Install camera tools (modern approach)
sudo apt update
sudo apt install rpicam-apps

# Optional: ImageMagick for image analysis
sudo apt install imagemagick

# OR for older systems
sudo apt install raspistill
```

### For Python Scripts
```bash
# Install required packages
sudo apt update
sudo apt install python3-picamera2 python3-pip

# Additional packages for advanced features
pip3 install pillow numpy
```

## Available Scripts

### 🚀 1. Smart Shell Script - `../capture_image_smart.sh` (RECOMMENDED FOR OUTDOOR)
**Best for:** Unattended outdoor photography, varying lighting conditions

```bash
# Basic usage - automatically adapts to current lighting
../capture_image_smart.sh

# The script automatically:
# - Detects time of day and adjusts exposure settings
# - Dawn/Dusk: Moderate exposure boost (EV +0.3, ISO 400)
# - Daylight: Standard exposure (EV 0, ISO 100)
# - Night: High exposure boost (EV +0.5, ISO 800)
# - Logs all captures with timestamps and settings
# - Works with both rpicam-still and raspistill
```

**Outdoor Features:**
- ⏰ **Time-based exposure adaptation** (dawn, day, dusk, night)
- 📋 **Comprehensive logging** of all captures and settings
- 🌤️ **Weather-appropriate white balance** settings
- 🔍 **Optional image analysis** with ImageMagick
- 🔧 **Automatic tool detection** (modern vs legacy camera tools)
- 📊 **Capture statistics and file size reporting**

### 🧠 2. Advanced Python Script - `capture_image_adaptive.py` (MAXIMUM CONTROL)
**Best for:** Professional outdoor installations, research applications

```bash
# Basic adaptive exposure (analyzes actual lighting conditions)
./capture_image_adaptive.py

# Exposure bracketing for challenging conditions
./capture_image_adaptive.py --bracket

# Disable adaptive exposure for manual control
./capture_image_adaptive.py --no-adaptive --exposure 5000 --iso 400

# High resolution for detailed outdoor monitoring
./capture_image_adaptive.py --width 2592 --height 1944 --quality 95
```

**Advanced Outdoor Features:**
- 🔬 **Real-time lighting analysis** using actual preview images
- 📸 **Exposure bracketing** - captures multiple exposures and selects best
- 🌡️ **Intelligent exposure compensation** based on scene brightness
- 📈 **Histogram analysis** to prevent over/under exposure
- 💾 **Detailed metadata** including lighting conditions and camera settings
- 🎯 **Automatic best-shot selection** from bracketed exposures

### 3. Basic Shell Script - `capture_image.sh` (SIMPLE)
**Best for:** Basic indoor use, manual lighting control

```bash
./capture_image.sh
```

### 4. Basic Python Script - `capture_image.py` (PYTHON INTEGRATION)
**Best for:** Integration with other Python projects

```bash
./capture_image.py
```

### 5. Advanced Manual Control Script - `capture_image_advanced_manual.py` (EXPERT CONTROL)
**Best for:** Photography experts who need precise manual control over every setting

```bash
# Custom resolution and manual exposure
./capture_image_advanced_manual.py --width 2592 --height 1944 --exposure 5000 --iso 400

# Manual white balance and image transformations  
./capture_image_advanced_manual.py --wb daylight --rotation 180 --flip-h

# List camera capabilities
./capture_image_advanced_manual.py --list-props
```

**Manual Control Features:**
- Precise exposure time control (microseconds)
- Manual ISO settings (100-1600)
- Custom white balance modes
- Image rotation and flipping
- High-resolution capture options
- Camera property inspection
- No automatic adjustments - you control everything

## 🌍 Outdoor Photography Recommendations

### For 24/7 Outdoor Monitoring:
```bash
# Use the smart shell script with cron
crontab -e

# Capture every hour with adaptive exposure
0 * * * * /home/paulsczurek/code/fasttracktocleartracks/iot/raspi/capture_image_smart.sh

# Or every 30 minutes during daylight hours (6 AM - 8 PM)
*/30 6-20 * * * /home/paulsczurek/code/fasttracktocleartracks/iot/raspi/capture_image_smart.sh

# Or every 2 hours during night (9 PM - 5 AM) to save storage
0 21,23,1,3,5 * * * /home/paulsczurek/code/fasttracktocleartracks/iot/raspi/capture_image_smart.sh
```

### For Research/High-Quality Outdoor Capture:
```bash
# Use Python script with bracketing for best quality
./capture_image_adaptive.py --bracket --width 2592 --height 1944 --quality 95
```

### For Variable Weather Conditions:
```bash
# The smart script automatically handles:
# ☀️ Bright sunny days - reduces exposure to prevent blown highlights
# ⛅ Overcast conditions - uses auto white balance and standard exposure
# 🌅 Dawn/dusk - boosts exposure and adjusts white balance
# 🌙 Night conditions - significant exposure boost and higher ISO
```

## Lighting Adaptation Details

### Smart Shell Script Time-Based Adaptation:
- **06:00-08:59**: Dawn (EV +0.3, ISO 400, 8ms exposure, auto WB)
- **09:00-16:59**: Day (EV 0, ISO 100, 2ms exposure, daylight WB)
- **17:00-19:59**: Dusk (EV +0.3, ISO 400, 8ms exposure, auto WB)
- **20:00-05:59**: Night (EV +0.5, ISO 800, 30ms exposure, auto WB)

### Python Adaptive Analysis:
- **Very Dark** (brightness < 50): Long exposure mode, ISO boost 2x
- **Dark** (brightness < 100): Normal exposure mode, ISO boost 1.5x
- **Normal** (brightness 100-180): Standard auto settings
- **Very Bright** (brightness > 180): Short exposure mode, reduce exposure

## Output Files and Logging

### File Locations
All scripts save to: `/home/paulsczurek/code/fasttracktocleartracks/iot/raspi/image/incoming/`

### Smart Script Output:
```
incoming/
├── captured_20250925_143022.jpg          # Main image
├── capture_log.txt                       # Comprehensive log
└── captured_20250925_143155.jpg
```

### Adaptive Python Script Output:
```
incoming/
├── captured_20250925_143022.jpg          # Main image
├── captured_20250925_143022_metadata.json # Detailed metadata
└── captured_20250925_143155.jpg
```

### Sample Log Entry (Smart Script):
```
[2025-09-25 14:30:22] Starting adaptive image capture for outdoor conditions
[2025-09-25 14:30:22] Time: Wed Sep 25 14:30:22 UTC 2025, Hour: 14
[2025-09-25 14:30:22] Daylight detected - using standard exposure
[2025-09-25 14:30:25] SUCCESS: Image captured - captured_20250925_143022.jpg (1.2M)
```

## Troubleshooting Outdoor Conditions

### Poor Image Quality in Low Light:
```bash
# Try the Python script with bracketing
./capture_image_adaptive.py --bracket

# Or manually increase exposure in smart script
# Edit the script to increase ISO and exposure time for night conditions
```

### Overexposed Images in Bright Sun:
```bash
# The scripts should handle this automatically, but you can manually adjust:
./capture_image_adaptive.py --no-adaptive --exposure 1000 --iso 100
```

### Inconsistent White Balance:
```bash
# For specific lighting conditions, set manual white balance:
./capture_image_adaptive.py --wb daylight    # For sunny conditions
./capture_image_adaptive.py --wb cloudy      # For overcast conditions
```

### Camera Not Working in Cold/Hot Weather:
- Ensure proper housing and ventilation
- Consider adding a warming circuit for very cold conditions
- Monitor the capture logs for hardware errors

## 🎯 Final Recommendations for Outdoor Use:

1. **For Simple 24/7 Monitoring**: Use `../capture_image_smart.sh` with cron
2. **For Research/High Quality**: Use `capture_image_adaptive.py` with `--bracket`
3. **For Testing**: Start with `../capture_image_smart.sh` to verify basic functionality

The smart shell script with time-based adaptation is usually the most reliable for outdoor installations since it doesn't depend on complex image analysis and handles varying conditions predictably.