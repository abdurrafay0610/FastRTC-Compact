"""
Minimal, dependency-free log-mel feature extraction for the Smart Turn ONNX model.

Numerically equivalent to::

    from transformers import WhisperFeatureExtractor

    fe = WhisperFeatureExtractor(chunk_length=N)
    fe(
        audio,
        sampling_rate=16000,
        return_tensors="np",
        padding="max_length",
        max_length=N * 16000,
        truncation=True,
        do_normalize=True,
    ).input_features

but depends only on numpy, avoiding a ~100 MB `transformers` install for what is
a fixed mel filterbank and one STFT.
"""

from __future__ import annotations

import numpy as np

# --- Slaney mel scale (matches transformers' mel_scale="slaney") ---------------

_MIN_LOG_HZ = 1000.0
_MIN_LOG_MEL = 15.0


def _hz_to_mel(freq: np.ndarray) -> np.ndarray:
    freq = np.atleast_1d(np.asarray(freq, dtype=np.float64))
    mels = 3.0 * freq / 200.0
    logstep = 27.0 / np.log(6.4)
    log_region = freq >= _MIN_LOG_HZ
    mels[log_region] = _MIN_LOG_MEL + np.log(freq[log_region] / _MIN_LOG_HZ) * logstep
    return mels


def _mel_to_hz(mels: np.ndarray) -> np.ndarray:
    mels = np.atleast_1d(np.asarray(mels, dtype=np.float64))
    freq = 200.0 * mels / 3.0
    logstep = np.log(6.4) / 27.0
    log_region = mels >= _MIN_LOG_MEL
    freq[log_region] = _MIN_LOG_HZ * np.exp(logstep * (mels[log_region] - _MIN_LOG_MEL))
    return freq


def mel_filter_bank(
    num_frequency_bins: int,
    num_mel_filters: int,
    min_frequency: float,
    max_frequency: float,
    sampling_rate: int,
) -> np.ndarray:
    """Slaney-normalized triangular mel filterbank, shape (num_frequency_bins, num_mel_filters)."""
    mel_min = float(_hz_to_mel(min_frequency)[0])
    mel_max = float(_hz_to_mel(max_frequency)[0])
    mel_freqs = np.linspace(mel_min, mel_max, num_mel_filters + 2)
    filter_freqs = _mel_to_hz(mel_freqs)

    fft_freqs = np.linspace(0, sampling_rate // 2, num_frequency_bins)

    filter_diff = np.diff(filter_freqs)
    slopes = np.expand_dims(filter_freqs, 0) - np.expand_dims(fft_freqs, 1)
    down_slopes = -slopes[:, :-2] / filter_diff[:-1]
    up_slopes = slopes[:, 2:] / filter_diff[1:]
    filters = np.maximum(np.zeros(1), np.minimum(down_slopes, up_slopes))

    # Slaney normalization: constant energy per filter
    enorm = 2.0 / (filter_freqs[2 : num_mel_filters + 2] - filter_freqs[:num_mel_filters])
    filters *= np.expand_dims(enorm, 0)
    return filters


class WhisperFeatures:
    """Drop-in replacement for the single WhisperFeatureExtractor call Smart Turn makes."""

    def __init__(
        self,
        chunk_length: int = 8,
        feature_size: int = 80,
        sampling_rate: int = 16000,
        hop_length: int = 160,
        n_fft: int = 400,
        padding_value: float = 0.0,
    ):
        self.n_samples = chunk_length * sampling_rate
        self.hop_length = hop_length
        self.n_fft = n_fft
        self.padding_value = padding_value

        # periodic Hann, float64 to match transformers' internal promotion
        self.window = np.hanning(n_fft + 1)[:-1].astype(np.float64)

        self.mel_filters = mel_filter_bank(
            num_frequency_bins=1 + n_fft // 2,
            num_mel_filters=feature_size,
            min_frequency=0.0,
            max_frequency=sampling_rate / 2.0,
            sampling_rate=sampling_rate,
        )

    def __call__(self, audio: np.ndarray) -> np.ndarray:
        """audio: mono float32 at self.sampling_rate. Returns (1, n_mels, n_frames) float32."""
        audio = np.asarray(audio, dtype=np.float64).reshape(-1)

        # truncate / pad to exactly n_samples
        length = min(audio.shape[0], self.n_samples)
        padded = np.full(self.n_samples, self.padding_value, dtype=np.float64)
        padded[:length] = audio[:length]

        # zero-mean unit-variance over the *unpadded* region only
        segment = padded[:length]
        padded[:length] = (segment - segment.mean()) / np.sqrt(segment.var() + 1e-7)
        padded[length:] = self.padding_value

        features = self._log_mel(padded)
        return features[np.newaxis, :, :].astype(np.float32)

    def _log_mel(self, waveform: np.ndarray) -> np.ndarray:
        # center=True with reflect padding
        pad = self.n_fft // 2
        waveform = np.pad(waveform, (pad, pad), mode="reflect")

        frames = np.lib.stride_tricks.sliding_window_view(waveform, self.n_fft)[
            :: self.hop_length
        ]
        spec = np.fft.rfft(frames * self.window, n=self.n_fft, axis=-1).T
        magnitudes = np.abs(spec) ** 2.0

        mel_spec = np.maximum(1e-10, self.mel_filters.T @ magnitudes)
        log_spec = np.log10(mel_spec)[:, :-1]
        log_spec = np.maximum(log_spec, log_spec.max() - 8.0)
        return (log_spec + 4.0) / 4.0