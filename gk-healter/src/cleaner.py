import os
import shutil
import subprocess
from src.utils import get_size, format_size
from typing import List, Dict, Any, Tuple
from src.i18n_manager import _

class SystemCleaner:
    def __init__(self):
        self.scan_results = []
        # Categories to scan
        # (Name, Path, IsSystem, Description)
        # Note: We store keys here, but we will translate them when needed or just here if dynamic update is not needed immediately. 
        # However, to be dynamic on language switch, we should probably translate in scan() or property if the class is long lived. 
        # But for now, let's translate them at initialization or during scan traversal.
        # Ideally, cleaner is instantiated, and if language changes, we might need to re-instantiate or re-fetch.
        # Let's use the keys in the tuple, and translate in `scan`.
        self.categories = [
            ("cat_apt_cache", "/var/cache/apt/archives", True, "desc_apt_cache"),
            ("cat_sys_logs", "/var/log", True, "desc_sys_logs"),
            ("cat_autoremove", "/usr/bin/apt", True, "desc_autoremove"),
            ("cat_coredumps", "/var/lib/systemd/coredump", True, "desc_coredumps"),
            ("cat_thumbnails", os.path.expanduser("~/.cache/thumbnails"), False, "desc_thumbnails"),
            ("cat_firefox", os.path.expanduser("~/.cache/mozilla"), False, "desc_firefox"),
            ("cat_chrome", os.path.expanduser("~/.cache/google-chrome"), False, "desc_chrome")
        ]

    def scan(self) -> List[Dict[str, Any]]:
        """
        Scans the defined categories and returns a list of dictionaries:
        {'category': str, 'path': str, 'size_str': str, 'size_bytes': int, 'system': bool, 'desc': str}
        """
        results = []
        for name, path, is_system, desc in self.categories:
            if os.path.exists(path):
                size_bytes = get_size(path)
                # Only offer to clean if size > 0 (or some threshold) to reduce noise
                if size_bytes > 0:
                    results.append({
                        'category': _(name),
                        'path': path,
                        'size_str': format_size(size_bytes),
                        'size_bytes': size_bytes,
                        'system': is_system,
                        'desc': _(desc)
                    })
        self.scan_results = results
        return results

    def is_safe_to_delete(self, path: str) -> bool:
        """
        Safety check: ensure we are not deleting critical system paths.
        This acts as a whitelist mechanism.
        """
        # Forbidden paths (prefixes)
        forbidden = ["/bin", "/boot", "/dev", "/etc", "/lib", "/proc", "/sys", "/usr/bin", "/usr/lib", "/usr/sbin"]
        
        # Explicitly allowed prefixes for System cleaning
        allowed_system = ["/var/cache/apt/archives", "/var/log", "/usr/bin/apt", "/var/lib/systemd/coredump"]
        
        # Explicitly allowed prefixes for User cleaning
        allowed_user = [os.path.expanduser("~/.cache")]

        path = os.path.abspath(path)

        # 1. Check strict forbidden list
        for f in forbidden:
            if path.startswith(f):
                return False
        
        # 2. Check if it matches an allowed category prefix
        is_allowed = False
        for a in allowed_system + allowed_user:
            if path.startswith(a):
                is_allowed = True
                break
        
        return is_allowed

    def clean(self, selected_items: List[Dict[str, Any]]) -> Tuple[int, int, List[str]]:
        """
        Performs actual cleaning.
        Returns: (success_count, fail_count, list_of_error_messages)
        """
        success_count = 0
        fail_count = 0
        errors = []

        for item in selected_items:
            path = item['path']
            is_system = item['system']

            if not self.is_safe_to_delete(path):
                msg = _("msg_safety_warning").format(path)
                print(msg)
                errors.append(msg)
                fail_count += 1
                continue

            success = False
            error_msg = None

            if is_system:
                success, error_msg = self._clean_system(path)
            else:
                success, error_msg = self._clean_user(path)

            if success:
                success_count += 1
            else:
                fail_count += 1
                if error_msg:
                    errors.append(error_msg)
                    
        return success_count, fail_count, errors

    def _clean_user(self, path: str) -> Tuple[bool, str]:
        """
        Cleans user paths. Returns (Bool Success, String ErrorMsg).
        """
        try:
            if os.path.isfile(path):
                os.remove(path)
            elif os.path.isdir(path):
                for root, dirs, files in os.walk(path):
                    for f in files:
                        try:
                            os.remove(os.path.join(root, f))
                        except Exception as e:
                            return False, _("err_file_delete").format(f, e)
            return True, None
        except Exception as e:
            msg = _("err_user_clean_fail").format(path, e)
            print(msg)
            return False, msg

    def _clean_system(self, path: str) -> Tuple[bool, str]:
        """
        Uses pkexec to clean system paths. Returns (Bool Success, String ErrorMsg).
        """
        cmd = []
        
        if path == "/var/cache/apt/archives":
            cmd = ["pkexec", "apt-get", "clean"]
        elif path == "/usr/bin/apt":
            cmd = ["pkexec", "apt-get", "autoremove", "-y"]
        elif path == "/var/log":
            bash_cmd = (
                "find /var/log -type f -regex '.*\\.\\(gz\\|[0-9]+\\)$' -delete && "
                "find /var/log -type f -name '*.log' -exec truncate -s 0 {} + && "
                "journalctl --vacuum-time=1s"
            )
            cmd = ["pkexec", "sh", "-c", bash_cmd]
        elif path == "/var/lib/systemd/coredump":
            cmd = ["pkexec", "sh", "-c", "rm -rf /var/lib/systemd/coredump/*"]
        else:
            return False, _("err_unknown_sys_path").format(path)

        try:
            print(f"Executing system clean: {cmd}")
            subprocess.run(cmd, check=True)
            return True, None
        except subprocess.CalledProcessError as e:
            # e.returncode 126 or 127 or 1 usually means auth failed or cancelled
            if e.returncode in [126, 127]:
                return False, _("err_auth_cancelled").format(path)
            return False, _("err_sys_clean_code").format(e.returncode, path)
        except Exception as e:
            return False, _("err_unexpected").format(path, e)



