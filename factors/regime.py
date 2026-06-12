"""CLI wrapper. Logic lives in factors/factor_api.py"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from factors.factor_api import get_r_factor

if __name__ == "__main__":
    print(f"R_t = {get_r_factor()}")
