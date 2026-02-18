"""
GK Healter – Test Suite: log_analyzer.py
"""

import pytest
from unittest.mock import patch, MagicMock
from gk_healter_tests.helpers import src_import

log_mod = src_import("log_analyzer")
LogAnalyzer = log_mod.LogAnalyzer


class TestGetErrorCount24h:
    @pytest.fixture
    def analyzer(self):
        return LogAnalyzer()

    def test_no_journalctl_returns_zero(self, analyzer):
        with patch("shutil.which", return_value=None):
            assert analyzer.get_error_count_24h() == 0

    def test_counts_lines(self, analyzer):
        mock_p1 = MagicMock()
        mock_p1.stdout = MagicMock()

        mock_p2 = MagicMock()
        mock_p2.communicate.return_value = ("42\n", "")
        mock_p2.returncode = 0

        def popen_side_effect(cmd, **kwargs):
            if cmd[0] == "journalctl":
                return mock_p1
            return mock_p2

        with patch("shutil.which", return_value="/usr/bin/journalctl"), \
             patch("subprocess.Popen", side_effect=popen_side_effect):
            result = analyzer.get_error_count_24h()
        assert result == 42

    def test_fallback_when_wc_missing(self, analyzer):
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "line1\nline2\nline3\n"

        def which_side(cmd):
            if cmd == "journalctl":
                return "/usr/bin/journalctl"
            return None  # wc not found

        with patch("shutil.which", side_effect=which_side), \
             patch("subprocess.run", return_value=mock_result):
            result = analyzer.get_error_count_24h()
        assert result == 3

    def test_exception_returns_zero(self, analyzer):
        with patch("shutil.which", return_value="/usr/bin/journalctl"), \
             patch("subprocess.Popen", side_effect=Exception("fail")):
            assert analyzer.get_error_count_24h() == 0


class TestGetRecentCriticalLogs:
    @pytest.fixture
    def analyzer(self):
        return LogAnalyzer()

    def test_no_journalctl(self, analyzer):
        with patch("shutil.which", return_value=None):
            result = analyzer.get_recent_critical_logs()
        assert result == ["Error: journalctl not found"]

    def test_returns_log_lines(self, analyzer):
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "critical error 1\ncritical error 2\n"
        with patch("shutil.which", return_value="/usr/bin/journalctl"), \
             patch("subprocess.run", return_value=mock_result):
            result = analyzer.get_recent_critical_logs(limit=5)
        assert len(result) == 2
        assert "critical error 1" in result[0]

    def test_exception_returns_error_message(self, analyzer):
        with patch("shutil.which", return_value="/usr/bin/journalctl"), \
             patch("subprocess.run", side_effect=Exception("timeout")):
            result = analyzer.get_recent_critical_logs()
        assert len(result) == 1
        assert "Error" in result[0]
