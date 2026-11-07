"""Rank the strongest ~37s sections of every audio (loud, full parts like drops/hooks first).

Writes media/audio_windows.json: {file: [start_seconds, ...]} best first, non-overlapping.
Re-run after adding new audios.
"""
import json, os, subprocess, sys
import numpy as np
here = os.path.dirname(os.path.abspath(__file__))
WIN, STEP, SR = 37.0, 1.0, 8000
out = {}
adir = os.path.join(here, "media", "audio")
for f in sorted(os.listdir(adir)):
    if not f.endswith(".m4a"):
        continue
    pcm = subprocess.run(["ffmpeg", "-v", "error", "-i", os.path.join(adir, f), "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"],
                         capture_output=True, check=True).stdout
    x = np.frombuffer(pcm, np.float32)
    dur = len(x) / SR
    if dur <= WIN + 2:
        out[f] = [0.0]
        continue
    hop = SR // 2
    rms = np.sqrt(np.convolve(x ** 2, np.ones(hop) / hop, mode="valid")[::hop] + 1e-12)
    db = 20 * np.log10(rms)
    per = int(WIN * 2)
    starts = np.arange(0, len(db) - per, int(STEP * 2))
    # loud on average AND consistently full (penalise quiet gaps); skip first/last 3s fades
    score = np.array([db[s:s + per].mean() - 0.5 * db[s:s + per].std() for s in starts])
    order = np.argsort(-score)
    picks = []
    for i in order:
        t = starts[i] / 2
        if t < 3 or t + WIN > dur - 3:
            continue
        if all(abs(t - p) >= WIN for p in picks):
            picks.append(float(t))
    out[f] = picks or [0.0]
json.dump(out, open(os.path.join(here, "media", "audio_windows.json"), "w"), indent=1)
for f, p in out.items():
    print(f"{f:45s} " + ", ".join(f"{int(t//60)}:{int(t%60):02d}" for t in p))
