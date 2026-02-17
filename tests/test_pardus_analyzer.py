"""
GK Healter – Test Suite: pardus_analyzer.py
"""

import os
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
