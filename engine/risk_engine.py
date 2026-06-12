# runtime counter (in-process only)
_CONSECUTIVE_LOSS_COUNT = 0


def evaluate_risk(signal, market_portfolio, params):
    """Deterministic risk evaluation (paper-trading / execution gate).

    No side effects.
    """
    global _CONSECUTIVE_LOSS_COUNT

    # 1. DAILY LOSS CHECK
    if market_portfolio["daily_pnl"] <= -params["daily_loss_limit"]:
        return {
            "approved": False,
            "position_size": 0,
            "reason": "DAILY_LOSS_LIMIT",
            "risk_metrics": {"daily_risk_used": 1.0},
        }

    # 2. CONSECUTIVE LOSS CHECK
    pnl = float(market_portfolio["daily_pnl"])
    if pnl < 0:
        _CONSECUTIVE_LOSS_COUNT += 1
    else:
        _CONSECUTIVE_LOSS_COUNT = 0

    if _CONSECUTIVE_LOSS_COUNT >= 4:
        return {
            "approved": False,
            "position_size": None,
            "reason": "CONSECUTIVE_LOSS_LIMIT",
            "risk_metrics": {"consecutive_loss_count": _CONSECUTIVE_LOSS_COUNT},
        }

    # 3. SIGNAL FILTER
    if signal["action"] == "FLAT":
        return {
            "approved": False,
            "position_size": 0,
            "reason": "FLAT_SIGNAL",
            "risk_metrics": {},
        }

    # 3. RISK AMOUNT
    risk_amount = market_portfolio["equity"] * params["risk_per_trade"]

    # 4. ATR SIZING
    atr = market_portfolio["atr"]
    stop_loss = atr * params["atr_multiplier"]
    position_size = risk_amount / stop_loss

    # 5. EXPOSURE CAP
    if market_portfolio["exposure"] + position_size > params["max_exposure"]:
        position_size = params["max_exposure"] - market_portfolio["exposure"]

    if position_size <= 0:
        return {
            "approved": False,
            "position_size": 0,
            "reason": "EXPOSURE_CAP",
            "risk_metrics": {},
        }

    # 6. APPROVE
    return {
        "approved": True,
        "position_size": position_size,
        "reason": "OK",
        "risk_metrics": {
            "atr_risk": stop_loss,
            "exposure_used": market_portfolio["exposure"] + position_size,
            "daily_risk_used": market_portfolio["daily_pnl"],
        },
    }
