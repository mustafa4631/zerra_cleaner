import os
import subprocess
import logging
from src.utils import get_size, format_size
from src.distro_manager import DistroManager
from typing import List, Dict, Any, Tuple
from src.i18n_manager import _

logger = logging.getLogger("gk-healter.cleaner")


class FileCleaner:
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
        pkg_paths = self.distro_manager.get_package_cache_paths()
        # Pardus/Apt Priority: Insert at the beginning
        for key, path, desc_key in reversed(pkg_paths):
            self.categories.insert(0, (key, path, True, desc_key))

    def scan(self) -> List[Dict[str, Any]]:
        """
        Scans the defined categories and returns a list of dictionaries.
        """
        results = []
        for name, path, is_system, desc in self.categories:
            if os.path.exists(path):
                size_bytes = get_size(path)
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

    def _get_marker_paths(self) -> set:
        markers: set = set()
        for _key, p, _desc in self.distro_manager.get_package_cache_paths():
            if self.distro_manager.get_clean_command(p):
                if not os.path.isdir(p) or p.startswith("/usr/"):
                    markers.add(os.path.abspath(p))
        return markers

    def is_safe_to_delete(self, path: str) -> bool:
        path = os.path.abspath(path)
        if path in self._get_marker_paths():
            return True

        forbidden = ["/bin", "/boot", "/dev", "/etc", "/lib", "/proc", "/sys", "/usr/bin", "/usr/lib", "/usr/sbin"]
        allowed_system = ["/var/log", "/var/lib/systemd/coredump"]
        
        marker_set = self._get_marker_paths()
        for _key, p, _desc in self.distro_manager.get_package_cache_paths():
            if os.path.abspath(p) not in marker_set:
                allowed_system.append(p)

        allowed_user = [os.path.expanduser("~/.cache")]

        for f in forbidden:
            if path.startswith(f):
                return False

        is_allowed = False
        for a in allowed_system + allowed_user:
            if path == a or path.startswith(a + os.sep):
                is_allowed = True
                break
        return is_allowed

    def clean_files(self, selected_items: List[Dict[str, Any]]) -> Tuple[int, int, List[str]]:
        """
        Performs actual file cleaning.
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

            success, error_msg = False, None
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
        distro_cmd = self.distro_manager.get_clean_command(path)
        if distro_cmd:
            cmd = distro_cmd
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
        except Exception as e:
            return False, str(e)


class RAMCleaner:
    def __init__(self):
        from src.ram_manager import RAMManager
        self.ram_manager = RAMManager()

    def scan(self) -> List[Dict[str, Any]]:
        """
        Scans current RAM usage and returns list of clearable cache categories.
        """
        import psutil
        from src.utils import format_size
        results = []
        mem = psutil.virtual_memory()
        
        # Category 1: Page Cache
        if hasattr(mem, 'cached'):
            size = mem.cached
            if size > 0:
                results.append({
                    'category': _("cat_ram_page_cache"),
                    'path': 'ram:1',
                    'size_str': format_size(size),
                    'size_bytes': size,
                    'system': True,
                    'desc': _("desc_ram_page_cache")
                })
        
        # Category 2: Dentries & Inodes
        if hasattr(mem, 'slab'):
            size = mem.slab
            if size > 0:
                results.append({
                    'category': _("cat_ram_slab_cache"),
                    'path': 'ram:2',
                    'size_str': format_size(size),
                    'size_bytes': size,
                    'system': True,
                    'desc': _("desc_ram_slab_cache")
                })
        
        return results

    def clean_ram(self, selected_items: List[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Triggers RAM optimization based on selected categories.
        If selected_items is None, cleans level 3 (everything).
        """
        if not selected_items:
            return self.ram_manager.clean_ram(level=3)
        
        # Determine highest level requested
        paths = [item['path'] for item in selected_items]
        if 'ram:1' in paths and 'ram:2' in paths:
            level = 3
        elif 'ram:2' in paths:
            level = 2
        else:
            level = 1
            
        return self.ram_manager.clean_ram(level=level)

