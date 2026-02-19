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

    # ── Pardus Mirror Health ────────────────────────────────────────────────

    def check_pardus_mirror_health(self) -> Dict[str, Any]:
        """Test reachability and response time of Pardus APT mirrors.

        Performs HTTP HEAD requests against the official Pardus repository
        and known mirrors.  Returns timing information so the UI can warn
        the user about slow or unreachable mirrors.

        Returns:
            dict with keys:
                - reachable: bool — at least one mirror responded
                - dns_resolved: bool — hostname resolved successfully
                - response_time_ms: int — fastest mirror response (ms)
                - mirrors: list[dict] — per-mirror detail
                - recommended_mirror: str — URL of the fastest mirror
        """
        import urllib.request
        import urllib.error
        import socket
        import time as _time

        MIRRORS = [
            "http://depo.pardus.org.tr/pardus",
            "http://depo2.pardus.org.tr/pardus",
            "http://mirror.yirmibir.org/pardus",
        ]

        result: Dict[str, Any] = {
            "reachable": False,
            "dns_resolved": False,
            "response_time_ms": 0,
            "mirrors": [],
            "recommended_mirror": "",
        }

        fastest_ms = float("inf")

        for url in MIRRORS:
            info: Dict[str, Any] = {
                "url": url,
                "reachable": False,
                "response_time_ms": 0,
                "error": None,
            }
            try:
                # DNS resolution check (first mirror only for flag)
                if not result["dns_resolved"]:
                    host = url.split("//")[1].split("/")[0]
                    socket.getaddrinfo(host, 80, socket.AF_INET)
                    result["dns_resolved"] = True

                req = urllib.request.Request(url, method="HEAD")
                start = _time.monotonic()
                with urllib.request.urlopen(req, timeout=5) as resp:
                    elapsed = (_time.monotonic() - start) * 1000
                    if resp.status < 400:
                        info["reachable"] = True
                        info["response_time_ms"] = int(elapsed)
                        result["reachable"] = True
                        if elapsed < fastest_ms:
                            fastest_ms = elapsed
                            result["response_time_ms"] = int(elapsed)
                            result["recommended_mirror"] = url
            except (urllib.error.URLError, socket.timeout, OSError) as e:
                info["error"] = str(e)
            except Exception as e:
                info["error"] = str(e)

            result["mirrors"].append(info)

        return result

    # ── Pardus Release Compatibility ─────────────────────────────────────────

    def check_pardus_release_compatibility(self) -> Dict[str, Any]:
        """Verify that APT sources match the running Pardus release.

        Compares ``VERSION_CODENAME`` from ``/etc/os-release`` against the
        suite / codename strings found in ``/etc/apt/sources.list`` and
        ``/etc/apt/sources.list.d/*.list``.  Mismatches indicate that a
        repository was configured for a different Pardus release which can
        cause dependency breakage.

        Returns:
            dict with keys:
                - compatible: bool
                - os_codename: str
                - repo_codenames: list[str]
                - mismatched_repos: list[str] — lines with wrong codename
        """
        result: Dict[str, Any] = {
            "compatible": True,
            "os_codename": "",
            "repo_codenames": [],
            "mismatched_repos": [],
        }

        # 1. Read OS codename
        version_info = self.get_pardus_version()
        os_codename = version_info.get("codename", "").strip().lower()
        result["os_codename"] = os_codename

        if not os_codename or os_codename == "unknown":
            return result  # Cannot compare without a codename

        # 2. Scan APT sources for codenames
        sources_files: List[str] = []
        if os.path.exists("/etc/apt/sources.list"):
            sources_files.append("/etc/apt/sources.list")
        sources_dir = "/etc/apt/sources.list.d"
        if os.path.isdir(sources_dir):
            try:
                for fname in os.listdir(sources_dir):
                    if fname.endswith(".list"):
                        sources_files.append(os.path.join(sources_dir, fname))
            except OSError:
                pass

        seen_codenames: set = set()

        for fpath in sources_files:
            try:
                with open(fpath, "r") as f:
                    for line in f:
                        stripped = line.strip()
                        if not stripped or stripped.startswith("#"):
                            continue
                        if not (stripped.startswith("deb ") or stripped.startswith("deb-src ")):
                            continue
                        # Only check Pardus repos
                        if "pardus" not in stripped.lower():
                            continue
                        # Extract codename: deb URL suite component...
                        parts = stripped.split()
                        if len(parts) >= 3:
                            suite = parts[2].strip().lower()
                            # Handle suite variants like "yirmiuc-deb"
                            base_suite = suite.split("-")[0]
                            seen_codenames.add(base_suite)
                            if base_suite != os_codename:
                                result["compatible"] = False
                                result["mismatched_repos"].append(stripped)
            except (PermissionError, OSError):
                continue

        result["repo_codenames"] = sorted(seen_codenames)
        return result

    # ── Pardus APT/dpkg Log Analysis ─────────────────────────────────────────

    def analyze_pardus_logs(self, days: int = 7) -> Dict[str, Any]:
        """Analyze dpkg and APT logs for recent package activity.

        Parses ``/var/log/dpkg.log`` and ``/var/log/apt/history.log`` to
        summarize install / remove / upgrade counts over the last *days*
        days.  Failed operations (dpkg errors) are also captured.

        Args:
            days: Number of days to look back (default 7).

        Returns:
            dict with keys:
                - total_operations: int
                - installs: int
                - removes: int
                - upgrades: int
                - failed_operations: list[str]
                - last_update: str — ISO date of most recent dpkg action
                - days_since_update: int
        """
        import datetime as _dt

        result: Dict[str, Any] = {
            "total_operations": 0,
            "installs": 0,
            "removes": 0,
            "upgrades": 0,
            "failed_operations": [],
            "last_update": "",
            "days_since_update": -1,
        }

        cutoff = _dt.datetime.now() - _dt.timedelta(days=days)
        latest_date: Optional[_dt.datetime] = None

        dpkg_log = "/var/log/dpkg.log"
        if os.path.isfile(dpkg_log):
            try:
                with open(dpkg_log, "r") as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        # Format: "2026-02-18 10:23:15 status installed pkg ..."
                        parts = line.split(None, 3)
                        if len(parts) < 4:
                            continue
                        try:
                            ts = _dt.datetime.strptime(
                                f"{parts[0]} {parts[1]}", "%Y-%m-%d %H:%M:%S"
                            )
                        except ValueError:
                            continue
                        if ts < cutoff:
                            continue

                        action = parts[2].lower()
                        result["total_operations"] += 1

                        if latest_date is None or ts > latest_date:
                            latest_date = ts

                        if action == "install":
                            result["installs"] += 1
                        elif action == "remove" or action == "purge":
                            result["removes"] += 1
                        elif action == "upgrade":
                            result["upgrades"] += 1

                        # Detect errors
                        if "error" in line.lower() or "half-installed" in line.lower():
                            result["failed_operations"].append(line[:200])

            except (PermissionError, OSError) as e:
                logger.warning("Cannot read dpkg log: %s", e)

        # Also scan apt history
        apt_log = "/var/log/apt/history.log"
        if os.path.isfile(apt_log):
            try:
                with open(apt_log, "r") as f:
                    current_date: Optional[_dt.datetime] = None
                    for line in f:
                        line = line.strip()
                        if line.startswith("Start-Date:"):
                            try:
                                date_str = line.split(":", 1)[1].strip()
                                current_date = _dt.datetime.strptime(
                                    date_str, "%Y-%m-%d  %H:%M:%S"
                                )
                            except ValueError:
                                current_date = None
                        if current_date and current_date >= cutoff:
                            if line.startswith("Install:"):
                                count = line.count("(")
                                result["installs"] += max(count, 1)
                                result["total_operations"] += max(count, 1)
                            elif line.startswith("Remove:"):
                                count = line.count("(")
                                result["removes"] += max(count, 1)
                                result["total_operations"] += max(count, 1)
                            elif line.startswith("Upgrade:"):
                                count = line.count("(")
                                result["upgrades"] += max(count, 1)
                                result["total_operations"] += max(count, 1)
            except (PermissionError, OSError) as e:
                logger.warning("Cannot read apt history: %s", e)

        if latest_date:
            result["last_update"] = latest_date.strftime("%Y-%m-%d %H:%M:%S")
            result["days_since_update"] = (_dt.datetime.now() - latest_date).days

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
            report["mirror_health"] = self.check_pardus_mirror_health()
            report["release_compatibility"] = self.check_pardus_release_compatibility()
            report["package_log_analysis"] = self.analyze_pardus_logs()
        else:
            report["pardus_services"] = []
            report["service_dependencies"] = {}
            report["repo_trust_score"] = {"score": 0, "details": []}
            report["repair_simulation"] = {}
            report["mirror_health"] = {"reachable": False, "mirrors": []}
            report["release_compatibility"] = {"compatible": True}
            report["package_log_analysis"] = {"total_operations": 0}

        return report
