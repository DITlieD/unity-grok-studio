"""Account model catalog: join team_settings.bin (this account's allow-list) with
model_configs_v3.bin (per-model name/ctx/cost).

FREE flag (grounded against the Devin UI 'Free' badge): a model entry has a
pricing struct in field 32 IFF it is billed. Free models have NO field 32.
Confirmed free set = {kimi-k2-6, kimi-k2-7, swe-1-6, swe-1-7, glm-5-2, SWE-1.5, swe-check}.

Field 3 is the relative credit/ACU cost multiplier for the BILLED models
(swe=0.5 paid? no -- see free flag; kimi/glm are free despite a nonzero field 3,
which is why field 32 presence, not field 3, is the real signal).
"""
from __future__ import annotations
import os, struct
from functools import lru_cache

_DIR = os.path.dirname(os.path.abspath(__file__))
_DATA = os.path.join(_DIR, "data")
KIT = os.path.normpath(os.path.join(_DIR, ".."))
_LEGACY_CFG = os.path.join(KIT, "cli-config")


def _cfg(name):
    """Find a catalog .bin in local data/ first, else the legacy kit cli-config/."""
    a = os.path.join(_DATA, name)
    return a if os.path.exists(a) else os.path.join(_LEGACY_CFG, name)


def _rv(b, i):
    s = o = 0
    while i < len(b):
        c = b[i]; i += 1; o |= (c & 0x7F) << s
        if not (c & 0x80):
            return o, i
        s += 7
    return o, i


def _walk(b):
    i = 0; out = {}
    while i < len(b):
        tag, i = _rv(b, i)
        if i > len(b):
            break
        fn, wt = tag >> 3, tag & 7
        if wt == 0:
            v, i = _rv(b, i)
        elif wt == 1:
            v = ("f64", b[i:i+8]); i += 8
        elif wt == 2:
            ln, i = _rv(b, i); v = b[i:i+ln]; i += ln
        elif wt == 5:
            v = ("f32", b[i:i+4]); i += 4
        else:
            break
        out.setdefault(fn, []).append(v)
    return out


def _s(v):
    return v.decode("utf-8", "replace") if isinstance(v, (bytes, bytearray)) else str(v)


def _f32(v):
    return struct.unpack("<f", v[1])[0] if isinstance(v, tuple) and v[0] == "f32" else None


def _tier(cost, free):
    if free:
        return "FREE"
    if cost is None:
        return "util"
    if cost <= 1.0:
        return "cheap"
    if cost <= 8.0:
        return "standard"
    return "premium"


@lru_cache(maxsize=1)
def load_account_catalog():
    """-> list of {id, name, ctx, cost, tier, free} sorted by cost asc."""
    ts = _walk(open(_cfg("team_settings.bin"), "rb").read())
    allowed = {_s(x) for x in ts.get(7, []) if isinstance(x, (bytes, bytearray))}

    mc = _walk(open(_cfg("model_configs_v3.bin"), "rb").read())
    meta = {}
    for ent in mc.get(1, []):
        if not isinstance(ent, (bytes, bytearray)):
            continue
        m = _walk(ent)
        mid = _s(m.get(22, [b""])[0]) if m.get(22) else ""
        if not mid:
            continue
        ctx = m.get(18, [0])[0]
        meta[mid] = {"name": _s(m.get(1, [b"?"])[0]),
                     "ctx": ctx if isinstance(ctx, int) else 0,
                     "cost": _f32(m.get(3, [None])[0]),
                     "free": 32 not in m}   # no pricing struct => free (UI 'Free' badge)

    rows = []
    for mid in allowed:
        c = meta.get(mid, {})
        free = c.get("free", False)
        cost = c.get("cost")
        rows.append({"id": mid, "name": c.get("name", mid), "ctx": c.get("ctx", 0),
                     "cost": cost, "free": free, "tier": _tier(cost, free)})
    # free first, then by cost
    rows.sort(key=lambda r: (0 if r["free"] else 1,
                             r["cost"] if r["cost"] is not None else 1e9, r["id"]))
    return rows


def annotated_display(r):
    if r["free"]:
        return f"{r['name']}  [FREE]"
    cost = "n/a" if r["cost"] is None else f"x{r['cost']:g}"
    return f"{r['name']}  [{cost} cr | {r['tier']}]"


if __name__ == "__main__":
    cat = load_account_catalog()
    free = [r for r in cat if r["free"]]
    print(f"{len(cat)} models on this account; {len(free)} FREE (no ACU/credit cost)\n")
    for r in cat:
        print(f"  {annotated_display(r):52} id={r['id']:38} ctx={r['ctx']}")
