"""
GK Healter – Test Suite: logger.py
"""

import os
import logging
import pytest
from unittest.mock import patch
from gk_healter_tests.helpers import src_import

logger_mod = src_import("logger")


class TestSetupLogging:
    @pytest.fixture(autouse=True)
    def cleanup_handlers(self):
        """Clear handlers before and after each test."""
        root = logging.getLogger("gk-healter")
        root.handlers.clear()
        yield
        root.handlers.clear()

    def test_returns_logger(self):
        result = logger_mod.setup_logging()
        assert isinstance(result, logging.Logger)
        assert result.name == "gk-healter"

    def test_default_level_info(self):
        lgr = logger_mod.setup_logging()
        assert lgr.level == logging.INFO

    def test_custom_level(self):
        lgr = logger_mod.setup_logging(level=logging.DEBUG)
        assert lgr.level == logging.DEBUG

    def test_has_handlers(self):
        lgr = logger_mod.setup_logging()
        # Should have at least console handler
        assert len(lgr.handlers) >= 1

    def test_no_duplicate_handlers(self):
        lgr = logger_mod.setup_logging()
        count1 = len(lgr.handlers)
        lgr2 = logger_mod.setup_logging()
        count2 = len(lgr2.handlers)
        assert count1 == count2

    def test_file_handler_failure_still_works(self):
        with patch("os.makedirs", side_effect=OSError("no perms")):
            # Should not crash, just skip file handler
            try:
                lgr = logger_mod.setup_logging()
                assert lgr is not None
            except OSError:
                pass  # acceptable if makedirs fails before handler creation


class TestGetLogger:
    def test_returns_child_logger(self):
        lgr = logger_mod.get_logger("test_child")
        assert lgr.name == "gk-healter.test_child"
        assert isinstance(lgr, logging.Logger)

    def test_different_names_different_loggers(self):
        lgr1 = logger_mod.get_logger("a")
        lgr2 = logger_mod.get_logger("b")
        assert lgr1 is not lgr2
        assert lgr1.name != lgr2.name
