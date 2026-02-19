"""
GK Healter – Test Suite: cleaner.py (safety mechanisms)
"""

import os
import pytest
from unittest.mock import patch, MagicMock
from gk_healter_tests.helpers import src_import

cleaner_mod = src_import("cleaner")
SystemCleaner = cleaner_mod.SystemCleaner


class TestSafetyWhitelist:
    """Tests for the is_safe_to_delete whitelist mechanism."""

    @pytest.fixture
    def cleaner(self):
        with patch.object(SystemCleaner, '__init__', lambda self: None):
            c = SystemCleaner.__new__(SystemCleaner)
            c.scan_results = []
            # Minimal distro_manager mock
            mock_dm = MagicMock()
            mock_dm.get_package_cache_paths.return_value = [
                ("cat_pkg_cache", "/var/cache/apt/archives", "desc_pkg_cache")
            ]
            c.distro_manager = mock_dm
            return c

    def test_forbidden_paths_rejected(self, cleaner):
        forbidden = ["/bin", "/boot", "/dev", "/etc", "/lib", "/proc", "/sys", "/usr/bin", "/usr/lib"]
        for p in forbidden:
            assert cleaner.is_safe_to_delete(p) is False, f"{p} should be forbidden"

    def test_var_log_allowed(self, cleaner):
        assert cleaner.is_safe_to_delete("/var/log") is True

    def test_coredump_allowed(self, cleaner):
        assert cleaner.is_safe_to_delete("/var/lib/systemd/coredump") is True

    def test_apt_cache_allowed(self, cleaner):
        assert cleaner.is_safe_to_delete("/var/cache/apt/archives") is True

    def test_user_cache_allowed(self, cleaner):
        cache = os.path.expanduser("~/.cache/thumbnails")
        assert cleaner.is_safe_to_delete(cache) is True

    def test_home_root_rejected(self, cleaner):
        assert cleaner.is_safe_to_delete(os.path.expanduser("~")) is False

    def test_random_path_rejected(self, cleaner):
        assert cleaner.is_safe_to_delete("/opt/something") is False


class TestCleanUser:
    """Tests for user-space cleaning operations."""

    @pytest.fixture
    def cleaner(self):
        with patch.object(SystemCleaner, '__init__', lambda self: None):
            c = SystemCleaner.__new__(SystemCleaner)
            c.scan_results = []
            return c

    def test_clean_existing_file(self, tmp_path, cleaner):
        f = tmp_path / "test.txt"
        f.write_text("data")
        success, err = cleaner._clean_user(str(f))
        assert success is True
        assert err is None
        assert not f.exists()

    def test_clean_directory_files(self, tmp_path, cleaner):
        (tmp_path / "a.txt").write_text("aaa")
        (tmp_path / "b.txt").write_text("bbb")
        success, err = cleaner._clean_user(str(tmp_path))
        assert success is True
        # Directory should exist but files should be gone
        assert len(list(tmp_path.iterdir())) == 0

    def test_clean_nonexistent_succeeds(self, cleaner):
        # os.path.isfile and os.path.isdir both return False → no-op
        success, err = cleaner._clean_user("/tmp/nonexistent_xyz_123")
        assert success is True


class TestMarkerPathSafety:
    """Tests for distro-manager marker path handling in is_safe_to_delete."""

    @pytest.fixture
    def cleaner_apt(self):
        """Cleaner configured with apt-style marker paths."""
        with patch.object(SystemCleaner, '__init__', lambda self: None):
            c = SystemCleaner.__new__(SystemCleaner)
            c.scan_results = []
            mock_dm = MagicMock()
            mock_dm.get_package_cache_paths.return_value = [
                ("cat_pkg_cache", "/var/cache/apt/archives", "desc_pkg_cache"),
                ("cat_autoremove", "/usr/bin/apt", "desc_autoremove"),
            ]
            # /var/cache/apt/archives → real dir, returns command
            # /usr/bin/apt → marker, returns command
            def mock_clean_cmd(path):
                if path == "/var/cache/apt/archives":
                    return ["pkexec", "apt-get", "clean"]
                if path == "/usr/bin/apt":
                    return ["pkexec", "apt-get", "autoremove", "-y"]
                return []
            mock_dm.get_clean_command.side_effect = mock_clean_cmd
            c.distro_manager = mock_dm
            return c

    @pytest.fixture
    def cleaner_pacman(self):
        """Cleaner configured with pacman-style marker paths."""
        with patch.object(SystemCleaner, '__init__', lambda self: None):
            c = SystemCleaner.__new__(SystemCleaner)
            c.scan_results = []
            mock_dm = MagicMock()
            mock_dm.get_package_cache_paths.return_value = [
                ("cat_pkg_cache", "/var/cache/pacman/pkg", "desc_pkg_cache"),
                ("cat_autoremove", "/usr/bin/pacman", "desc_unused_deps"),
            ]
            def mock_clean_cmd(path):
                if path == "/var/cache/pacman/pkg":
                    return ["pkexec", "pacman", "-Scc", "--noconfirm"]
                if path == "/usr/bin/pacman":
                    return ["sh", "-c", "pacman -Qtdq | xargs -r pkexec pacman -Rns --noconfirm"]
                return []
            mock_dm.get_clean_command.side_effect = mock_clean_cmd
            c.distro_manager = mock_dm
            return c

    def test_apt_marker_path_allowed(self, cleaner_apt):
        """The /usr/bin/apt marker must be allowed (triggers apt autoremove)."""
        assert cleaner_apt.is_safe_to_delete("/usr/bin/apt") is True

    def test_apt_cache_dir_also_allowed(self, cleaner_apt):
        """Real cache dir /var/cache/apt/archives must still be allowed."""
        assert cleaner_apt.is_safe_to_delete("/var/cache/apt/archives") is True

    def test_pacman_marker_path_allowed(self, cleaner_pacman):
        """The /usr/bin/pacman marker must be allowed (triggers orphan removal)."""
        assert cleaner_pacman.is_safe_to_delete("/usr/bin/pacman") is True

    def test_other_usr_bin_still_forbidden(self, cleaner_apt):
        """Arbitrary /usr/bin paths must remain blocked."""
        assert cleaner_apt.is_safe_to_delete("/usr/bin/bash") is False

    def test_forbidden_paths_unaffected_by_markers(self, cleaner_apt):
        """Core forbidden paths must never be allowed regardless of markers."""
        for p in ["/boot", "/dev", "/proc", "/sys"]:
            assert cleaner_apt.is_safe_to_delete(p) is False, f"{p} should stay forbidden"
