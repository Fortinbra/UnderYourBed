# UnderYourBed

Offline lip‑sync generation pipeline for animating an animatronic mouth from arbitrary YouTube links or local audio plus lyrics.

> Hardware / runtime code was removed for initial commit focus; repository currently ships only the portable content generation pipeline.

## Features

- YouTube or local audio ingestion (`yt-dlp`, `ffmpeg`)
- Rhubarb viseme extraction to frame list (`TimeSeconds`, `MouthOpen01`)
- Optional lyrics enrichment (word timing + emphasis)
- Forced alignment via Vosk (ASR) with fuzzy lyric matching fallback
- Automatic model & tool setup scripts (PowerShell / Bash)
- Run bundling with timestamped manifests + reproducibility metadata
- Clean environment scripts & strong `.gitignore` (no large binaries committed)

## Repository Layout

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

## License

See `LICENSE`.

