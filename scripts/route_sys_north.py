"""Phase 5: SYS feed to the north IR block (U12 IR-LED boost, L601, U13 IR-cut driver, their input caps).
The In2 SYS region ends at y 41, so the loads at y 7-12 get a 0.6 mm In2 trunk (A*-found, around the east side of the P4
plane keepout) from the SYS region to two drop vias: V1 between C605 and U12, V2 under L601.  F.Cu stubs fan out from
the vias.  C605 shifts 0.4 mm east and C608 moves onto U13 pin 1 (the old spot was walled in by IRCUT_A).
usage: $PY scripts/route_sys_north.py board.kicad_pcb"""
import os, sys
import pcbnew

PCB = sys.argv[1]
b = pcbnew.LoadBoard(PCB)
MM, TM = pcbnew.FromMM, pcbnew.ToMM
F, I2 = pcbnew.F_Cu, pcbnew.In2_Cu
SYS, GND = b.FindNet("SYS"), b.FindNet("GND")


def pad(ref, num):
    for p in b.FindFootprintByReference(ref).Pads():
        if p.GetNumber() == num:
            q = p.GetPosition(); return TM(q.x), TM(q.y)
    raise KeyError((ref, num))


def seg(n, pts, w, layer=F):
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        t = pcbnew.PCB_TRACK(b); t.SetStart(pcbnew.VECTOR2I(MM(x0), MM(y0))); t.SetEnd(pcbnew.VECTOR2I(MM(x1), MM(y1)))
        t.SetWidth(MM(w)); t.SetLayer(layer); t.SetNet(n); t.SetLocked(True); b.Add(t)


def via(n, x, y, d=0.5, h=0.25):
    v = pcbnew.PCB_VIA(b); v.SetPosition(pcbnew.VECTOR2I(MM(x), MM(y))); v.SetWidth(MM(d)); v.SetDrill(MM(h))
    v.SetNet(n); v.SetViaType(pcbnew.VIATYPE_THROUGH); v.SetLocked(True); b.Add(v)


# ---------------- parts
c605 = b.FindFootprintByReference("C605")
c605.SetPosition(pcbnew.VECTOR2I(MM(54.55), MM(6.15)))           # was 54.15: clears room for C608
c608 = b.FindFootprintByReference("C608")
for rot in (0, 90, 180, 270):                                     # vertical, SYS pad south onto U13.1
    c608.SetOrientationDegrees(rot); c608.SetPosition(pcbnew.VECTOR2I(MM(52.95), MM(7.3)))
    if pad("C608", "1")[1] > pad("C608", "2")[1] + 0.5:
        break
b.BuildConnectivity()

# ---------------- In2 trunk: SYS region (34.5, 43.5) -> east of the P4 keepout -> V1, branch -> V2
V1, V2 = (55.5, 7.15), (63.0, 10.7)
seg(SYS, [(34.5, 43.5), (38.85, 43.5), (46.4, 35.95), (46.4, 25.6), (47.0, 25.0),
          (47.0, 17.95), (53.2, 11.75), (55.9, 11.75), (56.35, 11.3), (56.35, 8.9), (55.5, 8.05), V1], 0.6, I2)
# V1 -> V2 goes north round the IR_LED_PWM In2 run (via at 56.7, 6.1), then 45 deg down past the IR_VOUT via (60, 9.1)
seg(SYS, [V1, (55.5, 6.15), (56.35, 5.3), (57.4, 5.3), (62.8, 10.7), V2], 0.6, I2)
via(SYS, *V1); via(SYS, *V2)

# ---------------- F.Cu fan-out
seg(SYS, [pad("C605", "1"), V1, pad("U12", "5")], 0.5)           # C605 -> V1 -> U12 VIN
seg(SYS, [pad("C608", "1"), (53.6, 8.01), (54.1, 7.51)], 0.3)       # under C608.2, into C605.1
seg(SYS, [pad("C608", "1"), pad("U13", "1")], 0.3)                # U13 VM
seg(SYS, [V2, pad("L601", "1")[0:1] + (9.6,)], 0.6)               # L601 input
seg(SYS, [V2, (62.75, 10.45), (58.3, 10.45), (57.5, 11.25), pad("C607", "1")], 0.3)
g = pad("C608", "2"); via(GND, 52.95, 6.1, d=0.45, h=0.2); seg(GND, [g, (52.95, 6.1)], 0.3)
for r in ("C608", "U13"):                                         # refs sat on the new C608 pads
    fp = b.FindFootprintByReference(r); fp.Reference().SetLayer(pcbnew.F_Fab); fp.Reference().SetPosition(fp.GetPosition())

pcbnew.SaveBoard(PCB, b)
for r in ("C605", "C608", "C607", "L601"):
    print(r, [(p.GetNumber(), p.GetNetname(), round(TM(p.GetPosition().x), 2), round(TM(p.GetPosition().y), 2))
              for p in b.FindFootprintByReference(r).Pads()])
sys.stdout.flush(); os._exit(0)
