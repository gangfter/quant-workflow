"""Automated factor research report (markdown).

This output IS the product: a daily factor-health report that can be
published / sold independently of trade execution (signal-as-a-service).

Usage: python research/report_generator.py [--telegram]
"""
import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backtest_runner import compute_metrics, regime_breakdown, simulate
from research.data import build_panel, forward_returns
from research.factor_decay import run as run_decay
from research.factor_ic import run as run_ic
from research.factor_rank_ic import run as run_rank_ic

REPORT_DIR = ROOT / "research" / "reports"
HORIZONS = [1, 5, 15, 60, 240]


def _ic_table(results, horizons, label):
    lines = [
        f"## {label}",
        "| factor | " + " | ".join(f"h={h}" for h in horizons) + " |",
        "|---|" + "---|" * len(horizons),
    ]
    for f, by_h in results.items():
        cells = []
        for h in horizons:
            r = by_h[h]
            cells.append("-" if r["ic"] is None else f"{r['ic']} (t={r['t_stat']})")
        lines.append(f"| {f} | " + " | ".join(cells) + " |")
    lines.append("")
    return lines


def build_report() -> str:
    panel = build_panel()
    panel_fwd = forward_returns(panel, HORIZONS)
    df, trades = simulate(panel)
    metrics = compute_metrics(df, trades)
    regimes = regime_breakdown(trades)
    ic = run_ic(HORIZONS, panel=panel_fwd)
    rank_ic = run_rank_ic(HORIZONS, panel=panel_fwd)
    decay = run_decay()

    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines = [
        "# Factor Research Report",
        f"_generated {now} | bars={len(panel)} | strategy: R+V+M, threshold=2, fee=4bps_",
        "",
        "## Strategy Metrics",
        "```",
        str(metrics),
        "```",
        "",
        "## Regime Breakdown",
        "```",
        str(regimes),
        "```",
        "",
    ]
    lines += _ic_table(ic, HORIZONS, "Information Coefficient (Pearson)")
    lines += _ic_table(rank_ic, HORIZONS, "Rank IC (Spearman)")
    lines += ["## Factor Decay / Alpha Half-life"]
    for f, d in decay.items():
        lines.append(f"- **{f}**: half_life = {d['half_life_bars']} bars")
    lines.append("")
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--telegram", action="store_true")
    args = ap.parse_args()

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    md = build_report()
    path = REPORT_DIR / f"factor_report_{datetime.now().strftime('%Y%m%d_%H%M')}.md"
    path.write_text(md)
    print(f"[REPORT] {path}")
    if args.telegram:
        try:
            from notifications.telegram_alert import send_message

            send_message(md[:3500])
        except Exception as e:
            print(f"[WARN] telegram failed: {e}")


if __name__ == "__main__":
    main()
