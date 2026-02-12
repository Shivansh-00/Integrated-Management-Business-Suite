from imbs_core.events.subscriber import on_event


def process_batch(events: list[dict]):
    results = []
    for event in events:
        results.append(on_event(event.get("topic", "unknown"), event.get("payload", {})))
    return results
