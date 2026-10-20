"""Hand-designed MIPI CSI-2 routing (2 data lanes + clock), 100 ohm diff: w 0.17, s 0.13 (centres 0.30) on F.Cu over L2 GND.
Lane order differs between the ESP32-P4 (D1, CK, D0 with CK as N,P) and the Pi FPC (CK as P,N, D1, D0), and the P4 has no
documented lane/polarity remap, so the clock pair carries the crossover:
  CKP drops to B.Cu under its 0R (VP1); CKN crosses over it on F.Cu and drops (VN1); both run on B.Cu under the D1 pair,
  then return to F.Cu in a pocket between D1 and D0 (VN, VP, staggered) - now in P4 order (N left, P right).
D0 and D1 stay on F.Cu end to end.  Every coordinate below was clearance-checked against 0.127 mm; DRC verifies.
usage: $PY scripts/route_mipi.py board.kicad_pcb"""
import math, os, sys
import pcbnew

PCB = sys.argv[1]
b = pcbnew.LoadBoard(PCB)
MM = pcbnew.FromMM
W, HALF = 0.17, 0.15
VIA_D, VIA_DRILL = 0.45, 0.2
NETS = {k: b.FindNet(n) for k, n in [
    ("CKP", "CSI_CK_P"), ("CKN", "CSI_CK_N"), ("D1P", "CSI_D1_P"), ("D1N", "CSI_D1_N"), ("D0P", "CSI_D0_P"), ("D0N", "CSI_D0_N"),
    ("pCKP", "/mcu/P4_CSI_CK_P"), ("pCKN", "/mcu/P4_CSI_CK_N"), ("pD1P", "/mcu/P4_CSI_D1_P"), ("pD1N", "/mcu/P4_CSI_D1_N"),
    ("pD0P", "/mcu/P4_CSI_D0_P"), ("pD0N", "/mcu/P4_CSI_D0_N")]}

# wipe any earlier copper on these nets
for t in list(b.GetTracks()):
    if t.GetNetCode() in {n.GetNetCode() for n in NETS.values()}:
        b.Delete(t)


def pad(ref, net):
    for p in b.FindFootprintByReference(ref).Pads():
        if p.GetNetCode() == net.GetNetCode():
            q = p.GetPosition(); return pcbnew.ToMM(q.x), pcbnew.ToMM(q.y)
    raise KeyError((ref, net))


def seg(net, layer, pts, w=W):
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        if abs(x0 - x1) < 1e-6 and abs(y0 - y1) < 1e-6:
            continue
        t = pcbnew.PCB_TRACK(b); t.SetStart(pcbnew.VECTOR2I(MM(x0), MM(y0))); t.SetEnd(pcbnew.VECTOR2I(MM(x1), MM(y1)))
        t.SetWidth(MM(w)); t.SetLayer(layer); t.SetNet(net); b.Add(t)


def via(net, x, y):
    v = pcbnew.PCB_VIA(b); v.SetPosition(pcbnew.VECTOR2I(MM(x), MM(y))); v.SetWidth(MM(VIA_D)); v.SetDrill(MM(VIA_DRILL))
    v.SetNet(net); v.SetViaType(pcbnew.VIATYPE_THROUGH); b.Add(v)


def offset(poly, d):
    """Parallel offset of a polyline by d (positive = right of travel direction, y down), mitred corners."""
    out = []
    for i, (x, y) in enumerate(poly):
        ns = []
        for a, c in ((poly[i - 1], (x, y)) if i > 0 else (None, None), ((x, y), poly[i + 1]) if i < len(poly) - 1 else (None, None)):
            if a is None:
                continue
            dx, dy = c[0] - a[0], c[1] - a[1]; L = math.hypot(dx, dy); ns.append((-dy / L, dx / L))
        if len(ns) == 1:
            nx, ny = ns[0]; k = 1.0
        else:
            nx, ny = ns[0][0] + ns[1][0], ns[0][1] + ns[1][1]; L = math.hypot(nx, ny); nx, ny = nx / L, ny / L
            k = 1.0 / max(0.3, nx * ns[0][0] + ny * ns[0][1])
        out.append((x - nx * d * k, y - ny * d * k))
    return out


F, B = pcbnew.F_Cu, pcbnew.B_Cu
# ---------------- FPC -> 0R row (pad "2" of each 0R is the FPC side, on top)
for lane, ref in (("CKP", "R318"), ("CKN", "R319"), ("D1P", "R320"), ("D1N", "R321"), ("D0P", "R316"), ("D0N", "R317")):
    xf, yf = pad("J2", NETS[lane]); xr, yr = pad(ref, NETS[lane])
    y1 = yf + 1.22; seg(NETS[lane], F, [(xf, yf), (xf, y1), (xr, y1 + abs(xr - xf)), (xr, yr)])


# ---------------- data pairs on F.Cu: coupled centreline, P/N offset, terminal legs to the 0R and P4 pads
def pair(p_lane, n_lane, rp, rn, centre):
    P, N = NETS["p" + p_lane], NETS["p" + n_lane]
    (rpx, rpy), (rnx, rny) = pad(rp, P), pad(rn, N)
    (ppx, ppy), (pnx, pny) = pad("U1", P), pad("U1", N)
    a, c = offset(centre, HALF), offset(centre, -HALF)
    lp, ln = (a, c) if abs(a[-1][0] - ppx) < abs(c[-1][0] - ppx) else (c, a)
    seg(P, F, [(rpx, rpy), (rpx, rpy + 0.19), (lp[0][0], lp[0][1])] + lp + [(ppx, ppy)])
    seg(N, F, [(rnx, rny), (rnx, rny + 0.19), (ln[0][0], ln[0][1])] + ln + [(pnx, pny)])


pair("D1P", "D1N", "R320", "R321", [(40.8, 9.25), (40.8, 9.55), (37.05, 13.30), (37.05, 15.45)])
pair("D0P", "D0N", "R316", "R317", [(43.0, 9.25), (43.0, 10.65), (38.45, 15.20), (38.45, 15.45)])

# ---------------- clock pair: polarity + lane crossover
cp, cn = NETS["pCKP"], NETS["pCKN"]
(rpx, rpy), (rnx, rny) = pad("R318", cp), pad("R319", cn)
(ppx, ppy), (pnx, pny) = pad("U1", cp), pad("U1", cn)
VP1, VN1, VN, VP = (rpx, 9.5), (37.6, 10.9), (37.7, 13.9), (38.6, 14.0)
seg(cp, F, [(rpx, rpy), VP1]); via(cp, *VP1)
seg(cp, B, [VP1, (rpx, 12.9), (38.6, 13.4), VP]); via(cp, *VP)
seg(cp, F, [VP, (ppx, 14.675), (ppx, ppy)])
seg(cn, F, [(rnx, rny), (rnx, 9.2), (37.6, 10.7), VN1]); via(cn, *VN1)
seg(cn, B, [VN1, (37.7, 11.0), VN]); via(cn, *VN)
seg(cn, F, [VN, (37.7, 14.4), (pnx, 14.6), (pnx, pny)])

pcbnew.SaveBoard(PCB, b)


def length(net):
    return sum(pcbnew.ToMM(t.GetLength()) for t in b.GetTracks() if t.GetNetCode() == net.GetNetCode() and t.GetClass() == "PCB_TRACK")


print("lengths mm (FPC->0R | 0R->P4):")
for lane in ("CK", "D1", "D0"):
    lp = (length(NETS[lane + "P"]), length(NETS["p" + lane + "P"])); ln = (length(NETS[lane + "N"]), length(NETS["p" + lane + "N"]))
    print(f"  {lane}: P {lp[0]:.2f}+{lp[1]:.2f}={sum(lp):.2f}  N {ln[0]:.2f}+{ln[1]:.2f}={sum(ln):.2f}  skew {abs(sum(lp) - sum(ln)):.3f}")
sys.stdout.flush(); os._exit(0)
