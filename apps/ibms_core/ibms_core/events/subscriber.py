from ibms_core.events.event_router import route_event


def on_event(topic: str, payload: dict):
    return route_event(topic, payload)
