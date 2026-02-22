"""
GK Healter — System Security Scanner

Performs automated security audits for Pardus/Debian-based systems:
  • World-writable file detection in system directories
  • Unexpected SUID/SGID binary identification
  • Sudoers configuration risk analysis
  • SSH daemon hardening checks
  • Unattended-upgrades status validation
  • Failed login attempt monitoring

This module runs entirely offline — no network access required.
"""

import os
import subprocess
import shutil
import logging
from typing import Dict, List, Any, Optional

logger = logging.getLogger("gk-healter.security")


class SecurityScanner:
    """System security analyzer for Pardus/Debian distributions."""

    # Directories to audit for world-writable / SUID anomalies
    CRITICAL_DIRS = ["/etc", "/usr", "/var", "/opt"]

    # Well-known SUID binaries that are expected on a standard system
    SUID_WHITELIST = frozenset({
        "/usr/bin/sudo",
        "/usr/bin/passwd",
        "/usr/bin/chsh",
        "/usr/bin/chfn",
        "/usr/bin/newgrp",
        "/usr/bin/gpasswd",
        "/usr/bin/pkexec",
        "/usr/bin/su",
        "/usr/bin/mount",
        "/usr/bin/umount",
        "/usr/bin/fusermount",
        "/usr/bin/fusermount3",
        "/usr/bin/crontab",
        "/usr/bin/at",
        "/usr/bin/ssh-agent",
        "/usr/bin/wall",
        "/usr/bin/write",
        "/usr/bin/expiry",
        "/usr/bin/chage",
        "/usr/lib/dbus-1.0/dbus-daemon-launch-helper",
        "/usr/lib/openssh/ssh-keysign",
        "/usr/lib/polkit-1/polkit-agent-helper-1",
        "/usr/lib/eject/dmcrypt-get-device",
        "/usr/sbin/unix_chkpwd",
        "/usr/sbin/pam_extrausers_chkpwd",
    })

    def __init__(self) -> None:
        self.logger = logger

    # ── World-Writable Files ─────────────────────────────────────────────────

    def scan_world_writable(
        self, paths: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """Find world-writable files/dirs outside /tmp and /proc.

        Args:
            paths: Directories to scan.  Defaults to CRITICAL_DIRS.

        Returns:
            List of finding dicts with keys: path, severity, issue,
            recommendation.
        """
        targets = paths or self.CRITICAL_DIRS
        results: List[Dict[str, Any]] = []

        if not shutil.which("find"):
            return results

        for target in targets:
            if not os.path.isdir(target):
                continue
            try:
                proc = subprocess.run(
                    [
                        "find", target, "-xdev",
                        "-perm", "-o+w",
                        "-not", "-type", "l",
                        "-not", "-path", "*/proc/*",
                        "-not", "-path", "*/tmp/*",
                    ],
                    capture_output=True, text=True, timeout=30,
                )
                for line in proc.stdout.strip().splitlines():
                    line = line.strip()
                    if line:
                        results.append({
                            "path": line,
                            "severity": "high",
                            "issue": "world_writable",
                            "recommendation": f"chmod o-w {line}",
                        })
            except subprocess.TimeoutExpired:
                self.logger.warning(
                    "World-writable scan timed out for %s", target
                )
            except Exception as e:
                self.logger.error("Error scanning %s: %s", target, e)

        return results

    # ── SUID / SGID Binaries ─────────────────────────────────────────────────

    def scan_suid_binaries(self) -> List[Dict[str, Any]]:
        """Detect unexpected SUID/SGID binaries system-wide.

        Compares found set-uid files against a known whitelist.
        Anything outside the whitelist is flagged as suspicious.

        Returns:
            List of finding dicts.
        """
        results: List[Dict[str, Any]] = []

        if not shutil.which("find"):
            return results

        try:
            proc = subprocess.run(
                [
                    "find", "/usr", "/opt", "/snap", "-xdev",
                    "-type", "f",
                    "(", "-perm", "-4000", "-o", "-perm", "-2000", ")",
                ],
                capture_output=True, text=True, timeout=60,
            )
            for line in proc.stdout.strip().splitlines():
                path = line.strip()
                if path and path not in self.SUID_WHITELIST:
                    results.append({
                        "path": path,
                        "severity": "critical",
                        "issue": "unexpected_suid",
                        "recommendation": (
                            f"Verify necessity: ls -la {path} && "
                            f"dpkg -S {path}"
                        ),
                    })
        except subprocess.TimeoutExpired:
            self.logger.warning("SUID scan timed out")
        except Exception as e:
            self.logger.error("SUID scan error: %s", e)

        return results

    # ── Sudoers Audit ────────────────────────────────────────────────────────

    def audit_sudoers(self) -> List[Dict[str, Any]]:
        """Audit /etc/sudoers* for risky NOPASSWD ALL entries.

        Reads sudoers files (requires read permission or pkexec).

        Returns:
            List of finding dicts with extra keys: line, content.
        """
        results: List[Dict[str, Any]] = []

        sudoers_paths: List[str] = []
        if os.path.exists("/etc/sudoers"):
            sudoers_paths.append("/etc/sudoers")
        sudoers_d = "/etc/sudoers.d"
        if os.path.isdir(sudoers_d):
            try:
                for fname in sorted(os.listdir(sudoers_d)):
                    fpath = os.path.join(sudoers_d, fname)
                    if os.path.isfile(fpath):
                        sudoers_paths.append(fpath)
            except PermissionError:
                pass

        for spath in sudoers_paths:
            content = self._read_privileged_file(spath)
            if content is None:
                continue
            for i, line in enumerate(content.splitlines(), 1):
                stripped = line.strip()
                if stripped.startswith("#") or not stripped:
                    continue
                if "NOPASSWD" in stripped and "ALL" in stripped:
                    results.append({
                        "path": spath,
                        "line": i,
                        "severity": "critical",
                        "issue": "nopasswd_all",
                        "content": stripped,
                        "recommendation": (
                            "Restrict NOPASSWD to specific commands "
                            "instead of ALL"
                        ),
                    })

        return results

    # ── SSH Configuration ────────────────────────────────────────────────────

    def check_ssh_config(self) -> List[Dict[str, Any]]:
        """Check /etc/ssh/sshd_config for insecure defaults.

        Returns:
            List of finding dicts.
        """
        issues: List[Dict[str, Any]] = []
        sshd_config = "/etc/ssh/sshd_config"
        if not os.path.exists(sshd_config):
            return issues

        # setting_key -> (bad_value, severity, recommendation)
        risky_settings = {
            "PermitRootLogin": (
                "yes", "critical",
                "Disable root SSH login: PermitRootLogin no",
            ),
            "PermitEmptyPasswords": (
                "yes", "critical",
                "Disable empty passwords: PermitEmptyPasswords no",
            ),
            "PasswordAuthentication": (
                "yes", "warning",
                "Consider key-based auth: PasswordAuthentication no",
            ),
            "X11Forwarding": (
                "yes", "info",
                "X11Forwarding enabled — disable if unused",
            ),
        }

        try:
            with open(sshd_config, "r") as f:
                lines = f.readlines()
        except PermissionError:
            self.logger.info("SSH config requires elevated privileges")
            return issues
        except Exception as e:
            self.logger.error("SSH config read error: %s", e)
            return issues

        for i, raw_line in enumerate(lines, 1):
            stripped = raw_line.strip()
            if stripped.startswith("#") or not stripped:
                continue
            parts = stripped.split(None, 1)
            if len(parts) != 2:
                continue
            key, value = parts
            if key in risky_settings:
                bad_value, severity, recommendation = risky_settings[key]
                if value.strip().lower() == bad_value.lower():
                    issues.append({
                        "path": sshd_config,
                        "line": i,
                        "severity": severity,
                        "issue": f"ssh_{key.lower()}",
                        "recommendation": recommendation,
                    })

        return issues

    # ── Unattended Upgrades Status ───────────────────────────────────────────

    def check_unattended_upgrades(self) -> Dict[str, Any]:
        """Check if unattended-upgrades is installed and enabled.

        Returns:
            Dict with keys: installed, enabled, config_issues.
        """
        result: Dict[str, Any] = {
            "installed": False,
            "enabled": False,
            "config_issues": [],
        }

        if not shutil.which("dpkg-query"):
            return result

        try:
            proc = subprocess.run(
                ["dpkg-query", "-W", "-f=${Status}",
                 "unattended-upgrades"],
                capture_output=True, text=True, timeout=5,
            )
            result["installed"] = (
                proc.returncode == 0
                and "install ok installed" in proc.stdout
            )
        except Exception:
            pass

        # Check configuration
        auto_conf = "/etc/apt/apt.conf.d/20auto-upgrades"
        if os.path.exists(auto_conf):
            try:
                with open(auto_conf, "r") as f:
                    content = f.read()
                if 'Unattended-Upgrade "1"' in content:
                    result["enabled"] = True
                elif 'Unattended-Upgrade "0"' in content:
                    result["config_issues"].append(
                        "Unattended-Upgrade is explicitly disabled"
                    )
            except Exception:
                pass
        elif result["installed"]:
            result["config_issues"].append(
                "unattended-upgrades installed but 20auto-upgrades "
                "config missing"
            )

        return result

    # ── Failed Login Attempts ────────────────────────────────────────────────

    def check_failed_logins(self, hours: int = 24) -> Dict[str, Any]:
        """Summarise failed authentication attempts from journal.

        Args:
            hours: How many hours back to search.

        Returns:
            Dict with count and sample entries.
        """
        result: Dict[str, Any] = {"count": 0, "samples": []}

        if not shutil.which("journalctl"):
            return result

        try:
            proc = subprocess.run(
                [
                    "journalctl", "-p", "4",
                    "-S", f"-{hours}h",
                    "--no-pager", "-g",
                    "authentication failure|Failed password|FAILED LOGIN",
                ],
                capture_output=True, text=True, timeout=15,
            )
            if proc.returncode == 0:
                lines = [
                    line.strip()
                    for line in proc.stdout.strip().splitlines()
                    if line.strip()
                ]
                result["count"] = len(lines)
                result["samples"] = lines[:10]
        except subprocess.TimeoutExpired:
            self.logger.warning("Failed-login scan timed out")
        except Exception as e:
            self.logger.error("Failed-login scan error: %s", e)

        return result

    # ── Full Scan Orchestrator ───────────────────────────────────────────────

    def run_full_scan(self) -> Dict[str, Any]:
        """Execute all security checks and return aggregated results.

        Returns:
            Dict keyed by scan type, plus a ``summary`` with severity
            counts.
        """
        results: Dict[str, Any] = {
            "world_writable": self.scan_world_writable(),
            "suid_binaries": self.scan_suid_binaries(),
            "sudoers_audit": self.audit_sudoers(),
            "ssh_config": self.check_ssh_config(),
            "unattended_upgrades": self.check_unattended_upgrades(),
            "failed_logins": self.check_failed_logins(),
            "summary": {
                "critical": 0,
                "high": 0,
                "warning": 0,
                "info": 0,
                "total_issues": 0,
            },
        }

        # Tally severities from list-based scans
        for key in ("world_writable", "suid_binaries", "sudoers_audit",
                    "ssh_config"):
            for item in results[key]:
                sev = item.get("severity", "info")
                if sev in results["summary"]:
                    results["summary"][sev] += 1
                results["summary"]["total_issues"] += 1

        # Unattended-upgrades issues
        for issue in results["unattended_upgrades"].get(
            "config_issues", []
        ):
            results["summary"]["warning"] += 1
            results["summary"]["total_issues"] += 1

        # Failed logins
        login_count = results["failed_logins"].get("count", 0)
        if login_count > 50:
            results["summary"]["critical"] += 1
            results["summary"]["total_issues"] += 1
        elif login_count > 10:
            results["summary"]["warning"] += 1
            results["summary"]["total_issues"] += 1

        return results

    # ── Helpers ──────────────────────────────────────────────────────────────

    def _read_privileged_file(self, path: str) -> Optional[str]:
        """Try to read a file, fall back to pkexec cat if permission denied."""
        try:
            with open(path, "r") as f:
                return f.read()
        except PermissionError:
            if shutil.which("pkexec"):
                try:
                    proc = subprocess.run(
                        ["pkexec", "cat", path],
                        capture_output=True, text=True, timeout=15,
                    )
                    if proc.returncode == 0:
                        return proc.stdout
                except Exception:
                    pass
        except Exception as e:
            self.logger.error("Error reading %s: %s", path, e)
        return None
