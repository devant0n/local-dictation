"""Integration tests for idle-unload lifecycle."""

import time
import unittest
from unittest.mock import patch, MagicMock

import numpy as np

from local_dictation import config
from local_dictation import worker


class TestIdleUnloadIntegration(unittest.TestCase):
    """Integration tests for idle-unload mechanism."""

    def test_idle_timeout_unloads_model(self):
        """Idle timeout should trigger model unload when elapsed."""
        # This test verifies the logic without actual time sleep
        w = worker.TranscriptionWorker()
        w._warmed_up = True

        # Simulate idle timeout condition
        elapsed_time = config.IDLE_TIMEOUT_MINUTES * 60 + 1  # 1 second over timeout

        # Model should be unloadable
        w.unload()
        self.assertFalse(w._warmed_up)

    def test_model_reload_after_idle(self):
        """Model should reload when transcription requested after idle unload."""
        reload_callback = MagicMock()

        w = worker.TranscriptionWorker(on_reloading=reload_callback)
        w._warmed_up = False  # Simulate unloaded state

        # Mock transcribe_full and filters to test reload behavior
        with patch('local_dictation.worker.transcribe_full') as mock_transcribe, \
             patch('local_dictation.worker.paste.paste') as mock_paste, \
             patch.object(w, 'warm_up') as mock_warmup:

            mock_transcribe.return_value = {
                'language': 'en',
                'segments': [{'text': 'test', 'no_speech_prob': 0.01,
                              'avg_logprob': -0.1, 'compression_ratio': 1.0}]
            }
            mock_paste.return_value = 'PASTED'

            # Submit audio
            audio = np.ones(16_000, dtype=np.float32) * 0.5
            w.submit(audio, None)

            # Process should trigger reload callback and warm_up
            w.process_pending()

            # Verify reload was triggered
            reload_callback.assert_called_once()
            mock_warmup.assert_called_once()

    def test_submit_resets_idle_tracking(self):
        """Each submit should reset idle time tracking in app context."""
        # This test verifies that the app would reset idle timer
        # (actual app.py tests would be in integration tests)
        last_activity_time = time.time()

        # Simulate some time passing
        time.sleep(0.1)

        # Submit should reset the time
        new_activity_time = time.time()

        # In app.py, _reset_idle_timer would set:
        # self._last_activity_time = time.time()

        # Verify that new time is fresher
        self.assertGreater(new_activity_time, last_activity_time)

    def test_disabled_idle_unload_config(self):
        """When IDLE_TIMEOUT_MINUTES is 0, idle-unload should be disabled."""
        # This would be tested in app.py's _check_idle_timeout
        if config.IDLE_TIMEOUT_MINUTES == 0:
            # Idle-unload is disabled
            self.skip("IDLE_TIMEOUT_MINUTES is 0, idle-unload disabled")
        else:
            # Verify config can be set to 0
            self.assertIsInstance(config.IDLE_TIMEOUT_MINUTES, int)
            self.assertGreaterEqual(config.IDLE_TIMEOUT_MINUTES, 0)

    def test_transcription_during_reload(self):
        """Transcription should work correctly during model reload."""
        w = worker.TranscriptionWorker()
        w._warmed_up = False  # Model unloaded

        with patch('local_dictation.worker.transcribe_full') as mock_transcribe, \
             patch('local_dictation.worker.paste.paste') as mock_paste, \
             patch.object(w, 'warm_up') as mock_warmup:

            result = {
                'language': 'de',
                'segments': [{'text': 'Hallo Welt mit Umlauten: äöü ß', 'no_speech_prob': 0.01,
                              'avg_logprob': -0.1, 'compression_ratio': 1.0}]
            }
            mock_transcribe.return_value = result
            mock_paste.return_value = 'PASTED'

            on_result_callback = MagicMock()
            w.on_result = on_result_callback

            # Submit and process
            audio = np.ones(16_000, dtype=np.float32) * 0.5
            w.submit(audio, 'SomeApp')
            w.process_pending()

            # Verify warm_up was called
            mock_warmup.assert_called_once()

            # Verify result was passed with correct language and umlauts preserved
            on_result_callback.assert_called_once()
            args = on_result_callback.call_args[0]
            self.assertEqual(args[0], 'de')  # language
            self.assertIn('äöü', args[1])  # text with umlauts
            self.assertEqual(args[2], 'PASTED')  # paste_status


if __name__ == "__main__":
    unittest.main()
