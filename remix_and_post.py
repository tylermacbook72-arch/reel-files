#!/usr/bin/env python3
"""Make a fresh variation of the base reel and post it as an Instagram trial reel.

Each run, without cutting or adding anything to the video:
  * speed: 1-2 random spoken parts play at 0.9x or 1.1x (voice pitch kept)
  * color: one random filter look + a tiny random tweak
  * on-screen captions: the spoken words, synced, in a random caption style
  * audio: your voice + a random background track from the audio folder at ~25%
Then it uploads the result to Instagram as a trial reel (unless --dry-run).

Posting: the reel is pushed to the public `staging` branch of the reel-files repo,
then Instagram downloads it from that link as a trial reel (trial mode only works
this way). The Meta access token is injected by the environment's network proxy
for graph.facebook.com, so no token is stored here.

Usage:
  python3 remix_and_post.py --video media/video.mp4 --words media/words.json \
      --audio-dir media/audio --caption "Follow @futurescorey for free trading info" [--dry-run]
"""
import argparse
import json
import os
import random
import re
import subprocess
import sys
import tempfile
import time
import urllib.parse
import urllib.request

GRAPH = "https://graph.facebook.com/v27.0"
IG_USER_ID = os.environ.get("IG_USER_ID", "17841480164538536")  # @futurescorey
CAPTION = "Follow @futurescorey for free trading info 📚"  # every trial reel uses exactly this
AUTH = {"Authorization": "Bearer proxy-injected"}  # the proxy replaces this
AUDIO_EXT = (".mp3", ".m4a", ".wav", ".aac", ".ogg", ".mp4", ".mov")

# ---------------------------------------------------------------- filters
FILTERS = {
    "Warm":    "colorbalance=rs=.05:rm=.06:rh=.03:bs=-.05:bm=-.06:bh=-.03,eq=saturation=1.08",
    "Toasty":  "colorbalance=rs=.1:rm=.1:gm=.03:bs=-.1:bm=-.1,eq=contrast=1.05:saturation=1.12:gamma=0.97",
    "Autumn":  "colorbalance=rm=.08:gm=.02:bm=-.1,hue=h=-6,eq=saturation=0.95:contrast=1.05",
    "Lounge":  "colorbalance=rs=.06:bm=-.04,curves=all='0/0.06 1/0.94',eq=saturation=0.9",
    "Spring":  "colorbalance=gm=.04:rh=.03:bs=.02,eq=brightness=0.03:saturation=1.1",
    "Cool":    "colorbalance=rm=-.05:bm=.07:bs=.05",
    "Oslo":    "colorbalance=bs=.08:bm=.04:rh=.02,eq=saturation=0.85:contrast=1.08",
    "Fresh":   "colorbalance=gm=.02:bm=.04,eq=brightness=0.04:saturation=1.15:contrast=1.04",
    "Shade":   "eq=brightness=-0.05:contrast=1.12:saturation=0.9,colorbalance=bs=.04",
    "Vintage": "curves=preset=vintage,eq=saturation=0.85",
    "Fade":    "curves=all='0/0.12 1/0.92',eq=saturation=0.8",
    "Wash":    "curves=all='0/0.08 1/1',eq=brightness=0.04:saturation=0.75:contrast=0.92",
    "Simple":  "eq=contrast=1.04:saturation=1.04",
    "Crisp":   "eq=contrast=1.15:saturation=1.1,unsharp=5:5:0.6",
    "Lively":  "vibrance=intensity=0.35,eq=contrast=1.06",
    "Paris":   "colorbalance=rh=.05:bh=.04:gm=-.03,eq=brightness=0.03:saturation=0.95",
    "Jakarta": "colorbalance=rs=-.03:gs=.04:rh=.06,eq=contrast=1.1:saturation=1.15",
}


def color_chain(name, rng):
    tweak = (f"eq=brightness={rng.uniform(-0.02, 0.02):.3f}"
             f":saturation={rng.uniform(0.95, 1.05):.3f},hue=h={rng.uniform(-4, 4):.1f}")
    return FILTERS[name] + "," + tweak


# ---------------------------------------------------------------- captions
# colors are ASS &HBBGGRR
WHITE, YELLOW, GREEN, RED = "&HFFFFFF", "&H00D7FF", "&H5AF23C", "&H3B3BFF"
COLORS = {"White": WHITE, "Yellow": YELLOW, "Green": GREEN, "Red": RED}
BLACK = "&H000000"
SEAM = 0.365  # line between face cam and chart
FACE_CAM_HEIGHT = 0.3625  # face cam is the top 36% of the base video

CAPTION_STYLES = {
    "Bold White": dict(font="Montserrat Black", size=78, color=WHITE, outline=BLACK, bord=5, shadow=0, pos=SEAM, upper=True, words=3, hl=None),
}
for cname, col in COLORS.items():   # colored text, 2 words at a time
    CAPTION_STYLES[f"{cname} Pop"] = dict(font="Montserrat Black", size=84, color=col, outline=BLACK, bord=5, shadow=0, pos=SEAM, upper=True, words=2, hl=None)
for cname, col in COLORS.items():   # white text, current word lit up
    if cname != "White":
        CAPTION_STYLES[f"{cname} Highlight"] = dict(font="Montserrat ExtraBold", size=76, color=WHITE, outline=BLACK, bord=5, shadow=0, pos=SEAM, upper=True, words=3, hl=col)
for cname, col in COLORS.items():   # one big word at a time
    CAPTION_STYLES[f"One Word {cname}"] = dict(font="Montserrat Black", size=110, color=col, outline=BLACK, bord=6, shadow=0, pos=SEAM - 0.005, upper=True, words=1, hl=None)
for cname, col in COLORS.items():   # Roboto, 2 words, current word lit up
    if cname != "White":
        CAPTION_STYLES[f"{cname} Accent"] = dict(font="Roboto Black", size=80, color=WHITE, outline=BLACK, bord=5, shadow=0, pos=SEAM, upper=True, words=2, hl=col)
CAPTION_STYLES.update({
    "Clean Lower": dict(font="Inter Bold", size=64, color=WHITE, outline=BLACK, bord=4, shadow=4, pos=0.31, upper=False, words=4, hl=None),
    "Boxed":       dict(font="Inter Black", size=66, color=WHITE, outline=BLACK, bord=0, shadow=0, pos=SEAM, upper=False, words=3, hl=None, box=True),
    "Center Big":  dict(font="Montserrat ExtraBold", size=92, color=WHITE, outline=BLACK, bord=5, shadow=2, pos=SEAM - 0.005, upper=True, words=2, hl=None),
    "Soft Shadow": dict(font="Roboto Medium", size=68, color=WHITE, outline=BLACK, bord=4, shadow=5, pos=0.31, upper=False, words=4, hl=None),
})


def ass_time(t):
    t = max(t, 0)
    h, r = divmod(t, 3600)
    m, s = divmod(r, 60)
    return f"{int(h)}:{int(m):02d}:{s:05.2f}"


def build_ass(words, st, W, H):
    box = st.get("box")
    style = (f"Style: Cap,{st['font']},{st['size']},&H00{st['color'][2:]},&H00FFFFFF,"
             f"&H{'80' if box else '00'}{st['outline'][2:]},&H80000000,0,0,0,0,100,100,0,0,"
             f"{3 if box else 1},{st['bord'] if not box else 14},{st['shadow']},5,60,60,0,1")
    out = ["[Script Info]", "ScriptType: v4.00+", f"PlayResX: {W}", f"PlayResY: {H}", "WrapStyle: 0", "",
           "[V4+ Styles]",
           "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, "
           "Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, "
           "Alignment, MarginL, MarginR, MarginV, Encoding", style, "",
           "[Events]", "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text"]
    pos = f"{{\\pos({W // 2},{int(H * st['pos'])})}}"
    n = st["words"]
    chunks = [words[i:i + n] for i in range(0, len(words), n)]
    for ci, ch in enumerate(chunks):
        end_of_chunk = chunks[ci + 1][0]["s"] if ci + 1 < len(chunks) else ch[-1]["e"] + 0.3
        texts = [w["w"].upper() if st["upper"] else w["w"] for w in ch]
        if st["hl"]:
            for wi, w in enumerate(ch):
                end = ch[wi + 1]["s"] if wi + 1 < len(ch) else end_of_chunk
                parts = [(f"{{\\c{st['hl']}&}}{t}{{\\c{st['color']}&}}" if k == wi else t) for k, t in enumerate(texts)]
                out.append(f"Dialogue: 0,{ass_time(w['s'])},{ass_time(end)},Cap,,0,0,0,,{pos}{' '.join(parts)}")
        else:
            out.append(f"Dialogue: 0,{ass_time(ch[0]['s'])},{ass_time(end_of_chunk)},Cap,,0,0,0,,{pos}{' '.join(texts)}")
    return "\n".join(out) + "\n"


# ---------------------------------------------------------------- words / parts
def load_words(path):
    raw = json.load(open(path, encoding="utf-8"))
    words = []
    for w in raw:  # glue tokens like ",000" or "%" onto the previous word
        if words and re.match(r"^[,%.]", w["w"]):
            words[-1]["w"] += w["w"]
            words[-1]["e"] = w["e"]
        else:
            words.append(dict(w))
    return words


def split_parts(words, total):
    """Split into spoken parts at sentence ends. Returns [(start, end)]."""
    starts = [0.0]
    for i, w in enumerate(words[:-1]):
        if re.search(r"[.?!]$", w["w"]):
            starts.append(words[i + 1]["s"])
    ends = starts[1:] + [total]
    return list(zip(starts, ends))


def remap(t, parts, speeds):
    """Where time t of the original lands in the sped-up video."""
    out = 0.0
    for (s, e), sp in zip(parts, speeds):
        if t < e or (s, e) == parts[-1]:
            return out + (max(t, s) - s) / sp
        out += (e - s) / sp
    return out


# ---------------------------------------------------------------- render
def probe(path, entry):
    return subprocess.check_output(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", entry,
                                    "-of", "default=nw=1:nk=1", path]).decode().split()


def duration(path):
    return float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                                          "-of", "default=nw=1:nk=1", path]))


USES_PER_SECTION = 3  # use an audio's best section 3 times, then move to its next-best section


def pick_variation(rng, parts, audio_dir, state=None, windows=None):
    state = state if state is not None else {}
    windows = windows or {}
    speeds = [1.0] * len(parts)
    changed = rng.sample(range(len(parts)), k=rng.choice([1, 2]))
    for i in changed:
        speeds[i] = rng.choice([0.9, 1.1])
    tracks = []
    if audio_dir and os.path.isdir(audio_dir):
        skip_file = os.path.join(audio_dir, "..", "audio_skip.txt")
        skip = set()
        if os.path.exists(skip_file):
            skip = {l.strip() for l in open(skip_file) if l.strip() and not l.startswith("#")}
        tracks = sorted(f for f in os.listdir(audio_dir) if f.lower().endswith(AUDIO_EXT) and f not in skip)
    music, music_start, section = None, 0.0, None
    if tracks:
        uses = state.setdefault("audio_uses", {})
        least = min(uses.get(t, 0) for t in tracks)          # spread posts evenly over all audios
        track = rng.choice([t for t in tracks if uses.get(t, 0) == least])
        starts = windows.get(track) or [0.0]
        section = (uses.get(track, 0) // USES_PER_SECTION) % len(starts)
        music, music_start = os.path.join(audio_dir, track), starts[section]
    return {
        "speeds": speeds,
        "changed_parts": sorted(i + 1 for i in changed),
        "filter": rng.choice(list(FILTERS)),
        "caption_style": rng.choice(list(CAPTION_STYLES)),
        "mirror": rng.random() < 0.5,
        "music": music,
        "music_start": music_start,
        "music_section": section,
    }


def render(video, words, v, out, rng, music_level_lufs=-30):
    W, H = map(int, probe(video, "stream=width,height"))
    total = duration(video)
    parts = split_parts(words, total)
    speeds = v["speeds"]

    # captions with timings moved to match the speed changes
    moved = [dict(w, s=remap(w["s"], parts, speeds), e=remap(w["e"], parts, speeds)) for w in words]
    tmp = tempfile.mkdtemp()
    ass = os.path.join(tmp, "caps.ass")
    open(ass, "w", encoding="utf-8").write(build_ass(moved, CAPTION_STYLES[v["caption_style"]], W, H))

    fc = []
    for i, ((s, e), sp) in enumerate(zip(parts, speeds)):
        fc.append(f"[0:v]trim={s:.3f}:{e:.3f},setpts=(PTS-STARTPTS)/{sp}[v{i}]")
        fc.append(f"[0:a]atrim={s:.3f}:{e:.3f},asetpts=PTS-STARTPTS" + (f",atempo={sp}" if sp != 1 else "") + f"[a{i}]")
    n = len(parts)
    fc.append("".join(f"[v{i}][a{i}]" for i in range(n)) + f"concat=n={n}:v=1:a=1[vc][voice]")
    fonts = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fonts")
    if v.get("mirror"):  # mirror only the face cam; flipping the chart would put its text and candles backwards
        top = int(H * FACE_CAM_HEIGHT) // 2 * 2
        fc.append(f"[vc]split[vfull][vtop];[vtop]crop=iw:{top}:0:0,hflip[vflip];[vfull][vflip]overlay=0:0[vm]")
        src = "[vm]"
    else:
        src = "[vc]"
    fc.append(f"{src}{color_chain(v['filter'], rng)},ass='{ass}':fontsdir='{fonts}',format=yuv420p[vout]")

    cmd = ["ffmpeg", "-y", "-v", "error", "-i", video]
    if v["music"]:
        cmd += ["-stream_loop", "-1", "-ss", f"{v.get('music_start', 0):.2f}", "-i", v["music"]]
        fc.append(f"[1:a]aformat=sample_rates=44100:channel_layouts=stereo,loudnorm=I={music_level_lufs}:TP=-6[bg]")
        fc.append("[voice]aformat=sample_rates=44100:channel_layouts=stereo[vo]")
        fc.append("[vo][bg]amix=inputs=2:duration=first:normalize=0,alimiter=limit=0.95[aout]")
    else:
        fc.append("[voice]anull[aout]")

    cmd += ["-filter_complex", ";".join(fc), "-map", "[vout]", "-map", "[aout]",
            "-c:v", "libx264", "-preset", "medium", "-crf", "21", "-profile:v", "high", "-r", "30",
            "-c:a", "aac", "-b:a", "160k", "-ar", "44100", "-movflags", "+faststart", out]
    subprocess.run(cmd, check=True)


# ---------------------------------------------------------------- instagram
def api(method, url, data=None, headers=None, body=None, json_body=None):
    if data is not None:
        body = urllib.parse.urlencode(data).encode()
    if json_body is not None:  # trial_params must be sent as a nested JSON object
        body = json.dumps(json_body).encode()
        headers = {**(headers or {}), "Content-Type": "application/json"}
    req = urllib.request.Request(url, data=body, method=method, headers={**AUTH, **(headers or {})})
    try:
        with urllib.request.urlopen(req, timeout=300) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        sys.exit(f"Instagram API error {e.code}: {e.read().decode()}")


REPO_URL = os.environ.get("REEL_REPO_URL", "https://github.com/tylermacbook72-arch/reel-files")
RAW_BASE = "https://raw.githubusercontent.com/tylermacbook72-arch/reel-files"
STAGING = "staging"


def open_staging():
    """Clone the staging branch (creating it on first run). Returns (dir, state)."""
    d = tempfile.mkdtemp()
    try:
        subprocess.run(["git", "clone", "-q", "--depth", "1", "--branch", STAGING, REPO_URL, d], check=True, capture_output=True)
    except subprocess.CalledProcessError:  # first run: start the branch from main
        subprocess.run(["git", "clone", "-q", "--depth", "1", REPO_URL, d], check=True, capture_output=True)
        subprocess.run(["git", "checkout", "-q", "-b", STAGING], cwd=d, check=True)
    sp = os.path.join(d, "state.json")
    state = json.load(open(sp)) if os.path.exists(sp) else {}
    return d, state


def stage_on_github(d, path, state):
    """Put the finished reel (and the updated usage memory) on the public staging branch.

    Instagram only applies trial mode when it downloads the video from a public URL
    (the direct-upload method silently ignores trial_params). The previous reel file
    is removed in the same commit. Returns the raw link to the new reel.
    """
    run = lambda *a: subprocess.run(a, cwd=d, check=True, capture_output=True, text=True).stdout.strip()
    for f in os.listdir(d):
        if f.endswith(".mp4"):
            run("git", "rm", "-q", f)
    name = f"reel-{time.strftime('%Y%m%d-%H%M%S')}.mp4"
    subprocess.run(["cp", path, os.path.join(d, name)], check=True)
    json.dump(state, open(os.path.join(d, "state.json"), "w"), indent=1)
    run("git", "add", name, "state.json")
    run("git", "-c", "user.name=Reel Poster", "-c", "user.email=tylermacbook72@gmail.com", "commit", "-q", "-m",
        "Stage reel for Instagram upload\n\nCo-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>\n"
        "Claude-Session: https://claude.ai/code/session_01DmfryRezHpK1ci6Zyf546s")
    run("git", "push", "-q", "origin", f"HEAD:{STAGING}")
    return f"{RAW_BASE}/{run('git', 'rev-parse', 'HEAD')}/{name}"


def save_state(d, state, message):
    """Commit just the memory file (used after a successful post to record the media id)."""
    run = lambda *a: subprocess.run(a, cwd=d, check=True, capture_output=True, text=True).stdout.strip()
    json.dump(state, open(os.path.join(d, "state.json"), "w"), indent=1)
    run("git", "add", "state.json")
    run("git", "-c", "user.name=Reel Poster", "-c", "user.email=tylermacbook72@gmail.com", "commit", "-q", "-m",
        message + "\n\nCo-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>\n"
        "Claude-Session: https://claude.ai/code/session_01DmfryRezHpK1ci6Zyf546s")
    run("git", "push", "-q", "origin", f"HEAD:{STAGING}")


def post_trial_reel(video_url, caption=CAPTION):
    if caption != CAPTION:
        sys.exit(f"Refusing to post: caption must be exactly {CAPTION!r}")
    c = api("POST", f"{GRAPH}/{IG_USER_ID}/media", json_body={
        "media_type": "REELS",
        "video_url": video_url,
        "caption": caption,
        "share_to_feed": False,
        "trial_params": {"graduation_strategy": "MANUAL"},
    })
    cid = c["id"]
    for _ in range(60):
        s = api("GET", f"{GRAPH}/{cid}?fields=status_code,status")
        if s.get("status_code") == "FINISHED":
            break
        if s.get("status_code") == "ERROR":
            sys.exit(f"Instagram processing failed: {s}")
        time.sleep(10)
    else:
        sys.exit("Timed out waiting for Instagram to process the video")
    return api("POST", f"{GRAPH}/{IG_USER_ID}/media_publish", data={"creation_id": cid})["id"]


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    ap = argparse.ArgumentParser()
    ap.add_argument("--video", default=os.path.join(here, "media", "video.mp4"))
    ap.add_argument("--words", default=os.path.join(here, "media", "words.json"))
    ap.add_argument("--audio-dir", default=os.path.join(here, "media", "audio"))
    ap.add_argument("--windows", default=os.path.join(here, "media", "audio_windows.json"))
    ap.add_argument("--caption", default=CAPTION)
    ap.add_argument("--out", default=os.path.join(tempfile.gettempdir(), "reel.mp4"))
    ap.add_argument("--seed", type=int)
    ap.add_argument("--filter", choices=list(FILTERS))
    ap.add_argument("--caption-style", choices=list(CAPTION_STYLES))
    ap.add_argument("--dry-run", action="store_true", help="render only: no GitHub, no Instagram")
    a = ap.parse_args()

    rng = random.Random(a.seed)
    words = load_words(a.words)
    parts = split_parts(words, duration(a.video))
    windows = json.load(open(a.windows)) if os.path.exists(a.windows) else {}
    d, state = (None, {}) if a.dry_run else open_staging()
    v = pick_variation(rng, parts, a.audio_dir, state, windows)
    if a.filter:
        v["filter"] = a.filter
    if a.caption_style:
        v["caption_style"] = a.caption_style
    track = os.path.basename(v["music"] or "none")
    summary = (f"{len(parts)} parts | sped-up: " + ", ".join(f"#{i} at {v['speeds'][i - 1]}x" for i in v["changed_parts"]) +
               f" | filter: {v['filter']} | captions: {v['caption_style']} | mirrored: {'yes' if v['mirror'] else 'no'}"
               f" | music: {track} from {int(v['music_start'] // 60)}:{int(v['music_start'] % 60):02d}"
               f" (section {(v['music_section'] or 0) + 1})")
    print(summary)
    render(a.video, words, v, a.out, rng)
    print(f"Rendered {a.out} ({duration(a.out):.1f}s, {os.path.getsize(a.out) / 1e6:.1f} MB)")
    if a.dry_run:
        return
    if v["music"]:
        state.setdefault("audio_uses", {})[track] = state["audio_uses"].get(track, 0) + 1
    url = stage_on_github(d, a.out, state)
    print("Staged at", url)
    media_id = post_trial_reel(url, a.caption)
    state.setdefault("history", []).append({"time": time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime()), "media_id": media_id,
                                             "summary": summary})
    save_state(d, state, "Record posted reel")
    print("Posted trial reel, media id:", media_id)


if __name__ == "__main__":
    main()
