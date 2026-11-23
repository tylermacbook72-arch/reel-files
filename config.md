# Trial reel auto-poster settings
- Account: @futurescorey (IG user 17841480164538536), posts as TRIAL REELS
- Post caption (every post): Follow @futurescorey for free trading info 📚
- Schedule (America/New_York): 11:00 AM, 2:00 PM, 5:00 PM, 8:00 PM, 11:00 PM (back to 5/day on 2026-11-21 with Video 2)
- Status: PAUSED on 2026-11-23 (Instagram reported the account as restricted; user asked to pause)

## Per-reel changes (nothing cut, trimmed or added beyond these)
- Speed: split the ~39s video into its spoken parts (by pauses in the voice);
  pick 1-2 parts at random, play them at 0.9x or 1.1x, rest at 1.0x; voice pitch preserved
- Color: one filter at random from Warm, Toasty, Autumn, Lounge, Spring, Cool, Oslo,
  Fresh, Shade, Vintage, Fade, Wash, Simple, Crisp, Lively, Paris, Jakarta + small random tweak
- On-screen captions: word-synced from media/words.json (user-corrected), random style per reel from 19 styles
  (Bold White; White/Yellow/Green/Red Pop; Yellow/Green/Red Highlight; One Word White/Yellow/Green/Red;
  Yellow/Green/Red Accent; Clean Lower; Boxed; Center Big; Soft Shadow)
- Audio: voice ~75% + random background track from Drive folder ~25%
  (base video is voice only, confirmed)

## Audio rotation
- 16 audios from the Drive folder (media/drive_files.json); each post uses the least-used audio
- Each audio starts at its best section (media/audio_windows.json, from find_best_parts.py);
  after 3 uses it moves to the next-best section, and so on
- Usage memory + post history live in state.json on the staging branch

## Mirroring
- Half the reels mirror the face cam (top part) only; the chart stays unflipped so its text and candles read correctly

## Base video
- Current: original "Video" from Drive (media/video_settings.json: video.mp4, words.json, face cam = top 36.25%), with the follow animation from "So follow" (33.64s)
- Video 2 settings (if switching back): video2.mp4, words2.json, face_cam_height 0.391, seam 0.394, follow_start 39.36
- Transcript fixes: "80 %" -> "86%", "top step" -> "Topstep" (raw transcript in words2.orig.json)
- Long sentences are also split at commas (14 parts)
- End graphic: "tap to follow" card (make_follow_overlay.py -> media/follow_overlay.mov) pops up on "So follow..." and stays to the end
