"""kisch -- tiny KiCad 10 hierarchical-schematic generator.

Design files describe parts + pin->net maps; this module embeds library symbols,
places parts in clusters, and connects every pin with a short stub plus a label,
global label, power symbol or no-connect flag.  UUIDs are deterministic (uuid5),
so regenerating keeps the schematic<->PCB links stable.
"""
from __future__ import annotations
import copy, math, re, uuid
from pathlib import Path

PROJECT = "esp32p4_lte_cam"
ROOT = Path(__file__).resolve().parent.parent
KICAD_SYM = Path(r"C:/Program Files/KiCad/10.0/share/kicad/symbols")
LOCAL_LIBS = {"lcsc": ROOT / "lib/lcsc.kicad_sym", "espressif": ROOT / "lib/espressif.kicad_sym",
              "project": ROOT / "lib/symbols/project.kicad_sym"}
NS = uuid.UUID("6f1c2b4e-5d0a-4a8e-9a77-1e2f3a4b5c6d")
GRID = 1.27
STUB = 2.54
PAPER = {"A4": (297, 210), "A3": (420, 297), "A2": (594, 420), "A1": (841, 594)}


def uid(*parts) -> str:
    return str(uuid.uuid5(NS, "/".join(map(str, parts))))


def snap(v: float) -> float:
    return round(round(v / GRID) * GRID, 4)


# ---------------------------------------------------------------- s-expressions
class Q(str):
    """A quoted string atom."""


_TOK = re.compile(r'\s*(?:(\()|(\))|"((?:[^"\\]|\\.)*)"|([^\s()"]+))')


def parse(text: str):
    stack, cur, pos = [], [], 0
    while True:
        m = _TOK.match(text, pos)
        if not m or m.end() == pos:
            break
        pos = m.end()
        lp, rp, qs, at = m.groups()
        if lp:
            stack.append(cur); cur = []
        elif rp:
            done, cur = cur, stack.pop(); cur.append(done)
        elif qs is not None:
            cur.append(Q(qs.replace('\\"', '"').replace("\\\\", "\\")))
        else:
            cur.append(at)
    return cur[0]


def fmt(node, ind=0) -> str:
    if not isinstance(node, list):
        if isinstance(node, Q):
            return '"' + node.replace("\\", "\\\\").replace('"', '\\"') + '"'
        if isinstance(node, float):
            return f"{node:.4f}".rstrip("0").rstrip(".")
        return str(node)
    simple = all(not isinstance(c, list) for c in node)
    if simple:
        return "(" + " ".join(fmt(c) for c in node) + ")"
    head = [fmt(c) for c in node if not isinstance(c, list)]
    out = "\t" * ind + "(" + " ".join(head)
    for c in node:
        if isinstance(c, list):
            s = fmt(c, ind + 1)
            out += "\n" + (s if s.startswith("\t") else "\t" * (ind + 1) + s)
    return out + "\n" + "\t" * ind + ")"


def kids(node, key):
    return [c for c in node if isinstance(c, list) and c and c[0] == key]


def kid(node, key):
    k = kids(node, key)
    return k[0] if k else None


# ---------------------------------------------------------------- symbol library
class Pin:
    def __init__(self, num, name, typ, x, y, ang, length, unit, hidden):
        self.num, self.name, self.type = num, name, typ
        self.x, self.y, self.ang, self.len, self.unit, self.hidden = x, y, ang, length, unit, hidden


class LibSym:
    def __init__(self, lib_id: str, node):
        self.lib_id, self.node = lib_id, node
        self.name = lib_id.split(":", 1)[1]
        self.props = {p[1]: p[2] for p in kids(node, "property")}
        self.is_power = kid(node, "power") is not None
        self.pins: list[Pin] = []
        xs, ys = [0.0], [0.0]
        for sub in kids(node, "symbol"):
            m = re.match(r".*_(\d+)_(\d+)$", sub[1])
            unit, style = (int(m.group(1)), int(m.group(2))) if m else (0, 1)
            if style > 1:
                continue
            for g in sub:
                if not isinstance(g, list):
                    continue
                if g[0] == "pin":
                    at, ln = kid(g, "at"), kid(g, "length")
                    nm, nu = kid(g, "name"), kid(g, "number")
                    p = Pin(str(nu[1]), str(nm[1]), g[1], float(at[1]), float(at[2]),
                            int(float(at[3])) if len(at) > 3 else 0, float(ln[1]) if ln else 2.54,
                            unit, "hide" in g or kid(g, "hide") is not None)
                    self.pins.append(p); xs.append(p.x); ys.append(p.y)
                for key in ("start", "end", "center"):
                    k = kid(g, key)
                    if k: xs.append(float(k[1])); ys.append(float(k[2]))
                pts = kid(g, "pts")
                if pts:
                    for xy in kids(pts, "xy"):
                        xs.append(float(xy[1])); ys.append(float(xy[2]))
        self.bbox = (min(xs), min(ys), max(xs), max(ys))   # symbol coords, y up
        self.units = sorted({p.unit for p in self.pins if p.unit > 0}) or [1]

    def find(self, key: str) -> list[Pin]:
        hits = [p for p in self.pins if p.num == key]
        if not hits:
            hits = [p for p in self.pins if p.name == key or p.name.split("/")[0] == key]
        return hits


class Libs:
    def __init__(self):
        self.files, self.cache = {}, {}

    def _file(self, nick):
        if nick not in self.files:
            path = LOCAL_LIBS.get(nick) or KICAD_SYM / f"{nick}.kicad_sym"
            root = parse(path.read_text(encoding="utf-8"))
            self.files[nick] = {s[1]: s for s in kids(root, "symbol")}
        return self.files[nick]

    def get(self, lib_id: str) -> LibSym:
        if lib_id in self.cache:
            return self.cache[lib_id]
        nick, name = lib_id.split(":", 1)
        syms = self._file(nick)
        if name not in syms:
            raise KeyError(f"symbol {lib_id} not found")
        node = copy.deepcopy(syms[name])
        ext = kid(node, "extends")
        if ext:  # flatten derived symbol onto its parent
            parent = copy.deepcopy(self.get(f"{nick}:{ext[1]}").node)
            child_props = {p[1]: p for p in kids(node, "property")}
            new = [parent[0], Q(name)]
            for c in parent[2:]:
                if isinstance(c, list) and c[0] == "property" and c[1] in child_props:
                    new.append(child_props.pop(c[1]))
                elif isinstance(c, list) and c[0] == "symbol":
                    c = copy.deepcopy(c); c[1] = Q(c[1].replace(ext[1].split(":")[-1], name, 1)); new.append(c)
                else:
                    new.append(c)
            new[2:2] = list(child_props.values())
            node = new
        node = copy.deepcopy(node)
        node[1] = Q(lib_id)
        sym = LibSym(lib_id, node)
        self.cache[lib_id] = sym
        return sym


LIBS = Libs()

# ---------------------------------------------------------------- design model
DIRS = {0: (-1, 0), 180: (1, 0), 90: (0, 1), 270: (0, -1)}   # pin angle -> outward unit vector (screen coords, y down)


class Part:
    def __init__(self, sheet, ref, lib_id, value, fp="", unit=1, **fields):
        self.sheet, self.ref, self.lib_id, self.value, self.fp, self.unit = sheet, ref, lib_id, value, fp, unit
        self.sym = LIBS.get(lib_id)
        self.fields = {k: v for k, v in fields.items() if v is not None and k != "dnp"}
        self.dnp = bool(fields.get("dnp"))
        self.conn: dict[str, str] = {}      # pin number -> net (or "NC")
        self.x = self.y = 0.0

    # pin map ------------------------------------------------------------
    def pins(self):
        return [p for p in self.sym.pins if p.unit in (0, self.unit)]

    def __setitem__(self, key, net):
        hits = [p for p in self.sym.find(str(key)) if p.unit in (0, self.unit)]
        if not hits:
            raise KeyError(f"{self.ref}: no pin '{key}' in {self.lib_id}")
        for p in hits:
            self.conn[p.num] = net

    def wire(self, mapping: dict):
        for k, v in mapping.items():
            self[k] = v
        return self

    # geometry -------------------------------------------------------------
    def extent(self):
        """Bounding box in sheet-relative coords (y down) incl. stubs + label text."""
        x0, y0, x1, y1 = self.sym.bbox
        L, R, T, B = x0, x1, -y1, -y0
        for p in self.pins():
            dx, dy = DIRS.get(p.ang, (0, 0))
            net = self.conn.get(p.num, "")
            lab = 0 if net in ("", "NC") or self.sheet.is_power(net) else len(net) * 1.05 + 3.5
            ex, ey = p.x + dx * (STUB + lab), -p.y + dy * (STUB + (lab if dy else 0))
            if self.sheet.is_power(net):
                ey += dy * 5
            L, R, T, B = min(L, ex), max(R, ex), min(T, ey - 2), max(B, ey + 2)
        txt = max(len(self.ref), len(self.value)) * 0.95 + 2.0      # ref/value text drawn right of the body
        R = max(R, x1 + 1.0 + txt)
        return L - 2.54, T - 3.81, R + 2.54, B + 3.81


class Sheet:
    def __init__(self, design, name, title, page):
        self.design, self.name, self.title, self.page = design, name, title, page
        self.parts: list[Part] = []
        self.groups: list[list[Part]] = []
        self.notes: list[str] = []
        self._ctr: dict[str, int] = {}
        self.ref_base = 100 * page

    def is_power(self, net):
        return net in self.design.power_nets

    def group(self):
        self.groups.append([]); return self

    def add(self, ref, lib_id, value, fp="", unit=1, **f) -> Part:
        if ref.endswith("?"):
            pre = ref[:-1]
            n = self._ctr.get(pre, self.ref_base) + 1
            self._ctr[pre] = n
            ref = f"{pre}{n}"
        p = Part(self, ref, lib_id, value, fp, unit, **f)
        self.parts.append(p)
        if not self.groups:
            self.groups.append([])
        self.groups[-1].append(p)
        return p

    # passives helpers ---------------------------------------------------
    def R(self, val, a, b, size="0402", **f):
        p = self.add("R?", "Device:R", val, f"Resistor_SMD:R_{size}_{_metric(size)}Metric", **_lcsc("R", val, size, f))
        return p.wire({"1": a, "2": b})

    def C(self, val, a, b="GND", size="0402", v="", **f):
        p = self.add("C?", "Device:C", val + (f" {v}" if v else ""), f"Capacitor_SMD:C_{size}_{_metric(size)}Metric",
                     **_lcsc("C", val, size, f, v))
        return p.wire({"1": a, "2": b})

    def L(self, val, a, b, fp, **f):
        p = self.add("L?", "Device:L", val, fp, **f)
        return p.wire({"1": a, "2": b})

    def flag(self, *nets):
        for n in nets:
            self.add("#FLG?", "power:PWR_FLAG", "PWR_FLAG", "", in_bom="no").wire({"1": n})

    def TP(self, net, fp="TestPoint:TestPoint_Pad_D1.0mm"):
        p = self.add("TP?", "Connector:TestPoint", net, fp, in_bom="no")
        return p.wire({"1": net})


def _metric(size):
    return {"0201": "0603", "0402": "1005", "0603": "1608", "0805": "2012", "1206": "3216", "1210": "3225"}[size]


def _lcsc(kind, val, size, f, volt=""):
    from parts import passive  # local module: value -> LCSC basic part
    if "LCSC" not in f and val != "DNP":
        code = passive(kind, val, size, volt)
        if code:
            f["LCSC"] = code
    if f.get("LCSC") and "MPN" not in f:
        from parts import mpn
        m = mpn(f["LCSC"])
        if m:
            f["MPN"] = m
    return f


class Design:
    def __init__(self, title, rev="A"):
        self.title, self.rev = title, rev
        self.sheets: list[Sheet] = []
        self.power_nets = {"GND"}
        self.root_uuid = uid("root")

    def sheet(self, name, title):
        s = Sheet(self, name, title, len(self.sheets) + 2)
        self.sheets.append(s)
        return s

    # ------------------------------------------------------------- checks
    def check(self):
        msgs, refs, net_sheets = [], {}, {}
        for s in self.sheets:
            for p in s.parts:
                if p.ref in refs:
                    msgs.append(f"duplicate ref {p.ref}")
                refs[p.ref] = p
                if p.sym.is_power:
                    continue
                for pin in p.pins():
                    if pin.num not in p.conn:
                        msgs.append(f"{s.name}: {p.ref} pin {pin.num} ({pin.name}) unassigned")
                for n in set(p.conn.values()):
                    if n != "NC":
                        net_sheets.setdefault(n, set()).add(s.name)
        nets = {}
        for s in self.sheets:
            for p in s.parts:
                for num, n in p.conn.items():
                    nets.setdefault(n, []).append(f"{p.ref}.{num}")
        for n, pins in nets.items():
            if n != "NC" and len(pins) == 1 and n not in self.power_nets and not n.startswith("TP_"):
                msgs.append(f"single-pin net {n}: {pins[0]}")
        self.net_sheets = net_sheets
        return msgs

    # ------------------------------------------------------------- output
    def write(self, out_dir: Path):
        self.check()
        for s in self.sheets:
            (out_dir / f"{s.name}.kicad_sch").write_text(self._sheet_text(s), encoding="utf-8")
        (out_dir / f"{PROJECT}.kicad_sch").write_text(self._root_text(), encoding="utf-8")

    def _head(self, uuid_, paper, title, page):
        return [ "kicad_sch", ["version", "20250114"], ["generator", Q("eeschema")], ["generator_version", Q("10.0")],
                 ["uuid", Q(uuid_)], ["paper", Q(paper)],
                 ["title_block", ["title", Q(title)], ["date", Q("2026-10-19")], ["rev", Q(self.rev)],
                  ["company", Q("Portfolio design - ESP32-P4 LTE Camera")], ["comment", 1, Q(self.title)]]]

    def _root_text(self):
        doc = self._head(self.root_uuid, "A4", "Top level / sheet index", 1)
        doc.append(["lib_symbols"])
        cols, w, h = 3, 70, 30
        for i, s in enumerate(self.sheets):
            x, y = 20 + (i % cols) * (w + 20), 40 + (i // cols) * (h + 25)
            su = uid("sheet", s.name)
            doc.append(["sheet", ["at", x, y], ["size", w, h], ["exclude_from_sim", "no"], ["in_bom", "yes"],
                        ["on_board", "yes"], ["dnp", "no"], ["fields_autoplaced", "yes"],
                        ["stroke", ["width", 0.1524], ["type", "solid"]], ["fill", ["color", 0, 0, 0, 0.0]],
                        ["uuid", Q(su)],
                        _prop("Sheetname", s.name, x, y - 0.7, size=1.8, justify=("left", "bottom")),
                        _prop("Sheetfile", f"{s.name}.kicad_sch", x, y + h + 0.6, justify=("left", "top")),
                        ["instances", ["project", Q(PROJECT), ["path", Q(f"/{self.root_uuid}"), ["page", Q(str(s.page))]]]]])
            doc.append(_text(s.title, x + 2, y + 6))
        y0 = 40 + ((len(self.sheets) - 1) // cols + 1) * (h + 25)
        for j, line in enumerate(self._index_notes()):
            doc.append(_text(line, 20, y0 + j * 4.5))
        doc.append(["sheet_instances", ["path", Q("/"), ["page", Q("1")]]])
        doc.append(["embedded_fonts", "no"])
        return fmt(doc) + "\n"

    def _index_notes(self):
        return [f"{self.title} - rev {self.rev}",
                "Inter-sheet connections use global labels; power rails use power symbols (net name = value).",
                "Generated by scripts/kisch.py from scripts/design/*.py - edit the design files, then regenerate."]

    def _sheet_text(self, s: Sheet):
        su = uid("sheet", s.name)
        path = f"/{self.root_uuid}/{su}"
        items, lib_ids = [], {}
        # ---- layout: groups packed in shelves
        boxes = []
        for g in s.groups:
            gx = gy = 0.0; row_h = 0.0; gw = 0.0; placed = []
            maxw = 170 if len(g) > 1 else 1e9
            first = True
            for p in g:
                L, T, R, B = p.extent()
                w, h = R - L, B - T
                if first:
                    placed.append((p, -L, -T)); gx, gy, row_h, gw = 0, h, 0, w; first = False; continue
                if gx + w > max(maxw, gw) and gx > 0:
                    gy += row_h; gx = 0; row_h = 0
                placed.append((p, gx - L, gy - T)); gx += w; row_h = max(row_h, h); gw = max(gw, gx)
            boxes.append((placed, max(gw, 1), gy + row_h))
        for paper in ("A3", "A2", "A1"):
            PW, PH = PAPER[paper]; mx, my = 15, 22
            x = mx; y = my; shelf = 0; ok = True; pos = []
            for placed, w, h in boxes:
                if x + w > PW - mx and x > mx:
                    y += shelf + 12; x = mx; shelf = 0
                pos.append((x, y)); x += w + 14; shelf = max(shelf, h)
                if y + h > PH - 30:
                    ok = False
            if ok:
                break
        for (placed, w, h), (ox, oy) in zip(boxes, pos):
            for p, dx, dy in placed:
                p.x, p.y = snap(ox + dx), snap(oy + dy)
        doc = self._head(su, paper, s.title, s.page)
        # ---- symbols
        pwr_ctr = [0]
        for p in s.parts:
            lib_ids[p.lib_id] = p.sym
            items.append(self._symbol(p, path))
            for pin in p.pins():
                net = p.conn.get(pin.num)
                if net is None:
                    continue
                px, py = p.x + pin.x, p.y - pin.y
                dx, dy = DIRS.get(pin.ang, (1, 0))
                if net == "NC":
                    items.append(["no_connect", ["at", px, py], ["uuid", Q(uid(s.name, p.ref, pin.num, "nc"))]]); continue
                ex, ey = px + dx * STUB, py + dy * STUB
                items.append(["wire", ["pts", ["xy", px, py], ["xy", ex, ey]], ["stroke", ["width", 0], ["type", "default"]],
                              ["uuid", Q(uid(s.name, p.ref, pin.num, "w"))]])
                if self.is_power_net(net):
                    pwr_ctr[0] += 1
                    lid = "power:GND" if net == "GND" else "power:VCC"
                    psym = LIBS.get(lid); lib_ids[lid] = psym
                    out = (dx, dy)
                    if net == "GND":
                        rot = {(0, 1): 0, (0, -1): 180, (1, 0): 90, (-1, 0): 270}[out]
                    else:
                        rot = {(0, -1): 0, (0, 1): 180, (1, 0): 270, (-1, 0): 90}[out]
                    ref = f"#PWR{s.page:02d}{pwr_ctr[0]:03d}"
                    items.append(self._power(lid, net, ref, ex, ey, rot, path, uid(s.name, p.ref, pin.num, "p")))
                else:
                    ang = {(1, 0): 0, (-1, 0): 180, (0, -1): 90, (0, 1): 270}[(dx, dy)]
                    glob = len(self.net_sheets.get(net, ())) > 1 or net in self.global_nets
                    items.append(_label(net, ex, ey, ang, uid(s.name, p.ref, pin.num, "l"), glob))
        for i, n in enumerate(s.notes):
            items.append(_text(n, 15, PAPER[paper][1] - 40 + i * 4))
        doc.append(["lib_symbols"] + [ls.node for ls in lib_ids.values()])
        doc += items
        doc.append(["embedded_fonts", "no"])
        return fmt(doc) + "\n"

    global_nets: set = set()

    def is_power_net(self, net):
        return net in self.power_nets

    def _symbol(self, p: Part, path):
        props = [("Reference", p.ref, 0, 0), ("Value", p.value, 0, 0), ("Footprint", p.fp, 0, 0),
                 ("Datasheet", p.fields.pop("Datasheet", p.sym.props.get("Datasheet", "")), 0, 0)]
        x0, y0, x1, y1 = p.sym.bbox
        node = ["symbol", ["lib_id", Q(p.lib_id)], ["at", p.x, p.y, 0], ["unit", p.unit],
                ["exclude_from_sim", "no"], ["in_bom", "no" if p.fields.get("in_bom") == "no" else "yes"],
                ["on_board", "yes"], ["dnp", "yes" if p.dnp else "no"], ["uuid", Q(uid(p.sheet.name, p.ref))]]
        node.append(_prop("Reference", p.ref, p.x + x1 + 1.0, p.y - y1 - 1.0, justify=("left",)))
        node.append(_prop("Value", p.value, p.x + x1 + 1.0, p.y - y1 + 1.6, justify=("left",)))
        node.append(_prop("Footprint", p.fp, p.x, p.y, hide=True))
        node.append(_prop("Datasheet", props[3][1], p.x, p.y, hide=True))
        for k, v in p.fields.items():
            if k == "in_bom":
                continue
            node.append(_prop(k, str(v), p.x, p.y, hide=True))
        for pin in p.pins():
            node.append(["pin", Q(pin.num), ["uuid", Q(uid(p.sheet.name, p.ref, "pin", pin.num))]])
        node.append(["instances", ["project", Q(PROJECT), ["path", Q(path), ["reference", Q(p.ref)], ["unit", p.unit]]]])
        return node

    def _power(self, lid, net, ref, x, y, rot, path, u):
        return ["symbol", ["lib_id", Q(lid)], ["at", x, y, rot], ["unit", 1], ["exclude_from_sim", "no"],
                ["in_bom", "yes"], ["on_board", "yes"], ["dnp", "no"], ["uuid", Q(u)],
                _prop("Reference", ref, x, y, hide=True),
                _prop("Value", net, x + (0 if rot in (0, 180) else (2 if rot == 270 else -2)),
                      y + (-3.8 if rot == 0 else 3.8 if rot == 180 else 0),
                      justify=(("left",) if rot == 270 else ("right",) if rot == 90 else ())),
                _prop("Footprint", "", x, y, hide=True), _prop("Datasheet", "", x, y, hide=True),
                ["pin", Q("1"), ["uuid", Q(u[:-4] + "0001")]],
                ["instances", ["project", Q(PROJECT), ["path", Q(path), ["reference", Q(ref)], ["unit", 1]]]]]


def _prop(name, val, x, y, size=1.27, justify=(), hide=False):
    eff = ["effects", ["font", ["size", size, size]]]
    if justify:
        eff.append(["justify", *justify])
    if hide:
        eff.append(["hide", "yes"])
    return ["property", Q(name), Q(val), ["at", round(x, 4), round(y, 4), 0], eff]


def _label(net, x, y, ang, u, glob):
    just = ["justify", "left" if ang in (0, 90) else "right"]
    if glob:
        return ["global_label", Q(net), ["shape", "bidirectional"], ["at", x, y, ang], ["fields_autoplaced", "yes"],
                ["effects", ["font", ["size", 1.27, 1.27]], just], ["uuid", Q(u)]]
    return ["label", Q(net), ["at", x, y, ang], ["fields_autoplaced", "yes"],
            ["effects", ["font", ["size", 1.27, 1.27]], just + ["bottom"]], ["uuid", Q(u)]]


def _text(s, x, y):
    return ["text", Q(s), ["exclude_from_sim", "no"], ["at", x, y, 0],
            ["effects", ["font", ["size", 1.8, 1.8]], ["justify", "left", "bottom"]], ["uuid", Q(uid("text", s))]]


def dump(lib_id):
    """Print a symbol's pins (helper for writing design files)."""
    s = LIBS.get(lib_id)
    print(f"{lib_id}: {len(s.pins)} pins, units {s.units}, footprint={s.props.get('Footprint')}")
    for p in sorted(s.pins, key=lambda p: (p.unit, int(p.num) if p.num.isdigit() else 9999, p.num)):
        print(f"  u{p.unit} {p.num:>4} {p.name:<22} {p.type}")
