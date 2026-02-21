"""
GK Healter — Pardus Verification Module

Provides concrete, exportable proof that the application is running on
a Pardus system.  Collects distribution metadata, hardware summary,
and Pardus-specific service status into a structured report that can
be serialised to JSON or plain text for competition evidence.
"""

import os
import platform
import shutil
import subprocess
import logging
import datetime
from typing import Dict, Any, Optional

logger = logging.getLogger("gk-healter.pardus-verifier")


class PardusVerifier:
    """Collects verifiable system identity data for Pardus environments."""

    def __init__(self) -> None:
        self._cache: Optional[Dict[str, Any]] = None

    # ── Core Verification ────────────────────────────────────────────────────

    def verify(self) -> Dict[str, Any]:
        """Run all verification checks and return a unified report.

        Returns:
            dict with keys:
                - is_pardus: bool
                - os_release: dict — raw /etc/os-release fields
                - lsb_release: dict — lsb_release command output
                - hardware: dict — CPU, RAM, kernel info
                - pardus_services: list — status of Pardus-specific packages
                - pardus_packages: list — installed pardus-* packages
                - desktop_environment: str
                - timestamp: str — ISO format
                - hostname: str
        """
        report: Dict[str, Any] = {
            "is_pardus": False,
            "os_release": self._read_os_release(),
            "lsb_release": self._read_lsb_release(),
            "hardware": self._collect_hardware_info(),
            "pardus_services": self._check_pardus_packages(),
            "pardus_packages": self._list_pardus_packages(),
            "desktop_environment": self._detect_desktop_environment(),
            "timestamp": datetime.datetime.now().isoformat(),
            "hostname": platform.node(),
        }

        # Determine if this is genuinely Pardus
        os_id = report["os_release"].get("ID", "").lower()
        lsb_id = report["lsb_release"].get("distributor_id", "").lower()
        report["is_pardus"] = "pardus" in os_id or "pardus" in lsb_id

        self._cache = report
        logger.info(
            "Pardus verification complete: is_pardus=%s, distro=%s",
            report["is_pardus"],
            report["os_release"].get("PRETTY_NAME", "Unknown"),
        )
        return report

    def get_cached_report(self) -> Optional[Dict[str, Any]]:
        """Return the last verification report without re-running checks."""
        return self._cache

    # ── /etc/os-release ──────────────────────────────────────────────────────

    @staticmethod
    def _read_os_release() -> Dict[str, str]:
        """Parse /etc/os-release into a dict."""
        data: Dict[str, str] = {}
        path = "/etc/os-release"
        if not os.path.isfile(path):
            return data
        try:
            with open(path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if "=" not in line or line.startswith("#"):
                        continue
                    key, _, value = line.partition("=")
                    data[key.strip()] = value.strip().strip('"')
        except Exception as e:
            logger.warning("Failed to read %s: %s", path, e)
        return data

    # ── lsb_release ──────────────────────────────────────────────────────────

    @staticmethod
    def _read_lsb_release() -> Dict[str, str]:
        """Run lsb_release -a and parse output into a dict."""
        data: Dict[str, str] = {}
        if not shutil.which("lsb_release"):
            return data
        try:
            proc = subprocess.run(
                ["lsb_release", "-a"],
                capture_output=True, text=True, timeout=10,
            )
            if proc.returncode == 0:
                for line in proc.stdout.strip().splitlines():
                    if ":" not in line:
                        continue
                    key, _, value = line.partition(":")
                    # Normalise key: "Distributor ID" → "distributor_id"
                    norm_key = key.strip().lower().replace(" ", "_")
                    data[norm_key] = value.strip()
            logger.info("lsb_release output collected: %s", data)
        except subprocess.TimeoutExpired:
            logger.warning("lsb_release timed out")
        except Exception as e:
            logger.warning("lsb_release failed: %s", e)
        return data

    # ── Hardware Information ─────────────────────────────────────────────────

    @staticmethod
    def _collect_hardware_info() -> Dict[str, Any]:
        """Collect basic hardware and kernel information."""
        info: Dict[str, Any] = {
            "kernel": platform.release(),
            "kernel_version": platform.version(),
            "architecture": platform.machine(),
            "processor": platform.processor() or "Unknown",
            "cpu_count": os.cpu_count() or 1,
            "total_ram_bytes": 0,
        }
        try:
            import psutil
            info["total_ram_bytes"] = psutil.virtual_memory().total
        except ImportError:
            # Fallback: read /proc/meminfo
            try:
                with open("/proc/meminfo", "r") as f:
                    for line in f:
                        if line.startswith("MemTotal:"):
                            parts = line.split()
                            info["total_ram_bytes"] = int(parts[1]) * 1024
                            break
            except Exception:
                pass
        return info

    # ── Pardus Package Detection ─────────────────────────────────────────────

    PARDUS_PACKAGES = [
        "pardus-software",
        "pardus-store",
        "pardus-power-manager",
        "pardus-lightdm-greeter",
        "pardus-locales",
        "pardus-night-light",
        "pardus-mycomputer",
        "pardus-package-installer",
        "pardus-usb-formatter",
        "pardus-about",
        "pardus-boot-repair",
        "pardus-pen-installer",
        "pardus-cheat-sheet",
        "pardus-xfce-tweaks",
    ]

    def _check_pardus_packages(self) -> list:
        """Check installation status of known Pardus packages."""
        results = []
        if not shutil.which("dpkg-query"):
            return results
        for pkg in self.PARDUS_PACKAGES:
            status = "not-installed"
            try:
                proc = subprocess.run(
                    ["dpkg-query", "-W", "-f=${Status}", pkg],
                    capture_output=True, text=True, timeout=5,
                )
                if proc.returncode == 0 and "install ok installed" in proc.stdout:
                    status = "installed"
            except Exception:
                status = "error"
            results.append({"name": pkg, "status": status})
        return results

    @staticmethod
    def _list_pardus_packages() -> list:
        """List all installed packages whose name starts with 'pardus-'."""
        packages = []
        if not shutil.which("dpkg-query"):
            return packages
        try:
            proc = subprocess.run(
                ["dpkg-query", "-W", "-f=${Package}\\n"],
                capture_output=True, text=True, timeout=15,
            )
            if proc.returncode == 0:
                for line in proc.stdout.strip().splitlines():
                    if line.strip().startswith("pardus-"):
                        packages.append(line.strip())
        except Exception as e:
            logger.warning("Failed to list pardus packages: %s", e)
        return packages

    # ── Desktop Environment ──────────────────────────────────────────────────

    @staticmethod
    def _detect_desktop_environment() -> str:
        """Detect the current desktop environment."""
        de = os.environ.get("XDG_CURRENT_DESKTOP", "")
        session = os.environ.get("DESKTOP_SESSION", "")
        return de or session or "Unknown"

    # ── Text Export ──────────────────────────────────────────────────────────

    def format_as_text(self, report: Optional[Dict[str, Any]] = None) -> str:
        """Format a verification report as human-readable plain text.

        Args:
            report: Verification dict.  Uses cached report if omitted.

        Returns:
            Multi-line text string suitable for logging or file export.
        """
        r = report or self._cache
        if not r:
            return "No verification data available. Run verify() first."

        lines = [
            "═══════════════════════════════════════════════════════",
            "  GK Healter — Pardus Verification Report",
            "═══════════════════════════════════════════════════════",
            "",
            f"Timestamp     : {r.get('timestamp', 'N/A')}",
            f"Hostname      : {r.get('hostname', 'N/A')}",
            f"Is Pardus     : {'Yes' if r.get('is_pardus') else 'No'}",
            "",
            "── OS Release ─────────────────────────────────────────",
        ]
        for key, val in r.get("os_release", {}).items():
            lines.append(f"  {key}: {val}")

        lines.append("")
        lines.append("── LSB Release ────────────────────────────────────────")
        lsb = r.get("lsb_release", {})
        if lsb:
            for key, val in lsb.items():
                lines.append(f"  {key}: {val}")
        else:
            lines.append("  (lsb_release not available)")

        lines.append("")
        lines.append("── Hardware ───────────────────────────────────────────")
        hw = r.get("hardware", {})
        lines.append(f"  Kernel       : {hw.get('kernel', 'N/A')}")
        lines.append(f"  Architecture : {hw.get('architecture', 'N/A')}")
        lines.append(f"  Processor    : {hw.get('processor', 'N/A')}")
        lines.append(f"  CPU Cores    : {hw.get('cpu_count', 'N/A')}")
        ram_bytes = hw.get("total_ram_bytes", 0)
        ram_gb = ram_bytes / (1024 ** 3) if ram_bytes else 0
        lines.append(f"  Total RAM    : {ram_gb:.1f} GB")

        lines.append("")
        lines.append(f"  Desktop Env  : {r.get('desktop_environment', 'N/A')}")

        lines.append("")
        lines.append("── Pardus Packages ────────────────────────────────────")
        installed = [
            p["name"] for p in r.get("pardus_services", [])
            if p.get("status") == "installed"
        ]
        all_pardus = r.get("pardus_packages", [])
        if installed:
            for pkg in installed:
                lines.append(f"  [✓] {pkg}")
        if all_pardus:
            for pkg in all_pardus:
                if pkg not in installed:
                    lines.append(f"  [✓] {pkg}")
        if not installed and not all_pardus:
            lines.append("  (No Pardus-specific packages detected)")

        lines.append("")
        lines.append("═══════════════════════════════════════════════════════")
        return "\n".join(lines)
