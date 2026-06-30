# decisions.md

## 2026-06-21

### Database Reconstruction

Decision:

* messages.db 재구축

Reason:

* 기존 DB 손실 및 스키마 불일치 해결

Impact:

* 연구 데이터셋 재생성 완료
* 43,500개 1분봉 확보

Status:

* Applied

---

### signal_performance 확장

Decision: signal_performance 테이블 컬럼 추가

Status: Applied

Required Columns:

* mt_window
* mt_score
* hold_minutes
* symbol
* regime
* confidence
* cvd_filter
* atr_cutoff
* exit_reason

Purpose:

* M_t Horizon 검증
* Half-Life 분석
* PF 최적화

---

### M_t Horizon Selection

Status:

* Resolved (no edge found) — see 2026-06-27

Candidates evaluated:

* VWAP(60)
* VWAP(100)
* VWAP(240)
* VWAP(1440)

Selection Criteria:

* PF > 1.3
* Half-Life ≈ Holding Time
* Lowest MDD

---

## 2026-06-27 — Phase 3 Validation

### VWAP Window Sweep + Walk-Forward (R+V+M)

Status: Complete — **gate FAILED**

M_t Horizon decision: **No window selected. M_t has no positive edge.**

Evidence (BTCUSDT, 2026-05-22 ~ 06-21):

* VWAP-window rank-IC sweep — all near-zero, mostly negative:
  * VWAP(60):  IC@{5,15,30,60} = -0.006 / -0.010 / -0.009 / -0.016
  * VWAP(100): -0.008 / -0.007 / -0.009 / -0.018
  * VWAP(240): +0.001 / -0.003 / -0.010 / -0.028
  * VWAP(1440): -0.004 / -0.002 / -0.005 / +0.000
* m_raw half-life = 14.8 bars (avg holding 13–16 bars — only criterion that passes)
* Walk-forward OOS PF = 0.76 ~ 1.18 across 5 folds; every fold total_return < 0

Conclusion:

* PF > 1.3 criterion NOT met → cannot promote to sizing/execution
* M_t IC consistently negative — sample is mean-reverting, not trending
* No code change to factor_api.py / signal_engine.py (Do-Not-Modify + orchestrator boundary)

---

### R+V Walk-Forward (M 제거 모델)

Status: **FAILED — not better than R+V+M**

Walk-forward 5-fold (threshold grid 1/2, fee 4bps):

| fold | th | OOS PF | WR | ret | trades |
| ---- | -- | ------ | -- | --- | ------ |
| 1 | 1 | 0.701 | 0.444 | -0.151 | 171 |
| 2 | 2 | 0.161 | 0.333 | -0.005 | 3 |
| 3 | 2 | 0.930 | 0.430 | -0.105 | 128 |
| 4 | 2 | 0.716 | 0.520 | -0.051 | 50 |
| 5 | 2 | 1.787 | 0.556 | -0.033 | 90 |

Conclusion: 4/5 folds fail PF>1.3 gate. M 제거가 도움 안 됨. 데이터 확장 없이 판단 불가.

---

### Regime-by-Regime IC Analysis

Key findings:

* RANGE (n=42,119 — 전체의 97.5%): 모든 factor IC ≤ 0. 알파 없음.
* TREND (n=1,033 — 2.5%): R·V h=1에서 약한 양의 IC(+0.02~+0.05), h≥5에서 음수.
* SHOCK (n=348 — 0.8%): V IC 양수(+0.06~+0.11 전 horizon), 하지만 전략은 SHOCK=FLAT.

Root cause: 1개월 표본이 거의 전부 RANGE → 어떤 factor도 edge 추출 불가.

다음 결정: 데이터 3개월 이상 확보 후 재검증 필수.

---

### RR-Bracket Backtest (Cycle 3 — RR>=3 objective)

Status: **FAILED — objective structurally unreachable with current signals**

신규 연구 엔진 `research/bracket_backtest.py` (production 미수정):
SL -1R / TP +RR / timeout, R = atr_mult x ATR(14), next-bar fill, close-only TP/SL.

목표: RR>=3.0, WR 35-45%, PF>1.3. 거래 축소 수단(threshold, TREND-only, CVD, ATR_z).

Evidence (BTCUSDT, 119일):

* RR=3 sweep 18개 config — 최고 PF=0.885 (contra TREND x2ATR, N=34). 전부 PF<1.
* RR frontier {1.0/1.5/2.0/3.0} 전 구간 — 최고 PF=0.873. 어떤 RR도 PF>1.0 미달.
* WR이 모든 RR에서 random-walk 손익분기(1/(1+k))에 정렬:
  rr1.0→~48%, rr1.5→~40%, rr2.0→~33-41%, rr3.0→~26-34%.

Conclusion:

* Entry signal에 bracket payoff에 대한 방향성 edge가 없음 (WR = bracket 기하학으로 결정).
* Contrarian-M은 mean-reversion(소폭·빠름) → RR>=3 momentum payoff와 구조적 반대.
* 필터로 거래수 2,165→27까지 축소해도 PF 개선 없음 → 부족한 것은 noise가 아니라 edge.
* 다음: intrabar OHLC 확보 후 재측정. RR>=3 고정 요구면 entry signal 교체 필요.
