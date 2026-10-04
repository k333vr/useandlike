#!/bin/sh
# Refreshes data/channel-videos.tsv with every video of our channels (needs: pip install yt-dlp).
# Columns: id, views, seconds, title, channel. Then run: python3 scripts/build-videos.py
set -e
cd "$(dirname "$0")/.."
out=data/channel-videos.tsv
: > "$out.tmp"
for pair in "HowToRocket:How To Rocket" "GuideGlimpse:Guide Glimpse" "Log1cProtocol:Logic Protocol"; do
  handle=${pair%%:*}; name=${pair#*:}
  yt-dlp --flat-playlist --print "%(id)s	%(view_count)s	%(duration)s	%(title)s	$name" \
    "https://www.youtube.com/@$handle/videos" >> "$out.tmp"
done
mv "$out.tmp" "$out"
wc -l "$out"
