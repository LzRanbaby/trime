#!/usr/bin/env python3
"""Synthesize the GlassKeys keypress click sound (glass/click.wav).

Self-contained (stdlib only). The sound is a 45 ms Gboard-style click,
synthesized from scratch -- it is NOT extracted from any proprietary
keyboard. Parameters follow the record in ~/workspace/glasskeys/STATUS.md
(section 4):

  * duration 45 ms, 44100 Hz, mono, 16-bit PCM
  * filtered noise burst (attack transient)
  * 1850 Hz + 3300 Hz decaying sine "ticks"
  * a low-frequency "thump" body
  * peak normalized to 0.85

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
DURATION_MS = 45
PEAK = 0.85
SEED = 20261029  # deterministic noise

OUTPUT_DEFAULT = "app/src/main/assets/rime/soundeffect/glass/click.wav"


def synthesize() -> list[float]:
    n = int(SAMPLE_RATE * DURATION_MS / 1000)  # 1984 frames
    rng = random.Random(SEED)
    out = []
    lp = 0.0  # one-pole lowpass state for the noise burst
    alpha = 0.55  # lowpass coefficient (the "filter" on the noise)
    for i in range(n):
        t = i / SAMPLE_RATE
        # Filtered noise burst: sharp attack, ~6 ms decay.
        white = rng.uniform(-1.0, 1.0)
        lp += alpha * (white - lp)
        burst = lp * math.exp(-t / 0.006) * 0.9
        # Two decaying sine ticks giving the crisp "click" body.
        tick1 = math.sin(2.0 * math.pi * 1850.0 * t) * math.exp(-t / 0.007) * 0.55
        tick2 = math.sin(2.0 * math.pi * 3300.0 * t) * math.exp(-t / 0.004) * 0.32
        # Low-frequency thump for weight.
        thump = math.sin(2.0 * math.pi * 170.0 * t) * math.exp(-t / 0.012) * 0.45
        out.append(burst + tick1 + tick2 + thump)
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
