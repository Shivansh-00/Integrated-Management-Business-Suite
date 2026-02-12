def evaluate_control_set(transaction: dict):
    violations = []
    if transaction.get("amount", 0) > 500000 and not transaction.get("approval_reference"):
        violations.append("MISSING_HIGH_VALUE_APPROVAL")
    return {"passed": len(violations) == 0, "violations": violations}
