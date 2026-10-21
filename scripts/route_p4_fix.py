"""Phase 5: hand finish of the P4 nets the autorouter left stranded.
C333 (XTAL_N load cap) was placed 8 mm from Y1, in the middle of the U1 east fan-out; it moves to B.Cu under Y1 pin 3
(beside the existing XTAL_N via), which also opens the east escape for C6_WAKE and its neighbours.  The rest are
A*-found (astar2.py) tracks with fixed coordinates.
usage: $PY scripts/route_p4_fix.py board.kicad_pcb"""
import os, sys
import pcbnew

PCB = sys.argv[1]
b = pcbnew.LoadBoard(PCB)
MM, TM = pcbnew.FromMM, pcbnew.ToMM
F, B = pcbnew.F_Cu, pcbnew.B_Cu
net = b.FindNet


def pad(ref, num):
    for p in b.FindFootprintByReference(ref).Pads():
        if p.GetNumber() == num:
            q = p.GetPosition(); return TM(q.x), TM(q.y)
    raise KeyError((ref, num))


def seg(n, pts, w, layer=F):
    n = net(n) if isinstance(n, str) else n
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        t = pcbnew.PCB_TRACK(b); t.SetStart(pcbnew.VECTOR2I(MM(x0), MM(y0))); t.SetEnd(pcbnew.VECTOR2I(MM(x1), MM(y1)))
        t.SetWidth(MM(w)); t.SetLayer(layer); t.SetNet(n); t.SetLocked(True); b.Add(t)


def via(n, x, y, d=0.45, h=0.2):
    n = net(n) if isinstance(n, str) else n
    v = pcbnew.PCB_VIA(b); v.SetPosition(pcbnew.VECTOR2I(MM(x), MM(y))); v.SetWidth(MM(d)); v.SetDrill(MM(h))
    v.SetNet(n); v.SetViaType(pcbnew.VIATYPE_THROUGH); v.SetLocked(True); b.Add(v)


# ---------------- C333 -> B.Cu under Y1.3, pad 1 (XTAL_N) north
c333 = b.FindFootprintByReference("C333")
if not c333.IsFlipped():
    c333.Flip(c333.GetPosition(), pcbnew.FLIP_DIRECTION_LEFT_RIGHT)
for rot in (0, 90, 180, 270):
    c333.SetOrientationDegrees(rot); c333.SetPosition(pcbnew.VECTOR2I(MM(45.2), MM(28.83)))
    if pad("C333", "1")[1] < pad("C333", "2")[1] - 0.5:
        break
c333.Reference().SetLayer(pcbnew.B_Fab); c333.Reference().SetPosition(c333.GetPosition())
seg("/mcu/XTAL_N", [pad("C333", "1"), (44.1, 28.75)], 0.13, B)       # onto the Y1.3 via
via("GND", 45.05, 29.65); seg("GND", [pad("C333", "2"), (45.05, 29.65)], 0.25, B)

pcbnew.SaveBoard(PCB, b)
sys.stdout.flush(); os._exit(0)
