#!/usr/bin/env python3
"""Beat-analyser: check whether a video edit's cuts land on the music's beats.

Usage:
    .venv/bin/python analyse.py <video> [--scene-threshold 0.3] [--frames]

Output: a report of every detected cut, its distance to the nearest beat,
shot-length pacing, and ending alignment. --frames also dumps a JPG at each
cut into frames/ for visual review.
"""

import argparse
import os
import re
import subprocess
import sys
import tempfile

import numpy as np

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
FFMPEG = os.path.join(PROJECT_DIR, "bin", "ffmpeg")
FFPROBE = os.path.join(PROJECT_DIR, "bin", "ffprobe")

ON_BEAT_MS = 100     # feels locked to the beat
CLOSE_MS = 160       # noticeable to a careful ear, fine for most viewers
LONG_SHOT_S = 5.0    # a shot longer than this in a montage usually drags


def run(cmd):
    return subprocess.run(cmd, capture_output=True, text=True)


def video_duration(path):
    r = run([FFPROBE, "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", path])
    return float(r.stdout.strip())


def detect_cuts(path, threshold):
    """Scene-change detection via ffmpeg's scene score; returns cut times in seconds."""
    r = run([FFMPEG, "-i", path,
             "-vf", f"select='gt(scene,{threshold})',showinfo",
             "-an", "-f", "null", "-"])
    times = [float(m) for m in re.findall(r"pts_time:([0-9.]+)", r.stderr)]
    return sorted(t for t in times if t > 0.2)


def detect_beats(path):
    """Extract audio and beat-track it; returns (tempo_bpm, beat times in seconds)."""
    import librosa
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        wav = tmp.name
    try:
        run([FFMPEG, "-y", "-i", path, "-vn", "-ac", "1", "-ar", "22050", wav])
        y, sr = librosa.load(wav, sr=22050, mono=True)
        tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr)
        beats = librosa.frames_to_time(beat_frames, sr=sr)
        tempo = float(np.atleast_1d(tempo)[0])
        if not len(beats):
            # beat_track can come up empty on sparse/percussive-only audio;
            # fall back to predominant-local-pulse peaks
            env = librosa.onset.onset_strength(y=y, sr=sr)
            tempo = float(librosa.feature.tempo(onset_envelope=env, sr=sr)[0])
            pulse = librosa.beat.plp(onset_envelope=env, sr=sr)
            peaks = librosa.util.peak_pick(pulse, pre_max=8, post_max=8,
                                           pre_avg=8, post_avg=8,
                                           delta=0.1, wait=8)
            beats = librosa.frames_to_time(peaks, sr=sr)
        return tempo, beats
    finally:
        os.unlink(wav)


def dump_frames(path, cuts, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    for i, t in enumerate(cuts, 1):
        run([FFMPEG, "-y", "-ss", f"{t:.3f}", "-i", path, "-frames:v", "1",
             "-q:v", "3", os.path.join(out_dir, f"cut{i:02d}_{t:.2f}s.jpg")])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("video")
    ap.add_argument("--scene-threshold", type=float, default=0.3)
    ap.add_argument("--frames", action="store_true",
                    help="dump a JPG at each cut into frames/")
    args = ap.parse_args()

    if not os.path.exists(args.video):
        sys.exit(f"not found: {args.video}")

    dur = video_duration(args.video)
    cuts = detect_cuts(args.video, args.scene_threshold)
    tempo, beats = detect_beats(args.video)

    print(f"video     : {args.video}")
    print(f"duration  : {dur:.2f}s")
    print(f"tempo     : {tempo:.1f} BPM  ({len(beats)} beats detected)")
    print(f"cuts      : {len(cuts)} detected (scene threshold {args.scene_threshold})")
    print()

    if not len(beats):
        sys.exit("no beats detected — is there music on the track?")

    # --- cut-to-beat alignment ---
    on = close = off = 0
    print("cut-to-beat alignment:")
    for i, t in enumerate(cuts, 1):
        d_ms = float(np.min(np.abs(beats - t))) * 1000
        if d_ms <= ON_BEAT_MS:
            verdict, on = "ON BEAT", on + 1
        elif d_ms <= CLOSE_MS:
            verdict, close = "close", close + 1
        else:
            verdict, off = "OFF — nudge it", off + 1
        print(f"  cut {i:2d} @ {t:7.2f}s   {d_ms:6.0f} ms from beat   {verdict}")
    print(f"  -> {on} on beat, {close} close, {off} off (of {len(cuts)})")
    print()

    # --- pacing ---
    bounds = [0.0] + cuts + [dur]
    shots = [(bounds[i], bounds[i + 1] - bounds[i]) for i in range(len(bounds) - 1)]
    lengths = [s[1] for s in shots]
    print("pacing:")
    print(f"  {len(shots)} shots, avg {np.mean(lengths):.2f}s, "
          f"shortest {min(lengths):.2f}s, longest {max(lengths):.2f}s")
    for start, length in shots:
        if length > LONG_SHOT_S:
            print(f"  shot @ {start:.2f}s runs {length:.2f}s — long for a montage, "
                  f"consider trimming or splitting")
    first_half = np.mean(lengths[: max(1, len(lengths) // 2)])
    second_half = np.mean(lengths[len(lengths) // 2:])
    trend = "accelerates" if second_half < first_half else "slows down"
    print(f"  rhythm {trend} toward the end "
          f"(avg {first_half:.2f}s first half -> {second_half:.2f}s second half)")
    print()

    # --- ending ---
    end_gap_ms = float(np.min(np.abs(beats - dur))) * 1000
    tail_ms = (dur - beats[-1]) * 1000
    print("ending:")
    if end_gap_ms <= CLOSE_MS:
        print(f"  last frame lands {end_gap_ms:.0f} ms from a beat — clean ending")
    else:
        print(f"  last frame is {end_gap_ms:.0f} ms from the nearest beat — "
              f"the video doesn't end on a hit; trim the tail to the last beat")
    if tail_ms > 500:
        print(f"  note: {tail_ms / 1000:.2f}s of audio after the last detected beat "
              f"(fade-out or silence)")

    if args.frames:
        out_dir = os.path.join(PROJECT_DIR, "frames")
        dump_frames(args.video, cuts, out_dir)
        print(f"\nframes at each cut written to {out_dir}/")


if __name__ == "__main__":
    main()
