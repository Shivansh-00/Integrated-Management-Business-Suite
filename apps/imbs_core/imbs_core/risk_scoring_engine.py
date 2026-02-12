def composite_risk_score(factors: dict):
    amount = float(factors.get("amount", 0))
    behavior = float(factors.get("behavior", 0))
    compliance = float(factors.get("compliance", 0))
    return round((0.5 * amount) + (0.3 * behavior) + (0.2 * compliance), 2)
