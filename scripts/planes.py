"""Copper pours (idempotent; owns every non-rule-area zone).
L1 F.Cu  : GND flood (thermal reliefs; RF_50R netclass clearance 0.2 gives the CPWG gap)
L2 In1.Cu: solid GND reference plane
L3 In2.Cu: power split, hand-drawn from the floor plan (priority: VBAT_LTE > SYS > 3V3)
L4 B.Cu  : GND flood
Usage: $PY scripts/planes.py <board.kicad_pcb>  (default: project board)"""
import os, sys
import pcbnew
from kisch import ROOT

PCB = sys.argv[1] if len(sys.argv) > 1 else str(ROOT / "esp32p4_lte_cam.kicad_pcb")
W, H, E = 75.0, 70.0, 0.3
FULL = [(E, E), (W - E, E), (W - E, H - E), (E, H - E)]
# VBAT_LTE: one region from U9 (south-west of the modem) across the whole SIM7600 footprint: both VBAT pin groups
VBAT = [(37.2, 31.8), (70.4, 31.8), (70.4, 69.7), (40.8, 69.7), (40.8, 64.4), (37.2, 64.4)]
# SYS: the power block (charger, protection, buck-boost input, LTE switch input). IR/IR-cut drivers take SYS by trace
SYS = [(0.3, 41.0), (37.0, 41.0), (37.0, 64.4), (40.8, 64.4), (40.8, 69.7), (0.3, 69.7)]
PLAN = [  # (layer, net, outline, priority, solid_pads)
    (pcbnew.In1_Cu, "GND", FULL, 0, True),
    (pcbnew.F_Cu, "GND", FULL, 0, False),
    (pcbnew.B_Cu, "GND", FULL, 0, False),
    (pcbnew.In2_Cu, "3V3", FULL, 0, True),
    (pcbnew.In2_Cu, "SYS", SYS, 1, True),
    (pcbnew.In2_Cu, "VBAT_LTE", VBAT, 2, True),
]

b = pcbnew.LoadBoard(PCB)
for z in list(b.Zones()):
    if not z.GetIsRuleArea():
        b.Delete(z)
MM = pcbnew.FromMM
for layer, net, pts, prio, solid in PLAN:
    z = pcbnew.ZONE(b)
    z.SetLayer(layer); z.SetNet(b.FindNet(net)); z.SetZoneName(f"{net}@{pcbnew.LayerName(layer)}")
    z.SetAssignedPriority(prio); z.SetLocalClearance(MM(0.127)); z.SetMinThickness(MM(0.2))
    z.SetPadConnection(pcbnew.ZONE_CONNECTION_FULL if solid else pcbnew.ZONE_CONNECTION_THERMAL)
    z.SetThermalReliefGap(MM(0.25)); z.SetThermalReliefSpokeWidth(MM(0.25))
    z.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)
    o = z.Outline(); o.NewOutline()
    for x, y in pts:
        o.Append(MM(x), MM(y))
    b.Add(z)
pcbnew.ZONE_FILLER(b).Fill(b.Zones())
for z in b.Zones():
    if not z.GetIsRuleArea():
        print(f"{z.GetZoneName():18} {z.GetFilledArea() / 1e12:8.1f} mm2", flush=True)
pcbnew.SaveBoard(PCB, b)
sys.stdout.flush(); os._exit(0)
