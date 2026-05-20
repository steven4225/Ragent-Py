from __future__ import annotations

import os
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"

os.environ.setdefault("PYTHON_INGESTION_BACKEND", "memory")

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))
