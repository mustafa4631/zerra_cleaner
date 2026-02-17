"""
GK Healter – Test Suite: recommendation_engine.py
"""

import pytest
from gk_healter_tests.helpers import src_import

rec_mod = src_import("recommendation_engine")
RecommendationEngine = rec_mod.RecommendationEngine


class TestRecommendationEngine:
    """Tests for recommendation generation logic."""

    @pytest.fixture
    def engine(self):
        return RecommendationEngine()

    def test_no_recommendations_healthy_system(self, engine):
        metrics = {"cpu": 20, "ram": 30, "disk": 40}
        recs = engine.analyze_health(metrics)
        assert recs == []

    def test_high_cpu_warning(self, engine):
        metrics = {"cpu": 85, "ram": 30, "disk": 40}
        recs = engine.analyze_health(metrics)
        assert len(recs) == 1
        assert recs[0]["type"] == "warning"
        assert recs[0]["action"] == "open_system_monitor"

    def test_high_ram_warning(self, engine):
        metrics = {"cpu": 20, "ram": 90, "disk": 40}
        recs = engine.analyze_health(metrics)
        assert len(recs) == 1
        assert recs[0]["type"] == "warning"

    def test_critical_disk(self, engine):
        metrics = {"cpu": 20, "ram": 30, "disk": 95}
        recs = engine.analyze_health(metrics)
        assert len(recs) == 1
        assert recs[0]["type"] == "critical"

    def test_warning_disk(self, engine):
        metrics = {"cpu": 20, "ram": 30, "disk": 85}
        recs = engine.analyze_health(metrics)
        assert len(recs) == 1
        assert recs[0]["type"] == "warning"

    def test_multiple_issues(self, engine):
        metrics = {"cpu": 90, "ram": 90, "disk": 95}
        recs = engine.analyze_health(metrics)
        assert len(recs) == 3

    def test_failed_services(self, engine):
        recs = engine.analyze_services(["sshd.service", "nginx.service"], [])
        assert len(recs) == 1
        assert recs[0]["type"] == "critical"
        assert "2" in recs[0]["message"]

    def test_no_failed_services(self, engine):
        recs = engine.analyze_services([], [])
        assert recs == []

    def test_high_error_count(self, engine):
        recs = engine.analyze_logs(150)
        assert len(recs) == 1
        assert recs[0]["type"] == "warning"

    def test_low_error_count_no_warning(self, engine):
        recs = engine.analyze_logs(5)
        assert recs == []
