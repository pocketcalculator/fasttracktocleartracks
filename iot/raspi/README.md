# Raspberry Pi IoT Setup

This directory contains IoT components for the Raspberry Pi, including camera capture functionality.

## 📁 Directory Structure

```
iot/raspi/
├── README.md                    # This overview
├── capture_image_smart.sh       # Quick-start smart camera script
├── capture_image/              # Complete camera capture solution
│   ├── README.md               # Full documentation
│   ├── capture_image.py        # Basic Python script
│   ├── capture_image.sh        # Basic shell script  
│   ├── capture_image_adaptive.py  # Advanced adaptive Python
│   └── capture_image_advanced_manual.py  # Advanced manual control Python
└── image/
    ├── incoming/               # Captured images
    ├── processing/             # Processing workspace
    └── archived/               # Processed images
```

## 🚀 Quick Start (Recommended)

For immediate outdoor camera capture with adaptive exposure:

```bash
# Run the smart script (handles all lighting conditions automatically)
./capture_image_smart.sh
```

## 📖 Full Documentation

For complete documentation, advanced features, and all script options, see:
**[capture_image/README.md](./capture_image/README.md)**

## 🎯 Key Features

- **Adaptive exposure** for outdoor photography
- **Time-based lighting adjustment** (day/night/dawn/dusk)
- **Advanced Python scripts** with real-time analysis
- **Exposure bracketing** for challenging conditions
- **Comprehensive logging** and metadata
- **Multiple script options** for different use cases

---
*For detailed setup, troubleshooting, and advanced features, navigate to the `capture_image` directory.*