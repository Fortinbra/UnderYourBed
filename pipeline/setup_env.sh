#!/usr/bin/env bash
set -euo pipefail
PYTHON=${PYTHON:-python3}
RHUBARB_URL=${RHUBARB_URL:-"https://github.com/DanielSWolf/rhubarb-lip-sync/releases/download/v1.13.0/rhubarb-lip-sync-1.13.0-linux.zip"}
TOOLS_DIR=${TOOLS_DIR:-tools_cache}
WITH_VOSK_SMALL=${WITH_VOSK_SMALL:-0}
VOSK_MODEL_URL=${VOSK_MODEL_URL:-}
MODELS_DIR=${MODELS_DIR:-models}

echo "Creating virtual environment..."
$PYTHON -m venv .venv
source .venv/bin/activate

pip install --upgrade pip
pip install -r requirements.txt
if [ "$WITH_VOSK_SMALL" = "1" ] || [ -n "$VOSK_MODEL_URL" ]; then
  pip install --upgrade vosk rapidfuzz
fi

echo "(Optional) Install ffmpeg via your package manager if missing." >&2

mkdir -p "$TOOLS_DIR"
RHUBARB_ZIP="$TOOLS_DIR/rhubarb.zip"
RHUBARB_BIN="$TOOLS_DIR/rhubarb"
if [ ! -f "$RHUBARB_BIN" ]; then
  echo "Downloading Rhubarb..."
  curl -L "$RHUBARB_URL" -o "$RHUBARB_ZIP"
  unzip -o "$RHUBARB_ZIP" -d "$TOOLS_DIR"
  FOUND=$(find "$TOOLS_DIR" -type f -name rhubarb | head -n 1 || true)
  if [ -n "$FOUND" ]; then
    cp "$FOUND" "$RHUBARB_BIN"
    chmod +x "$RHUBARB_BIN"
  fi
  rm "$RHUBARB_ZIP"
fi

if [ "$WITH_VOSK_SMALL" = "1" ] || [ -n "$VOSK_MODEL_URL" ]; then
  mkdir -p "$MODELS_DIR"
  URL=${VOSK_MODEL_URL:-https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip}
  echo "Downloading Vosk model: $URL"
  curl -L "$URL" -o "$MODELS_DIR/vosk_model.zip"
  unzip -o "$MODELS_DIR/vosk_model.zip" -d "$MODELS_DIR"
  rm "$MODELS_DIR/vosk_model.zip"
fi

echo "Setup complete. Activate with: source .venv/bin/activate"
echo "Example: python generate_lipsync.py --audio sample.wav --rhubarb $RHUBARB_BIN --out out.json"
