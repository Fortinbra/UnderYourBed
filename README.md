# UnderYourBed Animatronic System

A modular Python library for controlling animatronic systems with synchronized audio, servo movement, and OLED eye displays.

## 🎭 Features

- **Dual OLED Eye Displays**: Control SSD1351 128x128 RGB displays as animated eyes
- **Servo Mouth Control**: PCA9685-based servo control for lip-sync animation  
- **Audio Playback**: Multi-backend audio with precise timing synchronization
- **Modular Architecture**: Clean, importable modules for each subsystem
- **Content Pipeline**: Offline lip‑sync generation from YouTube links or local audio
- **Easy Integration**: Simple high-level API for complete performances

## 🔧 Hardware Requirements

### Eye Displays
- 2x SSD1351 OLED displays (128x128 RGB)
- SPI connection to Raspberry Pi
- Separate DC/RST pins for dual display support

### Servo Control
- Adafruit PCA9685 servo driver board
- Standard servo motor (SG90, MG996R, etc.)
- I2C connection to Raspberry Pi

### Audio
- Any Raspberry Pi audio output (3.5mm, HDMI, USB)
- Optional: External speakers or amplifier

## 📋 Pin Configuration

**Recommended GPIO pin assignment for dual eyes:**

| Signal | Left Eye      | Right Eye     | Shared        |
|--------|---------------|---------------|---------------|
| VCC    | Pin 1 (3.3V)  | Pin 1 (3.3V)  |               |
| GND    | Pin 6 (GND)   | Pin 6 (GND)   |               |
| SCK    |               |               | Pin 23 (GPIO11) |
| MOSI   |               |               | Pin 19 (GPIO10) |
| DC     | Pin 18 (GPIO24) | Pin 16 (GPIO23) |           |
| RST    | Pin 22 (GPIO25) | Pin 15 (GPIO22) |           |
| CS     | Pin 24 (GPIO8)  | Pin 26 (GPIO7)  |           |

**Servo Connection:**
- PCA9685 board connected via I2C (SDA/SCL)
- Servo connected to PCA9685 channel 0 (default)

## 🚀 Quick Start

### Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/Fortinbra/UnderYourBed.git
   cd UnderYourBed
   ```

2. **Create virtual environment:**
   ```bash
   python3 -m venv animatronic_env
   source animatronic_env/bin/activate
   ```

3. **Install dependencies:**
   ```bash
   # Python packages
   pip install -r requirements.txt
   
   # System packages
   sudo apt update
   sudo apt install -y ffmpeg python3-dev libasound2-dev portaudio19-dev
   ```

4. **Enable SPI and I2C:**
   ```bash
   sudo raspi-config
   # Navigate to Interface Options > SPI > Enable
   # Navigate to Interface Options > I2C > Enable
   # Reboot when prompted
   ```

### Basic Usage

```python
from animatronic import AnimatronicController

# Create controller
robot = AnimatronicController()

# Initialize all systems
robot.initialize()

# Play a complete performance
robot.play_performance("data/song.lipsync.json", "data/audio.wav")

# Manual control
robot.set_mouth_position(0.5)  # 50% open
robot.set_eye_positions((5, -2), (-3, 1))  # Move pupils
robot.blink()  # Single blink

# Cleanup
robot.close()
```

## 📁 Project Structure

```
UnderYourBed/
├── src/animatronic/           # Core library modules
│   ├── __init__.py           # Main imports
│   ├── controller.py         # High-level system orchestration
│   ├── display.py           # OLED eye display control
│   ├── servo.py             # Servo motor control
│   └── audio.py             # Audio playback and lip-sync
├── examples/                 # Usage examples
│   ├── basic_usage.py       # Complete system example
│   └── eyes_only.py         # Eye display testing
├── bundles/                 # Performance data
│   └── [bundle-name]/       # Audio + lip-sync data
├── pipeline/                # Content generation tools
├── runtime/                 # Legacy utilities
├── requirements.txt         # Python dependencies
└── README.md               # This file
```

## 🎨 Modules Overview

### Display Module (`animatronic.display`)
- **`SSD1351Display`**: Low-level OLED control
- **`EyeRenderer`**: Eyeball graphics rendering  
- **`DualEyeController`**: Coordinated dual-eye control
- **`Colors`**: BGR565 color utilities

### Servo Module (`animatronic.servo`)  
- **`ServoController`**: Individual servo control
- **`LipSyncController`**: Animated lip-sync playback

### Audio Module (`animatronic.audio`)
- **`AudioPlayer`**: Multi-backend audio playback
- **`LipSyncData`**: Lip-sync data loading and processing

### Controller Module (`animatronic.controller`)
- **`AnimatronicController`**: Complete system orchestration

## 📖 Examples

### Eyes Only Test
```python
from animatronic.display import DualEyeController

eyes = DualEyeController()
eyes.initialize()

# Test colors
eyes.left_display.fill_screen((0x00, 0xF8))   # Red
eyes.right_display.fill_screen((0x1F, 0x00))  # Green

# Animate eyeballs
eyes.draw_eyes((10, 5), (-5, 8), blink_amount=0.0)

eyes.close()
```

### Servo Only Test
```python
from animatronic.servo import ServoController

servo = ServoController(channel=0)
servo.initialize()

# Manual positioning
servo.set_position(0.0)   # Closed
servo.set_position(1.0)   # Open
servo.center()            # 50% open

servo.close()
```

## 🎬 Content Generation Pipeline

The pipeline tools generate lip-sync data from audio files:

- YouTube or local audio ingestion (`yt-dlp`, `ffmpeg`)
- Rhubarb viseme extraction to frame list (`TimeSeconds`, `MouthOpen01`)
- Optional lyrics enrichment (word timing + emphasis)
- Forced alignment via Vosk (ASR) with fuzzy lyric matching fallback
- Automatic model & tool setup scripts (PowerShell / Bash)

See `pipeline/` directory for content generation tools.

```text
hideandseek.txt                # Sample lyrics (tracked)
pipeline/                      # Python offline pipeline
	generate_lipsync.py          # Main generator (Rhubarb + alignment + bundling)
	setup_env.ps1 / setup_env.sh # Environment + optional model/tool download
	download_models.py           # Standalone model fetcher (Vosk)
	cleanup_env.ps1 / .sh        # Remove venv, models, intermediates
	bundles/                     # (Created on runs) archived outputs (audio ignored)
	models/                      # Speech / alignment models (ignored except README)
	tools_cache/                 # Downloaded executables (ignored except README)
```

## Quick Start (Windows PowerShell)

```powershell
cd pipeline
./setup_env.ps1 -WithVoskSmall   # creates .venv, downloads rhubarb + small Vosk model
./.venv/Scripts/Activate.ps1
python generate_lipsync.py `
	--youtube https://www.youtube.com/watch?v=G-YNNJIe2Vk `
	--rhubarb tools_cache/rhubarb.exe `
	--lyrics ..\hideandseek.txt `
	--aligner vosk `
	--vosk-model models\vosk-model-small-en-us-0.15 `
	--fps 50 `
	--out song.lipsync.json `
	--bundle-root bundles `
	--bundle-include-audio `
	--print-summary
```

## Quick Start (Linux / macOS)

```bash
cd pipeline
chmod +x setup_env.sh
WITH_VOSK_SMALL=1 ./setup_env.sh
source .venv/bin/activate
python generate_lipsync.py \
	--audio path/to/local_audio.mp3 \
	--rhubarb tools_cache/rhubarb \
	--lyrics ../hideandseek.txt \
	--aligner vosk \
	--vosk-model models/vosk-model-small-en-us-0.15 \
	--out song.lipsync.json \
	--bundle-root bundles \
	--print-summary
```

## Output

Enriched JSON bundle (object form) contains:

```jsonc
{
	"frames": [ { "TimeSeconds": 0.00, "MouthOpen01": 0.0 }, ... ],
	"words":  [ { "StartSeconds": 0.00, "EndSeconds": 0.12, "Word": "Ding", "Emphasis": true }, ... ],
	"metadata": { "schema": 1, "version": "1.0.0", "aligner": "vosk" }
}
```

Each bundled run also writes `manifest.json` summarizing parameters and source references.

## Bundling & Reproducibility

Use `--bundle-root bundles` to create a timestamped directory preserving:
`song.lipsync.json`, `manifest.json`, lyrics copy, raw `rhubarb.raw.json`, and optionally the normalized WAV (ignored by git).

## Cleaning

```powershell
cd pipeline
./cleanup_env.ps1 -Force
```

## Git Tracking Policy

Tracked: scripts, manifests, lyrics (.txt), generated lip‑sync JSON retained inside bundles (explicit allow)

Ignored: audio binaries (wav/mp3/m4a/flac), downloaded tools (rhubarb), large ASR models, intermediate work dir.

## Roadmap (Future)

- Servo playback runtime (separate repo or future re‑addition)
- Multi‑viseme / multi‑jaw parameter curves
- Phoneme smoothing & easing strategies
- Alternative aligners (MFA integration)

## Runtime Playback (Experimental)

An experimental Python playback script for Raspberry Pi 5 is included at `runtime/playback.py`.

Install on Pi:

```bash
cd runtime
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-runtime.txt
sudo apt-get install -y ffmpeg
```

Run (assuming a bundled output + copied/converted WAV):

```bash
python playback.py \
	--frames ../pipeline/bundles/G-YNNJIe2Vk_YYYYMMDD-HHMMSS/song.lipsync.json \
	--audio ../pipeline/bundles/G-YNNJIe2Vk_YYYYMMDD-HHMMSS/input.wav \
	--servo-channel 0 --eyes --aligner vosk
```

Adjust angles with `--min-angle` / `--max-angle` and fine tune sync via `--audio-delay-ms`.

## License

See `LICENSE`.

