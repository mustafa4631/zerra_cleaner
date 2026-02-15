import subprocess
import shutil

class ServiceAnalyzer:
    def __init__(self):
        pass

    def get_failed_services(self):
        """Returns a list of failed systemd units."""
        failed_services = []
        if not shutil.which('systemctl'):
            return ["Error: systemctl not found"]
            
        try:
            # list-units --state=failed
            cmd = ['systemctl', 'list-units', '--state=failed', '--plain', '--no-legend']
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                for line in result.stdout.strip().split('\n'):
                    if line.strip():
                        # Output format usually: unit  load  active  sub  description
                        # We just want the unit name (first column)
                        parts = line.split()
                        if len(parts) > 0:
                            failed_services.append(parts[0])
        except Exception as e:
            print(f"Error checking failed services: {e}")
            return [f"Error: {str(e)}"]
            
        return failed_services

    def get_slow_startup_services(self, limit=5):
        """Returns top slow startup services using systemd-analyze blame."""
        slow_services = []
        if not shutil.which('systemd-analyze'):
            return []
            
        try:
            cmd = ['systemd-analyze', 'blame']
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                # Filter out lines that might be empty
                valid_lines = [l for l in lines if l.strip()]
                
                for line in valid_lines[:limit]:
                    parts = line.strip().split()
                    if len(parts) >= 2:
                        # logical separation: time is first, service name is rest
                        time_taken = parts[0]
                        service_name = " ".join(parts[1:])
                        slow_services.append({'service': service_name, 'time': time_taken})
        except Exception as e:
            print(f"Error checking startup services: {e}")
            
        return slow_services

    def get_system_state(self):
        """Returns the overall system state (running, degraded, maintenance)."""
        if not shutil.which('systemctl'):
            return "unknown"
            
        try:
            # is-system-running returns exit code based on state, but also prints the state
            cmd = ['systemctl', 'is-system-running']
            result = subprocess.run(cmd, capture_output=True, text=True)
            # systemctl is-system-running returns non-zero if degraded, so we just want the output string
            return result.stdout.strip()
        except Exception:
            return "unknown"
