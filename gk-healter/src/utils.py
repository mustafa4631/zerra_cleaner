"""
GK Healter — Shared Utility Functions

Provides common helpers for file-size calculation and formatting
used across the application.
"""

import os


def get_size(path: str) -> int:
    """Recursively calculate total size of a directory in bytes.

    Symlinks are skipped. Permission errors on individual files
    are silently ignored so partial results are still returned.
    """
    total_size = 0
    try:
        for dirpath, dirnames, filenames in os.walk(path):
            for f in filenames:
                fp = os.path.join(dirpath, f)
                # skip symbolic links
                if not os.path.islink(fp):
                    try:
                        total_size += os.path.getsize(fp)
                    except (PermissionError, OSError):
                        pass
    except PermissionError:
        pass
    return total_size

def format_size(size: int) -> str:
    """Convert byte count to human-readable string (e.g. '1.50 MB')."""
    if size < 0:
        return "0.00 B"
    power = 2 ** 10
    n = 0
    power_labels = {0: '', 1: 'K', 2: 'M', 3: 'G', 4: 'T'}
    while size >= power and n < 4:
        size /= power
        n += 1
    return f"{size:.2f} {power_labels[n]}B"
