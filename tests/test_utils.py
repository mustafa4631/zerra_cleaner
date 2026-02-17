"""
GK Healter – Test Suite: utils.py
"""

import pytest
from gk_healter_tests.helpers import src_import

utils = src_import("utils")


class TestFormatSize:
    """Tests for the format_size utility function."""

    def test_zero_bytes(self):
        result = utils.format_size(0)
        assert "0" in result
        assert "B" in result

    def test_bytes_small(self):
        result = utils.format_size(500)
        assert "B" in result

    def test_kilobytes(self):
        result = utils.format_size(2048)
        # 2048 / 1024 = 2.0 KB
        assert "K" in result

    def test_megabytes(self):
        result = utils.format_size(5 * 1024 * 1024)
        assert "M" in result

    def test_gigabytes(self):
        result = utils.format_size(3 * 1024 ** 3)
        assert "G" in result

    def test_terabytes(self):
        result = utils.format_size(2 * 1024 ** 4)
        assert "T" in result

    def test_returns_string(self):
        result = utils.format_size(1234)
        assert isinstance(result, str)


class TestGetSize:
    """Tests for recursive directory size calculation."""

    def test_empty_dir(self, tmp_path):
        assert utils.get_size(str(tmp_path)) == 0

    def test_single_file(self, tmp_path):
        f = tmp_path / "test.txt"
        f.write_text("hello world")
        size = utils.get_size(str(tmp_path))
        assert size == len("hello world")

    def test_nested_files(self, tmp_path):
        sub = tmp_path / "sub"
        sub.mkdir()
        (tmp_path / "a.txt").write_text("aaa")
        (sub / "b.txt").write_text("bbbbb")
        size = utils.get_size(str(tmp_path))
        assert size == 3 + 5

    def test_symlink_skipped(self, tmp_path):
        real = tmp_path / "real.txt"
        real.write_text("data")
        link = tmp_path / "link.txt"
        link.symlink_to(real)
        size = utils.get_size(str(tmp_path))
        assert size == len("data")  # symlink not counted

    def test_nonexistent_returns_zero(self):
        assert utils.get_size("/nonexistent/path/xyz") == 0
