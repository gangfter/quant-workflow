"""Funding & Open-Interest factors (candidate alphas).

Philosophy gate: a factor enters S_final ONLY after IC / decay /
walk-forward validation in research/. Until then these exist for
measurement, not trading.
"""
from factors.factor_api import get_f_factor, get_oi_factor  # noqa: F401
