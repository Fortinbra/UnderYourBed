#!/usr/bin/env python3
"""Utility to download speech/alignment models (currently Vosk) for the pipeline.

Usage:
  python download_models.py --vosk-small
  python download_models.py --vosk MODEL_URL

Defaults download into: models/vosk/<model_folder>
Skips download if existing folder contains expected files.
"""
from __future__ import annotations
import argparse, tarfile, zipfile, sys, os, shutil, tempfile, hashlib, urllib.request, json
from pathlib import Path

VOSK_SMALL_EN = "https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip"

def sha256_file(path: Path) -> str:
    h=hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1<<20), b''):
            h.update(chunk)
    return h.hexdigest()

def download(url: str, dest: Path):
    dest.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(url) as r, open(dest, 'wb') as f:
        shutil.copyfileobj(r, f)

def extract(archive: Path, out_dir: Path) -> Path:
    if archive.suffix == '.zip':
        with zipfile.ZipFile(archive,'r') as z:
            z.extractall(out_dir)
            # Return first top-level directory
            top = sorted({p.split('/')[0] for p in z.namelist() if '/' in p})
            return out_dir / (top[0] if top else '')
    else:
        with tarfile.open(archive,'r:*') as t:
            t.extractall(out_dir)
            members = [m.name for m in t.getmembers() if '/' in m.name]
            top = sorted({m.split('/')[0] for m in members})
            return out_dir / (top[0] if top else '')

def main():
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument('--vosk-small', action='store_true', help='Download small English Vosk model.')
    g.add_argument('--vosk', help='Download Vosk model from custom URL.')
    ap.add_argument('--force', action='store_true', help='Force re-download even if present.')
    ap.add_argument('--dest', default='models/vosk', help='Destination base directory.')
    args = ap.parse_args()

    url = args.vosk if args.vosk else VOSK_SMALL_EN
    base = Path(args.dest)
    base.mkdir(parents=True, exist_ok=True)
    tmp = Path(tempfile.mkdtemp(prefix='mdl_dl_'))
    try:
        archive = tmp / 'model_download'
        model_name = url.rsplit('/',1)[-1].replace('.zip','').replace('.tar.gz','')
        target_dir = base / model_name
        if target_dir.exists() and not args.force:
            # crude validity check
            if any((target_dir / f).exists() for f in ('vosk-model-small-en-us-0.15','am','conf')):
                print(f"Model already present: {target_dir}")
                return
        print(f"Downloading: {url}")
        download(url, archive)
        print("Extracting...")
        extracted_root = extract(archive, base)
        # If extracted root name differs from desired, leave as is; symlink/copy optional
        print(f"Model ready at: {extracted_root}")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

if __name__ == '__main__':
    main()
