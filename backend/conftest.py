"""
conftest.py - Shared pytest fixtures and collection configuration.
"""
import sys
from pathlib import Path

# Ensure backend/ is on sys.path for test imports
BACKEND_DIR = Path(__file__).parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

collect_ignore = ["venv", ".venv", "setup.py"]
