# Offline Lip-Sync & Asset Pipeline (PC Only)

This directory contains scripts and notes for producing lip-sync data and other assets on a powerful PC. Only the lightweight playback (servo + display control) runs on the Raspberry Pi in C#.

## Overview

1. Download source audio (e.g., YouTube) with `yt-dlp`.
2. Normalize / clean audio (ffmpeg, optional loudness normalization).
3. Run Rhubarb Lip Sync to extract viseme JSON.
4. Convert visemes into simplified frame list (`TimeSeconds`, `MouthOpen01`) OR enriched structure with lyrics.
5. Transfer produced JSON + audio (if needed) to the device that will drive your servo.

## Suggested Tools

- Python 3.11+
- `yt-dlp`
- `ffmpeg`
- Rhubarb Lip Sync (CLI)

## Environment Setup

Windows (PowerShell):

```powershell
cd pipeline
./setup_env.ps1 -WithVoskSmall
./.venv/Scripts/Activate.ps1
python generate_lipsync.py --audio sample.wav --rhubarb tools_cache/rhubarb.exe --out sample.lipsync.json
python generate_lipsync.py --youtube https://youtu.be/VIDEO --ffmpeg ffmpeg --rhubarb tools_cache/rhubarb.exe --out sample.lipsync.json
```

Linux / macOS:

```bash
cd pipeline
chmod +x setup_env.sh
WITH_VOSK_SMALL=1 ./setup_env.sh
source .venv/bin/activate
python generate_lipsync.py --audio sample.wav --rhubarb tools_cache/rhubarb --out sample.lipsync.json
python generate_lipsync.py --youtube https://youtu.be/VIDEO --ffmpeg ffmpeg --rhubarb tools_cache/rhubarb --out sample.lipsync.json
```

Ensure `ffmpeg` is installed (e.g. `sudo apt-get install -y ffmpeg` or via package manager) before running.
If you see `FileNotFoundError` referencing ffmpeg, install it or pass the explicit path with `--ffmpeg C:/path/to/ffmpeg.exe`.

### Rhubarb Resource Error (cmudict-en-us.dict)

If Rhubarb reports a missing `cmudict-en-us.dict`, the `res` directory wasn’t placed beside `rhubarb.exe`.

Fix:

1. Re-run `setup_env.ps1` (it now copies the `res` folder automatically after extraction), OR
2. Manually copy the `res` folder from the unzipped Rhubarb release into `pipeline/tools_cache/` so you have:

```text
pipeline/tools_cache/rhubarb.exe
pipeline/tools_cache/res/sphinx/cmudict-en-us.dict
```

Then re-run the generation command.

## Generated Output Formats

Legacy (no lyrics): JSON array
[
  { "TimeSeconds": 0.00, "MouthOpen01": 0.00 },
  { "TimeSeconds": 0.02, "MouthOpen01": 0.35 }
]

Enriched (with `--lyrics`): JSON object
{
  "frames": [ { "TimeSeconds": 0.00, "MouthOpen01": 0.00 }, ... ],
  "words": [ { "StartSeconds": 0.00, "EndSeconds": 0.12, "Word": "Ding", "LineIndex": 0, "Emphasis": true }, ... ],
  "metadata": { "schema": 1, "version": "1.0.0", ... }
}

`words` timing is a proportional heuristic using word length across total voiced duration (fast + no external models). For production-quality alignment you could later integrate a phoneme aligner (e.g. Montreal Forced Aligner) and just replace the `words` section.

`MouthOpen01` values can be clamped via `--min-open`/`--max-open` to compensate for servo dead zones.

## Extending

If you later support multiple servos (jaw, upper lip, lower lip), generate objects like:

```json
{
  "TimeSeconds": 1.23,
  "Jaw": 0.7,
  "LipUpper": 0.2,
  "LipLower": 0.5
}
```

Then adapt the C# playback.

## Workflow Script

See `generate_lipsync.py` for an automated pipeline. Key flags:

 -youtube \<url\>            Download & process audio from YouTube
 -audio \<path\>             Use local audio file
--lyrics hideandseek.txt   Enrich output with word timings & emphasis
--fps 50                   Target frame rate for mouth samples
--min-open 0.1             Raise floor (servo slack)
--max-open 0.9             Lower ceiling (mechanical safety)
--emphasis-scale 1.25      Boost frames inside emphasized word spans
--print-summary            Emit concise JSON summary to stdout
 --bundle-root bundles      Create timestamped bundle folder under project root 'bundles/' (kept outside pipeline/) storing output + manifest
--bundle-include-audio     Also copy 16k mono wav into the bundle (kept gitignored)
--bundle-include-original  Also copy original source audio (e.g. .m4a) into bundle (gitignored)

Example enriched run:

```powershell
python generate_lipsync.py `
  --youtube https://youtu.be/VIDEO `
  --rhubarb tools_cache/rhubarb.exe `
  --lyrics ..\hideandseek.txt `
  --fps 50 `
  --min-open 0.05 `
  --max-open 0.95 `
  --out song.lipsync.json `
  --print-summary
```

The printed summary (one line JSON) can be parsed by other scripts:
{"frames":1234,"durationSeconds":61.2,"fps":50.0,"lyrics":true,"schema":1}

## Forced Alignment (Vosk)

Two strategies exist:

- heuristic (default): proportional distribution by word length
- vosk: real ASR-based timing (needs 16kHz mono wav + model)

Install & download model during setup with `-WithVoskSmall` (PowerShell) or `WITH_VOSK_SMALL=1` (bash) OR use the standalone downloader:

```powershell
python download_models.py --vosk-small
```

Then run:

```powershell
python generate_lipsync.py --audio song.wav --rhubarb tools_cache\rhubarb.exe --lyrics ..\hideandseek.txt --aligner vosk --vosk-model models\vosk-model-small-en-us-0.15 --out song.lipsync.json
```

If Vosk fails it falls back to heuristic automatically.

## Cleanup

Remove virtual env, models, intermediates, and generated artifacts interactively:

```powershell
./cleanup_env.ps1
```

Force non-interactive:

```powershell
./cleanup_env.ps1 -Force
```

Unix:

```bash
./cleanup_env.sh            # prompts
FORCE=1 ./cleanup_env.sh    # no prompts
```

## Bundling Runs

Use bundling to archive each run (audio stays local / ignored):

```powershell
python generate_lipsync.py `
  --youtube https://youtu.be/ID `
  --rhubarb tools_cache\rhubarb.exe `
  --lyrics ..\hideandseek.txt `
  --aligner vosk `
  --vosk-model models\vosk-model-small-en-us-0.15 `
  --out song.lipsync.json `
  --bundle-root bundles `
  --bundle-include-audio
  --bundle-include-original
```

Result structure (example) when invoked from within pipeline/ with `--bundle-root bundles` (bundles placed at repo root):

```text
bundles/
  G-YNNJIe2Vk_20250903-201530/
    song.lipsync.json
    manifest.json
    hideandseek.txt
    rhubarb.raw.json
    input.wav (optional if included)
```

`manifest.json` captures parameters, counts, and file references for reproducibility.

Note: Any relative path passed to `--bundle-root` is resolved relative to the repository root (parent of `pipeline/`) so that archives do not clutter the pipeline folder. Provide an absolute path if you need a custom location elsewhere.
