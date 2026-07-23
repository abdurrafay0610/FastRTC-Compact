from dataclasses import dataclass
from typing import Optional

import numpy as np
import onnxruntime as ort
from transformers import WhisperFeatureExtractor
import soxr


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
        target_sample_rate: int = 16000,
        max_audio_seconds: float = 8.0,
        providers: Optional[list[str]] = None,
    ):
        self.onnx_model_path = onnx_model_path
        self.threshold = threshold
        self.target_sample_rate = target_sample_rate
        self.max_audio_seconds = max_audio_seconds

        self.feature_extractor = WhisperFeatureExtractor(
            chunk_length=int(max_audio_seconds)
        )

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

        inputs = self.feature_extractor(
            audio,
            sampling_rate=self.target_sample_rate,
            return_tensors="np",
            padding="max_length",
            max_length=int(self.max_audio_seconds * self.target_sample_rate),
            truncation=True,
            do_normalize=True,
        )

        input_features = inputs.input_features.squeeze(0).astype(np.float32)
        input_features = np.expand_dims(input_features, axis=0)

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

        max_samples = int(self.max_audio_seconds * self.target_sample_rate)

        if len(audio) > max_samples:
            return audio[-max_samples:]

        return audio