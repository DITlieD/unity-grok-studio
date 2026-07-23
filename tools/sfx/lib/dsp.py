"""Deterministic DSP helpers for seed library + assemble sub/tail layers."""

from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import soundfile as sf


def rng_for(seed: int) -> np.random.Generator:
    return np.random.default_rng(int(seed) & 0xFFFFFFFF)


def write_wav(path: Path | str, data: np.ndarray, sr: int = 48000) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    # PCM_24: no PEAK-chunk wall-clock (FLOAT writes non-deterministic PEAK timestamps)
    x = np.asarray(data, dtype=np.float64)
    peak = np.max(np.abs(x)) if x.size else 0.0
    if peak > 0.99:
        x = x * (0.99 / peak)
    sf.write(str(path), x, sr, subtype="PCM_24")
    return path


def envelope_exp(n: int, sr: int, attack_ms: float, decay_ms: float) -> np.ndarray:
    att = max(1, int(sr * attack_ms / 1000.0))
    dec = max(1, int(sr * decay_ms / 1000.0))
    env = np.zeros(n, dtype=np.float64)
    a = min(att, n)
    env[:a] = np.linspace(0, 1, a, endpoint=False)
    rest = n - a
    if rest > 0:
        t = np.arange(rest) / sr
        tau = max(decay_ms / 1000.0, 1e-4)
        env[a:] = np.exp(-t / tau)
    return env


def synth_impact(
    sr: int = 48000,
    duration_s: float = 0.35,
    seed: int = 1,
    f0: float = 120.0,
    brightness: float = 0.4,
    label: str = "impact",
) -> np.ndarray:
    """Short dry impact body with noise transient."""
    g = rng_for(seed)
    n = int(sr * duration_s)
    t = np.arange(n) / sr
    # click transient
    click = g.standard_normal(n) * np.exp(-t * 80.0)
    # body tone
    body = np.sin(2 * math.pi * f0 * t) * np.exp(-t * 12.0)
    body += 0.5 * np.sin(2 * math.pi * f0 * 1.5 * t) * np.exp(-t * 18.0)
    # mid noise body
    noise = g.standard_normal(n) * np.exp(-t * 25.0) * brightness
    x = 0.55 * click + 0.7 * body + 0.35 * noise
    x *= envelope_exp(n, sr, 1.0, duration_s * 1000 * 0.6)
    # soft highpass-ish by differencing a bit of brightness
    if brightness > 0:
        x = x + 0.15 * np.diff(x, prepend=x[0])
    peak = np.max(np.abs(x)) or 1.0
    return (x / peak) * 0.85


def synth_debris(
    sr: int = 48000,
    duration_s: float = 0.8,
    seed: int = 2,
    density: float = 0.5,
) -> np.ndarray:
    g = rng_for(seed)
    n = int(sr * duration_s)
    x = np.zeros(n)
    n_hits = max(3, int(8 * density + g.integers(0, 4)))
    for i in range(n_hits):
        pos = int(g.uniform(0, n * 0.7))
        length = int(g.uniform(0.01, 0.08) * sr)
        t = np.arange(length) / sr
        hit = g.standard_normal(length) * np.exp(-t * g.uniform(30, 90))
        f = g.uniform(800, 4000)
        hit += 0.3 * np.sin(2 * math.pi * f * t) * np.exp(-t * 40)
        end = min(n, pos + length)
        x[pos:end] += hit[: end - pos] * g.uniform(0.3, 1.0)
    peak = np.max(np.abs(x)) or 1.0
    return (x / peak) * 0.7


def synth_wood_slam(
    sr: int = 48000,
    duration_s: float = 0.55,
    seed: int = 3,
) -> np.ndarray:
    g = rng_for(seed)
    n = int(sr * duration_s)
    t = np.arange(n) / sr
    # low thump
    thump = np.sin(2 * math.pi * 70 * t) * np.exp(-t * 14)
    thump += 0.4 * np.sin(2 * math.pi * 110 * t) * np.exp(-t * 20)
    # wood knock mid
    knock = g.standard_normal(n)
    # band-ish via simple recursive lowpass of noise then high emphasis
    for _ in range(2):
        knock = np.cumsum(knock)
        knock -= np.mean(knock)
    knock *= np.exp(-t * 18)
    # latch click
    click = np.zeros(n)
    c_n = int(0.008 * sr)
    click[:c_n] = g.standard_normal(c_n) * np.linspace(1, 0, c_n)
    x = 0.9 * thump + 0.45 * knock + 0.5 * click
    x = x - np.mean(x)
    peak = np.max(np.abs(x)) or 1.0
    return (x / peak) * 0.88


def synth_metal_impact(
    sr: int = 48000,
    duration_s: float = 0.4,
    seed: int = 4,
) -> np.ndarray:
    g = rng_for(seed)
    n = int(sr * duration_s)
    t = np.arange(n) / sr
    freqs = [g.uniform(400, 900), g.uniform(1200, 2200), g.uniform(2800, 4500)]
    x = np.zeros(n)
    for f in freqs:
        x += np.sin(2 * math.pi * f * t + g.uniform(0, 2 * math.pi)) * np.exp(
            -t * g.uniform(8, 20)
        )
    x += 0.4 * g.standard_normal(n) * np.exp(-t * 50)
    peak = np.max(np.abs(x)) or 1.0
    return (x / peak) * 0.8


def synth_glass_debris(
    sr: int = 48000,
    duration_s: float = 0.9,
    seed: int = 5,
) -> np.ndarray:
    g = rng_for(seed)
    n = int(sr * duration_s)
    x = np.zeros(n)
    for _ in range(int(g.integers(6, 14))):
        pos = int(g.uniform(0, n * 0.6))
        length = int(g.uniform(0.02, 0.15) * sr)
        t = np.arange(length) / sr
        f = g.uniform(2000, 8000)
        ring = np.sin(2 * math.pi * f * t) * np.exp(-t * g.uniform(15, 40))
        ring += 0.3 * g.standard_normal(length) * np.exp(-t * 60)
        end = min(n, pos + length)
        x[pos:end] += ring[: end - pos]
    peak = np.max(np.abs(x)) or 1.0
    return (x / peak) * 0.65


def synth_sub_boom(
    sr: int = 48000,
    duration_s: float = 0.9,
    seed: int = 6,
    f0: float = 45.0,
) -> np.ndarray:
    g = rng_for(seed)
    n = int(sr * duration_s)
    t = np.arange(n) / sr
    # pitch drop
    phase = 2 * math.pi * (f0 * t - 8 * t**2)
    x = np.sin(phase) * np.exp(-t * 3.5)
    x += 0.15 * g.standard_normal(n) * np.exp(-t * 20)
    peak = np.max(np.abs(x)) or 1.0
    return (x / peak) * 0.9


def synth_crackle_tail(
    sr: int = 48000,
    duration_s: float = 1.0,
    seed: int = 7,
) -> np.ndarray:
    g = rng_for(seed)
    n = int(sr * duration_s)
    x = np.zeros(n)
    t0 = 0
    while t0 < n:
        length = int(g.uniform(0.005, 0.04) * sr)
        gap = int(g.uniform(0.01, 0.08) * sr)
        burst = g.standard_normal(length) * g.uniform(0.2, 1.0)
        # highpass-ish
        burst = np.diff(burst, prepend=0)
        end = min(n, t0 + length)
        x[t0:end] += burst[: end - t0]
        t0 += length + gap
    # overall decay
    t = np.arange(n) / sr
    x *= np.exp(-t * 1.8)
    peak = np.max(np.abs(x)) or 1.0
    return (x / peak) * 0.55


def _one_pole_lp(x: np.ndarray, coef: float) -> np.ndarray:
    y = np.zeros_like(x)
    s = 0.0
    c = float(np.clip(coef, 0.0, 0.9999))
    for i, v in enumerate(x):
        s = s + c * (v - s)
        y[i] = s
    return y


def _one_pole_hp(x: np.ndarray, coef: float) -> np.ndarray:
    """Simple highpass via x - lowpass(x)."""
    return x - _one_pole_lp(x, coef)


def _wood_crack(
    sr: int,
    g: np.random.Generator,
    *,
    kind: str = "pop",
) -> np.ndarray:
    """Single wood/ember event: impulsive + short resonances (not steady hiss)."""
    if kind == "ember":
        length = int(g.uniform(0.003, 0.012) * sr)
        tt = np.arange(length) / sr
        # tiny HF tick, almost no body
        click = g.standard_normal(length)
        click = _one_pole_hp(click, 0.35)
        env = np.exp(-tt / g.uniform(0.0015, 0.004))
        return click * env * g.uniform(0.2, 0.7)

    if kind == "snap":
        length = int(g.uniform(0.035, 0.12) * sr)
        tt = np.arange(length) / sr
        # deeper wood split: multi-partial decay
        f0 = g.uniform(90, 220)
        body = np.zeros(length)
        for k, damp in ((1.0, 14.0), (2.1, 22.0), (3.4, 35.0), (5.2, 50.0)):
            body += (
                g.uniform(0.3, 1.0)
                * np.sin(2 * math.pi * f0 * k * tt + g.uniform(0, 6))
                * np.exp(-tt * damp * g.uniform(0.8, 1.3))
            )
        # short noise attack (the crack)
        att_n = max(8, int(0.004 * sr))
        att = g.standard_normal(length)
        att = _one_pole_hp(att, 0.25)
        att_env = np.zeros(length)
        att_env[:att_n] = np.linspace(1, 0, att_n)
        att_env *= np.exp(-tt * 80)
        out = 0.55 * body + 0.9 * att * att_env
        out *= np.exp(-tt * g.uniform(6, 12))
        return out * g.uniform(0.45, 1.0)

    # default pop / crackle
    length = int(g.uniform(0.012, 0.045) * sr)
    tt = np.arange(length) / sr
    f0 = g.uniform(400, 1400)
    # damped partials in mid band (sap/wood pop character)
    tone = np.zeros(length)
    for k, damp in ((1.0, 40.0), (1.7, 55.0), (2.6, 70.0)):
        tone += (
            g.uniform(0.4, 1.0)
            * np.sin(2 * math.pi * f0 * k * tt + g.uniform(0, 6))
            * np.exp(-tt * damp)
        )
    noise = g.standard_normal(length)
    noise = _one_pole_hp(noise, 0.2)
    noise = _one_pole_lp(noise, 0.7)
    n_env = np.exp(-tt / g.uniform(0.003, 0.012))
    # asymmetric envelope: fast attack, medium decay
    env = np.minimum(1.0, tt * sr / 40.0) * np.exp(-tt / g.uniform(0.008, 0.025))
    out = (0.65 * tone + 0.55 * noise * n_env) * env
    return out * g.uniform(0.35, 1.0)


def synth_fire_bed(
    sr: int = 48000,
    duration_s: float = 3.0,
    seed: int = 9001,
    intensity: float = 0.75,
) -> np.ndarray:
    """Campfire-style bed: sparse wood cracks + quiet low roar (not plastic hiss).

    Design notes vs v1 (plastic-bag failure):
    - almost no continuous broadband hiss (that reads as wind/fabric)
    - event-driven crackles with resonant partials
    - low end is intermittent whoomps, not steady filtered noise
    """
    g = rng_for(seed)
    n = int(sr * duration_s)
    x = np.zeros(n, dtype=np.float64)

    # --- quiet low combustion roar (sparse, heavily lowpassed) ---
    # Not continuous wind: gate brown noise with slow irregular envelope near zero most of the time
    white = g.standard_normal(n)
    roar = white.copy()
    for _ in range(4):
        roar = _one_pole_lp(roar, 0.015)
    roar -= np.mean(roar)
    # sparse gate: a few low "breaths" of heat, not a constant bed
    gate = np.zeros(n)
    n_whoomps = max(2, int(duration_s * g.uniform(1.2, 2.0)))
    for _ in range(n_whoomps):
        center = int(g.uniform(0.05, max(0.1, duration_s - 0.1)) * sr)
        width = int(g.uniform(0.18, 0.55) * sr)
        half = width // 2
        a = max(0, center - half)
        b = min(n, center + half)
        if b <= a:
            continue
        w = np.hanning(b - a)
        gate[a:b] += w * g.uniform(0.25, 0.7)
    gate = np.clip(gate, 0, 1.0)
    # tiny floor so it's not digital silence between events
    roar_layer = roar * (0.04 + 0.55 * gate) * intensity

    # --- event stream: wood pops, snaps, embers ---
    # density ~ campfire, not continuous sizzle
    t_cursor = g.uniform(0.02, 0.08)
    while t_cursor < duration_s - 0.02:
        r = g.random()
        if r < 0.12:
            kind = "snap"
            gap = g.uniform(0.25, 0.7)
        elif r < 0.55:
            kind = "pop"
            gap = g.uniform(0.04, 0.18)
        else:
            kind = "ember"
            gap = g.uniform(0.02, 0.1)

        event = _wood_crack(sr, g, kind=kind)
        pos = int(t_cursor * sr)
        end = min(n, pos + len(event))
        if end > pos:
            amp = intensity * (1.0 if kind != "ember" else 0.55)
            x[pos:end] += event[: end - pos] * amp
        t_cursor += gap * g.uniform(0.7, 1.4) / max(0.4, intensity)

    # a few intentional larger snaps spaced through the clip
    for _ in range(max(2, int(duration_s))):
        pos = int(g.uniform(0.15, max(0.2, duration_s - 0.15)) * sr)
        event = _wood_crack(sr, g, kind="snap")
        end = min(n, pos + len(event))
        if end > pos:
            x[pos:end] += event[: end - pos] * intensity * g.uniform(0.7, 1.15)

    # very light mid "air" only under whoomps (not free-running hiss)
    air = g.standard_normal(n)
    air = _one_pole_hp(air, 0.08)
    air = _one_pole_lp(air, 0.45)
    air_layer = air * gate * 0.08 * intensity

    x = x + roar_layer * 0.9 + air_layer

    fade = int(0.03 * sr)
    if fade > 0 and n > 2 * fade:
        x[:fade] *= np.linspace(0, 1, fade, endpoint=False)
        x[-fade:] *= np.linspace(1, 0, fade, endpoint=False)
    x = x - np.mean(x)
    peak = np.max(np.abs(x)) or 1.0
    return (x / peak) * 0.88


def synth_clipped_tone(
    sr: int = 48000,
    duration_s: float = 0.3,
    seed: int = 99,
) -> np.ndarray:
    """Deliberately clipped fixture for QA fail path."""
    n = int(sr * duration_s)
    t = np.arange(n) / sr
    x = 1.5 * np.sin(2 * math.pi * 440 * t)
    return np.clip(x, -1.0, 1.0)


def apply_gain_db(x: np.ndarray, gain_db: float) -> np.ndarray:
    return x * (10.0 ** (gain_db / 20.0))


def apply_fade(x: np.ndarray, sr: int, fade_in_ms: float, fade_out_ms: float) -> np.ndarray:
    y = x.copy()
    n = len(y)
    fi = min(n, int(sr * fade_in_ms / 1000.0))
    fo = min(n, int(sr * fade_out_ms / 1000.0))
    if fi > 0:
        y[:fi] *= np.linspace(0, 1, fi, endpoint=False)
    if fo > 0:
        y[-fo:] *= np.linspace(1, 0, fo, endpoint=False)
    return y


def pitch_shift_resample(x: np.ndarray, cents: float) -> np.ndarray:
    """Deterministic pitch via linear resample (rate change). Bounded by caller."""
    if abs(cents) < 1e-6:
        return x.copy()
    ratio = 2.0 ** (cents / 1200.0)
    n = len(x)
    new_n = max(1, int(round(n / ratio)))
    # map new indices into original
    idx = np.linspace(0, n - 1, new_n)
    i0 = np.floor(idx).astype(int)
    i1 = np.minimum(i0 + 1, n - 1)
    frac = idx - i0
    y = (1 - frac) * x[i0] + frac * x[i1]
    # pad/trim to original length for mix alignment simplicity
    if len(y) < n:
        out = np.zeros(n)
        out[: len(y)] = y
        return out
    return y[:n]


def first_onset_index(x: np.ndarray, sr: int, thresh: float = 0.05) -> int:
    absx = np.abs(x)
    peak = np.max(absx) if absx.size else 0.0
    if peak <= 0:
        return 0
    hits = np.where(absx >= thresh * peak)[0]
    return int(hits[0]) if hits.size else 0


def mix_layers(
    layers: list[tuple[np.ndarray, int]],  # (audio, start_sample)
    total_samples: int,
) -> np.ndarray:
    out = np.zeros(total_samples, dtype=np.float64)
    for audio, start in layers:
        start = max(0, int(start))
        end = min(total_samples, start + len(audio))
        if end > start:
            out[start:end] += audio[: end - start]
    peak = np.max(np.abs(out)) if out.size else 0.0
    if peak > 0.95:
        out *= 0.95 / peak
    return out
