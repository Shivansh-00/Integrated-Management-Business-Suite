import sys
from pathlib import Path
from types import SimpleNamespace


ROOT = Path(__file__).resolve().parents[3]
APP_PATH = ROOT / "apps" / "ibms_core"
if str(APP_PATH) not in sys.path:
    sys.path.insert(0, str(APP_PATH))


if "frappe" not in sys.modules:
    fake_cache = SimpleNamespace(
        get_value=lambda *args, **kwargs: None,
        set_value=lambda *args, **kwargs: None,
    )
    fake_frappe = SimpleNamespace(
        get_all=lambda *args, **kwargs: [],
        cache=lambda: fake_cache,
        session=SimpleNamespace(user="Administrator"),
        has_permission=lambda *args, **kwargs: True,
        throw=lambda msg, exc=None: (_ for _ in ()).throw(Exception(msg)),
    )
    sys.modules["frappe"] = fake_frappe
