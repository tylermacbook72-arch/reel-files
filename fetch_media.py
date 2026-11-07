"""Download the base video and every audio from the public Google Drive folder (skips files already here)."""
import json, os, re, subprocess, sys
here = os.path.dirname(os.path.abspath(__file__))
m = json.load(open(os.path.join(here, "media", "drive_files.json")))
URL = "https://drive.usercontent.google.com/download?id={}&export=download&confirm=t"
def get(fid, out):
    if os.path.exists(out) and os.path.getsize(out) > 0:
        return
    tmp = out + ".part"
    subprocess.run(["curl", "-sSL", "--retry", "3", "-o", tmp, URL.format(fid)], check=True)
    os.replace(tmp, out)
os.makedirs(os.path.join(here, "media", "audio"), exist_ok=True)
get(m["video"]["id"], os.path.join(here, "media", "video.mp4"))
for a in m["audio"]:
    slug = re.sub(r"[^a-z0-9]+", "_", a["name"].lower()).strip("_")
    out = os.path.join(here, "media", "audio", slug + ".m4a")
    if os.path.exists(out):
        continue
    raw = os.path.join(here, "media", "audio", slug + ".src")
    get(a["id"], raw)
    r = subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", raw, "-vn", "-ac", "2", "-ar", "44100", "-c:a", "aac", "-b:a", "192k", out])
    if r.returncode != 0:
        print("could not read audio from", a["name"], file=sys.stderr)
    os.remove(raw)
print("media ready")
