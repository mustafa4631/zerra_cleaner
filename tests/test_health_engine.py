"""
GK Healter – Test Suite: health_engine.py
"""

import pytest
from gk_healter_tests.helpers import src_import

health_mod = src_import("health_engine")
HealthEngine = health_mod.HealthEngine


class TestHealthScore:
    """Tests for health score calculation logic."""

    @pytest.fixture
    def engine(self):
        e = HealthEngine()
        return e

    def test_perfect_score(self, engine):
        engine._cpu_usage = 20
        engine._ram_usage = 40
        engine._disk_usage = 50
        engine._calculate_score()
        assert engine._health_score == 100

    def test_high_cpu_penalty(self, engine):
        engine._cpu_usage = 95
        engine._ram_usage = 30
        engine._disk_usage = 30
        engine._calculate_score()
        assert engine._health_score == 80  # -20 for cpu >90

    def test_high_ram_penalty(self, engine):
        engine._cpu_usage = 30
        engine._ram_usage = 92
        engine._disk_usage = 30
        engine._calculate_score()
        assert engine._health_score == 80  # -20 for ram >90

    def test_high_disk_penalty(self, engine):
        engine._cpu_usage = 30
        engine._ram_usage = 30
        engine._disk_usage = 95
        engine._calculate_score()
        assert engine._health_score == 80  # -20 for disk >90

    def test_all_critical(self, engine):
        engine._cpu_usage = 95
        engine._ram_usage = 95
        engine._disk_usage = 95
        engine._calculate_score()
        assert engine._health_score == 40  # -60 total

    def test_moderate_usage(self, engine):
        engine._cpu_usage = 75
        engine._ram_usage = 85
        engine._disk_usage = 85
        engine._calculate_score()
        assert engine._health_score == 70  # -10 -10 -10

    def test_score_never_negative(self, engine):
        engine._cpu_usage = 99
        engine._ram_usage = 99
        engine._disk_usage = 99
        engine._calculate_score()
        assert engine._health_score >= 0

    def test_get_metrics_returns_dict(self, engine):
        metrics = engine.get_metrics()
        assert "cpu" in metrics
        assert "ram" in metrics
        assert "disk" in metrics
        assert "score" in metrics

    def test_detailed_status_excellent(self, engine):
        engine._health_score = 95
        assert engine.get_detailed_status() == "Excellent"

    def test_detailed_status_critical(self, engine):
        engine._health_score = 30
        assert engine.get_detailed_status() == "Critical"
