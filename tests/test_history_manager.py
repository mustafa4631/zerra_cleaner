"""
GK Healter – Test Suite: history_manager.py
"""

import os
import json
import pytest
from gk_healter_tests.helpers import src_import

history_mod = src_import("history_manager")
HistoryManager = history_mod.HistoryManager


class TestHistoryManager:
    """Tests for HistoryManager storage operations."""

    @pytest.fixture
    def hm(self, tmp_path):
        """Create a HistoryManager with a temp storage directory."""
        mgr = HistoryManager.__new__(HistoryManager)
        mgr.history_dir = str(tmp_path)
        mgr.history_file = os.path.join(str(tmp_path), "history.json")
        return mgr

    def test_empty_history(self, hm):
        assert hm.get_all_entries() == []

    def test_add_entry(self, hm):
        hm.add_entry(["APT Cache"], "150.00 MB", "Success")
        entries = hm.get_all_entries()
        assert len(entries) == 1
        assert entries[0]["total_freed"] == "150.00 MB"
        assert entries[0]["status"] == "Success"

    def test_entries_ordered_newest_first(self, hm):
        hm.add_entry(["Logs"], "10.00 MB", "Success")
        hm.add_entry(["Cache"], "20.00 MB", "Success")
        entries = hm.get_all_entries()
        assert len(entries) == 2
        # Second entry should be first (newest)
        assert "Cache" in entries[0]["categories"]

    def test_max_100_entries(self, hm):
        for i in range(110):
            hm.add_entry([f"Cat{i}"], f"{i} MB", "Success")
        entries = hm.get_all_entries()
        assert len(entries) == 100

    def test_persistence(self, hm):
        hm.add_entry(["Test"], "1.00 MB", "Success")
        assert os.path.exists(hm.history_file)
        with open(hm.history_file, "r") as f:
            data = json.load(f)
        assert len(data) == 1

    def test_corrupted_file_returns_empty(self, hm):
        with open(hm.history_file, "w") as f:
            f.write("NOT JSON")
        entries = hm.get_all_entries()
        assert entries == []
