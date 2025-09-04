#!/usr/bin/env python3
"""Real-time playback of lip-sync frames + audio on Raspberry Pi.

Features:
 - Uses pre-generated lip-sync JSON (simple array or enriched object schema).
 - Plays original audio (wav/m4a/mp3) via ffplay or python sounddevice fallback.
 - Drives Adafruit PCA9685 servo hat to animate mouth.
 - Optional dual 128x128 RGB OLED eyes (SSD1351) with simple pupil & blink animation.
 - Graceful degradation: can run with --dry-run or without eyes/audio.

Requirements (install on Pi inside venv):
  pip install adafruit-circuitpython-pca9685 adafruit-circuitpython-busdevice Pillow luma.oled
  (Audio) sudo apt-get install -y ffmpeg

Usage examples:
  python playback.py --frames bundle/song.lipsync.json --audio bundle/input.wav --servo-channel 0
  python playback.py --frames bundle/song.lipsync.json --audio bundle/input.wav --eyes --left-cs 0 --right-cs 1

NOTE: ffplay start latency is compensated by aligning timeline to the moment the process is launched.
For tighter sync you can pass --audio-delay-ms to advance/retard servo updates.
"""
from __future__ import annotations
import argparse, json, time, math, os, sys, threading, subprocess, signal
from pathlib import Path

# Optional imports (loaded lazily to allow dry-run / headless execution)
try:
    from adafruit_pca9685 import PCA9685  # type: ignore
    from board import SCL, SDA  # type: ignore
    import busio  # type: ignore
except Exception:  # pragma: no cover - hardware not present
    PCA9685 = None  # type: ignore

EYE_AVAILABLE = True
try:  # pragma: no cover
    from luma.core.interface.serial import spi
    from luma.oled.device import ssd1351
    from PIL import Image, ImageDraw
except Exception:
    EYE_AVAILABLE = False


def load_frames(path: str):
    data = json.loads(Path(path).read_text())
    if isinstance(data, list):
        frames = data
        words = []
    else:
        frames = data.get("frames", [])
        words = data.get("words", [])
    # Validate minimal fields
    for f in frames:
        if "TimeSeconds" not in f or "MouthOpen01" not in f:
            raise ValueError("Invalid frame missing TimeSeconds/MouthOpen01")
    return frames, words


class ServoMouth:
    def __init__(self, channel: int, min_angle=20.0, max_angle=90.0, dry=False):
        self.channel = channel
        self.min_angle = min_angle
        self.max_angle = max_angle
        self.dry = dry or (PCA9685 is None)
        if not self.dry:
            i2c = busio.I2C(SCL, SDA)
            self.pca = PCA9685(i2c)
            self.pca.frequency = 50
        else:
            self.pca = None

    def set_open(self, openness01: float):
        openness01 = max(0.0, min(1.0, openness01))
        angle = self.min_angle + (self.max_angle - self.min_angle) * openness01
        if self.dry:
            return
        # Convert to pulse (approx 500-2500us -> 0-180 deg mapping)
        min_us, max_us = 500, 2500
        pulse_us = min_us + (angle / 180.0) * (max_us - min_us)
        ticks = int(pulse_us * 4096 / 20000)  # 20ms frame
        channel = self.pca.channels[self.channel]
        channel.duty_cycle = ticks << 4  # library expects 16-bit, scale up

    def close(self):
        if self.pca:
            self.pca.deinit()


class DualEyes:
    def __init__(self, left_cs=0, right_cs=1, enabled=True):
        self.enabled = enabled and EYE_AVAILABLE
        if not self.enabled:
            self.left = self.right = None
            return
        serial_left = spi(device=left_cs, port=0)
        serial_right = spi(device=right_cs, port=0)
        self.left = ssd1351(serial_left)
        self.right = ssd1351(serial_right)
        self.size = (self.left.width, self.left.height)
        self._last_blink = time.perf_counter()
        self._blink_dur = 0.15
        self._blinking = False

    def render(self, energy: float, t: float):  # energy 0..1
        if not self.enabled:
            return
        w, h = self.size
        # Blink scheduling (every ~5-8s random)
        if not self._blinking and t - self._last_blink > 5 + (hash(int(t)) % 3):
            self._blinking = True
            self._blink_start = t
        if self._blinking and t - self._blink_start > self._blink_dur:
            self._blinking = False
            self._last_blink = t
        # Eye image
        img = Image.new("RGB", (w, h), (0, 0, 0))
        draw = ImageDraw.Draw(img)
        # Sclera
        draw.ellipse((0, 0, w - 1, h - 1), fill=(255, 255, 255))
        if self._blinking:
            lid = int(h * 0.5)
            draw.rectangle((0, 0, w, lid), fill=(0, 0, 0))
            draw.rectangle((0, h - lid, w, h), fill=(0, 0, 0))
        else:
            # Pupil moves slightly with energy
            max_offset = int(w * 0.15)
            offset = int(max_offset * (0.5 - 0.5 * math.cos(energy * math.pi)))
            px = w // 2 + offset
            py = h // 2
            r = int(w * 0.18)
            draw.ellipse((px - r, py - r, px + r, py + r), fill=(0, 0, 0))
        self.left.display(img)
        self.right.display(img.transpose(Image.FLIP_LEFT_RIGHT))


def play_audio_ffplay(path: str):
    return subprocess.Popen([
        'ffplay', '-nodisp', '-autoexit', '-loglevel', 'quiet', path
    ])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--frames', required=True, help='Path to lip-sync JSON (array or enriched object).')
    ap.add_argument('--audio', required=True, help='Path to audio file (wav/m4a/mp3).')
    ap.add_argument('--servo-channel', type=int, default=0)
    ap.add_argument('--min-angle', type=float, default=20.0)
    ap.add_argument('--max-angle', type=float, default=90.0)
    ap.add_argument('--audio-delay-ms', type=float, default=0.0, help='Adjust sync (+ delays servo, - advances).')
    ap.add_argument('--eyes', action='store_true', help='Enable dual eye rendering (two SSD1351 displays).')
    ap.add_argument('--left-cs', type=int, default=0)
    ap.add_argument('--right-cs', type=int, default=1)
    ap.add_argument('--dry-run', action='store_true')
    args = ap.parse_args()

    frames, words = load_frames(args.frames)
    if not frames:
        print('No frames loaded.', file=sys.stderr)
        return 1

    servo = ServoMouth(args.servo_channel, args.min_angle, args.max_angle, dry=args.dry_run)
    eyes = DualEyes(args.left_cs, args.right_cs, enabled=args.eyes)

    # Precompute times for loop efficiency
    times = [f['TimeSeconds'] for f in frames]
    openness = [f['MouthOpen01'] for f in frames]
    energy_shared = {'value': 0.0}
    stop_flag = {'stop': False}

    def eye_thread():  # pragma: no cover - hardware rendering
        while not stop_flag['stop']:
            tnow = time.perf_counter()
            # Simple smoothing
            e = energy_shared['value']
            eyes.render(e, tnow)
            time.sleep(1/30)

    if args.eyes and eyes.enabled:
        et = threading.Thread(target=eye_thread, daemon=True)
        et.start()

    # Launch audio
    audio_proc = None
    if not args.dry_run:
        audio_proc = play_audio_ffplay(args.audio)

    start = time.perf_counter()
    audio_offset = args.audio_delay_ms / 1000.0
    i = 0
    total = len(times)
    try:
        while i < total:
            now = time.perf_counter() - start + audio_offset
            # Busy-wait with small sleep
            if now < times[i]:
                time.sleep(0.001)
                continue
            energy_shared['value'] = openness[i]
            servo.set_open(openness[i])
            i += 1
        # Wait for audio to finish
        if audio_proc:
            audio_proc.wait()
    except KeyboardInterrupt:
        print('Interrupted.')
    finally:
        stop_flag['stop'] = True
        servo.close()
        if audio_proc and audio_proc.poll() is None:
            audio_proc.send_signal(signal.SIGINT)
    return 0


if __name__ == '__main__':
    sys.exit(main())
