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

    # ── Service Dependency Graph ─────────────────────────────────────────────

    def get_service_dependency_graph(self) -> Dict[str, Any]:
        """Build a dependency graph for active systemd services.

        Maps each running service to its ``Requires``, ``Wants``, and
        ``After`` dependencies.  Also flags services that are in a
        *failed* or *inactive (dead)* state.

        Returns:
            dict with keys:
                - services: dict[str, dict] — per-service detail
                - failed: list[str]
                - total_active: int
        """
        result: Dict[str, Any] = {
            "services": {},
            "failed": [],
            "total_active": 0,
        }

        if not shutil.which("systemctl"):
            return result

        try:
            # List all loaded service units
            proc = subprocess.run(
                ["systemctl", "list-units", "--type=service",
                 "--no-pager", "--no-legend", "--plain"],
                capture_output=True, text=True, timeout=10,
            )
            if proc.returncode != 0:
                return result

            for line in proc.stdout.strip().splitlines():
                parts = line.split(None, 4)
                if len(parts) < 4:
                    continue
                unit_name, _load, active, sub = parts[:4]
                if not unit_name.endswith(".service"):
                    continue

                if active == "active":
                    result["total_active"] += 1
                if sub == "failed":
                    result["failed"].append(unit_name)

                # Query dependencies for this unit
                svc_info: Dict[str, Any] = {
                    "state": f"{active}/{sub}",
                    "requires": [],
                    "wants": [],
                    "after": [],
                }
                try:
                    dep_proc = subprocess.run(
                        ["systemctl", "show", unit_name,
                         "--property=Requires,Wants,After",
                         "--no-pager"],
                        capture_output=True, text=True, timeout=5,
                    )
                    if dep_proc.returncode == 0:
                        for dep_line in dep_proc.stdout.strip().splitlines():
                            if "=" not in dep_line:
                                continue
                            k, v = dep_line.split("=", 1)
                            deps = [
                                d.strip() for d in v.split()
                                if d.strip() and d.strip() != unit_name
                            ]
                            if k == "Requires":
                                svc_info["requires"] = deps
                            elif k == "Wants":
                                svc_info["wants"] = deps
                            elif k == "After":
                                svc_info["after"] = deps
                except Exception:
                    pass

                result["services"][unit_name] = svc_info

        except subprocess.TimeoutExpired:
            logger.warning("Service dependency scan timed out")
        except Exception as e:
            logger.error("Service dependency scan error: %s", e)

        return result

    # ── Repository Trust Score ───────────────────────────────────────────────

    def calculate_repo_trust_score(self) -> Dict[str, Any]:
        """Calculate a trust score (0-100) for configured APT repos.

        Scoring factors:
        - Official Pardus/Debian repos → high trust
        - Signed third-party repos → medium trust
        - Unsigned / unknown repos → low trust
        - Expired GPG keys → penalty

        Returns:
            dict with keys:
                - score: int (0-100)
                - details: list[dict] — per-repo breakdown
                - expired_keys: list[str]
        """
        result: Dict[str, Any] = {
            "score": 100,
            "details": [],
            "expired_keys": [],
        }

        if not self.is_debian_based():
            result["score"] = 0
            return result

        # 1. Check for expired APT keys
        if shutil.which("apt-key"):
            try:
                proc = subprocess.run(
                    ["apt-key", "list"],
                    capture_output=True, text=True, timeout=10,
                )
                if proc.returncode == 0:
                    for line in proc.stdout.splitlines():
                        if "expired" in line.lower():
                            result["expired_keys"].append(line.strip())
                            result["score"] = max(0, result["score"] - 10)
            except Exception:
                pass

        # 2. Scan repo sources for trust indicators
        repo_health = self.check_repo_health()
        third_party = repo_health.get("third_party_repos", 0)
        pardus_repos = repo_health.get("pardus_repos", 0)
        total = repo_health.get("active_repos", 0)

        if total == 0:
            result["score"] = 0
            result["details"].append({
                "issue": "no_repos",
                "severity": "critical",
                "message": "No active APT repositories configured",
            })
            return result

        # Deduct for third-party repos (each adds risk)
        if third_party > 0:
            penalty = min(30, third_party * 8)
            result["score"] = max(0, result["score"] - penalty)
            result["details"].append({
                "issue": "third_party_repos",
                "severity": "warning",
                "message": (
                    f"{third_party} third-party repo(s) detected — "
                    "each adds supply-chain risk"
                ),
            })

        # Bonus for official Pardus repos
        if pardus_repos > 0:
            result["details"].append({
                "issue": "official_pardus",
                "severity": "info",
                "message": (
                    f"{pardus_repos} official Pardus repo(s) configured"
                ),
            })

        # 3. Check /etc/apt/trusted.gpg.d for key count
        trusted_dir = "/etc/apt/trusted.gpg.d"
        if os.path.isdir(trusted_dir):
            try:
                key_files = [
                    f for f in os.listdir(trusted_dir)
                    if f.endswith((".gpg", ".asc"))
                ]
                if len(key_files) < total:
                    result["score"] = max(0, result["score"] - 10)
                    result["details"].append({
                        "issue": "missing_keys",
                        "severity": "warning",
                        "message": (
                            f"Only {len(key_files)} signing key(s) for "
                            f"{total} repo(s)"
                        ),
                    })
            except PermissionError:
                pass

        return result

    # ── Repair Simulation ────────────────────────────────────────────────────

    def simulate_repair(self) -> Dict[str, Any]:
        """Dry-run common repair actions and report what *would* change.

        Actions tested (non-destructive):
        1. ``apt-get install -f --dry-run``  (fix broken installs)
        2. ``dpkg --configure -a --dry-run`` (configure pending)
        3. ``apt-get autoremove --dry-run``   (remove orphans)

        Returns:
            dict with keys for each action containing stdout preview
            and a boolean ``changes_needed``.
        """
        result: Dict[str, Any] = {
            "fix_broken": {"output": "", "changes_needed": False},
            "configure_pending": {"output": "", "changes_needed": False},
            "autoremove": {"output": "", "changes_needed": False,
                           "removable_count": 0},
        }

        if not self.is_debian_based():
            return result

        # 1. Fix broken
        if shutil.which("apt-get"):
            try:
                proc = subprocess.run(
                    ["apt-get", "install", "-f", "--dry-run"],
                    capture_output=True, text=True, timeout=30,
                )
                output = proc.stdout.strip()
                result["fix_broken"]["output"] = output
                result["fix_broken"]["changes_needed"] = (
                    "newly installed" in output.lower()
                    or "to remove" in output.lower()
                    or "upgraded" in output.lower()
                )
            except Exception as e:
                result["fix_broken"]["output"] = str(e)

        # 2. Configure pending
        if shutil.which("dpkg"):
            try:
                proc = subprocess.run(
                    ["dpkg", "--configure", "-a", "--dry-run"],
                    capture_output=True, text=True, timeout=30,
                )
                output = (proc.stdout + proc.stderr).strip()
                result["configure_pending"]["output"] = output
                result["configure_pending"]["changes_needed"] = bool(output)
            except Exception as e:
                result["configure_pending"]["output"] = str(e)

        # 3. Autoremove
        if shutil.which("apt-get"):
            try:
                proc = subprocess.run(
                    ["apt-get", "autoremove", "--dry-run"],
                    capture_output=True, text=True, timeout=30,
                )
                output = proc.stdout.strip()
                result["autoremove"]["output"] = output
                # Count removable packages
                for line in output.splitlines():
                    if "to remove" in line.lower():
                        parts = line.split()
                        for i, p in enumerate(parts):
                            if p.isdigit() and i + 1 < len(parts):
                                if "remove" in parts[i + 1].lower():
                                    result["autoremove"]["removable_count"] = int(p)
                                    break
                result["autoremove"]["changes_needed"] = (
                    result["autoremove"]["removable_count"] > 0
                )
            except Exception as e:
                result["autoremove"]["output"] = str(e)

        return result

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
            report["service_dependencies"] = self.get_service_dependency_graph()
            report["repo_trust_score"] = self.calculate_repo_trust_score()
            report["repair_simulation"] = self.simulate_repair()
        else:
            report["pardus_services"] = []
            report["service_dependencies"] = {}
            report["repo_trust_score"] = {"score": 0, "details": []}
            report["repair_simulation"] = {}

        return report
