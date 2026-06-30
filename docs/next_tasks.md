# next_tasks.md

## Priority 1

### M_t Horizon 결정

후보:

* VWAP(60)
* VWAP(100)
* VWAP(240)
* VWAP(1440)

평가 기준:

* Profit Factor > 1.3
* Half-Life ≈ Holding Time
* MDD 최소화

---

## Priority 2

* M_t 후보 동시 계산
* Half-Life 측정
* Holding Time 비교
* Threshold Grid Search

---

## Priority 3

* Trailing Stop 검증
* Slippage 측정
* State Recovery 테스트

---

## Success Criteria

Phase 3 완료 조건:

* Profit Factor > 1.3
* Walk-Forward Validation 통과
* MDD 허용 범위 충족

---

## Current Question

~~M_t는 무엇으로 정의할 것인가?~~ → 2026-06-27 답: **현 데이터에서 long-momentum M_t는 edge 없음**
(모든 VWAP 윈도우에서 rank-IC ≈ 0 또는 음수, walk-forward PF 0.76~1.18).

다음 결정 필요 (사용자 판단 — 전략 변경이므로 자동 적용 안 함):

1. M_t를 contrarian(부호 반전)으로 재정의해 IC 재측정 — funding과 동일 패턴(음의 IC)이므로 가장 유망.
2. M_t를 S_final에서 제외하고 R+V만으로 walk-forward 재검증.
3. 데이터 기간/심볼 확대 후 재측정 (현재 1개월·BTC 단일, 표본 부족 가능).
