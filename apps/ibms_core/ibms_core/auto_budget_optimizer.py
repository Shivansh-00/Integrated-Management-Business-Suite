def optimize_budget(lines: list[dict], growth_target: float = 0.1):
    total = sum(float(line.get("amount", 0)) for line in lines)
    adjusted = round(total * (1 + growth_target), 2)
    return {"current_total": total, "optimized_total": adjusted}
