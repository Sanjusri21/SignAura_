"""
Root proxy test file for test_isign.py ensuring seamless test execution from workspace root.
"""

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
BACKEND_DIR = ROOT_DIR / "Backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

# Import and expose all test items from Backend/tests/test_isign.py
from tests.test_isign import *
