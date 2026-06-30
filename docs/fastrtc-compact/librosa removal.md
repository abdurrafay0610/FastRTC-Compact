# librosa & numba removal — fastrtc-compact

Companion to `gradio removal.md`. This change removes the **librosa** dependency —
and, with it, **numba** and **llvmlite** — from `fastrtc-compact`. librosa was used
for one thing only, audio resampling, which is now done with **soxr**.

Forked at FastRTC **v0.0.34**.

---

## Why

librosa appeared in the codebase in exactly one form — `librosa.resample` — but it is
an expensive dependency. It pulls a large transitive closure (numba → llvmlite, scipy,
scikit-learn) of roughly **400 MB installed**, of which llvmlite alone is **162 MB**.
The first `librosa.resample` call also triggers a one-time numba JIT compilation of
~14 s; because the VAD warmup feeds 24 kHz audio (≠ 16 kHz), that cost was being paid
on every boot during warmup.

`numba>=0.60.0` was a dependency only because librosa needs a compatible numba —
nothing in the package uses numba directly — so removing librosa removes numba and
llvmlite as well, with no other code changes.

**soxr** (the SoX Resampler library) is the same high-quality resampler librosa uses
under its default `soxr_hq` setting, but implemented in C with no numba/JIT. It does
exactly one job — resampling — in **536 KB**, has no heavy transitive dependencies,
and its first call is milliseconds instead of ~14 s.

**Net footprint:** −~400 MB (librosa, numba, llvmlite, scipy, scikit-learn) / +536 KB
(soxr).

---

## Removed — librosa / numba (resampling → soxr)

The package no longer requires or imports librosa or numba.

### `pyproject.toml`

- Dropped `librosa` and `numba>=0.60.0` from `dependencies`.
- Added `soxr` to `dependencies`. It is a **core** dependency, not an extra, because
  `utils.py` resamples on the audio output path, outside any optional feature.

### Resampler call sites

Every `librosa.resample(y, orig_sr=…, target_sr=…)` call was replaced with
`soxr.resample(x, in_rate, out_rate)`. soxr takes its rates **positionally**
(`in_rate, out_rate`), so the order matters where librosa's keywords made it implicit.
Audio is still converted to `float32` before resampling (ordering unchanged), and soxr
returns `float32`. soxr's default quality is `HQ`, equivalent to librosa's `soxr_hq`,
so output is unchanged for these mono resamples.

- **`backend/fastrtc/utils.py`** — top-level `import librosa` → `import soxr`. In
  `player_worker_decode` (the core audio output path):
  `librosa.resample(audio_array, target_sr=first_sample_rate, orig_sr=sample_rate)`
  → `soxr.resample(audio_array, sample_rate, first_sample_rate)`.
  The original wrote its keywords in reverse order (`target_sr` first), so the
  positional arguments are `(sample_rate, first_sample_rate)` — resampling *from* the
  chunk's rate *to* the stream's established rate. The frame is tagged
  `first_sample_rate` immediately afterward, confirming the direction.

- **`backend/fastrtc/websocket.py`** — top-level `import librosa` → `import soxr`. Two
  call sites, both on the telephone / μ-law path:
  - `convert_to_mulaw` (outbound):
    `librosa.resample(audio_data, orig_sr=original_rate, target_sr=target_rate)`
    → `soxr.resample(audio_data, original_rate, target_rate)`.
  - `handle_websocket`, inbound `media` event (phone audio in):
    `librosa.resample(audio_array, orig_sr=8000, target_sr=input_sample_rate)`
    → `soxr.resample(audio_array, 8000, input_sample_rate)`.

- **`backend/fastrtc/speech_to_text/stt_.py`** — top-level `import librosa` →
  `import soxr`. In `MoonshineSTT.stt`:
  `librosa.resample(audio_np, orig_sr=sr, target_sr=16000)`
  → `soxr.resample(audio_np, sr, 16000)`.

- **`backend/fastrtc/pause_detection/silero.py`** — lazy `import librosa` (inside
  `vad()`) → `import soxr`. In `vad()`:
  `librosa.resample(audio_, orig_sr=sampling_rate, target_sr=sr)`
  → `soxr.resample(audio_, sampling_rate, sr)` (`sr` is 16000). The guarding
  `ImportError` message now references soxr instead of librosa.

- **`backend/fastrtc/reply_on_stopwords.py`** — lazy `import librosa` (inside the
  stop-word detect handler) → `import soxr`:
  `librosa.resample(audio_f32, orig_sr=sampling_rate, target_sr=16000)`
  → `soxr.resample(audio_f32, sampling_rate, 16000)`.

---

## Notes

- librosa was used **only** for `librosa.resample` — no `load`, `stft`, or feature
  extraction — so resampling was the entire surface to replace.
- **numba is never used directly** in the package; it was purely a transitive
  dependency of librosa, so it (and llvmlite) leave the install closure automatically.
- The other resampler already in the tree, `av.AudioResampler` (PyAV), is left
  unchanged. PyAV is a core aiortc dependency and is used in `tracks.py` and
  immediately after the soxr call in `player_worker_decode`; consolidating the two
  resamplers onto PyAV is possible but out of scope for this change.