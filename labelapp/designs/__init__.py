"""Auto-discovers designs: every module in this package (except common) exposing
NAME (display name), ORDER (optional sort key) and render(data) -> 1-bit 400x640 Image."""
import importlib
import pkgutil

_cache: dict | None = None


def registry() -> dict:
    global _cache
    if _cache is None:
        found = {}
        for m in pkgutil.iter_modules(__path__):
            if m.name.startswith("_") or m.name == "common":
                continue
            mod = importlib.import_module(f"{__name__}.{m.name}")
            if hasattr(mod, "render") and hasattr(mod, "NAME"):
                found[m.name] = mod
        _cache = dict(sorted(found.items(), key=lambda kv: (getattr(kv[1], "ORDER", 100), kv[0])))
    return _cache


def listing() -> list[dict]:
    return [{"id": k, "name": m.NAME} for k, m in registry().items()]


def render(design_id: str, data: dict):
    reg = registry()
    if design_id not in reg:
        raise KeyError(design_id)
    from .common import normalize
    return reg[design_id].render(normalize(data))
