import subprocess
import shutil

class LogAnalyzer:
    def __init__(self):
        pass

    def get_error_count_24h(self):
        """Returns the number of error/critical logs in the last 24 hours."""
        if not shutil.which('journalctl'):
            return 0
            
        try:
            # Pipe journalctl output to wc -l to count lines without loading all into memory
            # journalctl -p 3 (err) -S -24h --no-pager
            cmd_journal = ['journalctl', '-p', '3', '-S', '-24h', '--no-pager']
            
            if not shutil.which('wc'):
                # Fallback if wc missing (unlikely on linux)
                result = subprocess.run(cmd_journal, capture_output=True, text=True)
                return len(result.stdout.strip().split('\n')) if result.stdout else 0

            p1 = subprocess.Popen(cmd_journal, stdout=subprocess.PIPE)
            p2 = subprocess.Popen(['wc', '-l'], stdin=p1.stdout, stdout=subprocess.PIPE, text=True)
            
            # Allow p1 to receive a SIGPIPE if p2 exits.
            p1.stdout.close()  
            output, _ = p2.communicate()
            
            if p2.returncode == 0:
                return int(output.strip())
            return 0
            
        except Exception as e:
            print(f"Error checking logs: {e}")
            return 0

    def get_recent_critical_logs(self, limit=10):
        """Returns the most recent critical log entries."""
        logs = []
        if not shutil.which('journalctl'):
            return ["Error: journalctl not found"]
            
        try:
            # -p 2 (crit, alert, emerg) -n limit --reverse (newest first)
            cmd = ['journalctl', '-p', '2', '-n', str(limit), '--no-pager', '--reverse']
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                for line in result.stdout.strip().split('\n'):
                    if line.strip():
                        logs.append(line.strip())
        except Exception as e:
            print(f"Error fetching critical logs: {e}")
            logs.append(f"Error: {str(e)}")
            
        return logs
