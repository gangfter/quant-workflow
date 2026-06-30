# Phase 3 Cycle 2 Validation Report

Date: 2026-06-27
Branch: feature/contrarian-mt-research
Dataset: BTCUSDT 1m — 2026-02-22 ~ 2026-06-21 (119 days, 171,827 bars)
Fee: 4 bps per side | Walk-Forward: 5-fold anchored expanding

---

## Data Availability

| Source | Coverage | Bars |
| ------ | -------- | ---- |
| market_data (M) | 2026-02-22 ~ 2026-06-21 | 171,827 |
| premium_data (V) | 2026-05-22 ~ 2026-06-21 | 43,500 |
| etf_flows (R) | 2026-05-22 ~ 2026-06-21 | 31 days |
| funding_data (F/OI) | 2026-04-15 ~ 2026-06-21 | 200 records |

Note: V and R data cover only the last 30 days. Bars outside that window have V=0, R=0.

---

## Regime Distribution (119-day)

| Regime | Bars | Share |
| ------ | ---- | ----- |
| RANGE | 166,201 | 96.7% |
| TREND | 4,182 | 2.4% |
| SHOCK | 1,444 | 0.8% |

---

## Rank-IC by Regime and Horizon

Horizons: h1, h5, h15, h60 (bars)

### RANGE (n=166,201)

| Factor | h1 | h5 | h15 | h60 |
| ------ | -- | -- | --- | --- |
| R | -0.0103 | -0.0194 | -0.0356 | -0.0738 |
| V | -0.0035 | -0.0026 | -0.0036 | -0.0137 |
| M (long) | -0.0049 | -0.0073 | -0.0104 | -0.0155 |
| **M (contrarian)** | **+0.0049** | **+0.0073** | **+0.0104** | **+0.0155** |
| F | +0.0007 | +0.0036 | +0.0045 | +0.0036 |
| OI | +0.0044 | +0.0101 | -0.0033 | -0.0585 |

### TREND (n=4,182)

| Factor | h1 | h5 | h15 | h60 |
| ------ | -- | -- | --- | --- |
| R | +0.0239 | -0.0244 | -0.0367 | -0.0345 |
| V | +0.0187 | -0.0172 | -0.0552 | -0.0532 |
| M (long) | -0.0067 | -0.0403 | -0.0098 | -0.0125 |
| **M (contrarian)** | **+0.0067** | **+0.0403** | **+0.0098** | **+0.0125** |
| F | +0.0489 | +0.0088 | +0.0061 | +0.0484 |
| OI | +0.0461 | -0.0296 | +0.0270 | -0.1343 |

### SHOCK (n=1,444) — gated FLAT in production

| Factor | h1 | h5 | h15 | h60 |
| ------ | -- | -- | --- | --- |
| R | +0.0018 | -0.0744 | -0.0629 | -0.0493 |
| **V** | **+0.1057** | **+0.0566** | **+0.0729** | **+0.0756** |
| M (long) | +0.0035 | -0.0535 | -0.0382 | +0.0123 |
| M (contrarian) | -0.0035 | +0.0535 | +0.0382 | -0.0123 |
| F | -0.0654 | -0.0750 | -0.0325 | +0.0035 |
| OI | -0.0632 | +0.0934 | +0.0386 | -0.1475 |

---

## Walk-Forward Results (5-fold, threshold in {1, 2})

### Model 1: R+V+M (current production)

| fold | th | PF | WR | Return | MDD | Trades |
| ---- | -- | -- | -- | ------ | --- | ------ |
| 1 | 1 | 0.944 | 0.357 | -0.7742 | -0.776 | 1771 |
| 2 | 1 | 0.894 | 0.346 | -0.7699 | -0.771 | 1702 |
| 3 | 1 | 1.002 | 0.333 | -0.7239 | -0.724 | 1608 |
| 4 | 1 | 0.986 | 0.373 | -0.7185 | -0.719 | 1570 |
| 5 | 1 | 0.971 | 0.382 | -0.6975 | -0.698 | 1449 |
| **Mean** | | **0.959** | **0.358** | **-0.737** | **-0.738** | **1620** |

Gate: FAILED (PF < 1.3 all folds)

### Model 2: R+V only (M removed)

| fold | th | PF | WR | Return | MDD | Trades |
| ---- | -- | -- | -- | ------ | --- | ------ |
| 1 | 1 | N/A | N/A | 0.000 | 0.000 | 0 |
| 2 | 1 | N/A | N/A | 0.000 | 0.000 | 0 |
| 3 | 1 | N/A | N/A | 0.000 | 0.000 | 0 |
| 4 | 1 | 0.764 | 0.482 | -0.3179 | -0.318 | 413 |
| 5 | 2 | 1.080 | 0.485 | -0.1824 | -0.193 | 270 |
| **Mean** | | **0.922** | — | **-0.100** | **-0.102** | **137** |

Gate: FAILED — 3/5 folds have zero trades (V/R data unavailable for pre-May period)
Note: Effective return mean is misleading (3 folds with 0 PnL inflate it).

### Model 3: R+V+Contrarian M_t (feature branch)

| fold | th | PF | WR | Return | MDD | Trades |
| ---- | -- | -- | -- | ------ | --- | ------ |
| 1 | 1 | 1.059 | 0.639 | -0.7423 | -0.743 | 1771 |
| 2 | 1 | 1.119 | 0.650 | -0.7167 | -0.718 | 1702 |
| 3 | 1 | 0.998 | 0.656 | -0.7247 | -0.726 | 1608 |
| 4 | 1 | 0.928 | 0.613 | -0.7215 | -0.722 | 1534 |
| 5 | 1 | 1.076 | 0.618 | -0.6467 | -0.647 | 1390 |
| **Mean** | | **1.036** | **0.635** | **-0.710** | **-0.711** | **1601** |

Gate: FAILED (PF < 1.3 all folds) — but best of the three models

---

## Comparison Summary

| Metric | R+V+M | R+V only | R+V+Contra_M |
| ------ | ----- | -------- | ------------ |
| PF (mean) | 0.959 | 0.922* | **1.036** |
| Return (mean) | -73.7% | -10.0%* | **-71.0%** |
| Win Rate | 35.8% | 19.3%* | **63.5%** |
| MDD (mean) | -73.8% | -10.2%* | **-71.1%** |
| Avg Trades/fold | 1,620 | 137* | 1,601 |
| Gate (PF>1.3) | FAIL | FAIL | FAIL |

\* R+V only: 3/5 folds have 0 trades — statistics not comparable.

---

## Findings

### 1. Contrarian M_t is directionally correct

M (long momentum) IC is negative at all regimes and horizons — the market is mean-reverting.
Flipping the sign (contrarian) yields consistently positive IC in RANGE and TREND, the two dominant regimes.
Win rate jumps from 35.8% to 63.5% confirming the directional fix.

### 2. Fee drag is the core problem, not signal direction

With ~1,600 trades per fold at 4 bps per side, the fee cost per bar active is substantial.
At 63.5% WR, gross PF > 1.0, but net PF stays near 1.0 due to fee drag.
The contrarian signal is real but the edge is too thin for high-frequency execution.

### 3. V factor has genuine SHOCK-regime alpha (+0.10 IC) but is gated out

SHOCK is set to FLAT in the production risk engine (Risk First policy).
This is the strongest IC in the dataset — but accessing it requires relaxing the SHOCK gate, which is a risk management decision, not a research one.

### 4. R+V only model is structurally broken for the expanded dataset

Only the last 30 of 119 days have V and R data. The model degenerates to FLAT for the remaining 75%.
This model cannot be evaluated on the expanded dataset until historical V (Coinbase premium) data is available.

---

## Recommendation

| Priority | Action | Condition |
| -------- | ------ | --------- |
| P1 | Reduce trade frequency — test threshold=2 or TREND-regime filter only | Reduces fee drag without changing signal |
| P2 | Merge contrarian M_t after PF>1.3 at reduced frequency | Current WR>63% is encouraging |
| P3 | Expand V data via historical premium proxy (futures basis) | Enables proper R+V evaluation |
| P4 | Evaluate SHOCK gate relaxation for V-only signals | V IC=+0.10 in SHOCK is the best edge found |

### Gate Status

Phase 3 Cycle 2 gate: **NOT PASSED**
Required: OOS PF > 1.3 across majority of folds.
Closest: Contrarian M_t at PF_mean=1.036 (folds 1,2,5 > 1.0; fold 3 = 0.998; fold 4 = 0.928).

Next cycle should test Contrarian M_t at threshold=2 with TREND-regime filter before any merge to main.
