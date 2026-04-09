import time


_METRICS = {"requests_total": 0, "last_refresh_ts": 0}


def inc_requests():
    _METRICS["requests_total"] += 1


def snapshot():
    _METRICS["last_refresh_ts"] = int(time.time())
    return _METRICS.copy()
