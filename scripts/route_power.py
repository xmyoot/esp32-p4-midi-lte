"""Phase 5: hand-routed power stages the autorouter handles badly.
U6 (TPS631000 buck-boost, 3V3 out): L202 turns 180 deg so LX2 (pin 2, west) and LX1 (pin 3, east) fall straight onto its
west / east pads without crossing; both switch nodes run short and wide on F.Cu (0.25 mm necks only while between the
0.5 mm-pitch pins).  The SYS pins (4 / 5, east column) leave north to a via, run south on B.Cu under U6 and drop into
the In2 SYS region through two vias between the L202 pads; the 10 uF input cap C206 moves under U6 on B.Cu.
usage: $PY scripts/route_power.py board.kicad_pcb"""
import os, sys
import pcbnew

PCB = sys.argv[1]
b = pcbnew.LoadBoard(PCB)
MM, TM = pcbnew.FromMM, pcbnew.ToMM
F, B = pcbnew.F_Cu, pcbnew.B_Cu
net = b.FindNet
LX1, LX2, SYS = net("/power/BB_LX1"), net("/power/BB_LX2"), net("SYS")


def pad(ref, num):
    for p in b.FindFootprintByReference(ref).Pads():
        if p.GetNumber() == num:
            q = p.GetPosition(); return TM(q.x), TM(q.y)
    raise KeyError((ref, num))


def seg(n, pts, w, layer=F):
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        t = pcbnew.PCB_TRACK(b); t.SetStart(pcbnew.VECTOR2I(MM(x0), MM(y0))); t.SetEnd(pcbnew.VECTOR2I(MM(x1), MM(y1)))
        t.SetWidth(MM(w)); t.SetLayer(layer); t.SetNet(n); t.SetLocked(True); b.Add(t)


def via(n, x, y, d=0.6, h=0.3):
    v = pcbnew.PCB_VIA(b); v.SetPosition(pcbnew.VECTOR2I(MM(x), MM(y))); v.SetWidth(MM(d)); v.SetDrill(MM(h))
    v.SetNet(n); v.SetViaType(pcbnew.VIATYPE_THROUGH); v.SetLocked(True); b.Add(v)


# ---------------- U6 / L202
codes = {LX1.GetNetCode(), LX2.GetNetCode()}
for t in list(b.GetTracks()):
    if t.GetNetCode() in codes:
        b.Delete(t)
l202 = b.FindFootprintByReference("L202")
l202.SetOrientationDegrees((l202.GetOrientationDegrees() + 180) % 360)
b.BuildConnectivity()
p2, p3 = pad("U6", "2"), pad("U6", "3")                          # LX2 (21.75, 39.64), LX1 (22.25, 39.64)
l2, l1 = pad("L202", "2"), pad("L202", "1")                      # now west (21.68) / east (23.82), y 41.75
# LX2 drops straight into the west pad (0.3 mm: it runs beside the LX1 neck); LX1 necks down, 45 deg past the SYS pin,
# then widens into the east pad.  Both loops are < 2 mm.
seg(LX2, [p2, (p2[0], 41.0)], 0.3)
# The LX1 neck threads the 0.74 mm between the SYS pin-4 corner (22.61, 39.98) and the LX2 pad corner (22.3, 40.65),
# square to that gap through its midpoint, then widens once past both.
seg(LX1, [p3, (p3[0], 40.22), (23.0, 40.567)], 0.3)
seg(LX1, [(23.0, 40.567), (l1[0] - 0.2, 41.0)], 0.6)
# SYS: pins 4 / 5 bridged inside the package, pin 5 north to a 0.5/0.25 via between the C212 pads, a 0.6 mm B.Cu run
# south under U6 to two vias in the 0.9 mm slot between the L202 pads, which land in the In2 SYS region (y >= 41).
p4, p5 = pad("U6", "4"), pad("U6", "5")
VA = (22.9, 37.2)
seg(SYS, [p4, p5], 0.28); seg(SYS, [p5, VA], 0.3); via(SYS, *VA, d=0.5, h=0.25)
VB = [(22.75, 41.75), (22.75, 42.55)]
for v in VB:
    via(SYS, *v, d=0.5, h=0.25)
seg(SYS, [VA, (VA[0], 37.9), (22.75, 38.05), VB[1]], 0.6, B)
# Input cap C206 (10 uF 0805) moves from 8 mm away to B.Cu right under U6: pad 1 (SYS) on the B.Cu run, pad 2 (GND)
# west with its own via to the In1 plane.
c206 = b.FindFootprintByReference("C206")
if not c206.IsFlipped():
    c206.Flip(c206.GetPosition(), pcbnew.FLIP_DIRECTION_LEFT_RIGHT)
for rot in (0, 90, 180, 270):
    c206.SetOrientationDegrees(rot); c206.SetPosition(pcbnew.VECTOR2I(MM(21.8), MM(39.9)))
    if pad("C206", "1")[0] > pad("C206", "2")[0] + 1:
        break
GND = net("GND")
g = pad("C206", "2"); via(GND, 20.6, 41.2, d=0.45, h=0.2); seg(GND, [g, (20.6, 41.2)], 0.4, B)
for r, lay in (("L202", pcbnew.F_Fab), ("C206", pcbnew.B_Fab)):
    fp = b.FindFootprintByReference(r); fp.Reference().SetLayer(lay); fp.Reference().SetPosition(fp.GetPosition())

pcbnew.SaveBoard(PCB, b)
for r in ("L202", "C206"):
    print(r, [(p.GetNumber(), p.GetNetname(), round(TM(p.GetPosition().x), 2), round(TM(p.GetPosition().y), 2)) for p in b.FindFootprintByReference(r).Pads()])
sys.stdout.flush(); os._exit(0)
