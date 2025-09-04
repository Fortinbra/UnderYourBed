#!/usr/bin/env python3
"""
Offline lip-sync generation script.

Steps:
1. Download audio from YouTube (if --youtube provided) using yt-dlp.
2. Convert to 16kHz mono WAV via ffmpeg.
3. Run Rhubarb Lip Sync to produce viseme JSON.
4. Map visemes to MouthOpen01 frames at desired FPS.

Usage examples:
  python generate_lipsync.py --youtube https://www.youtube.com/watch?v=VIDEO --out lipsync.json
  python generate_lipsync.py --audio localfile.mp3 --out lipsync.json

Requires: yt-dlp, ffmpeg, rhubarb in PATH (or specify --rhubarb ./rhubarb )
"""
from __future__ import annotations
import argparse, subprocess, json, tempfile, shutil, sys, math, os, re, datetime, urllib.parse
from pathlib import Path
import shutil

SCRIPT_VERSION = "1.0.0"

VISEME_OPEN_MAP = {
    "A": 0.9,
    "B": 0.2,
    "C": 0.6,
    "D": 0.8,
    "E": 0.1,
    "F": 0.3,
    "G": 0.7,
    "H": 0.5,
}

def run(cmd: list[str], check=True):
    print("[run]", " ".join(cmd))
    p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    if p.returncode != 0 and check:
        print(p.stdout)
        raise SystemExit(f"Command failed: {' '.join(cmd)}")
    return p.stdout

def ensure_wav(input_path: Path, work: Path, ffmpeg: str) -> Path:
    if input_path.suffix.lower() == ".wav":
        return input_path
    out = work / "input.wav"
    run([ffmpeg, "-y", "-i", str(input_path), "-ar", "16000", "-ac", "1", str(out)])
    return out

def download_youtube(url: str, work: Path) -> Path:
    out_file = work / "download.m4a"
    run(["yt-dlp", "-f", "bestaudio", "-o", str(out_file), url])
    return out_file

def run_rhubarb(rhubarb: str, wav: Path, work: Path) -> dict:
    out_json = work / "rhubarb.json"
    run([rhubarb, "-f", "json", "-o", str(out_json), str(wav)])
    return json.loads(out_json.read_text())

def cues_to_frames(data: dict, fps: float) -> list[dict]:
    """Convert Rhubarb mouth cues to fixed-rate frames.

    Optimized to iterate cues once instead of searching each frame (O(N+F)).
    """
    cues = data.get("mouthCues", [])
    if not cues:
        return []
    # Sort defensively (Rhubarb usually outputs sorted)
    cues = sorted(cues, key=lambda c: c.get("start", 0.0))
    duration = max(c.get("end", 0.0) for c in cues)
    dt = 1.0 / fps
    frames = []
    cue_index = 0
    active = cues[cue_index]
    for i in range(int(math.ceil(duration / dt))):
        t = i * dt
        # Advance cue if time past end
        while cue_index < len(cues) and t >= cues[cue_index].get("end", 0.0):
            cue_index += 1
            if cue_index < len(cues):
                active = cues[cue_index]
        if cue_index < len(cues) and active.get("start",0.0) <= t < active.get("end",0.0):
            open_amt = VISEME_OPEN_MAP.get(active.get("value"), 0.0)
        else:
            open_amt = 0.0
        frames.append({"TimeSeconds": round(t, 5), "MouthOpen01": round(open_amt, 3)})
    return frames

def load_lyrics_words(path: str) -> list[dict]:
    """Parse a lyrics text file into ordered word entries with simple emphasis heuristics.

    Heuristics:
      - A word containing any uppercase letter beyond the first is emphasis.
      - Lines ending with ! or ? mark all their words emphasized.
      - Specific repeated onomatopoeia like 'ding'/'dong' are emphasized.
    """
    words: list[dict] = []
    emphasis_tokens = {"ding", "dong"}
    with open(path, "r", encoding="utf-8") as f:
        for line_index, raw in enumerate(f):
            line = raw.strip()
            if not line:
                continue
            line_emphasis = line.endswith("!") or line.endswith("?")
            for token in re.findall(r"[A-Za-z']+", line):
                base = token.strip("'")
                if not base:
                    continue
                lower = base.lower()
                has_mid_caps = any(ch.isupper() for ch in base[1:])
                emphasis = line_emphasis or has_mid_caps or lower in emphasis_tokens
                words.append({
                    "Word": base,
                    "LineIndex": line_index,
                    "Emphasis": emphasis,
                })
    return words

def align_words(words: list[dict], cues: list[dict]) -> list[dict]:
    """Naively time-align words across total speaking duration derived from cues.

    This does NOT perform phonetic alignment; it proportionally distributes time by word length.
    """
    if not words or not cues:
        return []
    # Speaking duration is sum of voiced cue spans
    speaking_duration = sum((c.get("end",0)-c.get("start",0)) for c in cues)
    if speaking_duration <= 0:
        return []
    total_weight = sum(len(w["Word"]) for w in words)
    if total_weight == 0:
        return []
    t = 0.0
    events: list[dict] = []
    for w in words:
        weight = len(w["Word"]) / total_weight
        dur = speaking_duration * weight
        events.append({
            "StartSeconds": round(t, 5),
            "EndSeconds": round(t + dur, 5),
            **w,
        })
        t += dur
    # Clamp final end to max cue end for consistency
    max_end = max(c.get("end",0) for c in cues)
    if events:
        events[-1]["EndSeconds"] = round(max_end, 5)
    return events

def apply_emphasis_to_frames(frames: list[dict], words: list[dict], emphasis_scale: float):
    if not frames or not words or emphasis_scale <= 1.0:
        return
    # Build interval list of emphasis spans
    emphasis_spans = [(w["StartSeconds"], w["EndSeconds"]) for w in words if w.get("Emphasis")]
    if not emphasis_spans:
        return
    for fr in frames:
        t = fr["TimeSeconds"]
        for s,e in emphasis_spans:
            if s <= t <= e:
                fr["MouthOpen01"] = round(min(1.0, fr["MouthOpen01"] * emphasis_scale), 3)
                break

def main():
    ap = argparse.ArgumentParser()
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--youtube")
    src.add_argument("--audio")
    ap.add_argument("--rhubarb", default="rhubarb")
    ap.add_argument("--ffmpeg", default="ffmpeg", help="Path or command name for ffmpeg")
    ap.add_argument("--fps", type=float, default=50.0)
    ap.add_argument("--out", required=True)
    ap.add_argument("--work", default="work")
    ap.add_argument("--download-only", action="store_true", help="Only download/convert audio -> WAV; skip rhubarb & frame generation.")
    ap.add_argument("--lyrics", help="Path to lyrics .txt to enrich output with word timing & emphasis.")
    ap.add_argument("--emphasis-scale", type=float, default=1.2, help="Multiplier applied to MouthOpen01 during emphasized words (>=1.0).")
    ap.add_argument("--min-open", type=float, default=0.0, help="Clamp all MouthOpen01 values to be at least this (servo slack).")
    ap.add_argument("--max-open", type=float, default=1.0, help="Clamp all MouthOpen01 values to be at most this.")
    ap.add_argument("--print-summary", action="store_true", help="Print a concise JSON summary to stdout (frames, duration).")
    ap.add_argument("--aligner", choices=["none","heuristic","vosk"], default="heuristic", help="Word alignment strategy when lyrics provided.")
    ap.add_argument("--vosk-model", help="Path to a Vosk model directory (if using --aligner vosk).")
    ap.add_argument("--bundle-root", help="If set, create a bundle folder under this root with output, lyrics copy, manifest.")
    ap.add_argument("--bundle-include-audio", action="store_true", help="Include converted 16k mono WAV inside bundle (analysis audio, gitignored).")
    ap.add_argument("--bundle-include-original", action="store_true", help="Include original source audio (e.g. .m4a/.mp3) inside bundle for high-quality playback.")
    args = ap.parse_args()

    # Resolve project root (parent of this script's directory). We intentionally
    # treat any relative --bundle-root as relative to the project root (one
    # level above the 'pipeline' folder) so bundles are stored outside the
    # pipeline working directory, keeping the pipeline folder clean.
    script_dir = Path(__file__).resolve().parent
    project_root = script_dir.parent

    work = Path(args.work)
    work.mkdir(parents=True, exist_ok=True)

    # Tool availability checks
    if shutil.which(args.ffmpeg) is None:
        print("ERROR: ffmpeg not found on PATH (or provided --ffmpeg path invalid).", file=sys.stderr)
        print("Install: winget install Gyan.FFmpeg  OR  choco install ffmpeg  OR  https://ffmpeg.org/download.html", file=sys.stderr)
        sys.exit(1)
    if not args.download_only and shutil.which(args.rhubarb) is None:
        print("ERROR: rhubarb not found on PATH (or provided --rhubarb path invalid).", file=sys.stderr)
        print("Download from: https://github.com/DanielSWolf/rhubarb-lip-sync/releases", file=sys.stderr)
        sys.exit(1)

    if args.youtube:
        downloaded = download_youtube(args.youtube, work)
        original_audio = downloaded
        wav = ensure_wav(downloaded, work, args.ffmpeg)
    else:
        original_audio = Path(args.audio)
        wav = ensure_wav(original_audio, work, args.ffmpeg)

    if args.download_only:
        # Write a tiny manifest pointing to WAV for traceability
        manifest = {"wav": str(wav.resolve())}
        Path(args.out).write_text(json.dumps(manifest, indent=2))
        print(f"Download-only complete. WAV: {wav} Manifest: {args.out}")
        return

    data = run_rhubarb(args.rhubarb, wav, work)
    frames = cues_to_frames(data, args.fps)

    # Clamp & sanity adjust
    mn = max(0.0, min(1.0, args.min_open))
    mx = max(mn, min(1.0, args.max_open))
    if mn > 0.0 or mx < 1.0:
        for fr in frames:
            fr["MouthOpen01"] = round(min(mx, max(mn, fr["MouthOpen01"])), 3)

    output_obj: dict | list = frames

    if args.lyrics:
        if not os.path.isfile(args.lyrics):
            print(f"ERROR: Lyrics file not found: {args.lyrics}", file=sys.stderr)
            sys.exit(2)
        try:
            words_raw = load_lyrics_words(args.lyrics)
            if args.aligner == "vosk":
                word_events = []
                try:
                    from vosk import Model, KaldiRecognizer
                    import wave, json as _json
                    # Load model once
                    model_path = args.vosk_model
                    if not model_path or not os.path.isdir(model_path):
                        raise RuntimeError("--vosk-model directory required for vosk aligner")
                    # We may have converted to 16k mono already (wav variable)
                    wf = wave.open(str(wav), 'rb')
                    if wf.getnchannels() != 1 or wf.getframerate() != 16000:
                        raise RuntimeError("Expected 16kHz mono WAV for Vosk alignment")
                    rec = KaldiRecognizer(Model(model_path), wf.getframerate())
                    rec.SetWords(True)
                    results = []
                    while True:
                        data_bytes = wf.readframes(4000)
                        if len(data_bytes) == 0:
                            break
                        if rec.AcceptWaveform(data_bytes):
                            results.append(_json.loads(rec.Result()))
                    results.append(_json.loads(rec.FinalResult()))
                    wf.close()
                    # Flatten words
                    asr_words = []
                    for r in results:
                        asr_words.extend(r.get('result', []))
                    # Normalize for matching
                    from rapidfuzz import process, fuzz
                    lyric_tokens = [w['Word'] for w in words_raw]
                    used = set()
                    aligned = []
                    for aw in asr_words:
                        spoken = aw.get('word','').strip("'\" ").lower()
                        if not spoken:
                            continue
                        match, score, idx = process.extractOne(spoken, lyric_tokens, scorer=fuzz.ratio)
                        if score >= 75 and idx not in used:
                            used.add(idx)
                            base = words_raw[idx]
                            aligned.append({
                                'StartSeconds': round(aw.get('start',0.0),5),
                                'EndSeconds': round(aw.get('end',aw.get('start',0.0)),5),
                                **base
                            })
                    # Fallback fill for any missing words (simple proportional placement appended after last aligned)
                    if aligned:
                        aligned.sort(key=lambda w: w['StartSeconds'])
                        last_end = aligned[-1]['EndSeconds']
                        remaining = [words_raw[i] for i in range(len(words_raw)) if i not in used]
                        if remaining:
                            # distribute remaining over gap till max cue end
                            max_end = max(c.get('end',0) for c in data.get('mouthCues',[]))
                            span = max(0.01, max_end - last_end)
                            seg = span / max(1,len(remaining))
                            t = last_end
                            for r in remaining:
                                aligned.append({
                                    'StartSeconds': round(t,5),
                                    'EndSeconds': round(t+seg*0.9,5),
                                    **r
                                })
                                t += seg
                        word_events = aligned
                        print(f"Vosk alignment produced {len(word_events)} words (matched {len(used)}/{len(words_raw)})")
                    else:
                        print("WARNING: Vosk produced no aligned words; falling back to heuristic.")
                        word_events = align_words(words_raw, data.get('mouthCues', []))
                except Exception as vex:
                    print(f"WARNING: Vosk alignment failed: {vex}; falling back to heuristic.")
                    word_events = align_words(words_raw, data.get('mouthCues', []))
            else:
                # heuristic / none
                word_events = align_words(words_raw, data.get("mouthCues", [])) if args.aligner != 'none' else []
            apply_emphasis_to_frames(frames, word_events, args.emphasis_scale)
            output_obj = {
                "frames": frames,
                "words": word_events,
                "metadata": {
                    "lyricsFile": os.path.abspath(args.lyrics),
                    "wordCount": len(word_events),
                    "emphasisScale": args.emphasis_scale,
                    "generator": "generate_lipsync.py",
                    "version": SCRIPT_VERSION,
                    "schema": 1,
                    "aligner": args.aligner,
                },
            }
            print(f"Enriched with {len(word_events)} word events (lyrics)")
        except Exception as ex:
            print(f"WARNING: Failed to process lyrics: {ex}")

    Path(args.out).write_text(json.dumps(output_obj, indent=2))
    print(f"Wrote {len(frames)} frames -> {args.out}")

    if args.print_summary:
        total_dur = frames[-1]["TimeSeconds"] if frames else 0.0
        summary = {
            "frames": len(frames),
            "durationSeconds": round(total_dur, 3),
            "fps": args.fps,
            "lyrics": bool(args.lyrics),
            "schema": 1 if isinstance(output_obj, dict) else 0,
        }
        print(json.dumps(summary))

    # Bundle packaging
    if args.bundle_root:
        try:
            root = Path(args.bundle_root)
            if not root.is_absolute():
                # Place relative bundle roots at the project root (outside pipeline)
                root = project_root / root
            root.mkdir(parents=True, exist_ok=True)
            # Slug
            if args.youtube:
                qs = urllib.parse.urlparse(args.youtube)
                vid = None
                if qs.query:
                    qd = urllib.parse.parse_qs(qs.query)
                    if 'v' in qd:
                        vid = qd['v'][0]
                if not vid:
                    # fallback last path segment
                    vid = qs.path.strip('/').split('/')[-1] or 'youtube'
                base_slug = vid
            else:
                base_slug = Path(args.audio).stem
            timestamp = datetime.datetime.utcnow().strftime('%Y%m%d-%H%M%S')
            bundle_dir = root / f"{base_slug}_{timestamp}"
            bundle_dir.mkdir(parents=True, exist_ok=False)
            # Copy output JSON
            out_name = Path(args.out).name
            bundle_out = bundle_dir / out_name
            if Path(args.out).resolve() != bundle_out.resolve():
                shutil.copy2(args.out, bundle_out)
            # Copy lyrics (preserve original name or normalized)
            lyrics_rel = None
            if args.lyrics:
                lyr_target = bundle_dir / (Path(args.lyrics).name)
                shutil.copy2(args.lyrics, lyr_target)
                lyrics_rel = lyr_target.name
            # Copy rhubarb raw json if exists
            rhubarb_raw_src = work / "rhubarb.json"
            rhubarb_raw_rel = None
            if rhubarb_raw_src.exists():
                rhubarb_raw_target = bundle_dir / "rhubarb.raw.json"
                shutil.copy2(rhubarb_raw_src, rhubarb_raw_target)
                rhubarb_raw_rel = rhubarb_raw_target.name
            wav_rel = None
            original_rel = None
            if args.bundle_include_audio:
                try:
                    wav_target = bundle_dir / Path(wav).name
                    shutil.copy2(wav, wav_target)
                    wav_rel = wav_target.name
                except Exception as ce:
                    print(f"WARNING: Failed to copy wav into bundle: {ce}")
            if args.bundle_include_original:
                try:
                    # Avoid duplicate copy if original == wav
                    if Path(original_audio).resolve() != Path(wav).resolve():
                        orig_target = bundle_dir / f"original{Path(original_audio).suffix.lower()}"
                        shutil.copy2(original_audio, orig_target)
                        original_rel = orig_target.name
                    else:
                        original_rel = Path(wav).name
                except Exception as oe:
                    print(f"WARNING: Failed to copy original audio into bundle: {oe}")
            manifest = {
                "generatedUtc": datetime.datetime.utcnow().isoformat() + 'Z',
                "scriptVersion": SCRIPT_VERSION,
                "source": {
                    "type": "youtube" if args.youtube else "file",
                    "youtubeUrl": args.youtube,
                    "audioInput": args.audio,
                    "originalIncluded": bool(original_rel),
                    "wavCopied": bool(wav_rel),
                },
                "parameters": {
                    "fps": args.fps,
                    "aligner": args.aligner,
                    "emphasisScale": args.emphasis_scale,
                    "minOpen": args.min_open,
                    "maxOpen": args.max_open,
                },
                "counts": {
                    "frames": len(frames),
                    "words": len(output_obj.get('words', [])) if isinstance(output_obj, dict) else 0,
                },
                "files": {
                    "output": out_name,
                    "lyrics": lyrics_rel,
                    "rhubarbRaw": rhubarb_raw_rel,
                    "wav": wav_rel,
                    "original": original_rel,
                }
            }
            (bundle_dir / "manifest.json").write_text(json.dumps(manifest, indent=2))
            print(f"Bundle created: {bundle_dir}")
        except Exception as b_ex:
            print(f"WARNING: Failed to create bundle: {b_ex}")

if __name__ == "__main__":
    main()
