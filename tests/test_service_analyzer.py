"""
GK Healter – Test Suite: service_analyzer.py
"""

import pytest
from unittest.mock import patch, MagicMock
from gk_healter_tests.helpers import src_import

svc_mod = src_import("service_analyzer")
ServiceAnalyzer = svc_mod.ServiceAnalyzer


class TestGetFailedServices:
    @pytest.fixture
    def analyzer(self):
        return ServiceAnalyzer()

    def test_no_systemctl_returns_error(self, analyzer):
        with patch("shutil.which", return_value=None):
            result = analyzer.get_failed_services()
        assert len(result) == 1
        assert "Error" in result[0]

    def test_no_failed_services(self, analyzer):
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = ""
        with patch("shutil.which", return_value="/usr/bin/systemctl"), \
             patch("subprocess.run", return_value=mock_result):
            result = analyzer.get_failed_services()
        assert result == []

    def test_parses_failed_units(self, analyzer):
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = (
            "nginx.service   loaded failed failed  nginx web server\n"
            "sshd.service    loaded failed failed  OpenSSH server\n"
        )
        with patch("shutil.which", return_value="/usr/bin/systemctl"), \
             patch("subprocess.run", return_value=mock_result):
            result = analyzer.get_failed_services()
        assert "nginx.service" in result
        assert "sshd.service" in result
        assert len(result) == 2

    def test_exception_returns_error(self, analyzer):
        with patch("shutil.which", return_value="/usr/bin/systemctl"), \
             patch("subprocess.run", side_effect=Exception("timeout")):
            result = analyzer.get_failed_services()
        assert len(result) == 1
        assert "Error" in result[0]


class TestGetSlowStartupServices:
    @pytest.fixture
    def analyzer(self):
        return ServiceAnalyzer()

    def test_no_systemd_analyze(self, analyzer):
        with patch("shutil.which", return_value=None):
            result = analyzer.get_slow_startup_services()
        assert result == []

    def test_parses_blame_output(self, analyzer):
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = (
            "5.123s NetworkManager.service\n"
            "3.456s systemd-logind.service\n"
            "1.789s gdm.service\n"
        )
        with patch("shutil.which", return_value="/usr/bin/systemd-analyze"), \
             patch("subprocess.run", return_value=mock_result):
            result = analyzer.get_slow_startup_services(limit=3)
        assert len(result) == 3
        assert result[0]["time"] == "5.123s"
        assert result[0]["service"] == "NetworkManager.service"

    def test_respects_limit(self, analyzer):
        mock_result = MagicMock()
        mock_result.returncode = 0
        lines = [f"{i}.000s service{i}.service" for i in range(10)]
        mock_result.stdout = "\n".join(lines) + "\n"
        with patch("shutil.which", return_value="/usr/bin/systemd-analyze"), \
             patch("subprocess.run", return_value=mock_result):
            result = analyzer.get_slow_startup_services(limit=3)
        assert len(result) == 3


class TestGetSystemState:
    @pytest.fixture
    def analyzer(self):
        return ServiceAnalyzer()

    def test_no_systemctl(self, analyzer):
        with patch("shutil.which", return_value=None):
            assert analyzer.get_system_state() == "unknown"

    def test_running_state(self, analyzer):
        mock_result = MagicMock()
        mock_result.stdout = "running\n"
        with patch("shutil.which", return_value="/usr/bin/systemctl"), \
             patch("subprocess.run", return_value=mock_result):
            assert analyzer.get_system_state() == "running"

    def test_degraded_state(self, analyzer):
        mock_result = MagicMock()
        mock_result.stdout = "degraded\n"
        with patch("shutil.which", return_value="/usr/bin/systemctl"), \
             patch("subprocess.run", return_value=mock_result):
            assert analyzer.get_system_state() == "degraded"

    def test_exception_returns_unknown(self, analyzer):
        with patch("shutil.which", return_value="/usr/bin/systemctl"), \
             patch("subprocess.run", side_effect=Exception("fail")):
            assert analyzer.get_system_state() == "unknown"
