"""Objective audio QA metrics for analyze_audio."""

from __future__ import annotations

import math
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any

import numpy as np
import soundfile as sf

try:
    import pyloudnorm as pln

    HAS_PYLOUDNORM = True
except ImportError:
    HAS_PYLOUDNORM = False

try:
    import librosa

    HAS_LIBROSA = True
except ImportError:
    HAS_LIBROSA = False


@dataclass
class AudioMetrics:
    path: str
    duration_s: float
    sample_rate: int
    channels: int
    bit_depth: int | None
    peak_dbfs: float
    integrated_lufs: float | None
    clip_samples: int
    clip_run_max: int
    dc_offset: float
    leading_silence_ms: float
    trailing_silence_ms: float
    onset_times_s: list[float] = field(default_factory=list)
    onset_count: int = 0
    loop_seam_delta: float = 0.0
    stereo_correlation: float | None = None
    subtype: str = ""
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        # ensure JSON-serializable floats (no NaN)
        for k, v in list(d.items()):
            if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
                d[k] = None
                self.errors.append(f"nonfinite:{k}")
        return d

    def is_finite(self) -> bool:
        for v in (
            self.duration_s,
            self.peak_dbfs,
            self.dc_offset,
            self.leading_silence_ms,
            self.trailing_silence_ms,
            self.loop_seam_delta,
        ):
            if v is None or (isinstance(v, float) and (math.isnan(v) or math.isinf(v))):
                return False
        if self.integrated_lufs is not None and (
            math.isnan(self.integrated_lufs) or math.isinf(self.integrated_lufs)
        ):
            return False
        return True


def _to_float_mono(data: np.ndarray) -> np.ndarray:
    x = np.asarray(data, dtype=np.float64)
    if x.ndim == 1:
        return x
    return x.mean(axis=1)


def _peak_dbfs(x: np.ndarray) -> float:
    peak = float(np.max(np.abs(x))) if x.size else 0.0
    if peak <= 0.0:
        return -120.0
    return 20.0 * math.log10(peak)


def _clipping_stats(x: np.ndarray, thresh: float = 0.999) -> tuple[int, int]:
    hard = np.abs(x) >= thresh
    count = int(hard.sum())
    if count == 0:
        return 0, 0
    # run lengths
    runs = np.diff(np.concatenate(([0], hard.view(np.int8), [0])))
    starts = np.where(runs == 1)[0]
    ends = np.where(runs == -1)[0]
    max_run = int(np.max(ends - starts)) if len(starts) else 0
    return count, max_run


def _silence_edges_ms(x: np.ndarray, sr: int, thresh: float = 1e-4) -> tuple[float, float]:
    absx = np.abs(x)
    nz = np.where(absx > thresh)[0]
    if nz.size == 0:
        total_ms = 1000.0 * len(x) / sr
        return total_ms, total_ms
    lead = 1000.0 * float(nz[0]) / sr
    trail = 1000.0 * float(len(x) - 1 - nz[-1]) / sr
    return lead, trail


def _loop_seam_delta(x: np.ndarray, sr: int, window_ms: float = 10.0) -> float:
    n = max(1, int(sr * window_ms / 1000.0))
    if len(x) < 2 * n:
        return float(abs(x[0] - x[-1])) if len(x) else 0.0
    a = x[:n]
    b = x[-n:]
    # mean absolute difference between edge windows
    return float(np.mean(np.abs(a - b[::-1])))


def _stereo_corr(data: np.ndarray) -> float | None:
    if data.ndim != 2 or data.shape[1] < 2:
        return None
    l, r = data[:, 0], data[:, 1]
    if np.std(l) < 1e-12 or np.std(r) < 1e-12:
        return 1.0
    c = np.corrcoef(l, r)[0, 1]
    if math.isnan(c):
        return None
    return float(c)


def _onsets(x: np.ndarray, sr: int) -> list[float]:
    if len(x) < 64:
        return []
    if HAS_LIBROSA:
        try:
            # spectral flux style via librosa
            o = librosa.onset.onset_detect(
                y=x.astype(np.float32),
                sr=sr,
                units="time",
                backtrack=False,
                hop_length=max(64, int(sr * 0.01)),
            )
            return [float(t) for t in o]
        except Exception:
            pass
    # scipy-free spectral flux fallback via energy envelope peaks
    hop = max(64, int(sr * 0.01))
    n_frames = max(1, (len(x) - hop) // hop)
    env = np.array(
        [np.sqrt(np.mean(x[i * hop : i * hop + hop] ** 2)) for i in range(n_frames)]
    )
    if env.size < 3:
        return []
    flux = np.diff(env, prepend=env[0])
    flux = np.maximum(0.0, flux)
    thr = float(np.mean(flux) + 1.5 * np.std(flux))
    times: list[float] = []
    for i in range(1, len(flux) - 1):
        if flux[i] >= thr and flux[i] >= flux[i - 1] and flux[i] >= flux[i + 1]:
            times.append(i * hop / sr)
    return times


def _integrated_lufs(x: np.ndarray, sr: int) -> float | None:
    if HAS_PYLOUDNORM and len(x) > sr * 0.4:
        try:
            meter = pln.Meter(sr)
            # pyloudnorm expects shape (n,) or (n, ch)
            loud = meter.integrated_loudness(x.astype(np.float64))
            if loud is None or (isinstance(loud, float) and (math.isnan(loud) or math.isinf(loud))):
                return None
            return float(loud)
        except Exception:
            pass
    # rough RMS proxy when pyloudnorm unavailable or clip too short
    rms = float(np.sqrt(np.mean(x**2))) if x.size else 0.0
    if rms <= 0:
        return -70.0
    # not true LUFS; labeled as estimate downstream
    return 20.0 * math.log10(rms) - 0.691  # k-weight rough offset


def _bit_depth_from_subtype(subtype: str) -> int | None:
    s = (subtype or "").upper()
    if "PCM_16" in s or s == "PCM_16":
        return 16
    if "PCM_24" in s or s == "PCM_24":
        return 24
    if "PCM_32" in s or s == "PCM_32":
        return 32
    if "FLOAT" in s:
        return 32
    if "DOUBLE" in s:
        return 64
    if "PCM_U8" in s or "PCM_S8" in s:
        return 8
    return None


def load_audio(path: Path | str) -> tuple[np.ndarray, int, str]:
    """Load wav; returns (data float, sr, subtype). data shape (n,) or (n, ch)."""
    path = Path(path)
    data, sr = sf.read(str(path), always_2d=False)
    info = sf.info(str(path))
    subtype = getattr(info, "subtype", "") or ""
    return np.asarray(data, dtype=np.float64), int(sr), subtype


def analyze_file(path: Path | str) -> AudioMetrics:
    path = Path(path)
    try:
        data, sr, subtype = load_audio(path)
    except Exception as e:
        return AudioMetrics(
            path=str(path),
            duration_s=0.0,
            sample_rate=0,
            channels=0,
            bit_depth=None,
            peak_dbfs=float("nan"),
            integrated_lufs=None,
            clip_samples=0,
            clip_run_max=0,
            dc_offset=0.0,
            leading_silence_ms=0.0,
            trailing_silence_ms=0.0,
            errors=[f"scan_error:{e}"],
        )

    if data.ndim == 1:
        channels = 1
        mono = data
    else:
        channels = int(data.shape[1])
        mono = _to_float_mono(data)

    duration_s = float(len(mono) / sr) if sr else 0.0
    peak = _peak_dbfs(mono)
    clip_n, clip_run = _clipping_stats(mono)
    dc = float(np.mean(mono)) if mono.size else 0.0
    lead, trail = _silence_edges_ms(mono, sr)
    onsets = _onsets(mono, sr)
    seam = _loop_seam_delta(mono, sr)
    corr = _stereo_corr(data) if data.ndim == 2 else None
    lufs = _integrated_lufs(mono, sr)
    bd = _bit_depth_from_subtype(subtype)

    m = AudioMetrics(
        path=str(path.resolve()),
        duration_s=duration_s,
        sample_rate=sr,
        channels=channels,
        bit_depth=bd,
        peak_dbfs=peak,
        integrated_lufs=lufs,
        clip_samples=clip_n,
        clip_run_max=clip_run,
        dc_offset=dc,
        leading_silence_ms=lead,
        trailing_silence_ms=trail,
        onset_times_s=onsets,
        onset_count=len(onsets),
        loop_seam_delta=seam,
        stereo_correlation=corr,
        subtype=subtype,
    )
    return m


def load_profiles(toml_path: Path | str | None = None) -> dict[str, dict[str, Any]]:
    import tomllib

    if toml_path is None:
        toml_path = Path(__file__).resolve().parents[1] / "checks.toml"
    with open(toml_path, "rb") as f:
        raw = tomllib.load(f)
    return dict(raw.get("profiles", {}))


def evaluate_profile(
    metrics: AudioMetrics, profile: dict[str, Any]
) -> tuple[bool, list[str]]:
    """Return (pass, failed_check_names)."""
    fails: list[str] = []
    if metrics.errors and any(e.startswith("scan_error") for e in metrics.errors):
        return False, ["scan_error"]

    def check(name: str, cond: bool) -> None:
        if not cond:
            fails.append(name)

    d = metrics.duration_s
    check("min_duration_s", d >= float(profile.get("min_duration_s", 0)))
    check("max_duration_s", d <= float(profile.get("max_duration_s", 1e9)))
    check("min_sample_rate", metrics.sample_rate >= int(profile.get("min_sample_rate", 0)))
    check("max_peak_dbfs", metrics.peak_dbfs <= float(profile.get("max_peak_dbfs", 0.0)))
    check("min_peak_dbfs", metrics.peak_dbfs >= float(profile.get("min_peak_dbfs", -120)))
    check(
        "clipping",
        metrics.clip_samples <= int(profile.get("max_clip_samples", 0)),
    )
    check("dc_offset", abs(metrics.dc_offset) <= float(profile.get("max_dc_offset", 1.0)))
    check(
        "leading_silence_ms",
        metrics.leading_silence_ms <= float(profile.get("max_leading_silence_ms", 1e9)),
    )
    check(
        "trailing_silence_ms",
        metrics.trailing_silence_ms <= float(profile.get("max_trailing_silence_ms", 1e9)),
    )
    check(
        "loop_seam_delta",
        metrics.loop_seam_delta <= float(profile.get("max_loop_seam_delta", 1e9)),
    )
    if metrics.stereo_correlation is not None:
        check(
            "stereo_correlation",
            metrics.stereo_correlation
            >= float(profile.get("min_stereo_correlation", -1.0)),
        )
    if "min_onsets" in profile:
        check("min_onsets", metrics.onset_count >= int(profile["min_onsets"]))

    return len(fails) == 0, fails
