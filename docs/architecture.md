# architecture.md

## Project Overview

Termux(Android) 기반 멀티프로세싱 이벤트 반응형 암호화폐 선물 퀀트 트레이딩 시스템.

핵심 철학:

* 시장을 예측하지 않는다.
* 시장 변화에 반응한다.
* 뉴스는 Signal Generator가 아니라 Signal Validator다.
* 리스크 엔진이 시그널 엔진보다 우선한다.
* 데이터 무결성을 최우선으로 한다.
* Redis, HMM, 분산 서버 없이 Termux + SQLite + multiprocessing으로 구현한다.

---

## System Architecture

```text
Binance WebSocket
        ↓
Collector Process (I/O only)
        ↓
multiprocessing.Queue
        ↓
Engine Process
    ├─ SQLite :memory:
    ├─ Feature Engine (R_t, V_t, M_t)
    ├─ Market Regime Engine
    ├─ Signal Engine
    └─ Risk Engine
        ↓
Execution Engine
    ├─ Exchange API
    └─ Telegram Bot
```

---

## Feature Definitions

### R_t (Macro Bias)

* ETF Flow
* 뉴스 키워드 스코어
* 직접 시그널 생성 금지
* Confidence 조정에만 사용

### V_t (Demand Proxy)

* Coinbase Premium Index
* Kimchi Premium

### M_t (Momentum)

* VWAP
* CVD
* ATR

M_t Horizon은 현재 연구 중이다.

후보:

* VWAP(60)
* VWAP(100)
* VWAP(240)
* VWAP(1440)

---

## Market Regime

* Trend: Volume_Z > 1.5 AND ATR_Z > 1.0
* Range: 그 외
* Shock: Volume_Z > 3.0 AND ATR_Z > 2.5

Shock 발생 시:

* 기존 포지션 50% 축소
* 신규 진입 중단

---

## Risk Rules

* 거래당 최대 리스크: 총 자산의 1%
* Daily Loss Limit: -3%
* Consecutive Loss Limit: 4회
* Maximum Exposure: 30%
* 최소 손익비: 2:1
* ATR 기반 포지션 사이징

---

## OpenClaw Policy

OpenClaw는 주문 권한이 없다.

역할:

* 코드 리뷰
* 백테스트 자동화
* 리포트 생성
* DevOps 지원
