#!/bin/bash
# Build the ground-truth test video: 120 BPM click track, luma-distinct color
# segments with cuts at 2.00s (on beat) and ~3.27s (off beat, ~233ms).
set -e
OUT="${1:-/tmp/ba-test.mp4}"
DIR="$(cd "$(dirname "$0")/.." && pwd)"
CLICK="$(mktemp --suffix=.wav)"
"$DIR/.venv/bin/python" - "$CLICK" <<'EOF'
import sys, numpy as np, soundfile as sf
sr = 22050; dur = 6.0
y = np.zeros(int(sr*dur))
for t in np.arange(0, dur, 0.5):
    i = int(t*sr); n = int(0.03*sr)
    y[i:i+n] = 0.9*np.sin(2*np.pi*1000*np.arange(n)/sr)*np.hanning(n)
sf.write(sys.argv[1], y, sr)
EOF
"$DIR/bin/ffmpeg" -y -v error \
  -f lavfi -i color=black:s=320x240:d=2:r=30 \
  -f lavfi -i color=white:s=320x240:d=1.25:r=30 \
  -f lavfi -i color=gray:s=320x240:d=2.75:r=30 \
  -i "$CLICK" \
  -filter_complex "[0][1][2]concat=n=3:v=1:a=0[v]" -map "[v]" -map 3:a \
  -shortest "$OUT"
rm -f "$CLICK"
echo "test video: $OUT (cuts at 2.00s on-beat, ~3.27s off-beat)"
