# CLAUDE.md

Behavioral guidelines to reduce common LLM coding mistakes. Merge with project-specific instructions as needed.

**Tradeoff:** These guidelines bias toward caution over speed. For trivial tasks, use judgment.

## 1. Think Before Coding

**Don't assume. Don't hide confusion. Surface tradeoffs.**

Before implementing:
- State your assumptions explicitly. If uncertain, ask.
- If multiple interpretations exist, present them - don't pick silently.
- If a simpler approach exists, say so. Push back when warranted.
- If something is unclear, stop. Name what's confusing. Ask.

## 2. Simplicity First

**Minimum code that solves the problem. Nothing speculative.**

- No features beyond what was asked.
- No abstractions for single-use code.
- No "flexibility" or "configurability" that wasn't requested.
- No error handling for impossible scenarios.
- If you write 200 lines and it could be 50, rewrite it.

Ask yourself: "Would a senior engineer say this is overcomplicated?" If yes, simplify.

## 3. Surgical Changes

**Touch only what you must. Clean up only your own mess.**

When editing existing code:
- Don't "improve" adjacent code, comments, or formatting.
- Don't refactor things that aren't broken.
- Match existing style, even if you'd do it differently.
- If you notice unrelated dead code, mention it - don't delete it.

When your changes create orphans:
- Remove imports/variables/functions that YOUR changes made unused.
- Don't remove pre-existing dead code unless asked.

The test: Every changed line should trace directly to the user's request.

## 4. Goal-Driven Execution

**Define success criteria. Loop until verified.**

Transform tasks into verifiable goals:
- "Add validation" → "Write tests for invalid inputs, then make them pass"
- "Fix the bug" → "Write a test that reproduces it, then make it pass"
- "Refactor X" → "Ensure tests pass before and after"

For multi-step tasks, state a brief plan:
```
1. [Step] → verify: [check]
2. [Step] → verify: [check]
3. [Step] → verify: [check]
```

Strong success criteria let you loop independently. Weak criteria ("make it work") require constant clarification.

---

**These guidelines are working if:** fewer unnecessary changes in diffs, fewer rewrites due to overcomplication, and clarifying questions come before implementation rather than after mistakes.


##퀀트 프로젝트
quant_workflow

Stage 1
Telegram -> SQLite

Stage 2
ETF Parser -> R_t

Stage 3
LLM Analysis (선택적)

Stage 4
Market Data

V_t = Coinbase Premium
M_t = VWAP Momentum

Stage 5
Signal Engine

R_t
V_t
M_t

(독립 계산)

↓
Signal Engine
↓
S_final

Stage 6
Backtest

Stage 7
Execution

OpenClaw
= 오케스트레이터
(전략 자체가 아님) -이걸 벗어나면 안됨
추가
## 5. Quant-Specific Integrity (Critical)

**Prioritize mathematical correctness and data lineage over elegant code.**

- **Mathematical Traceability:** Break complex signals into intermediate steps (e.g., $R_t, V_t, M_t$). Avoid monolithic one-liners for formulas.
- **No Lookahead Bias:** Every change in Stage 5 must be verified against Stage 6 (Backtest) to ensure no future information leakage.
- **Data Pipeline Rigidity:** Stages 1-4 are "Read-Only" for logic changes. Only modify them if the schema itself is broken.
- **Orchestrator Boundary:** Do not attempt to rewrite the strategy inside the OpenClaw logic. OpenClaw manages, Signal Engine executes.
