import os
import sys
from pathlib import Path

# Needed so backend.db can be imported during test collection.
os.environ.setdefault("DATABASE_URL", "postgresql://user:pass@localhost:5432/hackradar_test")

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
