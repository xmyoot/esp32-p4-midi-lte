"""Phase 5: drop every plane-net pad (GND -> In1, 3V3 / SYS / VBAT_LTE -> their In2 regions) that the zone fill does
not already join to its plane, through a short pad -> via stub.  Candidate via sites ring each pad (16 directions,
nearest first); a site is kept only when the via clears every foreign object on all four layers, its drill clears
every hole, its stub clears every foreign object on the pad's layer, and it lands inside the main (largest) filled
island of its plane, so a via never feeds a fragment the In2 signal escapes cut off under the P4.
Pads that find no site are listed for hand routing.
usage: $PY scripts/plane_taps.py board.kicad_pcb"""
import math, os, sys
import pcbnew
from shapely.geometry import LineString, Point, Polygon, box
from shapely.strtree import STRtree

PCB = sys.argv[1]
b = pcbnew.LoadBoard(PCB)
MM, TM = pcbnew.FromMM, pcbnew.ToMM
F, I1, I2, B = pcbnew.F_Cu, pcbnew.In1_Cu, pcbnew.In2_Cu, pcbnew.B_Cu
CU = (F, I1, I2, B)
VD, VH, CLR, H2H, EDGE = 0.45, 0.2, 0.15, 0.25, 0.35
PLANE = {"GND": I1, "3V3": I2, "SYS": I2, "VBAT_LTE": I2}
STUB = {"GND": 0.3, "3V3": 0.3, "SYS": 0.4, "VBAT_LTE": 0.4}
pcbnew.ZONE_FILLER(b).Fill(b.Zones())
b.BuildConnectivity()
conn = b.GetConnectivity()


def chain(c):
    return [(TM(c.CPoint(i).x), TM(c.CPoint(i).y)) for i in range(c.PointCount())]


def polys(ps):
    out = []
    for i in range(ps.OutlineCount()):
        o = chain(ps.Outline(i))
        if len(o) >= 3:
            out.append(Polygon(o, [chain(ps.Hole(i, j)) for j in range(ps.HoleCount(i))]).buffer(0))
    return out


def item_poly(it, layer):
    ps = pcbnew.SHAPE_POLY_SET()
    it.TransformShapeToPolygon(ps, layer, 0, MM(0.005), pcbnew.ERROR_INSIDE)
    g = polys(ps)
    return g[0] if len(g) == 1 else (None if not g else g[0].union(g[1]))


# ---------------- per-layer obstacle geometry (net code, shape), plus drill holes
obs = {l: [] for l in CU}
holes = []
for p in b.GetPads():
    for l in CU:
        if p.IsOnLayer(l) and p.FlashLayer(l):
            g = item_poly(p, l)
            if g is not None:
                obs[l].append((p.GetNetCode(), g))
    if p.GetDrillSize().x > 0:
        holes.append(Point(TM(p.GetPosition().x), TM(p.GetPosition().y)).buffer(TM(p.GetDrillSize().x) / 2))
for t in b.GetTracks():
    if t.GetClass() == "PCB_VIA":
        c = Point(TM(t.GetPosition().x), TM(t.GetPosition().y))
        for l in CU:
            obs[l].append((t.GetNetCode(), c.buffer(TM(t.GetWidth(F)) / 2)))
        holes.append(c.buffer(TM(t.GetDrillValue()) / 2))
    else:
        s, e = t.GetStart(), t.GetEnd()
        g = LineString([(TM(s.x), TM(s.y)), (TM(e.x), TM(e.y))]).buffer(TM(t.GetWidth()) / 2)
        obs[t.GetLayer()].append((t.GetNetCode(), g))
# board outline
eb = b.GetBoardEdgesBoundingBox()
board = box(TM(eb.GetX()), TM(eb.GetY()), TM(eb.GetRight()), TM(eb.GetBottom())).buffer(-(EDGE + VD / 2))
trees = {l: STRtree([g for _, g in obs[l]]) for l in CU}
htree = STRtree(holes)
added = {l: [] for l in CU}
added_holes = []
# main filled island of every plane net on its plane layer
main = {}
for z in b.Zones():
    n = z.GetNetname()
    if n in PLANE and z.GetLayer() == PLANE[n]:
        isl = polys(z.GetFilledPolysList(PLANE[n]))
        if isl:
            main[n] = max(isl, key=lambda g: g.area).buffer(-(VD / 2 + 0.05))
# RF nets keep 0.2 mm
rfcodes = {b.FindNet(f"/lte/{a}_{s}").GetNetCode() for a in ("ANT", "RF") for s in ("MAIN", "AUX", "GNSS")}


def clear(layer, g, code):
    for i in trees[layer].query(g.buffer(0.2)):
        oc, og = obs[layer][i]
        if oc != code and g.distance(og) < (0.2 if oc in rfcodes else CLR):
            return False
    for oc, og in added[layer]:
        if oc != code and g.distance(og) < CLR:
            return False
    return True


def site_ok(n, code, layer, pad_xy, v):
    pv = Point(v)
    if not board.contains(pv) or n not in main or not main[n].contains(pv):
        return None
    vg = pv.buffer(VD / 2)
    if not all(clear(l, vg, code) for l in CU):
        return None
    hg = pv.buffer(VH / 2)
    for i in htree.query(hg.buffer(H2H)):
        if hg.distance(holes[i]) < H2H:
            return None
    if any(hg.distance(h) < H2H for h in added_holes):
        return None
    sg = LineString([pad_xy, v]).buffer(STUB[n] / 2)
    if not clear(layer, sg, code):
        return None
    return vg, hg, sg


nv, fail = 0, []
for p in sorted(b.GetPads(), key=lambda p: (p.GetParentFootprint().GetReference(), p.GetNumber())):
    n = p.GetNetname()
    if n not in PLANE or p.GetAttribute() == pcbnew.PAD_ATTRIB_PTH:
        continue
    if any(i.GetClass() == "ZONE" and i.GetLayer() == PLANE[n] for i in conn.GetConnectedItems(p)):
        continue
    layer = F if p.IsOnLayer(F) else B
    code = p.GetNetCode()
    x, y = TM(p.GetPosition().x), TM(p.GetPosition().y)
    pg = item_poly(p, layer)
    done = False
    for d in [k * 0.1 for k in range(0, 16)]:
        for k in range(16):
            a = k * math.pi / 8
            # distance from the pad centre to its edge along a, then d further
            far = (x + 10 * math.cos(a), y + 10 * math.sin(a))
            edge = pg.exterior.intersection(LineString([(x, y), far]))
            r = 0 if edge.is_empty else Point(x, y).distance(edge)
            v = (round(x + (r + VD / 2 + 0.1 + d) * math.cos(a), 3), round(y + (r + VD / 2 + 0.1 + d) * math.sin(a), 3))
            ok = site_ok(n, code, layer, (x, y), v)
            if ok:
                vg, hg, sg = ok
                via = pcbnew.PCB_VIA(b); via.SetPosition(pcbnew.VECTOR2I(MM(v[0]), MM(v[1]))); via.SetWidth(MM(VD))
                via.SetDrill(MM(VH)); via.SetNet(p.GetNet()); via.SetViaType(pcbnew.VIATYPE_THROUGH); b.Add(via)
                t = pcbnew.PCB_TRACK(b); t.SetStart(p.GetPosition()); t.SetEnd(via.GetPosition()); t.SetWidth(MM(STUB[n]))
                t.SetLayer(layer); t.SetNet(p.GetNet()); b.Add(t)
                for l in CU:
                    added[l].append((code, vg))
                added[layer].append((code, sg)); added_holes.append(hg)
                nv += 1; done = True
                break
        if done:
            break
    if not done:
        fail.append(f"{p.GetParentFootprint().GetReference()}.{p.GetNumber()} {n} ({x:.2f},{y:.2f})")

pcbnew.ZONE_FILLER(b).Fill(b.Zones())
pcbnew.SaveBoard(PCB, b)
print("taps", nv, "failed", len(fail))
for f in fail:
    print("  ", f)
sys.stdout.flush(); os._exit(0)
