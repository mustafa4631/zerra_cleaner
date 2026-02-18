"""
GK Healter – Test Suite: disk_analyzer.py
"""

import pytest
from unittest.mock import patch, MagicMock
from gk_healter_tests.helpers import src_import

disk_mod = src_import("disk_analyzer")
DiskAnalyzer = disk_mod.DiskAnalyzer


class TestGetLargeFiles:
    @pytest.fixture
    def analyzer(self):
        return DiskAnalyzer()

    def test_no_find_returns_empty(self, analyzer):
        with patch("shutil.which", return_value=None):
            result = analyzer.get_large_files("/home")
        assert result == []

    def test_parses_output(self, analyzer):
        mock_p1 = MagicMock()
        mock_p1.stdout = MagicMock()
        mock_p2 = MagicMock()
        mock_p2.stdout = MagicMock()

        mock_p3 = MagicMock()
        mock_p3.communicate.return_value = (
            "524288000 /home/user/bigfile.iso\n"
            "209715200 /home/user/movie.mp4\n",
            "",
        )

        call_count = [0]

        def popen_side_effect(cmd, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                return mock_p1
            elif call_count[0] == 2:
                return mock_p2
            return mock_p3

        with patch("shutil.which", return_value="/usr/bin/find"), \
             patch("os.path.exists", return_value=True), \
             patch("subprocess.Popen", side_effect=popen_side_effect):
            result = analyzer.get_large_files("/home")
        assert len(result) == 2
        assert result[0]["raw_size"] == 524288000
        assert "/home/user/bigfile.iso" in result[0]["path"]

    def test_invalid_path_defaults_home(self, analyzer):
        mock_p1 = MagicMock()
        mock_p1.stdout = MagicMock()
        mock_p2 = MagicMock()
        mock_p2.stdout = MagicMock()
        mock_p3 = MagicMock()
        mock_p3.communicate.return_value = ("", "")

        call_count = [0]

        def popen_side_effect(cmd, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                return mock_p1
            elif call_count[0] == 2:
                return mock_p2
            return mock_p3

        with patch("shutil.which", return_value="/usr/bin/find"), \
             patch("os.path.exists", return_value=False), \
             patch("subprocess.Popen", side_effect=popen_side_effect):
            result = analyzer.get_large_files("/nonexistent")
        assert result == []

    def test_exception_returns_empty(self, analyzer):
        with patch("shutil.which", return_value="/usr/bin/find"), \
             patch("os.path.exists", return_value=True), \
             patch("subprocess.Popen", side_effect=Exception("fail")):
            result = analyzer.get_large_files("/home")
        assert result == []


class TestFormatSize:
    def test_delegates_to_utils(self):
        result = DiskAnalyzer._format_size(1048576)
        assert "M" in result or "1" in result

    def test_legacy_format(self):
        da = DiskAnalyzer()
        assert "MB" in da._format_size_legacy(1048576)
        assert "GB" in da._format_size_legacy(1073741824)
        assert "B" in da._format_size_legacy(500)
