"""GK Healter — Recommendation Engine.

Analyzes system metrics, service status, and log data to generate
actionable recommendations for the user.
"""

from typing import Dict, List, Any
from src.i18n_manager import _


class RecommendationEngine:
    """Rule-based recommendation generator for system insights."""

    def __init__(self) -> None:
        pass

    def analyze_health(self, metrics: Dict[str, Any]) -> List[Dict[str, str]]:
        """Generates recommendations based on system metrics."""
        recommendations = []

        cpu = metrics.get('cpu', 0)
        ram = metrics.get('ram', 0)
        disk = metrics.get('disk', 0)

        if cpu > 80:
            recommendations.append({
                'type': 'warning',
                'message': _('rec_high_cpu'),
                'action': 'open_system_monitor'
            })

        if ram > 85:
            recommendations.append({
                'type': 'warning',
                'message': _('rec_high_ram'),
                'action': 'optimize_ram'
            })

        if disk > 90:
            recommendations.append({
                'type': 'critical',
                'message': _('rec_disk_critical'),
                'action': 'clean_disk'
            })
        elif disk > 80:
            recommendations.append({
                'type': 'warning',
                'message': _('rec_disk_warning'),
                'action': 'clean_disk'
            })

        return recommendations

    def analyze_services(
        self,
        failed_services: List[str],
        slow_services: List[Dict[str, str]],
    ) -> List[Dict[str, str]]:
        """Generates recommendations based on service analysis."""
        recommendations = []
        if failed_services:
            count = len(failed_services)
            recommendations.append({
                'type': 'critical',
                'message': _('rec_failed_services').format(count=count),
                'action': 'view_services'
            })

        # Flag excessively slow boot services (>10s)
        if slow_services:
            for svc in slow_services:
                time_str = svc.get('time', '0s')
                # Parse simple "Xs" or "Xmin Ys" format
                try:
                    if 'min' in time_str:
                        seconds = 60.0  # at least 1 minute
                    else:
                        seconds = float(time_str.rstrip('s'))
                except (ValueError, AttributeError):
                    seconds = 0.0
                if seconds > 10.0:
                    recommendations.append({
                        'type': 'warning',
                        'message': _('rec_slow_service').format(
                            service=svc.get('service', '?'),
                            time=time_str,
                        ),
                        'action': 'view_services'
                    })
                    break  # only warn once for the slowest

        return recommendations

    def analyze_logs(self, error_count: int) -> List[Dict[str, str]]:
        """Generates recommendations based on log analysis."""
        recommendations = []
        if error_count > 100:
            recommendations.append({
                'type': 'warning',
                'message': _('rec_high_errors').format(count=error_count),
                'action': 'view_logs'
            })
        elif error_count > 0:
            # Maybe normal traffic, no generic warning
            pass

        return recommendations
