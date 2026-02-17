def isolation_forest_score(payload: dict):
    """Placeholder for sklearn IsolationForest service integration."""
    amount = float(payload.get("amount", 0))
    velocity = float(payload.get("velocity", 0.2))
    score = min(1.0, (amount / 1_000_000) * 0.8 + velocity * 0.2)
    return round(score * 100, 2)


def detect_fraud(voucher_type: str, voucher_no: str, payload: dict):
    score = isolation_forest_score(payload)
    return {
        "voucher_type": voucher_type,
        "voucher_no": voucher_no,
        "fraud_score": score,
        "requires_review": score >= 70,
    }
