"""Phase 5: SIM7600 RF feeds (MAIN / AUX / GNSS) as short 0.30 mm F.Cu CPWG runs with the pi-match parts inline.
Each chain is  U4 RF pin -> shunt C (ANT_*) -> series 0R -> U.FL pad 1 (+ shunt C (RF_*) a short stub beyond).  Shunt caps hang off the
feed with their GND pad pointing away from it; a GND via fence (0.45/0.2) runs both sides of every feed, 0.65 mm off
the centreline (0.2 mm CPWG gap + via annulus), or 1.0 mm where a pad blocks the inner row.  MAIN and AUX share one geometry offset 19 mm in y; GNSS runs along
the 1 mm strip between the U4 top pad row and J7, the bias choke L501 closing the line at its east end.
The parts are moved here (not in place.py) because their final spots are set by the feed, not by the floor plan.
usage: $PY scripts/route_rf.py board.kicad_pcb"""
import math, os, sys
import pcbnew

PCB = sys.argv[1]
b = pcbnew.LoadBoard(PCB)
MM, TM = pcbnew.FromMM, pcbnew.ToMM
F = pcbnew.F_Cu
W, VD, VH = 0.30, 0.45, 0.2
net = b.FindNet
GND = net("GND")
RFN = [net(f"/lte/{p}_{s}") for p in ("ANT", "RF") for s in ("MAIN", "AUX", "GNSS")]
for t in list(b.GetTracks()):
    if t.GetNetCode() in [n.GetNetCode() for n in RFN]:
        b.Delete(t)


def place(ref, x, y, rot):
    fp = b.FindFootprintByReference(ref)
    fp.SetOrientationDegrees(rot); fp.SetPosition(pcbnew.VECTOR2I(MM(x), MM(y)))


def pad(ref, n):
    for p in b.FindFootprintByReference(ref).Pads():
        if p.GetNetCode() == n.GetNetCode():
            q = p.GetPosition(); return TM(q.x), TM(q.y)
    raise KeyError((ref, n.GetNetname()))


def seg(n, pts, w=W, layer=F):
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        t = pcbnew.PCB_TRACK(b); t.SetStart(pcbnew.VECTOR2I(MM(x0), MM(y0))); t.SetEnd(pcbnew.VECTOR2I(MM(x1), MM(y1)))
        t.SetWidth(MM(w)); t.SetLayer(layer); t.SetNet(n); b.Add(t)


feeds = []                                      # (polyline) of every RF run, for the via fence
# ---------------- MAIN (U4.82 -> J5) and AUX (U4.59 -> J6): east 1.5, south to the pi row, east, north into pad 1
for tag, (cs, rs, cr), dy in (("MAIN", ("C517", "R509", "C518"), 0.0), ("AUX", ("C519", "R510", "C520"), -19.0)):
    ant, rf = net(f"/lte/ANT_{tag}"), net(f"/lte/RF_{tag}")
    yr, XC = 61.3 + dy, 70.0                                         # pi row; feed column 0.2 clear of the U4 pads
    # 0402 courtyards are 1.92 x 1.02: shunt / series / shunt centres 1.47 apart so they just touch
    place(cs, XC, yr + 0.48, 270); place(rs, XC + 1.47, yr, 0); place(cr, XC + 2.94, yr + 0.48, 270)
    b.BuildConnectivity()
    u = pad("U4", ant); j = pad("J5" if tag == "MAIN" else "J6", rf)
    p1 = [u, (XC, u[1]), (XC, yr), pad(rs, ant)]
    p2 = [pad(rs, rf), pad(cr, rf)]
    seg(ant, p1); seg(rf, p2); seg(rf, [(j[0], yr), j]); feeds += [p1, p2]

# ---------------- GNSS (U4.79 -> J7) along y 31.45, shunt pads north (GND tied straight into the J7 shield pads)
ant, rf, bias = net("/lte/ANT_GNSS"), net("/lte/RF_GNSS"), net("/lte/GNSS_BIAS")
# C521 sits in the 0.5 mm slot between the Y1 and J7 courtyards, R511 ends under J7.1, C522/L501 east of the J7 courtyard
FY = 31.45                                                       # 0.2 mm (RF_50R) above the U4 pad row
place("J7", 47.6, 29.8, 0)                                        # 0.1 mm east of the floor plan: R511.1 clears J7.1 by 0.2
place("C521", 45.63, FY - 0.48, 90); place("R511", 47.1, FY, 0); place("C522", 49.45, FY - 0.48, 90)
place("L501", 50.92, FY, 180)
b.BuildConnectivity()
u, j = pad("U4", ant), pad("J7", rf)
p1 = [u, (u[0], FY), pad("R511", ant)]
p2 = [pad("R511", rf), pad("L501", rf)]
seg(ant, p1); seg(rf, p2); seg(rf, [(j[0], FY), j]); feeds += [p1, p2]
for c, gx in (("C521", 46.0), ("C522", 49.2)):                    # shunt GND pad -> J7 shield pad
    g = pad(c, GND); seg(GND, [g, (gx, 29.9)], 0.3)

# ---------------- silk: the pi parts sit courtyard-to-courtyard, so their refs go to F.Fab (assembly drawing).
# R511's north silk bar touches J7.1 (silk_over_copper); the footprint stays stock and the fab clips silk at pads.
for r in ("C517", "R509", "C518", "C519", "R510", "C520", "C521", "R511", "C522", "L501"):
    fp = b.FindFootprintByReference(r); fp.Reference().SetLayer(pcbnew.F_Fab)
    fp.Reference().SetPosition(fp.GetPosition())

# ---------------- GND via fence: candidates every 0.8 mm both sides of each feed, kept only where they clear everything
b.BuildConnectivity()
R = VD / 2
pads = [(p, p.GetBoundingBox()) for p in b.GetPads()]
trks = [t for t in b.GetTracks()]
noflyFP = [b.FindFootprintByReference(r).GetBoundingBox(False) for r in ("U4", "J5", "J6", "J7")]


def dseg(px, py, ax, ay, bx, by):
    dx, dy = bx - ax, by - ay; L2 = dx * dx + dy * dy
    k = 0 if L2 == 0 else max(0, min(1, ((px - ax) * dx + (py - ay) * dy) / L2))
    return math.hypot(px - ax - k * dx, py - ay - k * dy)


def drect(px, py, bb):
    x0, y0, x1, y1 = TM(bb.GetX()), TM(bb.GetY()), TM(bb.GetRight()), TM(bb.GetBottom())
    return math.hypot(max(x0 - px, 0, px - x1), max(y0 - py, 0, py - y1))


placed = []


def ok(x, y):
    if not (1 < x < 74 and 1 < y < 69):
        return False
    for bb in noflyFP:
        if drect(x, y, bb) < 0.05:
            return False
    for p, bb in pads:
        need = R + (0.15 if p.GetNetCode() == GND.GetNetCode() else 0.22)
        if drect(x, y, bb) < need:
            return False
    for t in trks:
        if t.GetClass() == "PCB_VIA":
            c = t.GetPosition()
            if math.hypot(TM(c.x) - x, TM(c.y) - y) < R + TM(t.GetWidth(F)) / 2 + 0.2:
                return False
            continue
        s, e = t.GetStart(), t.GetEnd()
        rf = t.GetNetCode() in [n.GetNetCode() for n in RFN]
        need = R + TM(t.GetWidth()) / 2 + (0.2 if rf else 0.15)
        if t.GetNetCode() == GND.GetNetCode():
            need = R + TM(t.GetWidth()) / 2 + 0.05
        if dseg(x, y, TM(s.x), TM(s.y), TM(e.x), TM(e.y)) < need:
            return False
    return all(math.hypot(x - a, y - c) >= 0.75 for a, c in placed)


STEP = 0.8
nv = 0
for poly in feeds:
    for (ax, ay), (bx, by) in zip(poly, poly[1:]):
        L = math.hypot(bx - ax, by - ay)
        if L < 1e-6:
            continue
        nx, ny = -(by - ay) / L, (bx - ax) / L
        for i in range(int(L / STEP) + 1):
            x, y = ax + (bx - ax) * i * STEP / L, ay + (by - ay) * i * STEP / L
            for s, OFF in ((1, 0.65), (-1, 0.65), (1, 1.0), (-1, 1.0)):    # inner row, then outer where blocked
                vx, vy = x + s * nx * OFF, y + s * ny * OFF
                if ok(vx, vy):
                    v = pcbnew.PCB_VIA(b); v.SetPosition(pcbnew.VECTOR2I(MM(vx), MM(vy))); v.SetWidth(MM(VD))
                    v.SetDrill(MM(VH)); v.SetNet(GND); v.SetViaType(pcbnew.VIATYPE_THROUGH); b.Add(v)
                    trks.append(v); placed.append((vx, vy)); nv += 1
# shunt-cap GND pads (MAIN/AUX): one via just beyond each pad
for c in ("C517", "C518", "C519", "C520"):
    gx, gy = pad(c, GND)
    for vx, vy in ((gx, gy + 0.75), (gx - 0.75, gy), (gx + 0.75, gy)):
        if ok(vx, vy):
            v = pcbnew.PCB_VIA(b); v.SetPosition(pcbnew.VECTOR2I(MM(vx), MM(vy))); v.SetWidth(MM(VD))
            v.SetDrill(MM(VH)); v.SetNet(GND); v.SetViaType(pcbnew.VIATYPE_THROUGH); b.Add(v)
            trks.append(v); placed.append((vx, vy)); nv += 1
            seg(GND, [(gx, gy), (vx, vy)], 0.3)
            break

pcbnew.SaveBoard(PCB, b)
for n in RFN:
    print(n.GetNetname(), f"{sum(TM(t.GetLength()) for t in b.GetTracks() if t.GetNetCode() == n.GetNetCode() and t.GetClass() == 'PCB_TRACK'):.2f} mm")
print("fence vias", nv)
for r in ("C517", "R509", "C518", "C519", "R510", "C520", "C521", "R511", "C522", "L501"):
    print(r, [(p.GetNumber(), p.GetNetname(), round(TM(p.GetPosition().x), 2), round(TM(p.GetPosition().y), 2))
              for p in b.FindFootprintByReference(r).Pads()])
sys.stdout.flush(); os._exit(0)
