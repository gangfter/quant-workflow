"""Deprecated entry point. Schema is unified in database/schema.py."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from database.schema import main

if __name__ == "__main__":
    main()
