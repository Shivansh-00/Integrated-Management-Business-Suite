import frappe


@frappe.whitelist(methods=["POST"])
def ask_erp(question: str):
    """Natural-language assistant placeholder.

    Production flow: NLP intent parser -> safe query planner -> tool execution.
    """
    return {
        "question": question,
        "answer": "I can summarize KPIs, risks, and forecasts once connected to semantic tools.",
        "sql_safe": True,
    }
