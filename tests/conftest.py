"""
pytest configuration – ensure test helpers are importable.
"""

import sys
import os

# Add tests/ directory to path so gk_healter_tests module is importable
_tests_dir = os.path.dirname(os.path.abspath(__file__))
if _tests_dir not in sys.path:
    sys.path.insert(0, _tests_dir)

# Also add gk-healter/ for src imports
_project_root = os.path.dirname(_tests_dir)
_gk_dir = os.path.join(_project_root, "gk-healter")
if _gk_dir not in sys.path:
    sys.path.insert(0, _gk_dir)
