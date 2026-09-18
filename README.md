# beat-analyser

Tells you whether your video edit is *clean with the music* — objectively.

Give it an exported video (e.g. a DaVinci Resolve draft) and it reports:

1. **Cut-to-beat alignment** — every detected cut, its distance in ms to the
   nearest musical beat, and a verdict (ON BEAT ≤100ms, close ≤160ms, OFF).
2. **Pacing** — shot lengths, shots that drag (>5s), whether the rhythm
   accelerates toward the end like a montage should.
3. **Ending** — whether the last frame lands on a beat.
4. `--frames` — a JPG snapshot at every cut for visual review.

## Run

```bash
.venv/bin/python analyse.py "~/Videos/my-edit.mp4" --frames
```

## Self-contained

ffmpeg/ffprobe are static binaries in `bin/`; python deps live in `.venv/`.
Nothing is installed globally. Delete the folder, it's gone.

## Test

```bash
tests/make_test.sh && .venv/bin/python analyse.py /tmp/ba-test.mp4
```
