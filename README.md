# reel-files

Auto-poster for @futurescorey Instagram **trial reels**.

Each run takes the base video and makes a fresh variation, then posts it as a trial reel:

- **Speed**: 1-2 random spoken parts (of 12) play at 0.9x or 1.1x, voice pitch kept
- **Color**: one of 17 filter looks (Warm, Toasty, Oslo, Paris, Vintage, ...) plus a tiny random tweak
- **On-screen captions**: your words, synced, in one of 19 styles (white / yellow / green / red variants)
- **Background audio**: a random track from the audio folder at about 25% under your voice
- **Post caption**: `Follow @futurescorey for free trading info`

Settings and schedule live in [config.md](config.md). Previews of the looks are in [previews/](previews/).

## How posting works

Instagram only applies trial mode when it downloads the video from a public link, so each reel is
pushed to the `staging` branch here, Instagram pulls it from there, and the next run replaces it.
The Meta access key is never stored in this repo; the cloud environment adds it to requests.

## Files

| File | What it does |
|---|---|
| `remix_and_post.py` | Makes a variation and posts it (`--dry-run` to only render) |
| `transcribe.py` | One-time: turns the base video's speech into word timings |
| `media/words.json` | Word timings with your corrections (`words.orig.json` = raw transcript) |
| `make_previews.py` | Builds the caption style preview sheet |

The base video and audio tracks live in the Google Drive folder "Bernard Posting Trial", not here.
