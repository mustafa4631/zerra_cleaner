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
