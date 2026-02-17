import os
import shutil
import subprocess
import logging
from src.utils import get_size, format_size
from src.distro_manager import DistroManager
from typing import List, Dict, Any, Tuple
from src.i18n_manager import _

logger = logging.getLogger("gk-healter.cleaner")

class SystemCleaner:
    def __init__(self):
        self.scan_results = []
        self.distro_manager = DistroManager()
        
        # Base categories (universal)
        self.categories = [
            ("cat_sys_logs", "/var/log", True, "desc_sys_logs"),
            ("cat_coredumps", "/var/lib/systemd/coredump", True, "desc_coredumps"),
            ("cat_thumbnails", os.path.expanduser("~/.cache/thumbnails"), False, "desc_thumbnails"),
            ("cat_firefox", os.path.expanduser("~/.cache/mozilla"), False, "desc_firefox"),
            ("cat_chrome", os.path.expanduser("~/.cache/google-chrome"), False, "desc_chrome")
        ]
        
        # Add distro-specific categories (pkg cache)
        # Note: get_package_cache_paths returns list of (key, path, desc_key)
        pkg_paths = self.distro_manager.get_package_cache_paths()
        # We need to insert them as tuples into self.categories
        # But wait, self.categories expects (name, path, is_system, desc)
        # Distro manager returns (key, path, desc_key)
        # We must add is_system=True manually here.
        for key, path, desc_key in pkg_paths:
            self.categories.insert(0, (key, path, True, desc_key))

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
        # Dynamically add pkg cache path
        allowed_system = ["/var/log", "/var/lib/systemd/coredump"]
        
        # Add distro specific paths to allowed list
        for _, p, _ in self.distro_manager.get_package_cache_paths():
            allowed_system.append(p)
            
        # Explicitly allowed prefixes for User cleaning
        allowed_user = [os.path.expanduser("~/.cache")]

        path = os.path.abspath(path)

        # 1. Check strict forbidden list
        for f in forbidden:
            if path.startswith(f):
                return False
        
        # 2. Check if it matches an allowed category prefix
        
        # Careful! self.distro_manager.get_package_cache_paths() might include pseudo-paths like /usr/bin/apt for markers
        # We should allow those markers if they are passed as 'path', but not as a prefix for actual file deletion.
        # But wait, cleaner only calls _clean_system with the marker path directly. 
        # So we just need to ensure the marker itself is allowed.
        
        is_allowed = False
        for a in allowed_system + allowed_user:
            # If path matches exactly (for markers) or starts with directory
            if path == a or path.startswith(a + os.sep) or path.startswith(a):
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
                logger.warning(msg)
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
            logger.error(msg)
            return False, msg

    def _clean_system(self, path: str) -> Tuple[bool, str]:
        """
        Uses pkexec to clean system paths. Returns (Bool Success, String ErrorMsg).
        """
        cmd = []
        
        # Check if this path is handled by distro manager
        # Some paths are distro-specific (pkg cache), others are generic (/var/log)

        # Distro specific paths
        distro_cmd = self.distro_manager.get_clean_command(path)
        if distro_cmd:
            cmd = distro_cmd

        # Generic system paths
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
            logger.info("Executing system clean: %s", cmd)
            subprocess.run(cmd, check=True, timeout=120)
            return True, None
        except subprocess.TimeoutExpired:
            logger.error("System clean timed out for: %s", path)
            return False, _("err_unexpected").format(path, "Operation timed out")
        except subprocess.CalledProcessError as e:
            # e.returncode 126 or 127 or 1 usually means auth failed or cancelled
            if e.returncode in [126, 127]:
                return False, _("err_auth_cancelled").format(path)
            return False, _("err_sys_clean_code").format(e.returncode, path)
        except Exception as e:
            return False, _("err_unexpected").format(path, e)



