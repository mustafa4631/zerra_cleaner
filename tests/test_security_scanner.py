"""
GK Healter – Test Suite: security_scanner.py
Covers all 6 scan types plus the full scan orchestrator.
"""

import pytest
from unittest.mock import patch, MagicMock
from gk_healter_tests.helpers import src_import

security_mod = src_import("security_scanner")
SecurityScanner = security_mod.SecurityScanner


class TestWorldWritableScan:
    """Tests for scan_world_writable."""

    @pytest.fixture
    def scanner(self):
        return SecurityScanner()

    def test_no_find_returns_empty(self, scanner):
        with patch("shutil.which", return_value=None):
            result = scanner.scan_world_writable()
        assert result == []

    def test_finds_world_writable_files(self, scanner):
        mock_proc = MagicMock()
        mock_proc.stdout = "/etc/bad_file\n/var/world_open\n"
        with patch("shutil.which", return_value="/usr/bin/find"), \
             patch("os.path.isdir", return_value=True), \
             patch("subprocess.run", return_value=mock_proc):
            result = scanner.scan_world_writable(["/etc"])
        assert len(result) == 2
        assert result[0]["severity"] == "high"
        assert result[0]["issue"] == "world_writable"
        assert "chmod" in result[0]["recommendation"]

    def test_empty_output(self, scanner):
        mock_proc = MagicMock()
        mock_proc.stdout = ""
        with patch("shutil.which", return_value="/usr/bin/find"), \
             patch("os.path.isdir", return_value=True), \
             patch("subprocess.run", return_value=mock_proc):
            result = scanner.scan_world_writable(["/etc"])
        assert result == []

    def test_skips_nonexistent_dirs(self, scanner):
        with patch("shutil.which", return_value="/usr/bin/find"), \
             patch("os.path.isdir", return_value=False):
            result = scanner.scan_world_writable(["/nonexistent"])
        assert result == []

    def test_timeout_handled(self, scanner):
        import subprocess
        with patch("shutil.which", return_value="/usr/bin/find"), \
             patch("os.path.isdir", return_value=True), \
             patch("subprocess.run", side_effect=subprocess.TimeoutExpired("find", 30)):
            result = scanner.scan_world_writable(["/etc"])
        assert result == []


class TestSuidBinaryScan:
    """Tests for scan_suid_binaries."""

    @pytest.fixture
    def scanner(self):
        return SecurityScanner()

    def test_no_find_returns_empty(self, scanner):
        with patch("shutil.which", return_value=None):
            result = scanner.scan_suid_binaries()
        assert result == []

    def test_whitelisted_binaries_not_flagged(self, scanner):
        mock_proc = MagicMock()
        mock_proc.stdout = "/usr/bin/sudo\n/usr/bin/passwd\n"
        with patch("shutil.which", return_value="/usr/bin/find"), \
             patch("subprocess.run", return_value=mock_proc):
            result = scanner.scan_suid_binaries()
        assert result == []

    def test_unknown_suid_flagged(self, scanner):
        mock_proc = MagicMock()
        mock_proc.stdout = "/usr/bin/sudo\n/opt/malware/evil_binary\n"
        with patch("shutil.which", return_value="/usr/bin/find"), \
             patch("subprocess.run", return_value=mock_proc):
            result = scanner.scan_suid_binaries()
        assert len(result) == 1
        assert result[0]["path"] == "/opt/malware/evil_binary"
        assert result[0]["severity"] == "critical"
        assert result[0]["issue"] == "unexpected_suid"

    def test_empty_scan(self, scanner):
        mock_proc = MagicMock()
        mock_proc.stdout = ""
        with patch("shutil.which", return_value="/usr/bin/find"), \
             patch("subprocess.run", return_value=mock_proc):
            result = scanner.scan_suid_binaries()
        assert result == []


class TestSudoersAudit:
    """Tests for audit_sudoers."""

    @pytest.fixture
    def scanner(self):
        return SecurityScanner()

    def test_nopasswd_all_flagged(self, scanner):
        sudoers_content = (
            "# comment\n"
            "root ALL=(ALL:ALL) ALL\n"
            "user ALL=(ALL) NOPASSWD: ALL\n"
        )
        with patch("os.path.exists", return_value=True), \
             patch("os.path.isdir", return_value=False), \
             patch.object(scanner, "_read_privileged_file",
                          return_value=sudoers_content):
            result = scanner.audit_sudoers()
        assert len(result) == 1
        assert result[0]["severity"] == "critical"
        assert result[0]["issue"] == "nopasswd_all"
        assert result[0]["line"] == 3

    def test_safe_sudoers_no_findings(self, scanner):
        sudoers_content = (
            "root ALL=(ALL:ALL) ALL\n"
            "user ALL=(ALL) NOPASSWD: /usr/bin/apt-get\n"
        )
        with patch("os.path.exists", return_value=True), \
             patch("os.path.isdir", return_value=False), \
             patch.object(scanner, "_read_privileged_file",
                          return_value=sudoers_content):
            result = scanner.audit_sudoers()
        assert result == []

    def test_unreadable_file(self, scanner):
        with patch("os.path.exists", return_value=True), \
             patch("os.path.isdir", return_value=False), \
             patch.object(scanner, "_read_privileged_file",
                          return_value=None):
            result = scanner.audit_sudoers()
        assert result == []


class TestSshConfig:
    """Tests for check_ssh_config."""

    @pytest.fixture
    def scanner(self):
        return SecurityScanner()

    def test_no_sshd_config(self, scanner):
        with patch("os.path.exists", return_value=False):
            result = scanner.check_ssh_config()
        assert result == []

    def test_root_login_yes_flagged(self, scanner):
        config = "PermitRootLogin yes\nPasswordAuthentication no\n"
        with patch("os.path.exists", return_value=True), \
             patch("builtins.open", create=True) as mock_open:
            mock_open.return_value.__enter__ = lambda s: s
            mock_open.return_value.__exit__ = MagicMock(return_value=False)
            mock_open.return_value.readlines.return_value = config.splitlines(True)
            result = scanner.check_ssh_config()
        assert len(result) == 1
        assert result[0]["issue"] == "ssh_permitrootlogin"
        assert result[0]["severity"] == "critical"

    def test_safe_config_no_findings(self, scanner):
        config = "PermitRootLogin no\nPasswordAuthentication no\n"
        with patch("os.path.exists", return_value=True), \
             patch("builtins.open", create=True) as mock_open:
            mock_open.return_value.__enter__ = lambda s: s
            mock_open.return_value.__exit__ = MagicMock(return_value=False)
            mock_open.return_value.readlines.return_value = config.splitlines(True)
            result = scanner.check_ssh_config()
        assert result == []

    def test_comments_ignored(self, scanner):
        config = "# PermitRootLogin yes\n"
        with patch("os.path.exists", return_value=True), \
             patch("builtins.open", create=True) as mock_open:
            mock_open.return_value.__enter__ = lambda s: s
            mock_open.return_value.__exit__ = MagicMock(return_value=False)
            mock_open.return_value.readlines.return_value = config.splitlines(True)
            result = scanner.check_ssh_config()
        assert result == []


class TestUnattendedUpgrades:
    """Tests for check_unattended_upgrades."""

    @pytest.fixture
    def scanner(self):
        return SecurityScanner()

    def test_no_dpkg_query(self, scanner):
        with patch("shutil.which", return_value=None):
            result = scanner.check_unattended_upgrades()
        assert result["installed"] is False
        assert result["enabled"] is False

    def test_installed_and_enabled(self, scanner):
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.stdout = "install ok installed"

        conf_content = 'APT::Periodic::Unattended-Upgrade "1";'
        with patch("shutil.which", return_value="/usr/bin/dpkg-query"), \
             patch("subprocess.run", return_value=mock_proc), \
             patch("os.path.exists", return_value=True), \
             patch("builtins.open", create=True) as mock_open:
            mock_open.return_value.__enter__ = lambda s: s
            mock_open.return_value.__exit__ = MagicMock(return_value=False)
            mock_open.return_value.read.return_value = conf_content
            result = scanner.check_unattended_upgrades()
        assert result["installed"] is True
        assert result["enabled"] is True

    def test_installed_but_disabled(self, scanner):
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.stdout = "install ok installed"

        conf_content = 'APT::Periodic::Unattended-Upgrade "0";'
        with patch("shutil.which", return_value="/usr/bin/dpkg-query"), \
             patch("subprocess.run", return_value=mock_proc), \
             patch("os.path.exists", return_value=True), \
             patch("builtins.open", create=True) as mock_open:
            mock_open.return_value.__enter__ = lambda s: s
            mock_open.return_value.__exit__ = MagicMock(return_value=False)
            mock_open.return_value.read.return_value = conf_content
            result = scanner.check_unattended_upgrades()
        assert result["installed"] is True
        assert len(result["config_issues"]) >= 1


class TestFailedLogins:
    """Tests for check_failed_logins."""

    @pytest.fixture
    def scanner(self):
        return SecurityScanner()

    def test_no_journalctl(self, scanner):
        with patch("shutil.which", return_value=None):
            result = scanner.check_failed_logins()
        assert result["count"] == 0
        assert result["samples"] == []

    def test_some_failures(self, scanner):
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        lines = ["Feb 18 10:00 sshd: Failed password for user"] * 5
        mock_proc.stdout = "\n".join(lines) + "\n"
        with patch("shutil.which", return_value="/usr/bin/journalctl"), \
             patch("subprocess.run", return_value=mock_proc):
            result = scanner.check_failed_logins()
        assert result["count"] == 5
        assert len(result["samples"]) == 5

    def test_samples_capped_at_10(self, scanner):
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        lines = [f"Feb 18 10:{i:02d} sshd: Failed password" for i in range(25)]
        mock_proc.stdout = "\n".join(lines) + "\n"
        with patch("shutil.which", return_value="/usr/bin/journalctl"), \
             patch("subprocess.run", return_value=mock_proc):
            result = scanner.check_failed_logins()
        assert result["count"] == 25
        assert len(result["samples"]) == 10


class TestFullScan:
    """Tests for run_full_scan orchestrator."""

    @pytest.fixture
    def scanner(self):
        return SecurityScanner()

    def test_full_scan_returns_all_keys(self, scanner):
        with patch.object(scanner, "scan_world_writable", return_value=[]), \
             patch.object(scanner, "scan_suid_binaries", return_value=[]), \
             patch.object(scanner, "audit_sudoers", return_value=[]), \
             patch.object(scanner, "check_ssh_config", return_value=[]), \
             patch.object(scanner, "check_unattended_upgrades",
                          return_value={"installed": True, "enabled": True,
                                        "config_issues": []}), \
             patch.object(scanner, "check_failed_logins",
                          return_value={"count": 0, "samples": []}):
            result = scanner.run_full_scan()
        expected_keys = {"world_writable", "suid_binaries", "sudoers_audit",
                         "ssh_config", "unattended_upgrades", "failed_logins",
                         "summary"}
        assert expected_keys.issubset(set(result.keys()))
        assert result["summary"]["total_issues"] == 0

    def test_full_scan_tallies_severities(self, scanner):
        with patch.object(scanner, "scan_world_writable", return_value=[
                {"path": "/etc/x", "severity": "high", "issue": "world_writable",
                 "recommendation": "chmod o-w /etc/x"}
             ]), \
             patch.object(scanner, "scan_suid_binaries", return_value=[
                {"path": "/opt/evil", "severity": "critical",
                 "issue": "unexpected_suid", "recommendation": "check"}
             ]), \
             patch.object(scanner, "audit_sudoers", return_value=[]), \
             patch.object(scanner, "check_ssh_config", return_value=[]), \
             patch.object(scanner, "check_unattended_upgrades",
                          return_value={"installed": True, "enabled": True,
                                        "config_issues": []}), \
             patch.object(scanner, "check_failed_logins",
                          return_value={"count": 0, "samples": []}):
            result = scanner.run_full_scan()
        assert result["summary"]["total_issues"] == 2
        assert result["summary"]["critical"] == 1
        assert result["summary"]["high"] == 1

    def test_high_failed_logins_counted(self, scanner):
        with patch.object(scanner, "scan_world_writable", return_value=[]), \
             patch.object(scanner, "scan_suid_binaries", return_value=[]), \
             patch.object(scanner, "audit_sudoers", return_value=[]), \
             patch.object(scanner, "check_ssh_config", return_value=[]), \
             patch.object(scanner, "check_unattended_upgrades",
                          return_value={"installed": True, "enabled": True,
                                        "config_issues": []}), \
             patch.object(scanner, "check_failed_logins",
                          return_value={"count": 100, "samples": []}):
            result = scanner.run_full_scan()
        assert result["summary"]["critical"] == 1
        assert result["summary"]["total_issues"] == 1
