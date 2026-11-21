#!/usr/bin/env python3
"""Build the "tap to follow" motion graphic used at the end of each reel.

A profile card (avatar from the base video, @futurescorey) pops in, a finger
taps the blue Follow button, and it flips to Following. Output is a short
transparent .mov (qtrle/argb) that remix_and_post.py overlays on the chart.

Run once per base video:  python3 make_follow_overlay.py media/video2.mp4 media/follow_overlay.mov
"""
import math
import os
import subprocess
import sys
import tempfile

from PIL import Image, ImageDraw, ImageFilter, ImageFont

VIDEO, OUT = sys.argv[1], sys.argv[2]
FACE_T = float(sys.argv[3]) if len(sys.argv) > 3 else 2.0  # frame to take the avatar from

FPS, DUR = 30, 2.4
W, H = 1000, 470                     # canvas (card + room for shadow and finger)
CX, CY, CW, CH = 60, 70, 880, 270    # card box
BTN = (CX + CW - 266, CY + 90, CX + CW - 30, CY + 180)
USER = "futurescorey"
SUB = "Trading tips daily"
BLUE, GREY = (0, 149, 246, 255), (239, 239, 239, 255)

def font(path, size):
    for p in (path, "/usr/share/fonts/opentype/inter/Inter-Regular.otf", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"):
        if os.path.exists(p):
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()

here = os.path.dirname(os.path.abspath(__file__))
F_BOLD = font(os.path.join(here, "fonts", "Inter-Bold.otf"), 46)
F_SUB = font("/usr/share/fonts/opentype/inter/Inter-Medium.otf", 32)
F_BTN = font(os.path.join(here, "fonts", "Inter-Bold.otf"), 36)

# avatar: the Instagram profile picture (media/pfp.jpg) if present, else a face crop from the video
tmp = tempfile.mkdtemp()
PFP = os.path.join(here, "media", "pfp.jpg")
if os.path.exists(PFP):
    avatar = Image.open(PFP).convert("RGBA").resize((180, 180), Image.LANCZOS)
else:
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", str(FACE_T), "-i", VIDEO, "-frames:v", "1",
                    "-vf", "crop=520:520:280:110,scale=180:180", os.path.join(tmp, "a.png")], check=True)
    avatar = Image.open(os.path.join(tmp, "a.png")).convert("RGBA")
mask = Image.new("L", avatar.size, 0)
ImageDraw.Draw(mask).ellipse((0, 0, 179, 179), fill=255)
avatar.putalpha(mask)
ring = Image.new("RGBA", (196, 196), (0, 0, 0, 0))
ImageDraw.Draw(ring).ellipse((0, 0, 195, 195), fill=(225, 48, 108, 255))  # story-style ring
ImageDraw.Draw(ring).ellipse((5, 5, 190, 190), fill=(255, 255, 255, 255))
ring.alpha_composite(avatar, (8, 8))

def ease_out(x):
    x = max(0.0, min(1.0, x))
    return 1 - (1 - x) ** 3

def ease_in_out(x):
    x = max(0.0, min(1.0, x))
    return 3 * x * x - 2 * x * x * x

def card(following, press):
    c = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    sh = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(sh).rounded_rectangle((CX + 4, CY + 14, CX + CW + 4, CY + CH + 14), 44, fill=(0, 0, 0, 90))
    c.alpha_composite(sh.filter(ImageFilter.GaussianBlur(18)))
    d = ImageDraw.Draw(c)
    d.rounded_rectangle((CX, CY, CX + CW, CY + CH), 44, fill=(255, 255, 255, 255))
    c.alpha_composite(ring, (CX + 36, CY + (CH - 196) // 2))
    d.text((CX + 256, CY + 70), USER, font=F_BOLD, fill=(20, 20, 20, 255))
    d.text((CX + 256, CY + 140), SUB, font=F_SUB, fill=(115, 115, 115, 255))
    # the button area is drawn over the subtitle's right edge region, so keep text short
    x0, y0, x1, y1 = BTN
    s = 1 - 0.07 * press
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    bw, bh = (x1 - x0) * s, (y1 - y0) * s
    box = (cx - bw / 2, cy - bh / 2, cx + bw / 2, cy + bh / 2)
    d.rounded_rectangle(box, 22, fill=GREY if following else BLUE)
    label = "Following" if following else "Follow"
    tw = d.textlength(label, font=F_BTN)
    d.text((cx - tw / 2, cy - 23), label, font=F_BTN, fill=(20, 20, 20, 255) if following else (255, 255, 255, 255))
    return c

frames = os.path.join(tmp, "f")
os.makedirs(frames)
bx, by = (BTN[0] + BTN[2]) / 2, (BTN[1] + BTN[3]) / 2
start = (W - 40, H - 10)
T_POP, T_MOVE0, T_TAP, T_FLIP = 0.22, 0.25, 0.85, 0.95
for i in range(int(FPS * DUR)):
    t = i / FPS
    press = max(0.0, 1 - abs(t - T_TAP) / 0.1) if T_TAP - 0.1 <= t <= T_TAP + 0.1 else 0.0
    base = card(t >= T_FLIP, press)
    # pop-in: scale + fade
    k = ease_out(t / T_POP)
    scale = 0.85 + 0.15 * k
    layer = base.resize((int(W * scale), int(H * scale)), Image.LANCZOS)
    frame = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    frame.alpha_composite(layer, ((W - layer.width) // 2, (H - layer.height) // 2))
    if k < 1:
        a = frame.getchannel("A").point(lambda v: int(v * k))
        frame.putalpha(a)
    d = ImageDraw.Draw(frame)
    # finger: glides to the button, taps, then fades away
    if t >= T_MOVE0:
        m = ease_in_out((t - T_MOVE0) / (T_TAP - T_MOVE0))
        fx = start[0] + (bx + 70 - start[0]) * m
        fy = start[1] + (by + 40 - start[1]) * m
        fade = 1.0 if t < T_FLIP + 0.1 else max(0.0, 1 - (t - T_FLIP - 0.1) / 0.25)
        r = 36 - 8 * press
        if fade > 0:
            d.ellipse((fx - r - 3, fy - r + 5, fx + r + 3, fy + r + 11), fill=(0, 0, 0, int(70 * fade)))
            d.ellipse((fx - r, fy - r, fx + r, fy + r), fill=(255, 255, 255, int(235 * fade)),
                      outline=(60, 60, 60, int(200 * fade)), width=4)
        if T_TAP <= t <= T_TAP + 0.35:  # ripple
            p = (t - T_TAP) / 0.35
            rr = 40 + 70 * p
            d.ellipse((fx - rr, fy - rr, fx + rr, fy + rr), outline=(255, 255, 255, int(220 * (1 - p))), width=6)
    frame.save(os.path.join(frames, f"{i:04d}.png"))

subprocess.run(["ffmpeg", "-v", "error", "-y", "-framerate", str(FPS), "-i", os.path.join(frames, "%04d.png"),
                "-c:v", "qtrle", "-pix_fmt", "argb", OUT], check=True)
print("wrote", OUT, f"{os.path.getsize(OUT) / 1e6:.1f} MB")
