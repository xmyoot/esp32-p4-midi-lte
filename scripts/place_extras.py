"""Placement extras (idempotent): global fiducials, SIM7600 top-layer track keep-out, bottom-side silkscreen
(board ID + connector legends, mirrored on B.SilkS). Run after place.py, before silk.py."""
import math, os, sys
import pcbnew
from kisch import ROOT

PCB = str(ROOT / "esp32p4_lte_cam.kicad_pcb")
MM = pcbnew.FromMM
FIDS = {"FID1": (8.0, 13.0), "FID2": (60.0, 12.0), "FID3": (37.0, 67.5)}   # preferred spots, searched outward
TAG = "kisch-extra"                                                       # marks items this script owns

b = pcbnew.LoadBoard(PCB)


def rect(fp):
    bb = fp.GetCourtyard(pcbnew.F_CrtYd).BBox() if fp.GetCourtyard(pcbnew.F_CrtYd).OutlineCount() else fp.GetBoundingBox(False, False)
    r = [bb.GetX(), bb.GetY(), bb.GetRight(), bb.GetBottom()]
    for p in fp.Pads():
        pb = p.GetBoundingBox(); r = [min(r[0], pb.GetX()), min(r[1], pb.GetY()), max(r[2], pb.GetRight()), max(r[3], pb.GetBottom())]
    return r


# ---- fiducials
fp_path = r"C:/Program Files/KiCad/10.0/share/kicad/footprints/Fiducial.pretty"
have = {fp.GetReference(): fp for fp in b.GetFootprints()}
obst = [rect(fp) for r, fp in have.items() if not r.startswith("FID")]
edge = b.GetBoardEdgesBoundingBox(); edge.Inflate(-MM(2.0))
for ref, (x, y) in FIDS.items():
    fp = have.get(ref)
    if fp is None:
        fp = pcbnew.FootprintLoad(fp_path, "Fiducial_1mm_Mask2mm"); fp.SetFPID(pcbnew.LIB_ID("Fiducial", "Fiducial_1mm_Mask2mm")); b.Add(fp)
    fp.SetReference(ref); fp.SetValue("Fiducial"); fp.Reference().SetVisible(False)
    fp.SetAttributes(fp.GetAttributes() | pcbnew.FP_EXCLUDE_FROM_BOM | pcbnew.FP_BOARD_ONLY)
    placed = False
    for ring in range(80):
        rr = ring * 0.25; n = max(1, int(2 * math.pi * rr / 0.25))
        for k in range(n):
            px, py = x + rr * math.cos(2 * math.pi * k / n), y + rr * math.sin(2 * math.pi * k / n)
            fp.SetPosition(pcbnew.VECTOR2I(MM(px), MM(py))); r = rect(fp); g = MM(0.5)
            if r[0] < edge.GetX() or r[1] < edge.GetY() or r[2] > edge.GetRight() or r[3] > edge.GetBottom():
                continue
            if not any(r[0] - g < q[2] and q[0] < r[2] + g and r[1] - g < q[3] and q[1] < r[3] + g for q in obst):
                obst.append(r); placed = True; break
        if placed:
            break
    print(ref, "placed" if placed else "NO ROOM", round(pcbnew.ToMM(fp.GetPosition().x), 2), round(pcbnew.ToMM(fp.GetPosition().y), 2))

# ---- remove previous extras (zones / texts we own)
for z in list(b.Zones()):
    if z.GetZoneName().startswith(TAG):
        b.Delete(z)
for d in list(b.GetDrawings()):
    if d.GetClass() == "PCB_TEXT" and d.GetLayer() == pcbnew.B_SilkS:
        b.Delete(d)

# ---- SIM7600: no tracks on F.Cu under the module body (SIMCom layout guide); pads/vias/GND pour allowed
u4 = b.FindFootprintByReference("U4"); c = u4.GetPosition(); h = MM(13.6)
z = pcbnew.ZONE(b); z.SetIsRuleArea(True); z.SetZoneName(TAG + ":SIM7600 no-tracks"); z.SetLayer(pcbnew.F_Cu)
z.SetDoNotAllowTracks(True); z.SetDoNotAllowVias(False); z.SetDoNotAllowPads(False); z.SetDoNotAllowZoneFills(False)
z.SetDoNotAllowFootprints(False)
o = z.Outline(); o.NewOutline()
for dx, dy in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
    o.Append(c.x + dx * h, c.y + dy * h)
b.Add(z)


# ---- bottom silkscreen (mirrored): board ID + connector legends behind each connector
def btext(s, x, y, size=1.2, thick=0.18, angle=0):
    t = pcbnew.PCB_TEXT(b); t.SetText(s); t.SetLayer(pcbnew.B_SilkS); t.SetMirrored(True)
    t.SetPosition(pcbnew.VECTOR2I(MM(x), MM(y))); t.SetTextSize(pcbnew.VECTOR2I(MM(size), MM(size)))
    t.SetTextThickness(MM(thick)); t.SetTextAngleDegrees(angle); b.Add(t)


btext("ESP32-P4 LTE CAMERA", 37.5, 40.0, 2.0, 0.3)
btext("rev A  -  2026-10", 37.5, 43.5, 1.4, 0.2)
btext("H. Jimenez  |  4L JLC04161H-7628", 37.5, 46.5, 1.0, 0.15)
for s, x, y in (("CAMERA", 37.5, 8.5), ("USB-C 5V", 16.5, 58.0), ("NANO-SIM", 29.8, 56.0), ("microSD", 13.5, 21.0),
                ("BATT +/NTC/-", 11.5, 50.0), ("IR-CUT", 49.5, 9.5), ("ANT MAIN", 68.5, 59.0), ("ANT DIV", 68.5, 40.0),
                ("GNSS", 47.5, 27.0), ("Wi-Fi 6 / BLE", 64.0, 28.5)):
    btext(s, x, y, 1.0, 0.15, 90 if s == "microSD" else 0)

b.BuildConnectivity(); pcbnew.SaveBoard(PCB, b)
print("extras done", flush=True)
os._exit(0)
