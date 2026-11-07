#!/bin/bash
# One scheduled post: update code, make sure media is downloaded, render a variation, post it as a trial reel.
set -euo pipefail
cd "$(dirname "$0")"
git pull -q --ff-only origin main || echo "warning: could not update code, using local copy"
python3 fetch_media.py
python3 remix_and_post.py
