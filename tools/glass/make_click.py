#!/usr/bin/env python3
"""Synthesize the GlassKeys keypress click sound (glass/click.wav).

Self-contained (stdlib only). The sound is synthesized from scratch -- it
is NOT extracted from any proprietary keyboard.

Current recipe: "light-mechanical" (轻机械), a blend picked by the user on
2026-10-29 -- the two-stage skeleton of the mechanical-switch variant
(recipe 3 on the audition page) with the lightness of the feather variant
(recipe 5):

  * stage 1 (press, t=0): bandpass noise click (1700 Hz, Q=1) + a low
    thump gliding 150 -> 90 Hz
  * stage 2 (release, t=48 ms): a lighter bandpass noise click (2300 Hz)
    + a lighter thump gliding 110 -> 70 Hz
  * noise gains cut ~40% vs the plain mechanical recipe; thumps kept,
    since the mechanical feel comes mostly from them
  * total duration 110 ms, 44100 Hz, mono, 16-bit PCM
  * peak normalized to 0.45 (between feather's 0.35 and the original
    Gboard-style click's 0.85)

Usage:
    python3 tools/glass/make_click.py [output.wav]

Default output: app/src/main/assets/rime/soundeffect/glass/click.wav
(relative to the current working directory, i.e. the repo root in CI).
"""

import math
import random
import struct
import sys
import wave

SAMPLE_RATE = 44100
DURATION_MS = 110
PEAK = 0.45
SEED = 20261029  # deterministic noise

STAGE2_OFFSET = 0.048  # seconds; release click delay
BP1_FREQ, BP2_FREQ = 1700.0, 2300.0  # bandpass centers (Hz)
BP_Q = 1.0
NOISE1_GAIN, NOISE2_GAIN = 0.30, 0.21  # recipe-3 gains (0.50/0.35) cut ~40%
NOISE1_TAU, NOISE2_TAU = 0.004, 0.0035  # burst decay time constants (s)
# (start Hz, end Hz, glide seconds, envelope tau seconds, gain)
THUMP1 = (150.0, 90.0, 0.050, 0.009, 0.32)
THUMP2 = (110.0, 70.0, 0.060, 0.010, 0.20)

OUTPUT_DEFAULT = "app/src/main/assets/rime/soundeffect/glass/click.wav"


class Bandpass:
    """RBJ biquad bandpass, constant 0 dB peak gain."""

    def __init__(self, freq: float, q: float) -> None:
        w0 = 2.0 * math.pi * freq / SAMPLE_RATE
        alpha = math.sin(w0) / (2.0 * q)
        norm = 1.0 + alpha
        self.b0 = alpha / norm
        self.b2 = -alpha / norm
        self.a1 = -2.0 * math.cos(w0) / norm
        self.a2 = (1.0 - alpha) / norm
        self.x1 = self.x2 = self.y1 = self.y2 = 0.0

    def step(self, x: float) -> float:
        y = (self.b0 * x + self.b2 * self.x2
             - self.a1 * self.y1 - self.a2 * self.y2)
        self.x2, self.x1 = self.x1, x
        self.y2, self.y1 = self.y1, y
        return y


def _glide_freq(f0: float, f1: float, glide: float, local_t: float) -> float:
    if local_t >= glide:
        return f1
    return f0 * (f1 / f0) ** (local_t / glide)


def synthesize() -> list[float]:
    n = int(SAMPLE_RATE * DURATION_MS / 1000)  # 4851 frames
    rng = random.Random(SEED)
    bp1 = Bandpass(BP1_FREQ, BP_Q)
    bp2 = Bandpass(BP2_FREQ, BP_Q)
    phase1 = phase2 = 0.0
    out = []
    for i in range(n):
        t = i / SAMPLE_RATE
        white = rng.uniform(-1.0, 1.0)
        # Stage 1 noise click: sharp bandpassed burst at t=0.
        s = bp1.step(white) * math.exp(-t / NOISE1_TAU) * NOISE1_GAIN
        # Stage 1 thump: sine gliding 150 -> 90 Hz with fast decay.
        f0, f1, glide, tau, gain = THUMP1
        phase1 += 2.0 * math.pi * _glide_freq(f0, f1, glide, t) / SAMPLE_RATE
        s += math.sin(phase1) * math.exp(-t / tau) * gain
        # Stage 2 (release): lighter click + thump, offset by 48 ms.
        t2 = t - STAGE2_OFFSET
        if t2 >= 0.0:
            s += bp2.step(white) * math.exp(-t2 / NOISE2_TAU) * NOISE2_GAIN
            f0, f1, glide, tau, gain = THUMP2
            phase2 += (2.0 * math.pi * _glide_freq(f0, f1, glide, t2)
                       / SAMPLE_RATE)
            s += math.sin(phase2) * math.exp(-t2 / tau) * gain
        else:
            bp2.step(white)  # keep the filter stream in sync
        out.append(s)
    peak = max(abs(x) for x in out) or 1.0
    scale = PEAK / peak
    return [x * scale for x in out]


def main() -> None:
    output = sys.argv[1] if len(sys.argv) > 1 else OUTPUT_DEFAULT
    samples = synthesize()
    frames = b"".join(
        struct.pack("<h", max(-32767, min(32767, int(round(x * 32767)))))
        for x in samples
    )
    with wave.open(output, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SAMPLE_RATE)
        w.writeframes(frames)
    print(f"wrote {output}: {len(samples)} frames, "
          f"{1000 * len(samples) / SAMPLE_RATE:.1f} ms @ {SAMPLE_RATE} Hz")


if __name__ == "__main__":
    main()
