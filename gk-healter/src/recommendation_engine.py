class RecommendationEngine:
    def __init__(self):
        pass

    def analyze_health(self, metrics):
        """Generates recommendations based on system metrics."""
        recommendations = []
        
        cpu = metrics.get('cpu', 0)
        ram = metrics.get('ram', 0)
        disk = metrics.get('disk', 0)
        
        if cpu > 80:
            recommendations.append({
                'type': 'warning',
                'message': 'High CPU usage detected. System responsiveness may be low.',
                'action': 'open_system_monitor'
            })
            
        if ram > 85:
            recommendations.append({
                'type': 'warning',
                'message': 'Available Memory is low. Consider closing heavy applications.',
                'action': 'optimize_ram'
            })
            
        if disk > 90:
            recommendations.append({
                'type': 'critical',
                'message': 'Disk space is critically low. Immediate cleanup recommended.',
                'action': 'clean_disk'
            })
        elif disk > 80:
            recommendations.append({
                'type': 'warning',
                'message': 'Disk space is getting full.',
                'action': 'clean_disk'
            })
            
        return recommendations

    def analyze_services(self, failed_services, slow_services):
        """Generates recommendations based on service analysis."""
        recommendations = []
        if failed_services:
            count = len(failed_services)
            recommendations.append({
                'type': 'critical',
                'message': f'{count} system services have failed.',
                'action': 'view_services'
            })
            
        # Check for very slow boot (e.g. if top slow service takes > 10s)
        if slow_services:
            # slow_services is list of dicts {service, time}
            # time is string like "2.0s" or "1min 2s"
            # Parsing time strings is complex, but we can just hint
            pass
            
        return recommendations
        
    def analyze_logs(self, error_count):
        """Generates recommendations based on log analysis."""
        recommendations = []
        if error_count > 100:
             recommendations.append({
                'type': 'warning',
                'message': f'Unusually high number of system errors ({error_count}) in last 24h.',
                'action': 'view_logs'
            })
        elif error_count > 0:
            # Maybe normal traffic, no generic warning
            pass
            
        return recommendations
