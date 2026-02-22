"""
GK Healter – Test Suite: ai_engine.py (hybrid architecture)
Tests both LocalAnalysisEngine and AIEngine.
"""

import json
import pytest
from unittest.mock import patch, MagicMock
from gk_healter_tests.helpers import src_import

ai_mod = src_import("ai_engine")
LocalAnalysisEngine = ai_mod.LocalAnalysisEngine
AIEngine = ai_mod.AIEngine


# ═══════════════════════════════════════════════════════════════════════════════
#  LocalAnalysisEngine Tests
# ═══════════════════════════════════════════════════════════════════════════════


class TestLocalAnalysisEngine:
    """Tests for the offline rule-based analysis engine."""

    @pytest.fixture
    def engine(self):
        return LocalAnalysisEngine()

    # ── Risk level tests ─────────────────────────────────────────────────────

    def test_healthy_system_low_risk(self, engine):
        report = engine.analyse(
            metrics={"cpu": 30, "ram": 40, "disk": 50, "score": 90},
            failed_services=[],
            error_count=0,
        )
        assert report["risk_level"] == "low"
        assert len(report["issues"]) == 0
        assert "healthy" in report["summary"].lower()

    def test_critical_cpu_triggers_critical_risk(self, engine):
        report = engine.analyse(
            metrics={"cpu": 97, "ram": 30, "disk": 30, "score": 70},
            failed_services=[],
            error_count=0,
        )
        assert report["risk_level"] == "critical"
        assert any(i["resource"] == "cpu" for i in report["issues"])

    def test_warning_ram(self, engine):
        report = engine.analyse(
            metrics={"cpu": 30, "ram": 82, "disk": 30, "score": 80},
            failed_services=[],
            error_count=0,
        )
        assert report["risk_level"] == "medium"
        assert any(
            i["resource"] == "ram" and i["severity"] == "warning"
            for i in report["issues"]
        )

    def test_critical_disk(self, engine):
        report = engine.analyse(
            metrics={"cpu": 30, "ram": 30, "disk": 96, "score": 60},
            failed_services=[],
            error_count=0,
        )
        assert report["risk_level"] == "critical"
        assert any(i["resource"] == "disk" for i in report["issues"])

    # ── Failed services ──────────────────────────────────────────────────────

    def test_failed_services_raise_risk(self, engine):
        report = engine.analyse(
            metrics={"cpu": 30, "ram": 30, "disk": 30, "score": 80},
            failed_services=["nginx.service", "sshd.service"],
            error_count=0,
        )
        assert report["risk_level"] == "high"
        svc_issue = next(
            (i for i in report["issues"] if i["resource"] == "services"),
            None,
        )
        assert svc_issue is not None
        assert "2" in svc_issue["message"]

    # ── Journal anomalies ────────────────────────────────────────────────────

    def test_high_error_count_flagged(self, engine):
        report = engine.analyse(
            metrics={"cpu": 30, "ram": 30, "disk": 30, "score": 80},
            failed_services=[],
            error_count=150,
        )
        assert any(
            i["resource"] == "journal" and i["severity"] == "high"
            for i in report["issues"]
        )

    def test_moderate_error_count_warning(self, engine):
        report = engine.analyse(
            metrics={"cpu": 30, "ram": 30, "disk": 30, "score": 80},
            failed_services=[],
            error_count=50,
        )
        assert any(
            i["resource"] == "journal" and i["severity"] == "warning"
            for i in report["issues"]
        )

    def test_low_error_count_no_issue(self, engine):
        report = engine.analyse(
            metrics={"cpu": 30, "ram": 30, "disk": 30, "score": 90},
            failed_services=[],
            error_count=5,
        )
        assert not any(
            i["resource"] == "journal" for i in report["issues"]
        )

    # ── Actions ──────────────────────────────────────────────────────────────

    def test_actions_list_not_empty_when_issues(self, engine):
        report = engine.analyse(
            metrics={"cpu": 96, "ram": 30, "disk": 30, "score": 70},
            failed_services=[],
            error_count=0,
        )
        assert len(report["actions"]) >= 1
        assert report["actions"][0] != "No immediate actions required."

    def test_no_actions_when_healthy(self, engine):
        report = engine.analyse(
            metrics={"cpu": 20, "ram": 30, "disk": 40, "score": 95},
            failed_services=[],
            error_count=0,
        )
        assert "No immediate actions required." in report["actions"]

    # ── format_as_text ───────────────────────────────────────────────────────

    def test_format_as_text_contains_summary(self, engine):
        report = engine.analyse(
            metrics={"cpu": 30, "ram": 30, "disk": 30, "score": 90},
            failed_services=[],
            error_count=0,
        )
        text = engine.format_as_text(report)
        assert "Summary:" in text

    def test_format_as_text_lists_issues(self, engine):
        report = engine.analyse(
            metrics={"cpu": 96, "ram": 92, "disk": 30, "score": 50},
            failed_services=[],
            error_count=0,
        )
        text = engine.format_as_text(report)
        assert "[CRITICAL]" in text
        assert "Recommended Actions:" in text

    # ── Missing keys handled gracefully ──────────────────────────────────────

    def test_missing_metric_keys_default_zero(self, engine):
        report = engine.analyse(
            metrics={},
            failed_services=[],
            error_count=0,
        )
        assert report["risk_level"] == "low"


# ═══════════════════════════════════════════════════════════════════════════════
#  AIEngine Tests (hybrid)
# ═══════════════════════════════════════════════════════════════════════════════


class TestAIEngine:
    """Tests for the hybrid AI engine."""

    @pytest.fixture
    def ai_engine(self):
        return AIEngine()

    # ── Configuration ────────────────────────────────────────────────────────

    def test_default_not_enabled(self, ai_engine):
        assert ai_engine.enabled is False

    def test_configure_enables(self, ai_engine):
        ai_engine.configure("gemini", "test-key", "gemini-2.5-flash")
        assert ai_engine.enabled is True
        assert ai_engine.provider == "gemini"
        assert ai_engine.api_key == "test-key"

    def test_configure_empty_key_disables(self, ai_engine):
        ai_engine.configure("openai", "", "gpt-4o")
        assert ai_engine.enabled is False

    # ── Fallback to local ────────────────────────────────────────────────────

    def test_no_api_key_uses_local(self, ai_engine):
        result = ai_engine.generate_insight(
            {"cpu": 30, "ram": 30, "disk": 30, "score": 90},
            [], 0,
        )
        assert isinstance(result, str)
        assert "Summary:" in result

    def test_api_failure_falls_back_to_local(self, ai_engine):
        ai_engine.configure("gemini", "bad-key", "gemini-2.5-flash")
        with patch.object(ai_engine, "_call_gemini",
                          side_effect=RuntimeError("API error")):
            result = ai_engine.generate_insight(
                {"cpu": 30, "ram": 30, "disk": 30, "score": 90},
                [], 0,
            )
        assert isinstance(result, str)
        assert "Summary:" in result

    # ── Successful AI call ───────────────────────────────────────────────────

    def test_gemini_success_returns_combined(self, ai_engine):
        ai_engine.configure("gemini", "valid-key", "gemini-2.5-flash")
        with patch.object(ai_engine, "_call_gemini",
                          return_value="AI says everything is fine."):
            result = ai_engine.generate_insight(
                {"cpu": 30, "ram": 30, "disk": 30, "score": 90},
                [], 0,
            )
        assert "AI Analysis" in result
        assert "Local Analysis" in result
        assert "AI says everything is fine." in result

    def test_openai_success_returns_combined(self, ai_engine):
        ai_engine.configure("openai", "valid-key", "gpt-4o")
        with patch.object(ai_engine, "_call_openai",
                          return_value="OpenAI insight here."):
            result = ai_engine.generate_insight(
                {"cpu": 30, "ram": 30, "disk": 30, "score": 90},
                [], 0,
            )
        assert "AI Analysis" in result
        assert "OpenAI insight here." in result

    def test_unknown_provider_falls_back(self, ai_engine):
        ai_engine.configure("claude", "valid-key", "claude-3")
        result = ai_engine.generate_insight(
            {"cpu": 30, "ram": 30, "disk": 30, "score": 90},
            [], 0,
        )
        # Unknown provider → only local text
        assert "AI Analysis" not in result
        assert "Summary:" in result

    # ── get_local_report ─────────────────────────────────────────────────────

    def test_get_local_report_returns_dict(self, ai_engine):
        report = ai_engine.get_local_report(
            {"cpu": 30, "ram": 30, "disk": 30, "score": 90},
            [], 0,
        )
        assert isinstance(report, dict)
        assert "risk_level" in report
        assert "issues" in report

    # ── Prompt construction ──────────────────────────────────────────────────

    def test_prompt_contains_metrics(self, ai_engine):
        prompt = ai_engine._construct_prompt(
            {"cpu": 75, "ram": 60, "disk": 80, "score": 65},
            ["sshd.service"],
            42,
        )
        assert "75%" in prompt
        assert "60%" in prompt
        assert "80%" in prompt
        assert "65/100" in prompt
        assert "sshd.service" in prompt
        assert "42" in prompt


class TestOpenAICall:
    """Tests for _call_openai HTTP interaction."""

    @pytest.fixture
    def ai_engine(self):
        e = AIEngine()
        e.configure("openai", "test-key", "gpt-4o")
        return e

    def test_successful_call(self, ai_engine):
        response_data = {
            "choices": [{"message": {"content": "Test response"}}]
        }
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps(response_data).encode()
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)

        with patch("urllib.request.urlopen", return_value=mock_resp):
            result = ai_engine._call_openai("test prompt")
        assert result == "Test response"

    def test_http_error_raises(self, ai_engine):
        import urllib.error
        error = urllib.error.HTTPError(
            "url", 401, "Unauthorized", {}, None
        )
        with patch("urllib.request.urlopen", side_effect=error):
            with pytest.raises(RuntimeError, match="OpenAI API Error"):
                ai_engine._call_openai("test prompt")


class TestGeminiCall:
    """Tests for _call_gemini HTTP interaction."""

    @pytest.fixture
    def ai_engine(self):
        e = AIEngine()
        e.configure("gemini", "test-key", "gemini-2.5-flash")
        return e

    def test_successful_call(self, ai_engine):
        response_data = {
            "candidates": [
                {"content": {"parts": [{"text": "Gemini response"}]}}
            ]
        }
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps(response_data).encode()
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)

        with patch("urllib.request.urlopen", return_value=mock_resp):
            result = ai_engine._call_gemini("test prompt")
        assert result == "Gemini response"

    def test_malformed_response_raises(self, ai_engine):
        response_data = {"candidates": []}
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps(response_data).encode()
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)

        with patch("urllib.request.urlopen", return_value=mock_resp):
            with pytest.raises(RuntimeError, match="malformed"):
                ai_engine._call_gemini("test prompt")
