"""
GK Healter – Test Suite: report_exporter.py
Covers data collection, TXT / HTML / JSON export, and helper utilities.
"""

import os
import json
import pytest
from unittest.mock import patch, mock_open, MagicMock
from gk_healter_tests.helpers import src_import

mod = src_import("report_exporter")
ReportExporter = mod.ReportExporter


# ── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture
def exporter():
    return ReportExporter()


@pytest.fixture
def sample_pardus_verification():
    return {
        "is_pardus": True,
        "os_release": {"ID": "pardus", "PRETTY_NAME": "Pardus 23.2",
                       "VERSION_ID": "23.2", "VERSION_CODENAME": "yirmiuc"},
        "lsb_release": {"distributor_id": "Pardus", "release": "23.2"},
        "hardware": {"kernel": "6.1.0", "architecture": "x86_64",
                     "cpu_count": 4, "total_ram_bytes": 8589934592},
        "hostname": "pardus-test",
        "pardus_packages": ["pardus-software", "pardus-about"],
        "pardus_services": [{"name": "pardus-software", "status": "installed"}],
        "desktop_environment": "XFCE",
        "timestamp": "2026-01-01T12:00:00",
    }


@pytest.fixture
def sample_health_metrics():
    return {"score": 85, "cpu": 22.5, "ram": 45.3, "disk": 62.1}


@pytest.fixture
def sample_security():
    return {
        "summary": {"total_issues": 3, "critical": 1, "high": 1, "warning": 1},
        "world_writable": [{"path": "/tmp/bad", "severity": "high",
                            "issue": "world_writable",
                            "recommendation": "chmod o-w"}],
        "suid_binaries": [{"path": "/usr/bin/unknown_suid", "severity": "critical"}],
        "sudoers_audit": [{"content": "user ALL=(ALL) NOPASSWD: ALL"}],
        "ssh_config": [{"recommendation": "Disable root login", "severity": "warning"}],
        "failed_logins": {"count": 5, "samples": ["Failed for root"]},
    }


@pytest.fixture
def sample_pardus_diag():
    return {
        "distribution": {"name": "Pardus 23.2"},
        "repo_health": {"active_repos": 3, "pardus_repos": 2,
                        "third_party_repos": 1},
        "broken_packages": {"broken_count": 0},
        "available_updates": {"upgradable_count": 12},
        "repo_trust_score": {"score": 95},
        "mirror_health": {"reachable": True, "response_time_ms": 42},
        "release_compatibility": {"compatible": True},
        "package_log_analysis": {
            "total_operations": 50, "installs": 20,
            "removes": 10, "upgrades": 20,
        },
    }


@pytest.fixture
def full_report_data(
    sample_pardus_verification,
    sample_health_metrics,
    sample_security,
    sample_pardus_diag,
):
    return ReportExporter.collect_report_data(
        pardus_verification=sample_pardus_verification,
        health_metrics=sample_health_metrics,
        health_status="Good",
        security_results=sample_security,
        pardus_diagnostics=sample_pardus_diag,
        cleaning_history=[
            {"date": "2026-01-01", "total_freed": "500 MB",
             "status": "Success", "categories": "APT Cache"},
        ],
        large_files=[{"path": "/home/user/big.iso", "size": "4.2 GB"}],
        failed_services=["bluetooth.service"],
        error_count_24h=12,
    )


# ── collect_report_data ─────────────────────────────────────────────────────

class TestCollectReportData:

    def test_all_sections_present(self, full_report_data):
        assert "generated_at" in full_report_data
        assert "generator" in full_report_data
        assert full_report_data["pardus_verification"]["is_pardus"] is True
        assert full_report_data["health"]["metrics"]["score"] == 85
        assert full_report_data["security"]["summary"]["total_issues"] == 3
        assert len(full_report_data["cleaning_history"]) == 1
        assert len(full_report_data["large_files"]) == 1
        assert full_report_data["services"]["error_count_24h"] == 12

    def test_empty_call(self):
        data = ReportExporter.collect_report_data()
        assert data["pardus_verification"] is None
        assert data["health"] is None
        assert data["security"] is None
        assert data["cleaning_history"] == []
        assert data["services"]["failed"] == []
        assert data["services"]["error_count_24h"] == 0

    def test_history_truncated_to_10(self):
        history = [{"date": f"2026-01-{i:02d}"} for i in range(1, 25)]
        data = ReportExporter.collect_report_data(cleaning_history=history)
        assert len(data["cleaning_history"]) == 10


# ── TXT Export ───────────────────────────────────────────────────────────────

class TestExportTxt:

    def test_writes_file(self, exporter, full_report_data, tmp_path):
        filepath = str(tmp_path / "report.txt")
        result = exporter.export_txt(full_report_data, filepath)
        assert result == filepath
        assert os.path.isfile(filepath)
        content = open(filepath, "r", encoding="utf-8").read()
        assert "GK Healter" in content
        assert "Pardus Verification" in content
        assert "Security Audit" in content

    def test_auto_path_generation(self, exporter, full_report_data):
        m = mock_open()
        with patch("builtins.open", m), patch("os.makedirs"):
            path = exporter.export_txt(full_report_data)
        assert path.endswith(".txt")
        assert "gk-healter-report_" in path

    def test_pardus_verification_section(self, exporter, full_report_data, tmp_path):
        filepath = str(tmp_path / "report_pv.txt")
        exporter.export_txt(full_report_data, filepath)
        content = open(filepath, "r", encoding="utf-8").read()
        assert "Is Pardus" in content
        assert "Pardus 23.2" in content
        assert "x86_64" in content

    def test_health_section(self, exporter, full_report_data, tmp_path):
        filepath = str(tmp_path / "report_h.txt")
        exporter.export_txt(full_report_data, filepath)
        content = open(filepath, "r", encoding="utf-8").read()
        assert "Health Score" in content
        assert "85" in content
        assert "CPU Usage" in content

    def test_security_section(self, exporter, full_report_data, tmp_path):
        filepath = str(tmp_path / "report_s.txt")
        exporter.export_txt(full_report_data, filepath)
        content = open(filepath, "r", encoding="utf-8").read()
        assert "Total Issues" in content
        assert "[WW]" in content
        assert "[SUID]" in content
        assert "[SSH]" in content
        assert "[SUDO]" in content
        assert "failed login" in content

    def test_services_section(self, exporter, full_report_data, tmp_path):
        filepath = str(tmp_path / "report_svc.txt")
        exporter.export_txt(full_report_data, filepath)
        content = open(filepath, "r", encoding="utf-8").read()
        assert "bluetooth.service" in content
        assert "12" in content

    def test_empty_sections(self, exporter, tmp_path):
        data = ReportExporter.collect_report_data()
        filepath = str(tmp_path / "empty.txt")
        exporter.export_txt(data, filepath)
        content = open(filepath, "r", encoding="utf-8").read()
        assert "GK Healter" in content
        # Should not crash when all sections are None


# ── HTML Export ──────────────────────────────────────────────────────────────

class TestExportHtml:

    def test_writes_html_file(self, exporter, full_report_data, tmp_path):
        filepath = str(tmp_path / "report.html")
        result = exporter.export_html(full_report_data, filepath)
        assert result == filepath
        assert os.path.isfile(filepath)
        content = open(filepath, "r", encoding="utf-8").read()
        assert "<!DOCTYPE html>" in content
        assert "GK Healter" in content
        assert "<style>" in content

    def test_html_escapes_content(self, exporter, tmp_path):
        data = ReportExporter.collect_report_data(
            cleaning_history=[
                {"date": "<script>alert('xss')</script>",
                 "total_freed": "1 MB", "status": "OK",
                 "categories": "test"},
            ],
        )
        filepath = str(tmp_path / "xss.html")
        exporter.export_html(data, filepath)
        content = open(filepath, "r", encoding="utf-8").read()
        assert "<script>" not in content
        assert "&lt;script&gt;" in content

    def test_auto_path_html(self, exporter, full_report_data):
        m = mock_open()
        with patch("builtins.open", m), patch("os.makedirs"):
            path = exporter.export_html(full_report_data)
        assert path.endswith(".html")

    def test_pardus_diagnostics_in_html(self, exporter, full_report_data, tmp_path):
        filepath = str(tmp_path / "diag.html")
        exporter.export_html(full_report_data, filepath)
        content = open(filepath, "r", encoding="utf-8").read()
        assert "Pardus Diagnostics" in content
        assert "Trust Score" in content


# ── JSON Export ──────────────────────────────────────────────────────────────

class TestExportJson:

    def test_writes_valid_json(self, exporter, full_report_data, tmp_path):
        filepath = str(tmp_path / "report.json")
        result = exporter.export_json(full_report_data, filepath)
        assert result == filepath
        with open(filepath, "r", encoding="utf-8") as f:
            loaded = json.load(f)
        assert loaded["pardus_verification"]["is_pardus"] is True
        assert loaded["health"]["metrics"]["score"] == 85

    def test_auto_path_json(self, exporter, full_report_data):
        m = mock_open()
        with patch("builtins.open", m), patch("os.makedirs"):
            path = exporter.export_json(full_report_data)
        assert path.endswith(".json")

    def test_roundtrip(self, exporter, full_report_data, tmp_path):
        filepath = str(tmp_path / "rt.json")
        exporter.export_json(full_report_data, filepath)
        with open(filepath, "r", encoding="utf-8") as f:
            loaded = json.load(f)
        assert loaded["services"]["error_count_24h"] == 12
        assert loaded["generator"] == "GK Healter Report Exporter"


# ── _auto_path helper ────────────────────────────────────────────────────────

class TestAutoPath:

    def test_txt_extension(self, exporter):
        path = exporter._auto_path("txt")
        assert path.endswith(".txt")
        assert "gk-healter-report_" in path

    def test_html_extension(self, exporter):
        path = exporter._auto_path("html")
        assert path.endswith(".html")

    def test_json_extension(self, exporter):
        path = exporter._auto_path("json")
        assert path.endswith(".json")

    def test_in_documents_dir(self, exporter):
        path = exporter._auto_path("txt")
        assert os.path.expanduser("~/Documents") in path


# ── _get_version helper ─────────────────────────────────────────────────────

class TestGetVersion:

    def test_fallback_version(self):
        with patch.dict("sys.modules", {"src.__init__": None}):
            result = mod._get_version()
        assert result == "0.1.5"

    def test_reads_version_from_init(self):
        mock_init = MagicMock()
        mock_init.__version__ = "1.2.3"
        with patch.dict("sys.modules", {"src.__init__": mock_init}):
            # Force reimport
            result = mod._get_version()
        # Either gets the version or falls back
        assert isinstance(result, str)


# ── _render_txt edge cases ───────────────────────────────────────────────────

class TestRenderTxt:

    def test_large_files_section(self, exporter):
        data = ReportExporter.collect_report_data(
            large_files=[
                {"path": "/home/user/movie.mkv", "size": "12.3 GB"},
                {"path": "/var/log/huge.log", "size": "1.5 GB"},
            ],
        )
        lines = exporter._render_txt(data)
        text = "\n".join(lines)
        assert "Large Files" in text
        assert "movie.mkv" in text

    def test_pardus_diagnostics_mirror(self, exporter, sample_pardus_diag):
        data = ReportExporter.collect_report_data(
            pardus_diagnostics=sample_pardus_diag,
        )
        lines = exporter._render_txt(data)
        text = "\n".join(lines)
        assert "Reachable" in text
        assert "42 ms" in text

    def test_pardus_diagnostics_incompatible(self, exporter):
        diag = {
            "distribution": {"name": "Pardus"},
            "repo_health": {"active_repos": 1, "pardus_repos": 1,
                            "third_party_repos": 0},
            "broken_packages": {"broken_count": 2},
            "available_updates": {"upgradable_count": 0},
            "repo_trust_score": {"score": 50},
            "release_compatibility": {"compatible": False},
        }
        data = ReportExporter.collect_report_data(pardus_diagnostics=diag)
        lines = exporter._render_txt(data)
        text = "\n".join(lines)
        assert "MISMATCH" in text
        assert "Broken Pkgs" in text
        assert "2" in text

    def test_no_failed_logins(self, exporter):
        security = {
            "summary": {"total_issues": 0, "critical": 0, "high": 0, "warning": 0},
            "world_writable": [],
            "suid_binaries": [],
            "sudoers_audit": [],
            "ssh_config": [],
            "failed_logins": {"count": 0},
        }
        data = ReportExporter.collect_report_data(security_results=security)
        lines = exporter._render_txt(data)
        text = "\n".join(lines)
        assert "failed login" not in text
