import shutil
import os
import logging
from typing import List, Tuple

logger = logging.getLogger("gk-healter.distro")


class DistroManager:
    """
    Abstracts distribution-specific logic for cleaning and system management.
    Supports: Debian/Ubuntu (apt), RHEL/Fedora (dnf), Arch (pacman), OpenSUSE (zypper).
    """
    
    def __init__(self):
        self.pkg_manager = self._detect_pkg_manager()

    def _detect_pkg_manager(self) -> str:
        """Detect available package manager binary."""
        # Prioritize widely used ones
        if shutil.which("apt-get"): return "apt"
        if shutil.which("pacman"): return "pacman"
        if shutil.which("dnf"): return "dnf"
        if shutil.which("zypper"): return "zypper"
        if shutil.which("yum"): return "yum"
        return "unknown"

    def get_package_cache_paths(self) -> List[Tuple[str, str, str]]:
        """
        Returns list of (key, path, description_key) for package caches.
        """
        if self.pkg_manager == "apt":
            return [
                ("cat_pkg_cache", "/var/cache/apt/archives", "desc_pkg_cache"),
                ("cat_autoremove", "/usr/bin/apt", "desc_autoremove") 
            ]
        elif self.pkg_manager == "pacman":
            return [
                ("cat_pkg_cache", "/var/cache/pacman/pkg", "desc_pkg_cache"),
                ("cat_autoremove", "/usr/bin/pacman", "desc_unused_deps") # Using dummy path as marker
            ]
        elif self.pkg_manager == "dnf":
            return [
                ("cat_pkg_cache", "/var/cache/dnf", "desc_pkg_cache"),
                ("cat_autoremove", "/usr/bin/dnf", "desc_autoremove")
            ]
        elif self.pkg_manager == "zypper":
             return [
                ("cat_pkg_cache", "/var/cache/zypp/packages", "desc_pkg_cache"),
                ("cat_autoremove", "/usr/bin/zypper", "desc_autoremove")
            ]
        return []

    def get_clean_command(self, path: str) -> List[str]:
        """
        Returns the specific command to clean the given path based on package manager.
        """
        # APT
        if self.pkg_manager == "apt":
            if path == "/var/cache/apt/archives":
                return ["pkexec", "apt-get", "clean"]
            if path == "/usr/bin/apt": # Marker for autoremove
                return ["pkexec", "apt-get", "autoremove", "-y"]

        # PACMAN (Arch)
        elif self.pkg_manager == "pacman":
            if path == "/var/cache/pacman/pkg":
                # 'pacman -Sc' cleans cached packages (requires interaction usually, so use --noconfirm for automation carefully)
                # But -Sc only removes uninstalled packages. -Scc removes all. 
                # Ideally, we should be careful. Standard cleanup usually implies removing all cached.
                return ["pkexec", "pacman", "-Scc", "--noconfirm"]
            if path == "/usr/bin/pacman": # Marker for orphans
                # Remove orphans: pacman -Rns $(pacman -Qtdq)
                # Complex command, run via sh
                cmd = "pacman -Qtdq | xargs -r pkexec pacman -Rns --noconfirm"
                return ["sh", "-c", cmd]

        # DNF (Fedora)
        elif self.pkg_manager == "dnf":
            if path == "/var/cache/dnf":
                return ["pkexec", "dnf", "clean", "all"]
            if path == "/usr/bin/dnf":
                return ["pkexec", "dnf", "autoremove", "-y"]

        # ZYPPER (OpenSUSE)
        elif self.pkg_manager == "zypper":
            if path == "/var/cache/zypp/packages":
                return ["pkexec", "zypper", "clean", "--all"]
            if path == "/usr/bin/zypper": # Very rare to automate on suse
                 # Zypper doesn't have a direct 'autoremove' equivalent in one command easily, usually 'packages --unneeded'
                 return []
        
        return []
