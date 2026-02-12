def suggest_price(base_price: float, demand_index: float, stock_index: float, competitor_index: float):
    multiplier = 1 + (0.4 * demand_index) - (0.2 * stock_index) + (0.2 * competitor_index)
    suggested = round(base_price * max(multiplier, 0.5), 2)
    return {"base_price": base_price, "suggested_price": suggested, "multiplier": round(multiplier, 4)}
