# beat-analyser

Checks whether the cuts in a video edit land on the beat of the music, and tells you which ones don't.

I built it for my own montage edits (I cut in DaVinci Resolve). Judging by ear whether a cut is a little early is slow and unreliable, so this puts a number on it.

## What it reports

- **Cut-to-beat alignment.** Every detected cut, its distance in milliseconds to the nearest beat, and a verdict: ON BEAT (100 ms or less), close (160 ms or less), or OFF.
- **Pacing.** Shot count, average, shortest and longest shot, any shot over 5 seconds, and whether the rhythm speeds up or slows down.
- **Ending.** Whether the last frame lands on a beat, and how much audio trails after the last one.
- **Frames (optional).** `--frames` saves a JPG at every cut so you can check them by eye.

## Example

Run against the synthetic test video from `tests/make_test.sh` (a 120 BPM click track with one cut on the beat at 2.00 s and one off the beat at about 3.27 s):

```
video     : /tmp/ba-test.mp4
duration  : 6.00s
tempo     : 117.5 BPM  (13 beats detected)
cuts      : 2 detected (scene threshold 0.3)

cut-to-beat alignment:
  cut  1 @    2.00s       43 ms from beat   ON BEAT
  cut  2 @    3.27s      225 ms from beat   OFF — nudge it
  -> 1 on beat, 0 close, 1 off (of 2)

pacing:
  3 shots, avg 2.00s, shortest 1.27s, longest 2.73s
  rhythm holds steady toward the end (avg 2.00s first half -> 2.00s second half)

ending:
  last frame lands 14 ms from a beat — clean ending
```

The tracker read 117.5 BPM on a 120 BPM click, so beat positions are an estimate. The two cuts still come out as expected.

## How it works

1. ffmpeg's scene detection (`select='gt(scene,0.3)'`) finds the cut times.
2. The audio is pulled out as mono 22.05 kHz WAV and beat-tracked with librosa. If the tracker finds nothing (sparse or purely percussive audio), it falls back to peaks of the predominant local pulse.
3. Each cut is compared with its nearest beat. The thresholds are constants at the top of `analyse.py`.

## Install

Python 3 plus three packages. `analyse.py` looks for `ffmpeg` and `ffprobe` in `./bin`, so link or copy your own binaries there.

```bash
python3 -m venv .venv
.venv/bin/pip install numpy librosa soundfile
mkdir -p bin
ln -s "$(which ffmpeg)" bin/ffmpeg
ln -s "$(which ffprobe)" bin/ffprobe
```

Nothing is installed globally. Delete the folder and it's gone.

## Usage

```bash
.venv/bin/python analyse.py my-edit.mp4
.venv/bin/python analyse.py my-edit.mp4 --scene-threshold 0.2 --frames
```

`--scene-threshold` (default 0.3) controls how big a change counts as a cut. Lower it for soft cuts.

## Test

```bash
tests/make_test.sh && .venv/bin/python analyse.py /tmp/ba-test.mp4
```

The first cut should come out ON BEAT and the second OFF.

## Limits

- Scene detection finds hard cuts. Dissolves and fast whip pans can be missed or double counted.
- Beat tracking is an estimate. On a track with no steady beat the verdicts mean little.
- The only check so far is the synthetic video from `tests/make_test.sh`.
