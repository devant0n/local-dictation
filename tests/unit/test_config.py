"""Tests for idle-unload configuration."""

import importlib
import logging
import logging.handlers
import sys

import pytest

from local_dictation import config


def test_idle_timeout_configured():
    """IDLE_TIMEOUT_MINUTES should be configured."""
    assert hasattr(config, 'IDLE_TIMEOUT_MINUTES')


def test_idle_timeout_is_positive():
    """IDLE_TIMEOUT_MINUTES should be a positive number or zero."""
    assert isinstance(config.IDLE_TIMEOUT_MINUTES, int)
    assert config.IDLE_TIMEOUT_MINUTES >= 0


def test_default_idle_timeout_reasonable():
    """Default idle timeout should be reasonable (between 1-60 minutes)."""
    if config.IDLE_TIMEOUT_MINUTES > 0:
        assert config.IDLE_TIMEOUT_MINUTES <= 60


def test_idle_timeout_default_is_10_minutes():
    """Default idle timeout should be 10 minutes."""
    assert config.IDLE_TIMEOUT_MINUTES == 10


def test_model_is_configured():
    """MODEL should be configured."""
    assert hasattr(config, 'MODEL')
    assert isinstance(config.MODEL, str)
    assert len(config.MODEL) > 0


@pytest.fixture
def reloaded_config(tmp_path, monkeypatch):
    """Reload config with LOCAL_DICTATION_LOG_DIR pointed at a scratch dir, restoring
    the root logger's original handlers afterward so this doesn't leak into other tests."""
    monkeypatch.setenv("LOCAL_DICTATION_LOG_DIR", str(tmp_path))
    original_handlers = logging.getLogger().handlers[:]
    try:
        yield importlib.reload(config)
    finally:
        for handler in logging.getLogger().handlers[:]:
            if handler not in original_handlers:
                handler.close()
        logging.getLogger().handlers = original_handlers


def test_log_level_defaults_to_info(reloaded_config, monkeypatch):
    """LOG_LEVEL should default to INFO when LOCAL_DICTATION_LOG_LEVEL is unset."""
    monkeypatch.delenv("LOCAL_DICTATION_LOG_LEVEL", raising=False)
    reloaded = importlib.reload(reloaded_config)
    assert reloaded.LOG_LEVEL == logging.INFO


def test_log_level_reads_env_override(reloaded_config, monkeypatch):
    """LOCAL_DICTATION_LOG_LEVEL should set LOG_LEVEL (case-insensitive)."""
    monkeypatch.setenv("LOCAL_DICTATION_LOG_LEVEL", "debug")
    reloaded = importlib.reload(reloaded_config)
    assert reloaded.LOG_LEVEL == logging.DEBUG


def test_log_level_invalid_value_falls_back_to_info(reloaded_config, monkeypatch):
    """An unrecognized LOCAL_DICTATION_LOG_LEVEL should not raise; it falls back to INFO."""
    monkeypatch.setenv("LOCAL_DICTATION_LOG_LEVEL", "not-a-level")
    reloaded = importlib.reload(reloaded_config)
    assert reloaded.LOG_LEVEL == logging.INFO


def test_root_logger_has_exactly_one_file_and_one_stream_handler(reloaded_config):
    """Reconfiguring (e.g. via repeated import) must not accumulate duplicate handlers."""
    importlib.reload(reloaded_config)
    importlib.reload(reloaded_config)  # reload twice to exercise the reentry guard

    handlers = logging.getLogger().handlers
    file_handlers = [h for h in handlers if isinstance(h, logging.FileHandler)]
    stream_handlers = [
        h for h in handlers
        if type(h) is logging.StreamHandler  # noqa: E721 (FileHandler subclasses StreamHandler)
    ]
    assert len(file_handlers) == 1
    assert len(stream_handlers) == 1


def test_file_diagnostics_rotate_at_bounded_size(reloaded_config):
    file_handlers = [
        handler
        for handler in logging.getLogger().handlers
        if isinstance(handler, logging.handlers.RotatingFileHandler)
    ]
    assert len(file_handlers) == 1
    assert reloaded_config.LOG_MAX_BYTES == 1 * 1024 * 1024
    assert reloaded_config.LOG_BACKUP_COUNT == 2
    assert file_handlers[0].maxBytes == reloaded_config.LOG_MAX_BYTES
    assert file_handlers[0].backupCount == reloaded_config.LOG_BACKUP_COUNT


def test_console_handler_targets_stderr_not_stdout(reloaded_config):
    """Console logging must stay off stdout so CLI output (the transcription) stays pipeable."""
    stream_handlers = [
        h for h in logging.getLogger().handlers
        if type(h) is logging.StreamHandler  # noqa: E721
    ]
    assert len(stream_handlers) == 1
    assert stream_handlers[0].stream is sys.stderr
    assert stream_handlers[0].stream is not sys.stdout
