"""Unit tests for filters.py (hallucination and silence detection)."""

import numpy as np
import pytest

from local_dictation.core import filters


class TestClipIsTooQuietOrShort:
    """Test silence and duration detection."""

    def test_empty_audio_is_rejected(self):
        """Empty audio should be rejected."""
        audio = np.array([], dtype=np.float32)
        assert filters.clip_is_too_quiet_or_short(audio)

    def test_very_short_clip_is_rejected(self):
        """Clip shorter than MIN_RECORDING_SECONDS should be rejected."""
        # Create a 0.1 second clip at 16kHz (default is 0.3s minimum)
        samples = int(16_000 * 0.1)
        audio = np.ones(samples, dtype=np.float32) * 0.1  # Low amplitude
        assert filters.clip_is_too_quiet_or_short(audio)

    def test_silent_clip_is_rejected(self):
        """Silent (near-zero amplitude) clip should be rejected."""
        # Create a 1 second clip but with amplitude below threshold
        samples = int(16_000 * 1.0)
        audio = np.ones(samples, dtype=np.float32) * 0.001  # Very quiet
        assert filters.clip_is_too_quiet_or_short(audio)

    def test_long_loud_clip_is_accepted(self):
        """Long clip with high amplitude should pass the gate."""
        # Create a 2 second clip with good amplitude
        samples = int(16_000 * 2.0)
        audio = np.ones(samples, dtype=np.float32) * 0.5  # Moderate amplitude
        assert not filters.clip_is_too_quiet_or_short(audio)

    def test_minimum_duration_boundary(self):
        """Test the boundary at MIN_RECORDING_SECONDS."""
        # Just above minimum (should pass)
        samples = int(16_000 * 0.35)
        audio = np.ones(samples, dtype=np.float32) * 0.5
        assert not filters.clip_is_too_quiet_or_short(audio)


class TestWorstCaseSignals:
    """Test per-segment confidence aggregation."""

    def test_empty_segments_returns_worst_case(self):
        """Empty segments list should return worst-case scores."""
        result = {"segments": []}
        no_speech_prob, avg_logprob, compression_ratio = filters._worst_case_signals(result)
        assert no_speech_prob == 1.0  # 100% chance of no speech
        assert avg_logprob == -999.0  # Very bad confidence
        assert compression_ratio == 0.0

    def test_no_segments_key_returns_worst_case(self):
        """Missing 'segments' key should return worst-case scores."""
        result = {"text": "hello"}
        no_speech_prob, avg_logprob, compression_ratio = filters._worst_case_signals(result)
        assert no_speech_prob == 1.0

    def test_single_segment_returns_its_values(self):
        """Single segment should return its own values."""
        result = {
            "segments": [
                {
                    "no_speech_prob": 0.1,
                    "avg_logprob": -0.5,
                    "compression_ratio": 1.2,
                }
            ]
        }
        no_speech_prob, avg_logprob, compression_ratio = filters._worst_case_signals(result)
        assert no_speech_prob == 0.1
        assert avg_logprob == -0.5
        assert compression_ratio == 1.2

    def test_multiple_segments_returns_worst_values(self):
        """Multiple segments should return aggregated worst values."""
        result = {
            "segments": [
                {
                    "no_speech_prob": 0.2,
                    "avg_logprob": -0.3,
                    "compression_ratio": 1.5,
                },
                {
                    "no_speech_prob": 0.5,  # Highest
                    "avg_logprob": -0.8,  # Lowest
                    "compression_ratio": 1.2,  # Lower
                },
                {
                    "no_speech_prob": 0.3,
                    "avg_logprob": -0.4,
                    "compression_ratio": 1.8,  # Highest
                },
            ]
        }
        no_speech_prob, avg_logprob, compression_ratio = filters._worst_case_signals(result)
        assert no_speech_prob == 0.5  # Max
        assert avg_logprob == -0.8  # Min
        assert compression_ratio == 1.8  # Max


class TestResultIsHallucination:
    """Test hallucination detection."""

    def test_confident_result_is_not_hallucination(self):
        """Good confidence scores should not be flagged as hallucination."""
        result = {
            "text": "hello world",
            "segments": [
                {
                    "no_speech_prob": 0.01,  # Low
                    "avg_logprob": -0.1,  # High (closer to 0)
                    "compression_ratio": 1.0,  # Low
                }
            ],
        }
        assert not filters.result_is_hallucination(result)

    def test_high_no_speech_prob_and_low_logprob_is_hallucination(self):
        """High no_speech_prob AND low avg_logprob should be flagged."""
        result = {
            "text": "thank you",
            "segments": [
                {
                    "no_speech_prob": 0.8,  # High (above threshold)
                    "avg_logprob": -2.0,  # Low (below threshold)
                    "compression_ratio": 1.0,
                }
            ],
        }
        assert filters.result_is_hallucination(result)

    def test_high_compression_ratio_is_hallucination(self):
        """High compression ratio alone should be flagged as hallucination."""
        result = {
            "text": "hello hello hello hello hello",
            "segments": [
                {
                    "no_speech_prob": 0.01,  # Good
                    "avg_logprob": -0.1,  # Good
                    "compression_ratio": 3.0,  # Very high (above threshold)
                }
            ],
        }
        assert filters.result_is_hallucination(result)

    def test_empty_segments_is_hallucination(self):
        """Empty segments list indicates hallucination."""
        result = {"text": "", "segments": []}
        assert filters.result_is_hallucination(result)


class TestAccept:
    """Test the complete acceptance pipeline."""

    def test_empty_audio_rejected(self):
        """Empty audio should be rejected."""
        audio = np.array([], dtype=np.float32)
        result = {"text": "hello", "segments": []}
        assert not filters.accept(audio, result)


def test_accepted_text_keeps_good_long_segments():
    audio = np.ones(16_000 * 35, dtype=np.float32) * 0.5
    result = {"segments": [
        {"text": "first sentence", "no_speech_prob": 0.01, "avg_logprob": -0.1,
         "compression_ratio": 1.0},
        {"text": "hallucination", "no_speech_prob": 0.9, "avg_logprob": -2.0,
         "compression_ratio": 1.0},
        {"text": "last sentence", "no_speech_prob": 0.01, "avg_logprob": -0.1,
         "compression_ratio": 1.0},
    ]}
    assert filters.accepted_text(audio, result) == "first sentence last sentence"


@pytest.mark.parametrize(
    ("audio", "reason"),
    [
        (np.array([], dtype=np.float32), "empty_capture"),
        (np.ones(int(16_000 * 0.2), dtype=np.float32) * 0.5, "too_short"),
        (np.ones(16_000, dtype=np.float32) * 0.001, "too_quiet"),
    ],
)
def test_evaluate_transcription_explains_capture_rejections(audio, reason):
    decision = filters.evaluate_transcription(audio, {"segments": []})

    assert decision.text is None
    assert decision.rejection_reason == reason
    assert decision.metrics.sample_count == audio.size


def test_evaluate_transcription_explains_missing_or_filtered_segments():
    audio = np.ones(16_000, dtype=np.float32) * 0.5

    assert filters.evaluate_transcription(audio, {"segments": []}).rejection_reason == "no_segments"
    decision = filters.evaluate_transcription(audio, {"segments": [{"text": "", "no_speech_prob": 0.0}]})
    assert decision.rejection_reason == "all_segments_filtered"

    def test_silent_audio_rejected(self):
        """Silent audio should be rejected."""
        samples = int(16_000 * 1.0)
        audio = np.ones(samples, dtype=np.float32) * 0.001
        result = {"text": "hello", "segments": []}
        assert not filters.accept(audio, result)

    def test_empty_text_rejected(self):
        """Empty transcription should be rejected."""
        samples = int(16_000 * 1.0)
        audio = np.ones(samples, dtype=np.float32) * 0.5
        result = {"text": "", "segments": []}
        assert not filters.accept(audio, result)

    def test_whitespace_only_text_rejected(self):
        """Whitespace-only text should be rejected."""
        samples = int(16_000 * 1.0)
        audio = np.ones(samples, dtype=np.float32) * 0.5
        result = {"text": "   \n  ", "segments": []}
        assert not filters.accept(audio, result)

    def test_hallucinated_result_rejected(self):
        """Hallucinated results should be rejected."""
        samples = int(16_000 * 1.0)
        audio = np.ones(samples, dtype=np.float32) * 0.5
        result = {
            "text": "thank you",
            "segments": [
                {
                    "no_speech_prob": 0.8,
                    "avg_logprob": -2.0,
                    "compression_ratio": 1.0,
                }
            ],
        }
        assert not filters.accept(audio, result)

    def test_good_result_accepted(self):
        """High-quality results should be accepted."""
        samples = int(16_000 * 1.0)
        audio = np.ones(samples, dtype=np.float32) * 0.5
        result = {
            "text": "hello world",
            "segments": [
                {
                    "no_speech_prob": 0.01,
                    "avg_logprob": -0.1,
                    "compression_ratio": 1.0,
                }
            ],
        }
        assert filters.accept(audio, result)

    def test_missing_result_fields_uses_defaults(self):
        """Missing fields in result should be treated as worst-case."""
        samples = int(16_000 * 1.0)
        audio = np.ones(samples, dtype=np.float32) * 0.5
        result = {"text": "hello"}  # Missing segments
        # This should be rejected because missing segments triggers hallucination detection
        assert not filters.accept(audio, result)
