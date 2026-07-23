"""Waveform + mel spectrogram PNG for agent eyes."""

from __future__ import annotations

from pathlib import Path

import numpy as np

# non-interactive backend before pyplot import
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402


def _to_mono(data: np.ndarray) -> np.ndarray:
    x = np.asarray(data, dtype=np.float64)
    if x.ndim == 1:
        return x
    return x.mean(axis=1)


def render_waveform_mel_png(
    data: np.ndarray,
    sr: int,
    out_path: Path | str,
    title: str | None = None,
) -> Path:
    """Write a 2-panel PNG: waveform + mel spectrogram. Returns path."""
    out_path = Path(out_path)
    mono = _to_mono(data)
    t = np.arange(len(mono)) / float(sr) if sr else np.arange(len(mono))

    fig, axes = plt.subplots(2, 1, figsize=(10, 5), constrained_layout=True)
    axes[0].plot(t, mono, color="#1a1a2e", linewidth=0.6)
    axes[0].set_ylabel("amp")
    axes[0].set_xlabel("time (s)")
    axes[0].set_xlim(t[0] if len(t) else 0, t[-1] if len(t) else 1)
    axes[0].set_title(title or "waveform")

    # mel-ish spectrogram via STFT + mel filterbank (librosa if present, else log-STFT)
    try:
        import librosa
        import librosa.display

        S = librosa.feature.melspectrogram(
            y=mono.astype(np.float32), sr=sr, n_mels=64, fmax=min(sr // 2, 16000)
        )
        S_db = librosa.power_to_db(S, ref=np.max)
        img = axes[1].imshow(
            S_db,
            aspect="auto",
            origin="lower",
            extent=[0, t[-1] if len(t) else 1, 0, S_db.shape[0]],
            cmap="magma",
        )
        axes[1].set_ylabel("mel bin")
        fig.colorbar(img, ax=axes[1], format="%+2.0f dB")
    except Exception:
        # fallback: log magnitude STFT
        n_fft = 512
        hop = 128
        if len(mono) < n_fft:
            pad = np.zeros(n_fft)
            pad[: len(mono)] = mono
            mono = pad
        frames = 1 + (len(mono) - n_fft) // hop
        window = np.hanning(n_fft)
        spec = np.empty((n_fft // 2 + 1, max(1, frames)))
        for i in range(max(1, frames)):
            frame = mono[i * hop : i * hop + n_fft] * window
            if len(frame) < n_fft:
                frame = np.pad(frame, (0, n_fft - len(frame)))
            mag = np.abs(np.fft.rfft(frame))
            spec[:, i] = 20.0 * np.log10(mag + 1e-10)
        img = axes[1].imshow(
            spec,
            aspect="auto",
            origin="lower",
            extent=[0, t[-1] if len(t) else 1, 0, sr / 2 if sr else 1],
            cmap="magma",
        )
        axes[1].set_ylabel("Hz")
        fig.colorbar(img, ax=axes[1], format="%+2.0f dB")

    axes[1].set_xlabel("time (s)")
    axes[1].set_title("mel / log spectrogram")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(str(out_path), dpi=120)
    plt.close(fig)
    return out_path
