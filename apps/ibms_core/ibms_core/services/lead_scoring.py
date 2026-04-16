

def score_lead(lead_name: str, features: dict | None = None):
    features = features or {}
    engagement = float(features.get("engagement", 0.5))
    fit = float(features.get("fit", 0.6))
    score = round((0.55 * engagement + 0.45 * fit) * 100, 2)
    return {"lead": lead_name, "score": score, "bucket": "hot" if score >= 75 else "warm"}
