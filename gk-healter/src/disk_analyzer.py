import subprocess
import shutil
import os
import logging

logger = logging.getLogger("gk-healter.disk")


class DiskAnalyzer:
    def __init__(self):
        pass

    def get_large_files(self, path, size_mb=100, limit=10):
        """Finds files larger than size_mb in the given path."""
        large_files = []
        if not shutil.which('find'):
            return [] 
        
        # Default to user home if path not valid
        if not path or not os.path.exists(path):
            path = os.path.expanduser("~")
            
        try:
            # find /path -type f -size +100M -printf "%s %p\n" | sort -rn | head -n 10
            # stderr=DEVNULL to ignore permission denied errors
            
            cmd_find = [
                'find', path, 
                '-type', 'f', 
                '-size', f'+{size_mb}M',
                '-printf', '%s %p\n'
            ]
            
            p1 = subprocess.Popen(cmd_find, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
            p2 = subprocess.Popen(['sort', '-rn'], stdin=p1.stdout, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
            p3 = subprocess.Popen(['head', '-n', str(limit)], stdin=p2.stdout, stdout=subprocess.PIPE, text=True, stderr=subprocess.DEVNULL)
            
            p1.stdout.close()
            p2.stdout.close()
            
            output, _ = p3.communicate()
            
            for line in output.split('\n'):
                if line.strip():
                    parts = line.strip().split(' ', 1)
                    if len(parts) == 2:
                        try:
                            size_bytes = int(parts[0])
                            filename = parts[1]
                            large_files.append({
                                'path': filename,
                                'size': self._format_size(size_bytes),
                                'raw_size': size_bytes
                            })
                        except ValueError:
                            continue
                        
        except Exception as e:
            logger.error("Error finding large files: %s", e)
            
        return large_files

    @staticmethod
    def _format_size(size_bytes):
        """Format bytes to human-readable string. Delegates to utils."""
        from src.utils import format_size
        return format_size(size_bytes)

    def _format_size_legacy(self, size_bytes):
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size_bytes < 1024:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024
        return f"{size_bytes:.1f} PB"
