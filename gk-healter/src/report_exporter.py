"""
GK Healter — Report Exporter Module

Generates comprehensive system analysis reports in plain-text (.txt)
and HTML (.html) formats.  No heavy external dependencies are required.

Exported reports include:
  • System identity and Pardus verification
  • Health metrics and score
  • Security audit summary
  • Pardus-specific diagnostics
  • Disk usage analysis
  • Service and log status
  • Cleaning history
  • Timestamp and generation metadata
"""

import os
import datetime
import json
import logging
from typing import Dict, Any, Optional, List

logger = logging.getLogger("gk-healter.report-exporter")


class ReportExporter:
    """Generates exportable system analysis reports."""

    def __init__(self) -> None:
        self._default_dir = os.path.expanduser("~/Documents")

    # ── Report Data Collection ───────────────────────────────────────────────

    @staticmethod
    def collect_report_data(
        pardus_verification: Optional[Dict[str, Any]] = None,
        health_metrics: Optional[Dict[str, Any]] = None,
        health_status: str = "",
        security_results: Optional[Dict[str, Any]] = None,
        pardus_diagnostics: Optional[Dict[str, Any]] = None,
        cleaning_history: Optional[List[Dict[str, Any]]] = None,
        large_files: Optional[list] = None,
        failed_services: Optional[list] = None,
        error_count_24h: int = 0,
    ) -> Dict[str, Any]:
        """Assemble all report data into a unified structure.

        All parameters are optional — missing sections are simply
        omitted from the final report.

        Returns:
            Dict with all available report sections.
        """
        return {
            "generated_at": datetime.datetime.now().isoformat(),
            "generator": "GK Healter Report Exporter",
            "generator_version": _get_version(),
            "pardus_verification": pardus_verification,
            "health": {
                "metrics": health_metrics,
                "status": health_status,
            } if health_metrics else None,
            "security": security_results,
            "pardus_diagnostics": pardus_diagnostics,
            "cleaning_history": cleaning_history[:10] if cleaning_history else [],
            "large_files": large_files,
            "services": {
                "failed": failed_services or [],
                "error_count_24h": error_count_24h,
            },
        }

    # ── TXT Export ───────────────────────────────────────────────────────────

    def export_txt(
        self,
        data: Dict[str, Any],
        filepath: Optional[str] = None,
    ) -> str:
        """Export report data as a plain-text file.

        Args:
            data: Report data dict from ``collect_report_data``.
            filepath: Destination path. Auto-generated if omitted.

        Returns:
            Absolute path of the written file.
        """
        if not filepath:
            filepath = self._auto_path("txt")

        lines = self._render_txt(data)
        text = "\n".join(lines)

        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(text)

        logger.info("TXT report exported to %s", filepath)
        return filepath

    # ── HTML Export ───────────────────────────────────────────────────────────

    def export_html(
        self,
        data: Dict[str, Any],
        filepath: Optional[str] = None,
    ) -> str:
        """Export report data as an HTML file.

        Uses inline CSS for a clean, printable appearance.
        No external dependencies required.

        Args:
            data: Report data dict from ``collect_report_data``.
            filepath: Destination path. Auto-generated if omitted.

        Returns:
            Absolute path of the written file.
        """
        if not filepath:
            filepath = self._auto_path("html")

        html = self._render_html(data)

        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(html)

        logger.info("HTML report exported to %s", filepath)
        return filepath

    # ── JSON Export ───────────────────────────────────────────────────────────

    def export_json(
        self,
        data: Dict[str, Any],
        filepath: Optional[str] = None,
    ) -> str:
        """Export report data as a JSON file.

        Args:
            data: Report data dict.
            filepath: Destination path. Auto-generated if omitted.

        Returns:
            Absolute path of the written file.
        """
        if not filepath:
            filepath = self._auto_path("json")

        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2, default=str)

        logger.info("JSON report exported to %s", filepath)
        return filepath

    # ── Internal Renderers ───────────────────────────────────────────────────

    def _render_txt(self, data: Dict[str, Any]) -> List[str]:
        """Render report as plain-text lines."""
        lines: List[str] = []
        _hr = "═" * 60

        lines.append(_hr)
        lines.append("  GK Healter — System Analysis Report")
        lines.append(_hr)
        lines.append("")
        lines.append(f"Generated : {data.get('generated_at', 'N/A')}")
        lines.append(f"Version   : {data.get('generator_version', 'N/A')}")
        lines.append("")

        # ── Pardus Verification ──
        pv = data.get("pardus_verification")
        if pv:
            lines.append("── Pardus Verification ────────────────────────────")
            lines.append(f"  Is Pardus      : {'Yes' if pv.get('is_pardus') else 'No'}")
            os_rel = pv.get("os_release", {})
            lines.append(f"  Distribution   : {os_rel.get('PRETTY_NAME', 'Unknown')}")
            lines.append(f"  Version        : {os_rel.get('VERSION_ID', 'Unknown')}")
            lines.append(f"  Codename       : {os_rel.get('VERSION_CODENAME', 'Unknown')}")
            lsb = pv.get("lsb_release", {})
            if lsb:
                lines.append(f"  LSB Distributor: {lsb.get('distributor_id', 'N/A')}")
                lines.append(f"  LSB Release    : {lsb.get('release', 'N/A')}")
            hw = pv.get("hardware", {})
            lines.append(f"  Kernel         : {hw.get('kernel', 'N/A')}")
            lines.append(f"  Architecture   : {hw.get('architecture', 'N/A')}")
            lines.append(f"  CPU Cores      : {hw.get('cpu_count', 'N/A')}")
            ram_gb = hw.get("total_ram_bytes", 0) / (1024 ** 3)
            lines.append(f"  Total RAM      : {ram_gb:.1f} GB")
            lines.append(f"  Desktop        : {pv.get('desktop_environment', 'N/A')}")
            lines.append(f"  Hostname       : {pv.get('hostname', 'N/A')}")

            pardus_pkgs = pv.get("pardus_packages", [])
            if pardus_pkgs:
                lines.append(f"  Pardus Packages: {', '.join(pardus_pkgs)}")
            lines.append("")

        # ── Health ──
        health = data.get("health")
        if health and health.get("metrics"):
            m = health["metrics"]
            lines.append("── System Health ──────────────────────────────────")
            lines.append(f"  Health Score : {m.get('score', 'N/A')}/100")
            lines.append(f"  Status       : {health.get('status', 'N/A')}")
            lines.append(f"  CPU Usage    : {m.get('cpu', 0):.1f}%")
            lines.append(f"  RAM Usage    : {m.get('ram', 0):.1f}%")
            lines.append(f"  Disk Usage   : {m.get('disk', 0):.1f}%")
            lines.append("")

        # ── Security ──
        sec = data.get("security")
        if sec:
            summary = sec.get("summary", {})
            lines.append("── Security Audit ────────────────────────────────")
            lines.append(f"  Total Issues : {summary.get('total_issues', 0)}")
            lines.append(f"  Critical     : {summary.get('critical', 0)}")
            lines.append(f"  High         : {summary.get('high', 0)}")
            lines.append(f"  Warning      : {summary.get('warning', 0)}")

            for item in sec.get("world_writable", [])[:5]:
                lines.append(f"    [WW] {item.get('path', '')}")
            for item in sec.get("suid_binaries", [])[:5]:
                lines.append(f"    [SUID] {item.get('path', '')}")
            for item in sec.get("sudoers_audit", []):
                lines.append(f"    [SUDO] {item.get('content', '')}")
            for item in sec.get("ssh_config", []):
                lines.append(f"    [SSH] {item.get('recommendation', '')}")

            logins = sec.get("failed_logins", {})
            if logins.get("count", 0) > 0:
                lines.append(f"    [AUTH] {logins['count']} failed login attempts")
            lines.append("")

        # ── Pardus Diagnostics ──
        pd = data.get("pardus_diagnostics")
        if pd:
            lines.append("── Pardus Diagnostics ────────────────────────────")
            dist = pd.get("distribution", {})
            lines.append(f"  Distribution  : {dist.get('name', 'N/A')}")
            repo = pd.get("repo_health", {})
            lines.append(f"  Active Repos  : {repo.get('active_repos', 0)}")
            lines.append(f"  Pardus Repos  : {repo.get('pardus_repos', 0)}")
            lines.append(f"  3rd-Party     : {repo.get('third_party_repos', 0)}")
            broken = pd.get("broken_packages", {})
            lines.append(f"  Broken Pkgs   : {broken.get('broken_count', 0)}")
            updates = pd.get("available_updates", {})
            lines.append(f"  Updates Avail : {updates.get('upgradable_count', 0)}")
            trust = pd.get("repo_trust_score", {})
            lines.append(f"  Trust Score   : {trust.get('score', 'N/A')}/100")

            mirror = pd.get("mirror_health", {})
            if mirror:
                lines.append(
                    f"  Mirror Status : "
                    f"{'Reachable' if mirror.get('reachable') else 'Unreachable'}"
                    f" ({mirror.get('response_time_ms', 0)} ms)"
                )

            compat = pd.get("release_compatibility", {})
            if compat:
                lines.append(
                    f"  Release Compat: "
                    f"{'OK' if compat.get('compatible') else 'MISMATCH'}"
                )

            pkg_log = pd.get("package_log_analysis", {})
            if pkg_log and pkg_log.get("total_operations", 0) > 0:
                lines.append(
                    f"  Pkg Activity  : {pkg_log['total_operations']} ops "
                    f"(I:{pkg_log.get('installs', 0)} "
                    f"R:{pkg_log.get('removes', 0)} "
                    f"U:{pkg_log.get('upgrades', 0)})"
                )
            lines.append("")

        # ── Services ──
        svcs = data.get("services")
        if svcs:
            lines.append("── Service Status ────────────────────────────────")
            failed = svcs.get("failed", [])
            lines.append(f"  Failed Services   : {len(failed)}")
            for s in failed[:10]:
                lines.append(f"    • {s}")
            lines.append(f"  Errors (24h)      : {svcs.get('error_count_24h', 0)}")
            lines.append("")

        # ── Large Files ──
        lf = data.get("large_files")
        if lf:
            lines.append("── Large Files (>100 MB) ─────────────────────────")
            for f in lf[:10]:
                lines.append(f"  {f.get('size', '?')}  {f.get('path', '?')}")
            lines.append("")

        # ── Cleaning History ──
        hist = data.get("cleaning_history")
        if hist:
            lines.append("── Recent Cleaning History ───────────────────────")
            for entry in hist[:5]:
                lines.append(
                    f"  {entry.get('date', '?')}  "
                    f"{entry.get('total_freed', '?')}  "
                    f"{entry.get('status', '?')}  "
                    f"[{entry.get('categories', '')}]"
                )
            lines.append("")

        lines.append(_hr)
        lines.append("  Report generated by GK Healter")
        lines.append("  https://github.com/GK-Developers/GK-Healter")
        lines.append(_hr)
        return lines

    def _render_html(self, data: Dict[str, Any]) -> str:
        """Render report as self-contained HTML with inline CSS."""
        txt_lines = self._render_txt(data)

        # Escape HTML entities
        import html as _html
        body_text = _html.escape("\n".join(txt_lines))

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>GK Healter — System Report</title>
<style>
  body {{
    font-family: 'Segoe UI', 'DejaVu Sans', Arial, sans-serif;
    background: #f8f9fa;
    color: #212529;
    max-width: 800px;
    margin: 2rem auto;
    padding: 0 1rem;
  }}
  .report {{
    background: #fff;
    border: 1px solid #dee2e6;
    border-radius: 8px;
    padding: 2rem;
    box-shadow: 0 2px 8px rgba(0,0,0,0.06);
  }}
  pre {{
    font-family: 'JetBrains Mono', 'Fira Code', 'DejaVu Sans Mono', monospace;
    font-size: 0.85rem;
    line-height: 1.6;
    white-space: pre-wrap;
    word-wrap: break-word;
  }}
  h1 {{
    text-align: center;
    color: #0d6efd;
    margin-bottom: 0.5rem;
  }}
  .meta {{
    text-align: center;
    color: #6c757d;
    font-size: 0.9rem;
    margin-bottom: 2rem;
  }}
  @media print {{
    body {{ background: #fff; margin: 0; }}
    .report {{ border: none; box-shadow: none; }}
  }}
</style>
</head>
<body>
<div class="report">
  <h1>GK Healter</h1>
  <p class="meta">System Analysis Report — {data.get('generated_at', 'N/A')}</p>
  <pre>{body_text}</pre>
</div>
</body>
</html>"""

    # ── Helpers ──────────────────────────────────────────────────────────────

    def _auto_path(self, ext: str) -> str:
        """Generate a timestamped filename in the user's Documents directory."""
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"gk-healter-report_{ts}.{ext}"
        return os.path.join(self._default_dir, filename)


def _get_version() -> str:
    """Retrieve application version string."""
    try:
        from src.__init__ import __version__
        return __version__
    except Exception:
        return "0.1.5"
