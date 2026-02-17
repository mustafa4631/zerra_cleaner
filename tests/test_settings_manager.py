"""
GK Healter – Test Suite: settings_manager.py
"""

import os
import json
import pytest
from gk_healter_tests.helpers import src_import

settings_mod = src_import("settings_manager")
SettingsManager = settings_mod.SettingsManager


class TestSettingsManager:
    """Tests for SettingsManager persistence and defaults."""

    @pytest.fixture
    def sm(self, tmp_path):
        """Create a SettingsManager with a temp config directory."""
        mgr = SettingsManager.__new__(SettingsManager)
        mgr.config_dir = str(tmp_path)
        mgr.config_file = os.path.join(str(tmp_path), "settings.json")
        mgr.defaults = {
            "auto_maintenance_enabled": False,
            "last_maintenance_date": None,
            "maintenance_frequency_days": 7,
            "idle_threshold_minutes": 15,
            "language": "auto",
        }
        mgr.settings = mgr.defaults.copy()
        return mgr

    def test_default_values(self, sm):
        assert sm.get("language") == "auto"
        assert sm.get("auto_maintenance_enabled") is False
        assert sm.get("maintenance_frequency_days") == 7

    def test_set_and_get(self, sm):
        sm.set("language", "tr")
        assert sm.get("language") == "tr"

    def test_persistence(self, sm):
        sm.set("language", "tr")
        # Verify the file was written
        assert os.path.exists(sm.config_file)
        with open(sm.config_file, "r") as f:
            data = json.load(f)
        assert data["language"] == "tr"

    def test_unknown_key_returns_none(self, sm):
        assert sm.get("nonexistent_key") is None

    def test_is_maintenance_due_never_run(self, sm):
        sm.settings["auto_maintenance_enabled"] = True
        sm.settings["last_maintenance_date"] = None
        assert sm.is_maintenance_due() is True

    def test_is_maintenance_due_recently_run(self, sm):
        import datetime
        sm.settings["auto_maintenance_enabled"] = True
        sm.settings["last_maintenance_date"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        assert sm.is_maintenance_due() is False
