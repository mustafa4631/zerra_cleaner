"""
GK Healter – Test Suite: distro_manager.py
"""

import pytest
from unittest.mock import patch
from gk_healter_tests.helpers import src_import

distro_mod = src_import("distro_manager")
DistroManager = distro_mod.DistroManager


class TestDistroDetection:
    """Tests for package manager detection."""

    def test_apt_detected(self):
        def which_side_effect(cmd):
            return "/usr/bin/apt-get" if cmd == "apt-get" else None
        with patch("shutil.which", side_effect=which_side_effect):
            dm = DistroManager()
            assert dm.pkg_manager == "apt"

    def test_pacman_detected(self):
        def which_side_effect(cmd):
            return "/usr/bin/pacman" if cmd == "pacman" else None
        with patch("shutil.which", side_effect=which_side_effect):
            dm = DistroManager()
            assert dm.pkg_manager == "pacman"

    def test_dnf_detected(self):
        def which_side_effect(cmd):
            return "/usr/bin/dnf" if cmd == "dnf" else None
        with patch("shutil.which", side_effect=which_side_effect):
            dm = DistroManager()
            assert dm.pkg_manager == "dnf"

    def test_unknown_fallback(self):
        with patch("shutil.which", return_value=None):
            dm = DistroManager()
            assert dm.pkg_manager == "unknown"


class TestPackageCachePaths:
    """Tests for distro-specific cache paths."""

    def test_apt_paths(self):
        def which_side_effect(cmd):
            return "/usr/bin/apt-get" if cmd == "apt-get" else None
        with patch("shutil.which", side_effect=which_side_effect):
            dm = DistroManager()
            paths = dm.get_package_cache_paths()
            assert len(paths) == 2
            assert paths[0][1] == "/var/cache/apt/archives"

    def test_unknown_returns_empty(self):
        with patch("shutil.which", return_value=None):
            dm = DistroManager()
            paths = dm.get_package_cache_paths()
            assert paths == []


class TestCleanCommands:
    """Tests for clean command generation."""

    def test_apt_clean(self):
        def which_side_effect(cmd):
            return "/usr/bin/apt-get" if cmd == "apt-get" else None
        with patch("shutil.which", side_effect=which_side_effect):
            dm = DistroManager()
            cmd = dm.get_clean_command("/var/cache/apt/archives")
            assert cmd == ["pkexec", "apt-get", "clean"]

    def test_apt_autoremove(self):
        def which_side_effect(cmd):
            return "/usr/bin/apt-get" if cmd == "apt-get" else None
        with patch("shutil.which", side_effect=which_side_effect):
            dm = DistroManager()
            cmd = dm.get_clean_command("/usr/bin/apt")
            assert cmd == ["pkexec", "apt-get", "autoremove", "-y"]

    def test_unknown_path_returns_empty(self):
        def which_side_effect(cmd):
            return "/usr/bin/apt-get" if cmd == "apt-get" else None
        with patch("shutil.which", side_effect=which_side_effect):
            dm = DistroManager()
            cmd = dm.get_clean_command("/some/random/path")
            assert cmd == []
