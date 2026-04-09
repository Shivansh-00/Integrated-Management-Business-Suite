import uuid


def start_trace(name: str):
    return {"trace_id": str(uuid.uuid4()), "span": name}
