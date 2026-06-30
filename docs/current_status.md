# current_status.md

## Current Phase

Phase 3 Cycle 3 — RR-bracket objective (RR>=3, WR 35-45%, PF>1.3) gate FAILED. Max PF=0.873 at any RR/filter. No directional/continuation edge in R/V/M signals (see research/reports/phase3_cycle3_bracket_20260627.md).

---

## Completed

* messages.db 재구축 완료
* BTCUSDT 1분봉 43,500개 적재 완료 (이후 119일 171,827개로 확장)
* ETF Flow 데이터 적재 완료
* Coinbase Premium 데이터 적재 완료
* Funding/OI 데이터 적재 완료
* 연구 스크립트 실행 검증 완료
* Lookahead Bias 제거 완료
* Backtest 환경 구축 완료
* M_t Horizon Selection — no window passes PF>1.3; IC negative at all windows
* Half-Life Analysis — m=14.8, r=39.5, v=94.3, f=33.4, oi=46.5 bars
* Profit Factor Optimization — BLOCKED: OOS PF 0.76~1.18, no edge to optimize
* Grid Search — threshold grid (1/2/3) in walk_forward; best=1, still PF<1.3
* R+V Walk-Forward — FAILED: broken on extended dataset (V/R only last 30 days)
* Regime-by-Regime IC — RANGE 96.7% of bars; M_long IC negative, M_contra IC positive
* Contrarian M_t WF — PF_mean=1.036, WR=63.5% (best model, still fails gate)
* RR-Bracket Backtest (Cycle 3) — new engine (SL -1R / TP +RR / timeout); max PF=0.873 across all RR{1,1.5,2,3} x filters; WR pinned to random-walk break-even at every RR -> no continuation edge

---

## Research Results

* Data Coverage: 2026-05-22 ~ 2026-06-21
* Trades: 1,187
* Win Rate: 35.5%
* Profit Factor: 0.76 ~ 1.18
* Return: -65.7%

Half-Life (bars):

* m=14.8 / r=39.5 / v=94.3 / f=33.4 / oi=46.5

Rank-IC — M_t (VWAP 60/100/240/1440):

* ≈ 0 ~ negative at all windows and horizons

Conclusion:

* Current dataset shows no statistically significant momentum edge.
* Root cause: 1개월 표본이 97.5% RANGE regime — factor alpha 추출 불가.

---

## Next Research (Priority)

P1 — 완료 (2026-06-27 Cycle 1):

* R+V only Walk-Forward ✓
* Regime별 Rank-IC (TREND/RANGE/SHOCK) ✓

P2 — 완료 (2026-06-27 Cycle 2):

* Dataset 119일 확대 (Binance 1m backfill) ✓
* 3모델 Walk-Forward (R+V+M / R+V / Contrarian M_t) ✓
* Contrarian M_t feature branch 실험 ✓
* 비교 리포트: research/reports/phase3_cycle2_validation_20260627.md ✓

P3 — 완료 (2026-06-27 Cycle 3): RR>=3 bracket 검증

* 신규 엔진 research/bracket_backtest.py (SL -1R / TP +RR / timeout)
* direction(contra/mom) x stop-width(2/4/8 ATR) x filter(TREND/CVD/ATR_z) sweep
* RR frontier {1.0, 1.5, 2.0, 3.0} — 어떤 조합도 PF>1.0 미달 (max PF=0.873)
* 근본 원인: 모든 RR에서 WR이 random-walk 손익분기선에 고정 -> entry edge 없음
* 결론: 현 R/V/M signal로 RR>=3 목표는 구조적으로 도달 불가

P4 — 다음 단계 / 보류:

* 우선 intrabar OHLC(high/low) 확보 — close-only TP/SL은 낙관적 추정
* RR>=3가 product 요구라면 exit가 아니라 entry signal 자체를 교체해야 함
* Coinbase premium 히스토리 프록시 (futures basis)로 V 확장
* SHOCK 게이트 완화 검토 (V IC=+0.10, 리스크 결정 사항)

Merge 조건:

* OOS PF > 1.3
* Stable IC (|IC| > 0.03, t > 2)
* No lookahead / Half-Life ≈ Holding Time

---

## Branch Policy

* Main branch: 전략 동결 (factor_api.py / signal_engine.py 수정 금지)
* 실험적 변경은 feature branch에서만 수행

---

## Constraints

* Android Termux 환경
* SQLite only
* No Redis
* No HMM
* Multiprocessing 기반

---

## Do Not Modify

* execution_engine.py
* risk_engine.py
* signal_engine.py
* backtest_runner.py

실거래 엔진 수정 없이 연구 계층에서만 실험 수행.

---

## Phase 3 Research Setup

signal_performance 테이블 확장 완료:

* symbol
* regime
* hold_minutes
* mt_window
* mt_score
* confidence
* cvd_filter
* atr_cutoff
* exit_reason
