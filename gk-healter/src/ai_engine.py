"""
GK Healter — Hybrid AI Analysis Engine

Provides two layers of system analysis:

1. **LocalAnalysisEngine** — Always-available, offline rule-based analysis
   that produces actionable diagnostics from system metrics.

2. **AIEngine** — Optional cloud-based enrichment via OpenAI or Google
   Gemini APIs.  Falls back to the local engine when no API key is
   configured or when API calls fail.

This hybrid architecture ensures the tool is useful even without an
internet connection (a TEKNOFEST competition requirement).
"""

import json
import urllib.request
import urllib.error
import logging
from typing import Dict, List, Any

logger = logging.getLogger("gk-healter.ai")


# ── Local / Offline Analysis Engine ──────────────────────────────────────────


class LocalAnalysisEngine:
    """Rule-based system diagnostics — works completely offline."""

    # Threshold definitions: (warn, critical)
    THRESHOLDS: Dict[str, tuple] = {
        "cpu": (80, 95),
        "ram": (75, 90),
        "disk": (80, 95),
    }

    def analyse(
        self,
        metrics: Dict[str, Any],
        failed_services: List[str],
        error_count: int,
    ) -> Dict[str, Any]:
        """Produce a structured diagnostic report from raw metrics.

        Args:
            metrics: dict with keys ``cpu``, ``ram``, ``disk``, ``score``.
            failed_services: list of failed systemd unit names.
            error_count: number of journal anomalies (24 h).

        Returns:
            dict with ``summary``, ``issues`` (list), ``actions`` (list),
            ``risk_level`` (str: low | medium | high | critical).
        """
        issues: List[Dict[str, str]] = []
        actions: List[str] = []
        risk_level = "low"

        cpu = metrics.get("cpu", 0)
        ram = metrics.get("ram", 0)
        disk = metrics.get("disk", 0)
        score = metrics.get("score", 100)

        # ── Resource analysis ────────────────────────────────────────────
        for key, label, value in [
            ("cpu", "CPU", cpu),
            ("ram", "RAM", ram),
            ("disk", "Disk", disk),
        ]:
            warn, crit = self.THRESHOLDS[key]
            if value >= crit:
                issues.append({
                    "resource": key,
                    "severity": "critical",
                    "message": f"{label} usage critically high: {value}%",
                })
                risk_level = "critical"
                actions.append(self._resource_action(key, "critical"))
            elif value >= warn:
                issues.append({
                    "resource": key,
                    "severity": "warning",
                    "message": f"{label} usage elevated: {value}%",
                })
                if risk_level not in ("high", "critical"):
                    risk_level = "medium"
                actions.append(self._resource_action(key, "warning"))

        # ── Failed services ──────────────────────────────────────────────
        if failed_services:
            issues.append({
                "resource": "services",
                "severity": "high",
                "message": (
                    f"{len(failed_services)} failed service(s): "
                    + ", ".join(failed_services[:5])
                ),
            })
            if risk_level not in ("critical",):
                risk_level = "high"
            actions.append(
                "Run `systemctl --failed` and restart or mask the "
                "failing units."
            )

        # ── Journal anomalies ────────────────────────────────────────────
        if error_count > 100:
            issues.append({
                "resource": "journal",
                "severity": "high",
                "message": f"{error_count} journal anomalies in 24 h",
            })
            actions.append(
                "Inspect logs with `journalctl -p 3 -S -24h` to "
                "identify recurring errors."
            )
        elif error_count > 20:
            issues.append({
                "resource": "journal",
                "severity": "warning",
                "message": f"{error_count} journal anomalies in 24 h",
            })

        # ── Summary construction ─────────────────────────────────────────
        if not issues:
            summary = (
                f"System is healthy (score {score}/100). "
                "No issues detected."
            )
        else:
            summary = (
                f"System score {score}/100 — {len(issues)} issue(s) "
                f"detected, risk level: {risk_level}."
            )

        if not actions:
            actions.append("No immediate actions required.")

        return {
            "summary": summary,
            "issues": issues,
            "actions": actions,
            "risk_level": risk_level,
        }

    @staticmethod
    def _resource_action(key: str, severity: str) -> str:
        """Return a concrete action string for a resource alert."""
        tips = {
            "cpu": {
                "critical": (
                    "Identify CPU-hogging processes with "
                    "`top -o %CPU` and consider `nice`/`renice`."
                ),
                "warning": (
                    "Monitor CPU trends; check for background "
                    "compilation or indexing tasks."
                ),
            },
            "ram": {
                "critical": (
                    "Free memory: close unused applications, check for "
                    "memory leaks with `smem`, consider adding swap."
                ),
                "warning": (
                    "Review per-process memory with `ps aux --sort=-%mem`."
                ),
            },
            "disk": {
                "critical": (
                    "Immediately free disk space: `sudo apt autoremove`, "
                    "`journalctl --vacuum-size=100M`, clear caches."
                ),
                "warning": (
                    "Audit large files with `du -sh /* 2>/dev/null | "
                    "sort -rh | head` and clean old logs."
                ),
            },
        }
        return tips.get(key, {}).get(severity, "Investigate resource usage.")

    def format_as_text(self, report: Dict[str, Any]) -> str:
        """Render a local analysis report as human-readable text.

        Args:
            report: Output of :meth:`analyse`.

        Returns:
            Multi-line plain-text string.
        """
        lines = [f"Summary: {report['summary']}", ""]

        if report["issues"]:
            lines.append("Issues:")
            for issue in report["issues"]:
                severity = issue["severity"].upper()
                lines.append(f"  [{severity}] {issue['message']}")
            lines.append("")

        lines.append("Recommended Actions:")
        for i, action in enumerate(report["actions"], 1):
            lines.append(f"  {i}. {action}")

        return "\n".join(lines)


# ── Cloud AI Enrichment Engine ───────────────────────────────────────────────


class AIEngine:
    """Hybrid AI analysis: local engine + optional cloud enrichment.

    When no API key is configured the engine falls back transparently
    to :class:`LocalAnalysisEngine`.
    """

    # Timeout for HTTP requests (seconds)
    HTTP_TIMEOUT = 30

    def __init__(self) -> None:
        self.provider: str = "gemini"
        self.api_key: str = ""
        self.model: str = "gemini-2.5-flash"
        self.enabled: bool = False
        self._local = LocalAnalysisEngine()

    def configure(
        self,
        provider: str,
        api_key: str,
        model: str = "gemini-2.5-flash",
    ) -> None:
        """Set the AI provider credentials.

        Args:
            provider: ``"openai"`` or ``"gemini"``.
            api_key: API key string.
            model: Model identifier.
        """
        self.provider = provider
        self.api_key = api_key
        self.model = model
        self.enabled = bool(api_key)

    # ── Public API ───────────────────────────────────────────────────────

    def generate_insight(
        self,
        metrics: Dict[str, Any],
        failed_services: List[str],
        error_count: int,
    ) -> str:
        """Generate system insight text — hybrid strategy.

        Always runs the local engine first.  If a cloud provider is
        configured, attempts to enrich the result with AI-generated
        analysis.  On failure, returns the local report only.

        Args:
            metrics: System metrics dict.
            failed_services: List of failed unit names.
            error_count: Journal anomaly count.

        Returns:
            Human-readable insight string.
        """
        local_report = self._local.analyse(metrics, failed_services,
                                           error_count)
        local_text = self._local.format_as_text(local_report)

        if not self.enabled:
            return local_text

        try:
            prompt = self._construct_prompt(metrics, failed_services,
                                            error_count)
            if self.provider == "openai":
                ai_text = self._call_openai(prompt)
            elif self.provider == "gemini":
                ai_text = self._call_gemini(prompt)
            else:
                return local_text

            return (
                f"── AI Analysis ──\n{ai_text}\n\n"
                f"── Local Analysis ──\n{local_text}"
            )
        except Exception as e:
            logger.warning("AI enrichment failed, using local: %s", e)
            return local_text

    def get_local_report(
        self,
        metrics: Dict[str, Any],
        failed_services: List[str],
        error_count: int,
    ) -> Dict[str, Any]:
        """Return the structured local analysis report.

        Useful when callers need machine-readable data rather than text.
        """
        return self._local.analyse(metrics, failed_services, error_count)

    # ── Prompt Construction ──────────────────────────────────────────────

    def _construct_prompt(
        self,
        metrics: Dict[str, Any],
        failed_services: List[str],
        error_count: int,
    ) -> str:
        """Build the prompt sent to the cloud AI provider."""
        score = metrics.get("score", 0)
        cpu = metrics.get("cpu", 0)
        mem = metrics.get("ram", 0)
        disk = metrics.get("disk", 0)
        failed_str = (
            ", ".join(failed_services) if failed_services else "None"
        )

        return (
            "Role: Expert Linux System Administrator.\n"
            "Task: Analyze the following periodic health report and "
            "provide a professional assessment.\n\n"
            "--- SYSTEM METRICS ---\n"
            f"• Health Score: {score}/100\n"
            f"• CPU Load: {cpu}%\n"
            f"• RAM Usage: {mem}%\n"
            f"• Disk Usage: {disk}%\n"
            f"• Failed Units: {failed_str}\n"
            f"• Journal Anomalies (24h): {error_count}\n\n"
            "--- OUTPUT REQUIREMENTS ---\n"
            "1. Executive Summary: A one-sentence status overview.\n"
            "2. Critical Analysis: Identify the most pressing issue "
            "(if any).\n"
            "3. Action Plan: Provide 3 concrete, technical steps to "
            "optimize or fix the system.\n"
            "Format using simple headers (e.g., 'Summary:', "
            "'Analysis:', 'Actions:'). Keep tone professional and "
            "concise."
        )

    # ── Cloud Provider Calls ─────────────────────────────────────────────

    def _call_openai(self, prompt: str) -> str:
        """Send a prompt to the OpenAI Chat Completions API."""
        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }
        data = {
            "model": self.model or "gpt-4o",
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 300,
        }

        req = urllib.request.Request(
            url, json.dumps(data).encode("utf-8"), headers
        )
        try:
            with urllib.request.urlopen(
                req, timeout=self.HTTP_TIMEOUT
            ) as resp:
                result = json.loads(resp.read().decode("utf-8"))
                return (
                    result["choices"][0]["message"]["content"].strip()
                )
        except urllib.error.HTTPError as e:
            raise RuntimeError(
                f"OpenAI API Error: {e.code} {e.reason}"
            ) from e

    def _call_gemini(self, prompt: str) -> str:
        """Send a prompt to the Google Gemini API."""
        model_name = self.model or "gemini-2.5-flash"
        url = (
            f"https://generativelanguage.googleapis.com/v1beta/"
            f"models/{model_name}:generateContent?key={self.api_key}"
        )
        headers = {"Content-Type": "application/json"}
        data = {
            "contents": [{"parts": [{"text": prompt}]}],
        }

        req = urllib.request.Request(
            url, json.dumps(data).encode("utf-8"), headers
        )
        try:
            with urllib.request.urlopen(
                req, timeout=self.HTTP_TIMEOUT
            ) as resp:
                result = json.loads(resp.read().decode("utf-8"))
                try:
                    return (
                        result["candidates"][0]["content"]
                        ["parts"][0]["text"]
                    )
                except (KeyError, IndexError):
                    raise RuntimeError(
                        "Received malformed response from Gemini."
                    )
        except urllib.error.HTTPError as e:
            raise RuntimeError(
                f"Gemini API Error: {e.code} {e.reason}"
            ) from e
