from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import TYPE_CHECKING, Optional

import click
import numpy as np
import soxr
from huggingface_hub import hf_hub_download

from .whisper_features import WhisperFeatures

if TYPE_CHECKING:
    import onnxruntime as ort


@lru_cache
def get_smart_turn_model(
    filename: str = "smart-turn-v3.2-cpu.onnx",
    threshold: float = 0.5,
) -> SmartTurnV3Detector:
    """Downloads (or reuses the cached) Smart Turn v3 ONNX model and returns a
    warmed-up detector. Weights: https://huggingface.co/pipecat-ai/smart-turn-v3
    (BSD-2-Clause)."""
    import importlib.util

    if importlib.util.find_spec("onnxruntime") is None:
        raise RuntimeError(
            "Install fastrtc-compact[smart-turn] to use Smart Turn detection"
        )
    path = hf_hub_download(repo_id="pipecat-ai/smart-turn-v3", filename=filename)
    detector = SmartTurnV3Detector(onnx_model_path=path, threshold=threshold)
    print(click.style("INFO", fg="green") + ":\t  Warming up Smart Turn model.")
    detector.warmup()
    print(click.style("INFO", fg="green") + ":\t  Smart Turn model warmed up.")
    return detector

@dataclass
class SmartTurnResult:
    is_complete: bool
    probability: float


class SmartTurnV3Detector:
    """
    Wrapper around Smart Turn v3/v3.x ONNX model.

    Usage:
        detector = SmartTurnV3Detector(
            onnx_model_path="smart-turn-v3.2.onnx",
            threshold=0.5,
        )

        result = detector.predict(audio, sample_rate=48000)

        if result.is_complete:
            ...
    """

    def __init__(
        self,
        onnx_model_path: str,
        threshold: float = 0.5,
        providers: Optional[list[str]] = None,
    ):

        try:
            import onnxruntime
        except ImportError as e:
            raise RuntimeError(
                "Smart Turn detection requires the onnxruntime package. "
                "Install fastrtc-compact[smart-turn]."
            ) from e

        self.onnx_model_path = onnx_model_path
        self.threshold = threshold



        # Value Fixed at 16k by the model: Smart Turn v3 consumes Whisper log-mel features,
        # which are defined at 16 kHz (400-sample window, 160-sample hop).
        # target_sample_rate is a parameter with exactly one valid value.
        self.max_audio_seconds =  8
        self.target_sample_rate = 16000

        self.feature_extractor = WhisperFeatures(chunk_length=self.max_audio_seconds)

        self.session = self._build_session(
            onnx_model_path=onnx_model_path,
            providers=providers,
        )

    @staticmethod
    def _build_session(
        onnx_model_path: str,
        providers: Optional[list[str]] = None,
    ) -> ort.InferenceSession:
        session_options = ort.SessionOptions()
        session_options.execution_mode = ort.ExecutionMode.ORT_SEQUENTIAL
        session_options.inter_op_num_threads = 1
        session_options.graph_optimization_level = (
            ort.GraphOptimizationLevel.ORT_ENABLE_ALL
        )

        return ort.InferenceSession(
            onnx_model_path,
            sess_options=session_options,
            providers=providers or ["CPUExecutionProvider"],
        )

    def predict(
        self,
        audio: np.ndarray,
        sample_rate: int,
    ) -> SmartTurnResult:
        """
        Returns:
            SmartTurnResult(
                is_complete=True/False,
                probability=probability_that_turn_is_complete,
            )

        Args:
            audio:
                Current user-turn audio. Can be int16 PCM or float audio.
                Shape can be:
                    (samples,)
                    (samples, channels)
                    (channels, samples)

            sample_rate:
                Sample rate of the given audio.
                WebRTC is often 48000 Hz.
                Smart Turn expects 16000 Hz.
        """

        if audio is None or audio.size == 0:
            return SmartTurnResult(is_complete=False, probability=0.0)

        audio = self._prepare_audio(audio, sample_rate)

        input_features = self.feature_extractor(audio)  # already (1, 80, 800) float32

        outputs = self.session.run(
            None,
            {"input_features": input_features},
        )

        probability = float(outputs[0][0].item())
        is_complete = probability > self.threshold

        return SmartTurnResult(
            is_complete=is_complete,
            probability=probability,
        )

    def is_complete(
        self,
        audio: np.ndarray,
        sample_rate: int,
    ) -> bool:
        """
        Convenience method if you only want True/False.
        """
        return self.predict(audio, sample_rate).is_complete

    def _prepare_audio(
        self,
        audio: np.ndarray,
        sample_rate: int,
    ) -> np.ndarray:
        """
        Converts input audio to:
            - mono
            - float32
            - range roughly [-1.0, 1.0]
            - 16 kHz
            - last <= 8 seconds
        """

        if sample_rate <= 0:
            raise ValueError("sample_rate must be greater than 0")

        audio = np.asarray(audio)

        audio = self._to_mono(audio)
        audio = self._to_float32(audio)

        if sample_rate != self.target_sample_rate:
            audio = self._resample_audio(
                audio,
                orig_sr=sample_rate,
                target_sr=self.target_sample_rate,
            )

        audio = self._crop_to_last_n_seconds(audio)

        return audio.astype(np.float32, copy=False)

    @staticmethod
    def _to_mono(audio: np.ndarray) -> np.ndarray:
        """
        Handles:
            (samples,)
            (samples, channels)
            (channels, samples)

        For FastRTC / WebRTC, you will usually already have mono audio.
        """

        if audio.ndim == 1:
            return audio

        if audio.ndim != 2:
            raise ValueError(f"Expected 1D or 2D audio, got shape={audio.shape}")

        # Common shape: (samples, channels)
        if audio.shape[1] in (1, 2):
            return audio.mean(axis=1)

        # Less common shape: (channels, samples)
        if audio.shape[0] in (1, 2):
            return audio.mean(axis=0)

        raise ValueError(f"Could not infer audio channel axis from shape={audio.shape}")

    @staticmethod
    def _to_float32(audio: np.ndarray) -> np.ndarray:
        """
        Converts int PCM or float audio to float32.
        """

        if audio.dtype == np.int16:
            return audio.astype(np.float32) / 32768.0

        if audio.dtype == np.int32:
            return audio.astype(np.float32) / 2147483648.0

        audio = audio.astype(np.float32, copy=False)

        max_abs = np.max(np.abs(audio)) if audio.size else 0.0

        # If float audio is already normalized, leave it.
        # If it looks like raw PCM values, normalize it.
        if max_abs > 1.0:
            audio = audio / max_abs

        return audio

    @staticmethod
    def _resample_audio(
            audio: np.ndarray,
            orig_sr: int,
            target_sr: int,
    ) -> np.ndarray:
        """
        Resamples audio using python-soxr.
        Input should already be mono float32.
        """

        return soxr.resample(
            audio,
            in_rate=orig_sr,
            out_rate=target_sr,
            quality="HQ",
        ).astype(np.float32, copy=False)

    def _crop_to_last_n_seconds(
        self,
        audio: np.ndarray,
    ) -> np.ndarray:
        """
        If audio is longer than max_audio_seconds, keep only the last N seconds.
        """

        max_samples = self.feature_extractor.n_samples

        if len(audio) > max_samples:
            return audio[-max_samples:]

        return audio

    def warmup(self) -> None:
        """Runs dummy inferences so first-run allocations happen before real audio."""
        dummy = np.zeros(16000, dtype=np.float32)
        for _ in range(3):
            self.predict(dummy, sample_rate=16000)