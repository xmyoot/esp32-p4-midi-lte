"""Hand escape of the P4 USB-Serial/JTAG pins (52 DN top row, 53 DP left column) to the 22R series pair on B.Cu.
Full-speed USB (12 Mbit/s, edges >= 4 ns) is electrically short here, so the escape only needs to be short and
tidy, not impedance-exact.  F.Cu stubs climb to two vias in the keep-clear corridor north of the USB corner
(place.py KEEPOUT_F/B), then two parallel B.Cu lanes run west to R315 (DN) / R314 (DP) pad 1.
The USB_D* side of the resistors (to J1 and the BQ25895 BC1.2 pins) is left to route_diff / route.py.
usage: $PY scripts/route_usb.py board.kicad_pcb"""
import math, os, sys
import pcbnew

PCB = sys.argv[1]
b = pcbnew.LoadBoard(PCB)
MM = pcbnew.FromMM
W = 0.22
DP, DN = b.FindNet("/mcu/P4_USB_DP"), b.FindNet("/mcu/P4_USB_DN")
for t in list(b.GetTracks()):
    if t.GetNetCode() in (DP.GetNetCode(), DN.GetNetCode()):
        b.Delete(t)


def pad(ref, net):
    for p in b.FindFootprintByReference(ref).Pads():
        if p.GetNetCode() == net.GetNetCode():
            q = p.GetPosition(); return pcbnew.ToMM(q.x), pcbnew.ToMM(q.y)
    raise KeyError((ref, net))


def seg(net, layer, pts, w=W):
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        t = pcbnew.PCB_TRACK(b); t.SetStart(pcbnew.VECTOR2I(MM(x0), MM(y0))); t.SetEnd(pcbnew.VECTOR2I(MM(x1), MM(y1)))
        t.SetWidth(MM(w)); t.SetLayer(layer); t.SetNet(net); b.Add(t)


def via(net, x, y):
    v = pcbnew.PCB_VIA(b); v.SetPosition(pcbnew.VECTOR2I(MM(x), MM(y))); v.SetWidth(MM(0.45)); v.SetDrill(MM(0.2))
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
(dnx, dny), (dpx, dpy) = pad("U1", DN), pad("U1", DP)
(rnx, rny), (rpx, rpy) = pad("R315", DN), pad("R314", DP)
VN, VP = (dnx, 14.0), (34.12, 14.55)
# 0.15 mm necks while beside the 0.35 mm-pitch QFN pads (pad 51 / pad 54), full width once clear
NECK = 0.15
seg(DN, F, [(dnx, dny), (dnx, 15.6)], NECK); seg(DN, F, [(dnx, 15.6), VN]); via(DN, *VN)
seg(DP, F, [(dpx, dpy), (34.12, dpy)], NECK); seg(DP, F, [(34.12, dpy), VP]); via(DP, *VP)
# B.Cu: DN north lane, DP south lane, 0.35 mm pitch (0.13 gap) between the jogs
seg(DN, B, [VN, (dnx - 0.15, 13.85), (rnx + 0.6, 13.85), (rnx, rny)])
seg(DP, B, [VP, (33.77, 14.2), (rpx + 0.95, 14.2), (rpx, rpy)])

# ---------------- connector side: J1 -> B.Cu pair -> R314/R315 pad 2, coupled 0.22 / 0.13 (0.35 mm centres)
# The receptacle interleaves the data pins (B7 DN, A6 DP, A7 DN, B6 DP) and the ESD part (U17) only exposes its IO
# pins on the west column, so a true flow-through is impossible: the pair drops to B.Cu right at J1 and runs under
# U17, and the ESD pins tap it through short (< 1 mm) stubs -- irrelevant at full speed.  B.Cu is empty along this
# corridor (P4 decaps sit east of x 30.8, U5 EP west of 16.7).  The pair crosses the In2 SYS/3V3 split at y 41;
# at 12 Mbit/s (>= 4 ns edges) the return detour is negligible.  The BQ25895 BC1.2 taps (R203/R204) are left to route.py.
UDP, UDN = b.FindNet("USB_DP"), b.FindNet("USB_DN")
CC1, CC2 = b.FindNet("/power/USB_CC1"), b.FindNet("/power/USB_CC2")
for t in list(b.GetTracks()):
    if t.GetNetCode() in (UDP.GetNetCode(), UDN.GetNetCode(), CC1.GetNetCode(), CC2.GetNetCode()):
        b.Delete(t)
(tpx, tpy), (tnx, tny) = pad("R314", UDP), pad("R315", UDN)       # (29.39, 14.55) / (29.39, 13.45)
J = {p.GetNumber(): (pcbnew.ToMM(p.GetPosition().x), pcbnew.ToMM(p.GetPosition().y))
     for p in b.FindFootprintByReference("J1").Pads() if p.GetNumber()}
U = {p.GetNumber(): (pcbnew.ToMM(p.GetPosition().x), pcbnew.ToMM(p.GetPosition().y))
     for p in b.FindFootprintByReference("U17").Pads()}
# J1 F.Cu: DP pins joined under the pad row (y 63), DN pins joined just above it (y 60.85); one via each
DPV, DNV = (17.25, 60.45), (15.945, 60.6)
seg(UDP, F, [J["A6"], (J["A6"][0], 63.0), (J["B6"][0], 63.0), J["B6"], DPV]); via(UDP, *DPV)
seg(UDN, F, [J["B7"], (J["B7"][0], 60.85), (J["A7"][0], 60.85), J["A7"]]); seg(UDN, F, [(DNV[0], 60.85), DNV]); via(UDN, *DNV)
# B.Cu pair: north under U17, 45 deg NE, north to the 22R pair
XN, H = 28.1, 0.175                                              # trunk centre x on the north run, half pitch
cl = [(16.12, 59.5), (16.12, 55.82), (XN, 55.82 - (XN - 16.12)), (XN, 14.85)]
pdp, pdn = offset(cl, -H), offset(cl, H)                         # DP east of DN going north
seg(UDP, B, [DPV] + pdp + [(XN + H + 0.3, tpy), (tpx, tpy)])
seg(UDN, B, [DNV] + pdn + [(XN - H, tny + 0.3), (XN - H + 0.3, tny), (tnx, tny)])
# U17 ESD taps: pad 1 (DP) north to a via east of the pair, pad 2 (DN) west to a via beside it
TP, TN = (16.6, 56.95), (15.45, 58.0)
seg(UDP, F, [U["1"], (U["1"][0], 57.15), (U["1"][0] + 0.2, 56.95), TP]); via(UDP, *TP); seg(UDP, B, [TP, (16.12 + H, TP[1])])
seg(UDN, F, [U["2"], TN]); via(UDN, *TN); seg(UDN, B, [TN, (16.12 - H, TN[1])])
# CC1: A5 -> U17.4 on F.Cu (west of U17); B.Cu link under the J1 pad row to R201.1 (east)
WC = 0.2
seg(CC1, F, [J["A5"], (J["A5"][0], 61.1), (14.85, 60.7), (14.85, U["4"][1]), U["4"]], WC); via(CC1, 14.85, 60.7)
seg(CC1, B, [(14.85, 60.7), (14.85, 61.6), (18.0, 61.6), (18.0, 60.35)], WC); via(CC1, 18.0, 60.35)
r201 = pad("R201", CC1); seg(CC1, F, [(18.0, 60.35), (r201[0], 60.1), r201], WC)
# CC2: B5 -> R202.1 on F.Cu; B.Cu loop around the CC1 link (under J1, up the west side) to a via beside U17.5
r202 = pad("R202", CC2)
seg(CC2, F, [J["B5"], (J["B5"][0], 61.05), (18.6, 60.7), (r202[0], 60.7), r202], WC); via(CC2, 18.95, 60.7)
seg(CC2, B, [(18.95, 60.7), (18.95, 62.3), (14.3, 62.3), (14.3, 59.9), (15.1, 59.9), (15.45, 59.55)], WC); via(CC2, 15.45, 59.55)
seg(CC2, F, [(15.45, 59.55), U["5"]], WC)

pcbnew.SaveBoard(PCB, b)
for n in (DP, DN, UDP, UDN, CC1, CC2):
    print(n.GetNetname(), f"{sum(pcbnew.ToMM(t.GetLength()) for t in b.GetTracks() if t.GetNetCode() == n.GetNetCode() and t.GetClass() == 'PCB_TRACK'):.2f} mm")
sys.stdout.flush(); os._exit(0)
