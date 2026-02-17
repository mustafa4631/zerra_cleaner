"""
GK Healter — Pardus-Specific Analyzer Module

Provides diagnostics, repo health checks, and version analysis
tailored to Pardus and Debian-based distributions.
"""

import os
import subprocess
import shutil
import logging
from typing import Dict, List, Optional, Any

logger = logging.getLogger("gk-healter.pardus")


class PardusAnalyzer:
    """
    Pardus/Debian-specific system analysis engine.

    Features:
    - Pardus version and release detection
    - APT repository health checks
    - Broken package detection
    - Pardus-specific service analysis
    - Package conflict detection
    - Update advisory engine
    """

    # Known Pardus-specific services
    PARDUS_SERVICES = [
        "pardus-software-center",
        "pardus-power-manager",
        "pardus-lightdm-greeter",
        "pardus-locales",
        "pardus-night-light",
        "pardus-mycomputer",
        "pardus-package-installer",
        "pardus-usb-formatter",
    ]

    def __init__(self) -> None:
        self._is_pardus: Optional[bool] = None
        self._pardus_version: Optional[str] = None
        self._codename: Optional[str] = None

    # ── Distribution Detection ───────────────────────────────────────────────

    def is_pardus(self) -> bool:
        """Check if the running system is Pardus."""
        if self._is_pardus is not None:
            return self._is_pardus

        self._is_pardus = False
        try:
            if os.path.exists("/etc/os-release"):
                with open("/etc/os-release", "r") as f:
                    content = f.read().lower()
                    if "pardus" in content:
                        self._is_pardus = True
            # Fallback: check lsb_release
            if not self._is_pardus and shutil.which("lsb_release"):
                result = subprocess.run(
                    ["lsb_release", "-is"],
                    capture_output=True, text=True, timeout=5
                )
                if result.returncode == 0 and "pardus" in result.stdout.lower():
                    self._is_pardus = True
        except Exception as e:
            logger.warning("Could not detect distribution: %s", e)
        return self._is_pardus

    def is_debian_based(self) -> bool:
        """Check if the running system is Debian-based (Pardus, Ubuntu, etc.)."""
        return shutil.which("apt-get") is not None

    def get_pardus_version(self) -> Dict[str, str]:
        """
        Returns Pardus/Debian version details.

        Returns:
            dict with keys: name, version, codename, base
        """
        info: Dict[str, str] = {
            "name": "Unknown",
            "version": "Unknown",
            "codename": "Unknown",
            "base": "Unknown",
        }
        try:
            if os.path.exists("/etc/os-release"):
                with open("/etc/os-release", "r") as f:
                    for line in f:
                        line = line.strip()
                        if line.startswith("PRETTY_NAME="):
                            info["name"] = line.split("=", 1)[1].strip('"')
                        elif line.startswith("VERSION_ID="):
                            info["version"] = line.split("=", 1)[1].strip('"')
                        elif line.startswith("VERSION_CODENAME="):
                            info["codename"] = line.split("=", 1)[1].strip('"')
                        elif line.startswith("ID_LIKE="):
                            info["base"] = line.split("=", 1)[1].strip('"')
                        elif line.startswith("ID=") and info["base"] == "Unknown":
                            info["base"] = line.split("=", 1)[1].strip('"')

            self._pardus_version = info["version"]
            self._codename = info["codename"]
        except Exception as e:
            logger.error("Failed to read OS version: %s", e)
        return info

    # ── APT Repository Health ────────────────────────────────────────────────

    def check_repo_health(self) -> Dict[str, Any]:
        """
        Checks the health of APT repositories.

        Returns:
            dict with keys:
                - total_repos: int
                - active_repos: int
                - disabled_repos: int
                - pardus_repos: int
                - third_party_repos: int
                - errors: list[str]
        """
        result: Dict[str, Any] = {
            "total_repos": 0,
            "active_repos": 0,
            "disabled_repos": 0,
            "pardus_repos": 0,
            "third_party_repos": 0,
            "errors": [],
        }

        if not self.is_debian_based():
            result["errors"].append("Not a Debian-based system")
            return result

        sources_dirs = ["/etc/apt/sources.list.d"]
        sources_files = ["/etc/apt/sources.list"]

        # Gather all .list and .sources files
        all_files: List[str] = []
        for sf in sources_files:
            if os.path.exists(sf):
                all_files.append(sf)
        for sd in sources_dirs:
            if os.path.isdir(sd):
                for fname in os.listdir(sd):
                    if fname.endswith((".list", ".sources")):
                        all_files.append(os.path.join(sd, fname))

        for fpath in all_files:
            try:
                with open(fpath, "r") as f:
                    for line in f:
                        stripped = line.strip()
                        if not stripped or stripped.startswith("#"):
                            if stripped.startswith("#") and ("deb " in stripped or "deb-src " in stripped):
                                result["disabled_repos"] += 1
                                result["total_repos"] += 1
                            continue
                        if stripped.startswith("deb ") or stripped.startswith("deb-src "):
                            result["total_repos"] += 1
                            result["active_repos"] += 1
                            if "pardus" in stripped.lower() or "depo.pardus.org.tr" in stripped:
                                result["pardus_repos"] += 1
                            elif "debian.org" not in stripped:
                                result["third_party_repos"] += 1
            except PermissionError:
                result["errors"].append(f"Permission denied: {fpath}")
            except Exception as e:
                result["errors"].append(f"Error reading {fpath}: {e}")

        return result

    # ── Broken Packages ──────────────────────────────────────────────────────

    def check_broken_packages(self) -> Dict[str, Any]:
        """
        Detect broken or unconfigured packages using dpkg and apt.

        Returns:
            dict with keys: broken_count, packages, fixable
        """
        result: Dict[str, Any] = {
            "broken_count": 0,
            "packages": [],
            "fixable": False,
        }

        if not shutil.which("dpkg"):
            return result

        try:
            # dpkg --audit lists packages with issues
            cmd = ["dpkg", "--audit"]
            proc = subprocess.run(
                cmd, capture_output=True, text=True, timeout=15
            )
            if proc.stdout.strip():
                lines = [l for l in proc.stdout.strip().split("\n") if l.strip()]
                result["broken_count"] = len(lines)
                result["packages"] = lines[:20]  # cap at 20

            # Also check dpkg -l for packages in bad state (not 'ii')
            cmd2 = ["dpkg", "-l"]
            proc2 = subprocess.run(
                cmd2, capture_output=True, text=True, timeout=15
            )
            if proc2.returncode == 0:
                for line in proc2.stdout.split("\n"):
                    if line and len(line) > 3 and not line.startswith("ii") and not line.startswith("Desired") and not line.startswith("|") and not line.startswith("+"):
                        # Lines starting with 'rc', 'iU', 'iF' etc. indicate issues
                        state = line[:2].strip()
                        if state and state not in ("ii", ""):
                            pkg_parts = line.split()
                            if len(pkg_parts) >= 2:
                                result["packages"].append(
                                    f"[{state}] {pkg_parts[1]}"
                                )
                                result["broken_count"] += 1

            # Check if fix is likely possible
            if result["broken_count"] > 0 and shutil.which("apt-get"):
                result["fixable"] = True

        except subprocess.TimeoutExpired:
            logger.warning("dpkg audit timed out")
        except Exception as e:
            logger.error("Broken package check failed: %s", e)

        return result

    def get_fix_broken_command(self) -> List[str]:
        """Returns the pkexec command to fix broken packages."""
        return ["pkexec", "apt-get", "install", "-f", "-y"]

    # ── Pardus Service Analysis ──────────────────────────────────────────────

    def check_pardus_services(self) -> List[Dict[str, str]]:
        """
        Checks the status of known Pardus-specific packages/services.

        Returns:
            List of dicts with keys: name, installed, status
        """
        results: List[Dict[str, str]] = []

        if not shutil.which("dpkg-query"):
            return results

        for pkg in self.PARDUS_SERVICES:
            info: Dict[str, str] = {
                "name": pkg,
                "installed": "unknown",
                "status": "unknown",
            }
            try:
                cmd = ["dpkg-query", "-W", "-f=${Status}", pkg]
                proc = subprocess.run(
                    cmd, capture_output=True, text=True, timeout=5
                )
                if proc.returncode == 0 and "install ok installed" in proc.stdout:
                    info["installed"] = "yes"
                    info["status"] = "installed"
                else:
                    info["installed"] = "no"
                    info["status"] = "not-installed"
            except subprocess.TimeoutExpired:
                info["status"] = "timeout"
            except Exception:
                info["status"] = "error"

            results.append(info)
        return results

    # ── Update Advisory ──────────────────────────────────────────────────────

    def check_available_updates(self) -> Dict[str, Any]:
        """
        Checks for available package updates.

        Returns:
            dict with keys: upgradable_count, security_count, packages
        """
        result: Dict[str, Any] = {
            "upgradable_count": 0,
            "security_count": 0,
            "packages": [],
        }

        if not shutil.which("apt"):
            return result

        try:
            cmd = ["apt", "list", "--upgradable"]
            proc = subprocess.run(
                cmd, capture_output=True, text=True, timeout=30
            )
            if proc.returncode == 0:
                for line in proc.stdout.split("\n"):
                    if "/" in line and "upgradable" in line.lower():
                        result["upgradable_count"] += 1
                        pkg_name = line.split("/")[0]
                        result["packages"].append(pkg_name)
                        if "security" in line.lower():
                            result["security_count"] += 1

        except subprocess.TimeoutExpired:
            logger.warning("Update check timed out")
        except Exception as e:
            logger.error("Update check failed: %s", e)

        return result

    # ── Package Conflict Detection ───────────────────────────────────────────

    def check_held_packages(self) -> List[str]:
        """Returns list of packages that are held back from updates."""
        held: List[str] = []

        if not shutil.which("apt-mark"):
            return held

        try:
            cmd = ["apt-mark", "showhold"]
            proc = subprocess.run(
                cmd, capture_output=True, text=True, timeout=10
            )
            if proc.returncode == 0:
                held = [l.strip() for l in proc.stdout.strip().split("\n") if l.strip()]
        except Exception as e:
            logger.error("Hold check failed: %s", e)

        return held

    # ── Aggregate Diagnostics ────────────────────────────────────────────────

    def run_full_diagnostics(self) -> Dict[str, Any]:
        """
        Run all Pardus-specific diagnostics and return a unified report.

        Returns:
            dict with all diagnostic results keyed by analysis type
        """
        report: Dict[str, Any] = {
            "distribution": self.get_pardus_version(),
            "is_pardus": self.is_pardus(),
            "is_debian_based": self.is_debian_based(),
            "repo_health": self.check_repo_health(),
            "broken_packages": self.check_broken_packages(),
            "available_updates": self.check_available_updates(),
            "held_packages": self.check_held_packages(),
        }

        # Only check Pardus services if on Pardus or Debian-based
        if report["is_debian_based"]:
            report["pardus_services"] = self.check_pardus_services()
        else:
            report["pardus_services"] = []

        return report
