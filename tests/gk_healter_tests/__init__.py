"""
Test helpers – import machinery for src modules without GTK dependency.
"""

import sys
import os
import importlib

# Add the gk-healter directory to path so 'src.X' imports resolve
_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_gk_dir = os.path.join(_project_root, "gk-healter")

if _gk_dir not in sys.path:
    sys.path.insert(0, _gk_dir)


def src_import(module_name: str):
    """
    Import a module from src/ without triggering GTK.
    Usage: utils = src_import("utils")
    """
    return importlib.import_module(f"src.{module_name}")
