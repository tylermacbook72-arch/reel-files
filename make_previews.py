"""Build preview sheets of all caption styles (and filters) on the base video."""
import subprocess, sys, tempfile, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from remix_and_post import CAPTION_STYLES, build_ass, load_words

V, WORDS, OUT = sys.argv[1], sys.argv[2], sys.argv[3]
T = tempfile.mkdtemp(); words = load_words(WORDS); tiles = []
for i, (n, st) in enumerate(CAPTION_STYLES.items()):
    ass = f"{T}/c{i}.ass"; open(ass, "w").write(build_ass(words, st, 1080, 1920)); o = f"{T}/c{i:02d}.png"
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-ss", "0.9", "-i", V, "-frames:v", "1", "-vf",
                    f"ass='{ass}',crop=1080:1100:0:0,scale=432:440,drawbox=y=0:w=iw:h=56:color=black@0.75:t=fill,"
                    f"drawtext=font=Inter Bold:text='{i+1}. {n}':fontcolor=white:fontsize=30:x=(w-tw)/2:y=13", o], check=True)
    tiles.append(o)
cols = 5; rows = -(-len(tiles) // cols)
while len(tiles) < cols * rows:
    o = f"{T}/blank{len(tiles)}.png"
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", "color=black:s=432x440", "-frames:v", "1", o], check=True)
    tiles.append(o)
args = sum((["-i", t] for t in tiles), [])
subprocess.run(["ffmpeg", "-y", "-v", "error", *args, "-filter_complex",
                "".join(f"[{i}]" for i in range(len(tiles))) + f"xstack=inputs={len(tiles)}:grid={cols}x{rows}", OUT], check=True)
