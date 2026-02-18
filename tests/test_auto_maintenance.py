"""
GK Healter – Test Suite: auto_maintenance_manager.py
"""

import datetime
import pytest
from unittest.mock import patch, MagicMock
from gk_healter_tests.helpers import src_import

auto_mod = src_import("auto_maintenance_manager")
AutoMaintenanceManager = auto_mod.AutoMaintenanceManager


class TestAutoMaintenanceConditions:
    """Tests for can_run_maintenance logic."""

    @pytest.fixture
    def manager(self):
        settings = MagicMock()
        settings.get.side_effect = lambda key: {
            "auto_maintenance_enabled": True,
            "check_ac_power": False,
            "idle_threshold_minutes": 5,
            "disk_threshold_enabled": False,
            "disk_threshold_percent": 90,
        }.get(key)
        settings.is_maintenance_due.return_value = True

        history = MagicMock()
        with patch.object(AutoMaintenanceManager, "__init__", lambda self, *a: None):
            mgr = AutoMaintenanceManager.__new__(AutoMaintenanceManager)
            mgr.settings = settings
            mgr.history = history
            mgr.cleaner = MagicMock()
            mgr.last_disk_check_date = None
        return mgr

    def test_disabled_returns_false(self, manager):
        manager.settings.get.side_effect = lambda key: {
            "auto_maintenance_enabled": False,
        }.get(key, False)
        assert manager.can_run_maintenance() is False

    def test_all_conditions_met(self, manager):
        with patch.object(manager, "get_idle_time_seconds", return_value=600):
            assert manager.can_run_maintenance() is True

    def test_not_idle_enough(self, manager):
        with patch.object(manager, "get_idle_time_seconds", return_value=60):
            assert manager.can_run_maintenance() is False

    def test_ac_power_required_but_on_battery(self, manager):
        manager.settings.get.side_effect = lambda key: {
            "auto_maintenance_enabled": True,
            "check_ac_power": True,
            "idle_threshold_minutes": 5,
        }.get(key)
        with patch.object(manager, "is_on_ac_power", return_value=False):
            assert manager.can_run_maintenance() is False

    def test_ac_power_required_and_plugged_in(self, manager):
        manager.settings.get.side_effect = lambda key: {
            "auto_maintenance_enabled": True,
            "check_ac_power": True,
            "idle_threshold_minutes": 5,
        }.get(key)
        with patch.object(manager, "is_on_ac_power", return_value=True), \
             patch.object(manager, "get_idle_time_seconds", return_value=600):
            assert manager.can_run_maintenance() is True

    def test_disk_threshold_triggers(self, manager):
        manager.settings.get.side_effect = lambda key: {
            "auto_maintenance_enabled": True,
            "check_ac_power": False,
            "idle_threshold_minutes": 5,
            "disk_threshold_enabled": True,
            "disk_threshold_percent": 90,
        }.get(key)
        with patch.object(manager, "get_idle_time_seconds", return_value=600), \
             patch.object(manager, "get_disk_usage_percent", return_value=95.0):
            result = manager.can_run_maintenance(force_disk_check=True)
        assert result is True


class TestDiskUsage:
    @pytest.fixture
    def manager(self):
        with patch.object(AutoMaintenanceManager, "__init__", lambda self, *a: None):
            mgr = AutoMaintenanceManager.__new__(AutoMaintenanceManager)
        return mgr

    def test_returns_percentage(self, manager):
        with patch("shutil.disk_usage", return_value=(100_000_000, 60_000_000, 40_000_000)):
            result = manager.get_disk_usage_percent()
        assert abs(result - 60.0) < 0.1

    def test_exception_returns_zero(self, manager):
        with patch("shutil.disk_usage", side_effect=Exception("fail")):
            assert manager.get_disk_usage_percent() == 0.0


class TestACPower:
    @pytest.fixture
    def manager(self):
        with patch.object(AutoMaintenanceManager, "__init__", lambda self, *a: None):
            mgr = AutoMaintenanceManager.__new__(AutoMaintenanceManager)
        return mgr

    def test_no_power_supply_dir_returns_true(self, manager):
        with patch("os.path.exists", return_value=False):
            assert manager.is_on_ac_power() is True


class TestRunMaintenance:
    @pytest.fixture
    def manager(self):
        settings = MagicMock()
        history = MagicMock()
        cleaner = MagicMock()

        with patch.object(AutoMaintenanceManager, "__init__", lambda self, *a: None):
            mgr = AutoMaintenanceManager.__new__(AutoMaintenanceManager)
            mgr.settings = settings
            mgr.history = history
            mgr.cleaner = cleaner
            mgr.last_disk_check_date = None
        return mgr

    def test_no_scan_results_returns_none(self, manager):
        manager.cleaner.scan.return_value = []
        assert manager.run_maintenance() is None

    def test_only_system_items_returns_none(self, manager):
        manager.cleaner.scan.return_value = [
            {"category": "APT", "system": True, "size_bytes": 100, "path": "/x"},
        ]
        assert manager.run_maintenance() is None

    def test_successful_clean_returns_report(self, manager):
        manager.cleaner.scan.return_value = [
            {"category": "Thumbnails", "system": False,
             "size_bytes": 5000, "path": "/home/u/.cache/thumb",
             "desc": "thumbs", "size_str": "5 KB"},
        ]
        manager.cleaner.clean.return_value = (1, 0, [])
        result = manager.run_maintenance()
        assert result is not None
        assert "freed" in result
        assert "categories" in result
        manager.history.add_entry.assert_called_once()
