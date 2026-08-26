"""Guards against hallucinated or empty output from short/silent recordings.

mlx_whisper.transcribe() can return confidently-worded hallucinations ("Thank you.") on
near-silent audio -- its own no_speech_prob/avg_logprob skip logic doesn't catch all of
these. This applies stricter, tunable thresholds before accepting a result.
"""

from dataclasses import dataclass

import numpy as np

from local_dictation import config

SAMPLE_RATE = 16_000


@dataclass(frozen=True)
class CaptureMetrics:
    """Content-free measurements that explain capture and filter outcomes."""

    sample_count: int
    duration_seconds: float
    rms: float


@dataclass(frozen=True)
class FilterDecision:
    """A transcription acceptance decision without retaining any transcribed text."""

    text: str | None
    rejection_reason: str | None
    metrics: CaptureMetrics
    segment_count: int
    accepted_segment_count: int


def capture_metrics(audio: np.ndarray) -> CaptureMetrics:
    """Return content-free capture metrics for logging and filter decisions."""
    sample_count = int(audio.size)
    duration_seconds = sample_count / SAMPLE_RATE
    rms = float(np.sqrt(np.mean(np.square(audio)))) if sample_count else 0.0
    return CaptureMetrics(sample_count, duration_seconds, rms)


def capture_rejection_reason(metrics: CaptureMetrics) -> str | None:
    """Return a stable reason code when capture alone cannot be transcribed."""
    if metrics.sample_count == 0:
        return "empty_capture"
    if metrics.duration_seconds < config.MIN_RECORDING_SECONDS:
        return "too_short"
    if metrics.rms < config.RMS_SILENCE_THRESHOLD:
        return "too_quiet"
    return None


def clip_is_too_quiet_or_short(audio: np.ndarray) -> bool:
    """Cheap pre-transcription gate: duration and RMS energy."""
    return capture_rejection_reason(capture_metrics(audio)) is not None


def _worst_case_signals(result: dict) -> tuple[float, float, float]:
    """Aggregate per-segment confidence signals to their most-hallucination-prone values."""
    segments = result.get("segments") or []
    if not segments:
        # No segments at all is itself a strong no-speech signal.
        return 1.0, -999.0, 0.0
    no_speech_prob = max(seg.get("no_speech_prob", 0.0) for seg in segments)
    avg_logprob = min(seg.get("avg_logprob", 0.0) for seg in segments)
    compression_ratio = max(seg.get("compression_ratio", 0.0) for seg in segments)
    return no_speech_prob, avg_logprob, compression_ratio


def result_is_hallucination(result: dict) -> bool:
    """Stricter confidence check than Whisper's own internal skip logic (see design.md)."""
    no_speech_prob, avg_logprob, compression_ratio = _worst_case_signals(result)
    if no_speech_prob > config.NO_SPEECH_PROB_THRESHOLD and avg_logprob < config.AVG_LOGPROB_THRESHOLD:
        return True
    if compression_ratio > config.COMPRESSION_RATIO_THRESHOLD:
        return True
    return False


def accept(audio: np.ndarray, result: dict) -> bool:
    """True if this clip's transcription should be used; False if it should be discarded."""
    if clip_is_too_quiet_or_short(audio):
        return False
    text = result.get("text", "").strip()
    if not text:
        return False
    if result_is_hallucination(result):
        return False
    return True


def accepted_text(audio: np.ndarray, result: dict) -> str | None:
    """Return usable text, dropping only low-confidence result segments.

    Whisper already divides long input into segments.  Treating their worst confidence as
    the confidence of the whole recording loses otherwise valid long dictations.
    """
    return evaluate_transcription(audio, result).text


def evaluate_transcription(audio: np.ndarray, result: dict) -> FilterDecision:
    """Explain whether a transcription is usable without exposing its text in diagnostics."""
    metrics = capture_metrics(audio)
    capture_reason = capture_rejection_reason(metrics)
    segments = result.get("segments") or []
    if capture_reason is not None:
        return FilterDecision(None, capture_reason, metrics, len(segments), 0)
    if not segments:
        return FilterDecision(None, "no_segments", metrics, 0, 0)

    accepted_segments = []
    for segment in segments:
        if not segment.get("text", "").strip():
            continue
        if result_is_hallucination({"segments": [segment]}):
            continue
        accepted_segments.append(segment["text"].strip())
    text = " ".join(accepted_segments).strip()
    return FilterDecision(
        text or None,
        None if text else "all_segments_filtered",
        metrics,
        len(segments),
        len(accepted_segments),
    )
