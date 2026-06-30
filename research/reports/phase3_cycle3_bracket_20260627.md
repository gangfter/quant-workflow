# Phase 3 Cycle 3 — RR-Bracket Backtest Report

Date: 2026-06-27
Branch: feature/contrarian-mt-research
Engine: `research/bracket_backtest.py` (research layer; production engine untouched)
Dataset: BTCUSDT 1m — 2026-02-22 ~ 2026-06-21 (119 days, 171,827 bars)
Fee: 4 bps/side (8 bps round-trip)

---

## Objective (changed from Cycle 2)

| Target | Value |
| ------ | ----- |
| Reward:Risk | >= 3.0 |
| Win Rate | 35-45% (NOT maximized) |
| Profit Factor | > 1.3 |

Method: cut trades aggressively via higher threshold, TREND-only entries,
CVD (V/Coinbase-premium) confirmation, and ATR-expansion filtering.

This required a **new engine**. `backtest_runner.simulate()` uses signal-flip
exits and has no defined R-multiple. The bracket engine assigns every trade a
fixed risk unit `R = atr_mult x ATR(14)` with exits at **SL -1R / TP +RR / timeout**.

Data limitation: `market_data` has close only (no intrabar high/low). TP/SL are
evaluated close-to-close, so reported numbers are mildly **optimistic** (cannot
see intrabar stop-outs). Entries fill at the next bar's close; the exit scan
starts strictly after the fill bar (zero lookahead). A `min_risk=0.0015` floor
prevents the fixed fee from dominating a sub-fee stop.

---

## Result: NO configuration meets the objective

### RR=3.0 sweep (direction x stop-width x filter)

| Config | Trades | WR | PF | Avg R | Avg Win | Avg Loss |
| ------ | -----: | -: | -: | ----: | ------: | -------: |
| contra th2 x2ATR | 201 | 28.9% | 0.705 | -0.300 | +2.479 | -1.427 |
| contra TREND th2 x2ATR | 34 | 32.4% | 0.885 | -0.110 | +2.612 | -1.412 |
| contra TREND th2 +CVD x2ATR | 27 | 29.6% | 0.779 | -0.219 | +2.606 | -1.408 |
| contra th2 x8ATR | 267 | 34.1% | 0.682 | -0.253 | +1.596 | -1.209 |
| mom TREND th2 +CVD x4ATR | 67 | 32.8% | 0.791 | -0.188 | +2.172 | -1.341 |
| mom TREND th2 x4ATR | 89 | 31.5% | 0.770 | -0.212 | +2.260 | -1.347 |

Best PF at RR=3 = **0.885** (contra TREND x2ATR, only 34 trades). All < 1.0.

### RR frontier — does any RR cross PF>1.3?

| Config | rr | Trades | WR | PF | Avg R |
| ------ | -: | -----: | -: | -: | ----: |
| contra th2 x4ATR | 1.0 | 522 | 48.5% | 0.450 | -0.383 |
| contra th2 x4ATR | 1.5 | 438 | 40.2% | 0.562 | -0.354 |
| contra th2 x4ATR | 2.0 | 379 | 33.5% | 0.590 | -0.368 |
| contra th2 x4ATR | 3.0 | 332 | 25.9% | 0.611 | -0.387 |
| contra th2 x8ATR | 1.0 | 363 | 48.5% | 0.539 | -0.289 |
| contra th2 x8ATR | 2.0 | 292 | 37.0% | 0.664 | -0.255 |
| contra th2 x8ATR | 3.0 | 267 | 34.1% | 0.682 | -0.253 |
| mom TREND +CVD x4ATR | 1.0 | 83 | 53.0% | 0.579 | -0.264 |
| mom TREND +CVD x4ATR | 2.0 | 70 | 41.4% | 0.873 | -0.100 |
| mom TREND +CVD x4ATR | 3.0 | 67 | 32.8% | 0.791 | -0.188 |

**Max PF across all configs and all RR = 0.873.** None reach 1.0, let alone 1.3.

---

## Root cause: win rate tracks the random-walk break-even line

For a TP:SL = k:1 bracket, a zero-edge (random-walk) entry wins with probability
`1/(1+k)`. Observed WR sits almost exactly there at every RR:

| RR | Break-even WR (no edge) | Observed WR |
| -: | ----------------------: | ----------: |
| 1.0 | 50.0% | 48-53% |
| 1.5 | 40.0% | 40-44% |
| 2.0 | 33.3% | 33-41% |
| 3.0 | 25.0% | 26-34% |

The entries carry **no directional/continuation information** for the bracket
payoff — WR is set by the bracket geometry, not the signal. Fee drag (8 bps RT)
then turns the ~break-even raw edge into PF < 1 everywhere. Aggressive filtering
(TREND-only, CVD, wider stops) shrinks trade count from 2,165 to 27-140 but does
**not** lift PF above 1, confirming the missing ingredient is edge, not noise.

This is consistent with Cycle 2: the contrarian-M edge is **mean-reverting**
(small, fast), which is structurally the *opposite* of an RR>=3 momentum payoff.
RR>=3 needs price to *continue* 3R after entry before retracing 1R; a
mean-reverting signal predicts the reverse.

---

## Requested metrics — best WR-target candidate

The single config landing inside the 35-45% WR band with the least loss:

| Metric | Value |
| ------ | ----- |
| Config | mom, TREND-only, +CVD, 4xATR stop, **RR=2.0** |
| Trade Count | 70 |
| Win Rate | 41.4% |
| Avg R multiple | -0.100 |
| Avg Win | +2.172 R |
| Avg Loss | -1.341 R |
| Profit Factor | **0.873** |

Still net-losing. Avg Loss is -1.34R (not -1.0R) because the 8 bps fee plus
timeout losers push realized losses past the nominal stop.

---

## Recommendation

| Priority | Action | Rationale |
| -------- | ------ | --------- |
| P1 | **Do not pursue RR>=3 with current signals** | WR pinned to random-walk line at every RR; no continuation edge exists |
| P2 | Acquire intrabar OHLC (high/low) before any further bracket work | Close-only TP/SL is optimistic; current numbers are an upper bound and still fail |
| P3 | If RR>=3 is a hard product requirement, the entry signal must change — not the exit | Filtering tightened trade count 16x with zero PF improvement |
| P4 | Otherwise revert objective to the edge the data actually has | V-in-SHOCK IC=+0.10 (gated), contra-M mean-reversion (PF~1.0 at high frequency) |

### Gate Status

Phase 3 Cycle 3 gate (RR>=3, WR 35-45%, PF>1.3): **NOT PASSED.**
Best achievable PF at any RR/filter = 0.873. The objective is not reachable with
the R/V/M signal set on the current (close-only, 119-day) dataset.
