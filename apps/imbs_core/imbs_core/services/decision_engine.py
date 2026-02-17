class DecisionEngine:
    """Rule + ML hybrid decision engine."""

    def evaluate(self, context: dict) -> dict:
        threshold = float(context.get("threshold", 60))
        risk_score = float(context.get("risk_score", 0))
        confidence = min(max(risk_score / 100, 0), 1)
        action = "approve" if risk_score < threshold else "review"
        return {"action": action, "confidence": confidence, "risk_score": risk_score}


def evaluate_document(context: dict):
    return DecisionEngine().evaluate(context)
