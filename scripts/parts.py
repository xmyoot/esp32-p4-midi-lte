"""Resolve passive values to JLCPCB parts (basic preferred), cached in scripts/parts_cache.json."""
import json, re, time
from pathlib import Path
from jlc_search import search

CACHE = Path(__file__).with_name("parts_cache.json")
_cache = json.loads(CACHE.read_text()) if CACHE.exists() else {}

_UNIT = {"R": "Ω", "C": "F"}


def _norm(val: str, kind: str) -> str:
    v = val.replace("µ", "u").replace("Ω", "").strip()
    if kind == "R":
        if v.upper() in ("0", "0R"):
            return "0Ω"
        m = re.fullmatch(r"([\d.]+)([kKmM]?)", v)
        if m:
            n, s = m.groups(); return f"{n}{s.lower() if s.lower()=='k' else s.upper()}Ω".replace("kΩ", "kΩ")
        m = re.fullmatch(r"(\d+)([kKmMR])(\d+)", v)  # 4k7, 49R9
        if m:
            a, s, b = m.groups(); s = "" if s.upper() == "R" else s
            return f"{a}.{b}{s.lower() if s.lower()=='k' else s.upper()}Ω"
    if kind == "C":
        m = re.fullmatch(r"([\d.]+)\s*([pnu])F?", v, re.I)
        if m:
            return f"{m.group(1)}{m.group(2).lower()}F"
    return v


def passive(kind: str, val: str, size: str, volt: str = ""):
    key = f"{kind}|{val}|{size}" + (f"|{volt}" if volt else "")
    if key in _cache:
        return _cache[key]
    want = _norm(val, kind)
    q = f"{size} {want}" + (f" {volt}" if volt else "") + (" resistor" if kind == "R" else " capacitor")
    best = None
    rows = []
    for attempt in range(4):
        try:
            rows = search(q, 25); break
        except Exception:
            time.sleep(1.5 * (attempt + 1))
    for r in rows:
        desc = f"{r.get('describe','')} {r.get('componentSpecificationEn','')}"
        spec = str(r.get("componentSpecificationEn") or "")
        if size not in spec:
            continue
        if not re.search(r"(?<![\d.])" + re.escape(want) + r"(?![\d])", desc):
            continue
        if volt:
            vs = [float(x) for x in re.findall(r"(\d+(?:\.\d+)?)V(?![A-Za-z])", desc)]
            if not vs or max(vs) < float(volt.rstrip("V")):
                continue
        if kind == "C" and "Capacitor" not in str(r.get("componentTypeEn", "")) and "Capacitor" not in desc:
            continue
        if kind == "R" and "Resistor" not in desc and "Resistor" not in str(r.get("componentTypeEn", "")):
            continue
        score = (r.get("componentLibraryType") == "base", r.get("stockCount") or 0)
        if best is None or score > best[0]:
            best = (score, r.get("componentCode"), r.get("componentModelEn"))
    code = best[1] if best else None
    time.sleep(0.4)
    if code is None:
        print(f"[parts] no JLC match for {key}")
        return None
    _cache[key] = code
    _cache["MPN|" + code] = best[2]
    CACHE.write_text(json.dumps(_cache, indent=1, sort_keys=True))
    return code


def mpn(code: str):
    """Manufacturer part number for an LCSC code (cached)."""
    k = "MPN|" + code
    if k not in _cache:
        for attempt in range(4):
            try:
                rows = search(code, 3); break
            except Exception:
                rows = []; time.sleep(1.5 * (attempt + 1))
        hit = [r for r in rows if r.get("componentCode") == code]
        if not hit:
            return None
        _cache[k] = hit[0].get("componentModelEn")
        CACHE.write_text(json.dumps(_cache, indent=1, sort_keys=True))
        time.sleep(0.3)
    return _cache[k]
