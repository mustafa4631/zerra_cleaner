"""
GK Healter – Test Suite: pardus_analyzer.py
"""

import os
import subprocess
import pytest
from unittest.mock import patch, MagicMock
from gk_healter_tests.helpers import src_import

pardus_mod = src_import("pardus_analyzer")
PardusAnalyzer = pardus_mod.PardusAnalyzer


class TestPardusDetection:
    """Tests for Pardus distribution detection."""

    def test_detects_pardus_from_os_release(self, tmp_path):
        os_release = tmp_path / "os-release"
        os_release.write_text(
            'PRETTY_NAME="Pardus 23.2 Yirmiüç"\n'
            'NAME="Pardus"\n'
            'VERSION_ID="23.2"\n'
            'VERSION_CODENAME=yirmiuc\n'
            'ID=pardus\n'
            'ID_LIKE="debian gnu/linux"\n'
        )
        pa = PardusAnalyzer()
        pa._is_pardus = None  # reset
        with patch("builtins.open", create=True) as mock_open:
            mock_open.return_value.__enter__ = lambda s: s
            mock_open.return_value.__exit__ = MagicMock(return_value=False)
            mock_open.return_value.read.return_value = os_release.read_text()
            with patch("os.path.exists", return_value=True):
                result = pa.is_pardus()
        assert result is True

    def test_non_pardus_returns_false(self):
        pa = PardusAnalyzer()
        pa._is_pardus = None
        with patch("os.path.exists", return_value=False):
            with patch("shutil.which", return_value=None):
                result = pa.is_pardus()
        assert result is False


class TestRepoHealth:
    """Tests for APT repository health checks."""

    def test_repo_scan_with_sources(self, tmp_path):
        sources = tmp_path / "sources.list"
        sources.write_text(
            "deb http://depo.pardus.org.tr/pardus yirmiuc main\n"
            "# deb http://old.repo.org/test test main\n"
            "deb http://ppa.launchpad.net/some/ppa focal main\n"
        )
        pa = PardusAnalyzer()
        with patch("os.path.exists", return_value=True), \
             patch("os.path.isdir", return_value=False), \
             patch("builtins.open", create=True) as mock_open:
            mock_open.return_value.__enter__ = lambda s: s
            mock_open.return_value.__exit__ = MagicMock(return_value=False)
            mock_open.return_value.__iter__ = lambda s: iter(sources.read_text().splitlines(True))
            with patch.object(pa, "is_debian_based", return_value=True):
                result = pa.check_repo_health()

        assert result["active_repos"] >= 1


class TestBrokenPackages:
    """Tests for broken package detection."""

    def test_no_dpkg_returns_empty(self):
        pa = PardusAnalyzer()
        with patch("shutil.which", return_value=None):
            result = pa.check_broken_packages()
        assert result["broken_count"] == 0
        assert result["packages"] == []

    def test_clean_system(self):
        pa = PardusAnalyzer()
        mock_result = MagicMock()
        mock_result.stdout = ""
        mock_result.returncode = 0
        with patch("shutil.which", return_value="/usr/bin/dpkg"), \
             patch("subprocess.run", return_value=mock_result):
            result = pa.check_broken_packages()
        assert result["broken_count"] == 0


class TestVersionInfo:
    """Tests for version info parsing."""

    def test_parse_os_release(self, tmp_path):
        os_release = tmp_path / "os-release"
        os_release.write_text(
            'PRETTY_NAME="Pardus 23.2"\n'
            'VERSION_ID="23.2"\n'
            'VERSION_CODENAME=yirmiuc\n'
            'ID=pardus\n'
            'ID_LIKE=debian\n'
        )
        pa = PardusAnalyzer()
        with patch("os.path.exists", return_value=True), \
             patch("builtins.open", return_value=open(str(os_release), "r")):
            result = pa.get_pardus_version()
        assert result["version"] == "23.2"
        assert result["codename"] == "yirmiuc"


class TestHeldPackages:
    """Tests for held package detection."""

    def test_no_apt_mark(self):
        pa = PardusAnalyzer()
        with patch("shutil.which", return_value=None):
            result = pa.check_held_packages()
        assert result == []

    def test_held_packages_found(self):
        pa = PardusAnalyzer()
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "linux-image-amd64\nlibc6\n"
        with patch("shutil.which", return_value="/usr/bin/apt-mark"), \
             patch("subprocess.run", return_value=mock_result):
            result = pa.check_held_packages()
        assert "linux-image-amd64" in result
        assert "libc6" in result


class TestMirrorHealth:
    """Tests for Pardus mirror health check."""

    def test_mirror_reachable(self):
        pa = PardusAnalyzer()
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        with patch("urllib.request.urlopen", return_value=mock_resp), \
             patch("socket.getaddrinfo", return_value=[(None,)]):
            result = pa.check_pardus_mirror_health()
        assert result["reachable"] is True
        assert result["dns_resolved"] is True
        assert result["recommended_mirror"] != ""

    def test_mirror_unreachable(self):
        pa = PardusAnalyzer()
        import urllib.error
        with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("timeout")), \
             patch("socket.getaddrinfo", side_effect=OSError("DNS failed")):
            result = pa.check_pardus_mirror_health()
        assert result["reachable"] is False
        assert len(result["mirrors"]) > 0

    def test_mirror_partial_failure(self):
        """Some mirrors fail, at least one succeeds."""
        pa = PardusAnalyzer()
        import urllib.error
        call_count = [0]
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)

        def side_effect(req, timeout=5):
            call_count[0] += 1
            if call_count[0] == 1:
                raise urllib.error.URLError("first mirror down")
            return mock_resp

        with patch("urllib.request.urlopen", side_effect=side_effect), \
             patch("socket.getaddrinfo", return_value=[(None,)]):
            result = pa.check_pardus_mirror_health()
        assert result["reachable"] is True


class TestReleaseCompatibility:
    """Tests for Pardus release compatibility check."""

    def test_compatible_repos(self, tmp_path):
        sources = tmp_path / "sources.list"
        sources.write_text(
            "deb http://depo.pardus.org.tr/pardus yirmiuc main\n"
        )

        pa = PardusAnalyzer()
        # Patch get_pardus_version to avoid file-open recursion
        with patch.object(pa, "get_pardus_version", return_value={
                "name": "Pardus 23.2", "version": "23.2",
                "codename": "yirmiuc", "base": "debian"
             }), \
             patch("os.path.exists", side_effect=lambda p: p == "/etc/apt/sources.list"), \
             patch("os.path.isdir", return_value=False), \
             patch("builtins.open", return_value=open(str(sources))):
            result = pa.check_pardus_release_compatibility()
        assert result["compatible"] is True
        assert result["os_codename"] == "yirmiuc"

    def test_mismatched_repos(self, tmp_path):
        sources = tmp_path / "sources.list"
        sources.write_text(
            "deb http://depo.pardus.org.tr/pardus yirmibir main\n"
        )

        pa = PardusAnalyzer()
        with patch.object(pa, "get_pardus_version", return_value={
                "name": "Pardus 23.2", "version": "23.2",
                "codename": "yirmiuc", "base": "debian"
             }), \
             patch("os.path.exists", side_effect=lambda p: p == "/etc/apt/sources.list"), \
             patch("os.path.isdir", return_value=False), \
             patch("builtins.open", return_value=open(str(sources))):
            result = pa.check_pardus_release_compatibility()
        assert result["compatible"] is False
        assert len(result["mismatched_repos"]) > 0

    def test_no_codename_returns_early(self):
        pa = PardusAnalyzer()
        with patch.object(pa, "get_pardus_version", return_value={"codename": "Unknown"}):
            result = pa.check_pardus_release_compatibility()
        assert result["compatible"] is True  # Cannot determine, assume OK


class TestPardusLogs:
    """Tests for Pardus APT/dpkg log analysis."""

    def test_dpkg_log_parse(self, tmp_path):
        import datetime
        today = datetime.datetime.now().strftime("%Y-%m-%d")
        dpkg_log = tmp_path / "dpkg.log"
        dpkg_log.write_text(
            f"{today} 10:00:00 install libfoo:amd64 1.0\n"
            f"{today} 10:01:00 upgrade libbar:amd64 1.0 2.0\n"
            f"{today} 10:02:00 remove libbaz:amd64 1.0\n"
        )
        pa = PardusAnalyzer()
        with patch("os.path.isfile", side_effect=lambda p: p == "/var/log/dpkg.log"), \
             patch("builtins.open", return_value=open(str(dpkg_log))):
            result = pa.analyze_pardus_logs(days=7)
        assert result["installs"] >= 1
        assert result["upgrades"] >= 1
        assert result["removes"] >= 1
        assert result["total_operations"] >= 3

    def test_no_log_files(self):
        pa = PardusAnalyzer()
        with patch("os.path.isfile", return_value=False):
            result = pa.analyze_pardus_logs()
        assert result["total_operations"] == 0
        assert result["days_since_update"] == -1

    def test_permission_error_handled(self):
        pa = PardusAnalyzer()
        with patch("os.path.isfile", return_value=True), \
             patch("builtins.open", side_effect=PermissionError("denied")):
            result = pa.analyze_pardus_logs()
        assert result["total_operations"] == 0


class TestPardusServices:
    """Tests for Pardus service checking."""

    def test_no_dpkg_query_returns_empty(self):
        pa = PardusAnalyzer()
        with patch("shutil.which", return_value=None):
            result = pa.check_pardus_services()
        assert result == []

    def test_services_checked(self):
        pa = PardusAnalyzer()
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "install ok installed"
        with patch("shutil.which", return_value="/usr/bin/dpkg-query"), \
             patch("subprocess.run", return_value=mock_result):
            result = pa.check_pardus_services()
        assert len(result) > 0
        assert result[0]["installed"] == "yes"

    def test_services_not_installed(self):
        pa = PardusAnalyzer()
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = ""
        with patch("shutil.which", return_value="/usr/bin/dpkg-query"), \
             patch("subprocess.run", return_value=mock_result):
            result = pa.check_pardus_services()
        assert len(result) > 0
        assert result[0]["installed"] == "no"

    def test_service_timeout(self):
        pa = PardusAnalyzer()
        with patch("shutil.which", return_value="/usr/bin/dpkg-query"), \
             patch("subprocess.run", side_effect=subprocess.TimeoutExpired("cmd", 5)):
            result = pa.check_pardus_services()
        assert len(result) > 0
        assert result[0]["status"] == "timeout"


class TestGetFixCommand:
    """Test for fix broken command."""

    def test_returns_pkexec_command(self):
        pa = PardusAnalyzer()
        cmd = pa.get_fix_broken_command()
        assert cmd[0] == "pkexec"
        assert "install" in cmd
        assert "-f" in cmd


class TestDebianBased:
    """Test for debian-based detection."""

    def test_is_debian_based_with_apt(self):
        pa = PardusAnalyzer()
        with patch("shutil.which", return_value="/usr/bin/apt-get"):
            assert pa.is_debian_based() is True

    def test_not_debian_based(self):
        pa = PardusAnalyzer()
        with patch("shutil.which", return_value=None):
            assert pa.is_debian_based() is False

    def test_repo_health_non_debian(self):
        pa = PardusAnalyzer()
        with patch.object(pa, "is_debian_based", return_value=False):
            result = pa.check_repo_health()
        assert "Not a Debian-based system" in result["errors"]
