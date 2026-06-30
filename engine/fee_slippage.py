def apply_cost(pnl, fee=0.05, slippage=0.03):
    """
    pnl: percent
    fee + slippage 반영
    """
    cost = fee + slippage
    return pnl - cost if pnl > 0 else pnl + cost