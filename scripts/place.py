"""Phase 4 placement.
1. ANCHORS: connectors, modules, ICs at hand-chosen poses (docs/PLACEMENT.md explains each).
2. SATELLITES: every other part goes to the nearest free spot next to the pin it serves.
   Decoupling caps are spread across the owner IC's supply pins (least-used pin first).
Collision model: courtyard bboxes + 0.20 mm, mounting-hole circles, 0.5 mm board margin.
Run: $PY scripts/place.py   (rewrites positions in esp32p4_lte_cam.kicad_pcb)"""
import math, os, sys
import pcbnew
from kisch import ROOT

PCB = ROOT / "esp32p4_lte_cam.kicad_pcb"
W, H, MARGIN, GAP = 75.0, 70.0, 0.5, 0.20
HOLES = [(3.5, 9.5), (71.5, 9.5), (3.5, 66.5), (71.5, 66.5)]
HOLE_R = 2.9

ANCHORS = {  # ref: (x, y, rot)   board origin top-left, +y toward the USB (bottom) edge
    # front edge: camera FPC (cable exits north), IR LEDs in the corners, PIR, IR-cut connector, IR driver
    "J2": (37.5, 3.6, 180), "D602": (4.5, 3.0, 0), "D603": (10.5, 3.0, 0), "D604": (64.5, 3.0, 0), "D605": (70.5, 3.0, 0),
    "U19": (21.5, 6.6, 0), "J9": (49.5, 4.2, 180), "U12": (57.5, 6.5, 0), "U13": (54.0, 9.5, 0),
    # MIPI CSI 0R series row in FPC lane order (pad 2 = FPC side on top): CK, D1, D0 - see scripts/route_mipi.py
    "R318": (38.1, 8.2, 90), "R319": (39.1, 8.2, 90), "R320": (40.3, 8.2, 90), "R321": (41.3, 8.2, 90),
    "R316": (42.5, 8.2, 90), "R317": (43.5, 8.2, 90),
    # SoC rotated 180 deg: CSI pins face the FPC, flash pins face U2, XTAL/32k/CHIP_PU face the modem side
    "U1": (39.5, 21.0, 180), "U2": (50.0, 17.5, 90), "Y1": (43.0, 29.6, 0), "Y2": (47.5, 25.0, 90),
    "U7": (30.0, 30.5, 0), "U15": (36.5, 29.4, 0),
    # Wi-Fi module top-right, antenna end on the east edge; microSD slot on the west edge
    "U3": (66.3, 20.0, 270), "J3": (9.9, 21.0, 270),
    # modem bottom-right, U.FLs at its antenna pins, LTE switch at its VBAT pins
    "U4": (53.5, 48.0, 0), "J5": (72.6, 59.0, 0), "J6": (72.6, 40.0, 0), "J7": (47.5, 29.8, 0), "U9": (41.5, 67.4, 0),
    # service edge (bottom): nano-SIM slot, USB-C; battery on the west edge; buttons by the USB
    "J4": (29.8, 61.3, 0), "U18": (29.8, 51.6, 0), "J1": (16.5, 66.0, 0), "U17": (16.5, 58.5, 0), "D201": (16.5, 55.3, 0),
    "J8": (5.4, 50.0, 90), "SW301": (5.0, 58.0, 0), "SW302": (11.2, 58.0, 0),
    # power block west/centre
    # USB 22R series pair on B.Cu, ~5 mm from the P4 USB pins (52 DN / 53 DP); fed by two vias in the corridor
    # north of the USB corner (KEEPOUT_F/B below), then B.Cu toward J1.  4th field = side.
    "R315": (29.9, 13.45, 180, "B"), "R314": (29.9, 14.55, 180, "B"),
    "U5": (15.5, 47.5, 0), "U6": (22.0, 39.0, 0), "U8": (27.0, 36.0, 0), "U14": (5.5, 40.5, 0), "Q201": (10.0, 40.5, 0),
}
P4_DECAPS_BOTTOM = True        # Review 3 decision (2026-10-19): SoC 100n/1u caps on B.Cu under their pins
LOOP_OWNER = {"/camera_ir/IR_SW": "U12", "/mcu/HP_SW": "U7", "/power/CHG_SW": "U5", "/power/BB_LX1": "U6",
              "/power/BB_LX2": "U6", "/power/CHG_BTST": "U5", "/power/CHG_REGN": "U5", "/power/CHG_PMID": "U5"}
# keep-clear corridors (x0, y0, x1, y1): MIPI lanes between FPC and P4 (top), and the clock pair's B.Cu dip (bottom)
KEEPOUT_F = [(35.9, 5.45, 44.4, 15.35), (33.5, 12.8, 35.9, 15.35)]   # CSI fan-in; USB escape vias
KEEPOUT_B = [(36.9, 8.9, 40.2, 14.7), (30.8, 12.7, 36.9, 15.35)]     # CSI clock crossover; USB B.Cu corridor
BROAD = {"GND", "3V3", "SYS", "VBAT_LTE", "1V8_IO6", "BAT", "VBUS"}   # rails too wide to imply a location
SHEET_OWNER = {("mcu.kicad_sch", "3V3"): "U1", ("mcu.kicad_sch", "1V8_IO6"): "U1", ("wifi.kicad_sch", "3V3"): "U3",
               ("lte.kicad_sch", "3V3"): "U16", ("lte.kicad_sch", "1V8_IO6"): "U16", ("lte.kicad_sch", "SYS"): "U9",
               ("camera_ir.kicad_sch", "3V3"): "U13", ("camera_ir.kicad_sch", "SYS"): "U12",
               ("storage.kicad_sch", "3V3"): "U11", ("power.kicad_sch", "3V3"): "U6", ("power.kicad_sch", "SYS"): "U5",
               ("power.kicad_sch", "VBUS"): "U5", ("power.kicad_sch", "BAT"): "U5"}
DECAP_OWNER = {"VDD_HP": "U1", "VDD_FLASH": "U1", "VDD_PSRAM": "U1", "VDD_MIPI": "U1", "/mcu/VDDO_4": "U1",
               "VBAT_LTE": "U4", "3V3_CAM": "J2", "3V3_SD": "J3", "/camera_ir/PIR_VDD": "U19"}


def V(x, y):
    return pcbnew.VECTOR2I(pcbnew.FromMM(x), pcbnew.FromMM(y))


def mm(v):
    return pcbnew.ToMM(v)


class Placer:
    def __init__(self, board):
        self.b = board
        self.fps = {fp.GetReference(): fp for fp in board.GetFootprints()}
        self.rects = []          # placed obstacle rects (F side, plus through-hole/anchor parts)
        self.brects = []         # B side obstacles
        self.pin_use = {}        # (ref, pad) -> decaps assigned
        self.anchor_refs = []

    def crt(self, fp):
        """Keep-out box = courtyard UNION pads (+0.15): imported footprints draw body-only courtyards."""
        c = fp.GetCourtyard(pcbnew.B_CrtYd if fp.IsFlipped() else pcbnew.F_CrtYd)
        bb = c.BBox() if c.OutlineCount() else fp.GetBoundingBox(False, False)
        x0, y0, x1, y1 = mm(bb.GetX()), mm(bb.GetY()), mm(bb.GetRight()), mm(bb.GetBottom())
        for p in fp.Pads():
            pb = p.GetBoundingBox()
            x0, y0 = min(x0, mm(pb.GetX()) - 0.15), min(y0, mm(pb.GetY()) - 0.15)
            x1, y1 = max(x1, mm(pb.GetRight()) + 0.15), max(y1, mm(pb.GetBottom()) + 0.15)
        return x0, y0, x1, y1

    def set_pose(self, fp, x, y, rot):
        fp.SetOrientationDegrees(rot); fp.SetPosition(V(x, y))

    def free(self, r, rects=None):
        rects = self.rects if rects is None else rects
        x0, y0, x1, y1 = r
        for (a0, b0, a1, b1) in (KEEPOUT_B if rects is self.brects else KEEPOUT_F):
            if x0 < a1 and a0 < x1 and y0 < b1 and b0 < y1:
                return False
        if x0 < MARGIN or y0 < MARGIN or x1 > W - MARGIN or y1 > H - MARGIN:
            return False
        for (a0, b0, a1, b1) in rects:
            if x0 < a1 + GAP and a0 < x1 + GAP and y0 < b1 + GAP and b0 < y1 + GAP:
                return False
        for hx, hy in HOLES:
            cx, cy = min(max(hx, x0), x1), min(max(hy, y0), y1)
            if (cx - hx) ** 2 + (cy - hy) ** 2 < HOLE_R ** 2:
                return False
        return True

    def place_anchors(self):
        for ref, (x, y, rot, *side) in ANCHORS.items():
            fp = self.fps[ref]; bottom = side == ["B"]
            if bottom != fp.IsFlipped():
                fp.Flip(fp.GetPosition(), pcbnew.FLIP_DIRECTION_LEFT_RIGHT)
            self.set_pose(fp, x, y, rot)
            r = self.crt(fp)
            if bottom:
                self.brects.append(r); continue
            for other, (a0, b0, a1, b1) in zip(self.anchor_refs, self.rects):
                if r[0] < a1 and a0 < r[2] and r[1] < b1 and b0 < r[3]:
                    print(f"!! anchor {ref} overlaps {other}: dx={min(r[2], a1) - max(r[0], a0):.2f} dy={min(r[3], b1) - max(r[1], b0):.2f}")
            self.rects.append(r); self.anchor_refs.append(ref)
            if any(pd.GetAttribute() == pcbnew.PAD_ATTRIB_PTH for pd in fp.Pads()):
                self.brects.append(r)

    def pads_on(self, net, placed_only=True, exclude=None):
        out = []
        for ref, fp in self.fps.items():
            if ref == exclude or (placed_only and ref not in self.done):
                continue
            for p in fp.Pads():
                if p.GetNetname() == net:
                    out.append((ref, p))
        return out

    def target(self, fp):
        ref = fp.GetReference()
        nets = {p.GetNetname() for p in fp.Pads() if p.GetNetname()}
        # switch-node parts hug their regulator's SW/boot pin (hot loop first, rails second)
        for n in nets:
            if n in LOOP_OWNER and LOOP_OWNER[n] in self.done:
                o = self.fps[LOOP_OWNER[n]]
                pins = [q for q in o.Pads() if q.GetNetname() == n]
                if pins:
                    return self.outward(o, pins[0], 1.2)
        # decoupling: one rail + GND, owner known -> least-used supply pin of the owner
        rail = [n for n in nets if n != "GND"]
        if len(rail) == 1 and "GND" in nets and rail[0] in DECAP_OWNER and DECAP_OWNER[rail[0]] in self.done:
            owner = self.fps[DECAP_OWNER[rail[0]]]
            pins = [p for p in owner.Pads() if p.GetNetname() == rail[0]]
            if pins:
                p = min(pins, key=lambda q: self.pin_use.get((owner.GetReference(), q.GetNumber()), 0))
                self.pin_use[(owner.GetReference(), p.GetNumber())] = self.pin_use.get((owner.GetReference(), p.GetNumber()), 0) + 1
                return self.outward(owner, p)
        if len(rail) == 1 and "GND" in nets:                           # rail decap: owner by sheet
            owner = SHEET_OWNER.get((fp.GetSheetfile(), rail[0]))
            if owner in self.done:
                o = self.fps[owner]
                pins = [q for q in o.Pads() if q.GetNetname() == rail[0]]
                if pins:
                    q = min(pins, key=lambda q: self.pin_use.get((owner, q.GetNumber()), 0))
                    self.pin_use[(owner, q.GetNumber())] = self.pin_use.get((owner, q.GetNumber()), 0) + 1
                    return self.outward(o, q)
        pts = []
        for n in nets:
            if n in BROAD and len(nets - BROAD) > 0:
                continue
            for r, p in self.pads_on(n, exclude=ref):
                if self.fps[r].GetSheetfile() == fp.GetSheetfile() or n not in BROAD:
                    pts.append(self.outward(self.fps[r], p))
        if not pts:
            return None
        return sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts)

    def outward(self, owner, pad, d=1.6):
        c, p = owner.GetPosition(), pad.GetPosition()
        vx, vy = mm(p.x - c.x), mm(p.y - c.y); n = math.hypot(vx, vy) or 1
        return mm(p.x) + vx / n * d, mm(p.y) + vy / n * d

    def bottom_decap(self, fp):
        """--p4-decaps-bottom: SoC 100n/1u caps go on B.Cu right under the supply pin they serve."""
        if not P4_DECAPS_BOTTOM or fp.GetSheetfile() != "mcu.kicad_sch" or not fp.GetReference().startswith("C"):
            return False
        nets = {p.GetNetname() for p in fp.Pads()}
        if "GND" not in nets or fp.GetValue().startswith(("10u", "22u", "4.7u", "22p", "18p")):
            return False
        rail = [n for n in nets if n != "GND"]
        if len(rail) != 1 or rail[0] not in ("3V3", "VDD_HP", "VDD_FLASH", "VDD_PSRAM", "VDD_MIPI", "/mcu/VDDO_4", "1V8_IO6"):
            return False
        return True

    def place_satellite(self, fp):
        if self.bottom_decap(fp):
            return self.place_on(fp, self.target(fp), side="B")
        return self.place_on(fp, self.target(fp), side="F")

    def place_on(self, fp, t, side):
        if (side == "B") != fp.IsFlipped():          # flip onto the requested side (undoes earlier runs too)
            fp.Flip(fp.GetPosition(), pcbnew.FLIP_DIRECTION_LEFT_RIGHT)
        rects = self.brects if side == "B" else self.rects
        if t is None:
            t = (W / 2, H / 2)
        tx, ty = t
        offs = {}
        for rot in (0, 90):
            self.set_pose(fp, 0, 0, rot); offs[rot] = self.crt(fp)
        step = 0.25
        for ring in range(0, 160):
            rr = ring * step
            n = max(1, int(2 * math.pi * rr / step))
            best = None
            for k in range(n):
                a = 2 * math.pi * k / n
                x, y = round((tx + rr * math.cos(a)) / 0.05) * 0.05, round((ty + rr * math.sin(a)) / 0.05) * 0.05
                for rot in (0, 90):
                    o = offs[rot]; r = (x + o[0], y + o[1], x + o[2], y + o[3])
                    if self.free(r, rects):
                        best = (x, y, rot, r); break
                if best:
                    break
            if best:
                x, y, rot, r = best
                self.set_pose(fp, x, y, rot); rects.append(r)
                return math.hypot(x - tx, y - ty)
        print(f"!! no room for {fp.GetReference()}")
        return None

    def run(self):
        self.place_anchors()
        self.done = set(ANCHORS)
        rest = [f for r, f in self.fps.items() if r not in ANCHORS and not r.startswith("H")]
        # order: decaps of the SoC first, other passives by sheet, test points last
        def key(fp):
            r = fp.GetReference(); nets = {p.GetNetname() for p in fp.Pads()}
            soc_decap = fp.GetSheetfile() == "mcu.kicad_sch" and "GND" in nets and r.startswith("C")
            sw_loop = r.startswith("L") or bool(nets & {"/mcu/HP_SW", "/power/CHG_SW", "/power/BB_LX1", "/power/BB_LX2",
                                                         "/camera_ir/IR_SW", "/camera_ir/IR_VOUT"})
            return (r.startswith("TP"), not sw_loop, not soc_decap, r[0] not in "LDQUY", fp.GetSheetfile(), r)
        dists = {}
        for fp in sorted(rest, key=key):
            d = self.place_satellite(fp)
            self.done.add(fp.GetReference()); dists[fp.GetReference()] = d
        far = sorted(((d, r) for r, d in dists.items() if d is not None and d > 4), reverse=True)
        print(f"placed {len(ANCHORS)} anchors + {len(dists)} satellites; >4 mm from target: {len(far)}")
        for d, r in far[:20]:
            print(f"   {r}: {d:.1f} mm")


def main():
    board = pcbnew.LoadBoard(str(PCB))
    Placer(board).run()
    pcbnew.SaveBoard(str(PCB), board)
    print("saved", flush=True)
    os._exit(0)


if __name__ == "__main__":
    main()
