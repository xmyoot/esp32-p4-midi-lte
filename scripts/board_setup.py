"""Phase 3 board setup (idempotent): outline, mounting holes, JLC04161H-7628 stackup, title block,
design rules, net classes + patterns, track/via/diff-pair presets, custom DRC rules.
Numbers: docs/BOARD_SETUP.md (impedance from scripts/impedance.py, limits from JLCPCB capabilities)."""
import json, re, sys
import pcbnew
from kisch import ROOT

PCB = ROOT / "esp32p4_lte_cam.kicad_pcb"
PRO = ROOT / "esp32p4_lte_cam.kicad_pro"
W, H, R = 75.0, 70.0, 2.0                       # board mm, corner radius
HOLES = {"H1": (3.5, 9.5), "H2": (71.5, 9.5), "H3": (3.5, 66.5), "H4": (71.5, 66.5)}
HOLE_FP = ("MountingHole", "MountingHole_2.7mm_M2.5_Pad_Via")


def V(x, y):
    return pcbnew.VECTOR2I(pcbnew.FromMM(x), pcbnew.FromMM(y))


def outline(board):
    for d in list(board.GetDrawings()):
        if d.GetLayer() == pcbnew.Edge_Cuts:
            board.Delete(d)
    w = pcbnew.FromMM(0.05)
    segs = [((R, 0), (W - R, 0)), ((W, R), (W, H - R)), ((W - R, H), (R, H)), ((0, H - R), (0, R))]
    for a, b in segs:
        s = pcbnew.PCB_SHAPE(board, pcbnew.SHAPE_T_SEGMENT); s.SetStart(V(*a)); s.SetEnd(V(*b))
        s.SetLayer(pcbnew.Edge_Cuts); s.SetWidth(w); board.Add(s)
    for cx, cy, sx, sy in ((R, R, 0, R), (W - R, R, W - R, 0), (W - R, H - R, W, H - R), (R, H - R, R, H)):
        a = pcbnew.PCB_SHAPE(board, pcbnew.SHAPE_T_ARC); a.SetCenter(V(cx, cy)); a.SetStart(V(sx, sy))
        a.SetArcAngleAndEnd(pcbnew.EDA_ANGLE(90, pcbnew.DEGREES_T)); a.SetLayer(pcbnew.Edge_Cuts); a.SetWidth(w); board.Add(a)


def holes(board):
    gnd = board.FindNet("GND")
    have = {fp.GetReference(): fp for fp in board.GetFootprints()}
    path = r"C:/Program Files/KiCad/10.0/share/kicad/footprints/" + HOLE_FP[0] + ".pretty"
    for ref, (x, y) in HOLES.items():
        fp = have.get(ref)
        if fp is None:
            fp = pcbnew.FootprintLoad(path, HOLE_FP[1]); fp.SetFPID(pcbnew.LIB_ID(*HOLE_FP)); board.Add(fp)
        fp.SetReference(ref); fp.SetValue("M2.5"); fp.SetPosition(V(x, y)); fp.Reference().SetVisible(False)
        fp.SetAttributes(fp.GetAttributes() | pcbnew.FP_EXCLUDE_FROM_BOM | pcbnew.FP_EXCLUDE_FROM_POS_FILES | pcbnew.FP_BOARD_ONLY)
        for p in fp.Pads():
            p.SetNet(gnd)


def gnd_plane(board):
    """Solid GND reference plane on L2 (In1.Cu) - the return path for every L1 controlled-impedance trace."""
    for z in list(board.Zones()):
        if z.GetZoneName() == "GND_L2":
            board.Delete(z)
    z = pcbnew.ZONE(board)
    z.SetLayer(pcbnew.In1_Cu); z.SetNet(board.FindNet("GND")); z.SetZoneName("GND_L2")
    z.SetAssignedPriority(0); z.SetLocalClearance(pcbnew.FromMM(0.2)); z.SetMinThickness(pcbnew.FromMM(0.2))
    z.SetPadConnection(pcbnew.ZONE_CONNECTION_FULL)
    o = z.Outline(); o.NewOutline()
    for x, y in ((0.3, 0.3), (W - 0.3, 0.3), (W - 0.3, H - 0.3), (0.3, H - 0.3)):
        o.Append(pcbnew.FromMM(x), pcbnew.FromMM(y))
    board.Add(z)


def title(board):
    tb = board.GetTitleBlock()
    tb.SetTitle("ESP32-P4 LTE Camera Board"); tb.SetRevision("A"); tb.SetDate("2026-10-19")
    tb.SetCompany("Portfolio design - Hector Jimenez")
    tb.SetComment(0, "4-layer JLC04161H-7628, 1.6 mm, ENIG, 75 x 70 mm")
    tb.SetComment(1, "Impedance control: 50R CPWG (RF), 90R diff (USB), 100R diff (MIPI CSI)")


STACKUP = """(stackup
\t\t\t(layer "F.SilkS" (type "Top Silk Screen"))
\t\t\t(layer "F.Paste" (type "Top Solder Paste"))
\t\t\t(layer "F.Mask" (type "Top Solder Mask") (thickness 0.01))
\t\t\t(layer "F.Cu" (type "copper") (thickness 0.035))
\t\t\t(layer "dielectric 1" (type "prepreg") (color "FR4 natural") (thickness 0.2104) (material "7628") (epsilon_r 4.4) (loss_tangent 0.02))
\t\t\t(layer "In1.Cu" (type "copper") (thickness 0.0152))
\t\t\t(layer "dielectric 2" (type "core") (color "FR4 natural") (thickness 1.065) (material "FR4") (epsilon_r 4.6) (loss_tangent 0.02))
\t\t\t(layer "In2.Cu" (type "copper") (thickness 0.0152))
\t\t\t(layer "dielectric 3" (type "prepreg") (color "FR4 natural") (thickness 0.2104) (material "7628") (epsilon_r 4.4) (loss_tangent 0.02))
\t\t\t(layer "B.Cu" (type "copper") (thickness 0.035))
\t\t\t(layer "B.Mask" (type "Bottom Solder Mask") (thickness 0.01))
\t\t\t(layer "B.Paste" (type "Bottom Solder Paste"))
\t\t\t(layer "B.SilkS" (type "Bottom Silk Screen"))
\t\t\t(copper_finish "ENIG")
\t\t\t(dielectric_constraints no)
\t\t)"""


def stackup_text():
    t = PCB.read_text(encoding="utf-8")
    t = re.sub(r"\(stackup\b.*?\n\t\t\)", "", t, flags=re.S)          # drop old stackup block
    t = t.replace("(setup\n", "(setup\n\t\t" + STACKUP + "\n", 1)
    t = re.sub(r'\(layer "In1\.Cu" (signal|power)', '(layer "In1.Cu" power', t)   # L2 = GND plane
    t = re.sub(r"\n\t\t\((aux_axis_origin|grid_origin) [^)]*\)", "", t)
    t = t.replace("(setup\n", f"(setup\n\t\t(aux_axis_origin 0 {H})\n\t\t(grid_origin 0 {H})\n", 1)
    PCB.write_text(t, encoding="utf-8")


NETCLASSES = [  # name, clearance, track, via_d, via_drill, dp_width, dp_gap, colour
    ("Default", 0.127, 0.127, 0.45, 0.2, 0.2, 0.13, "rgba(0, 0, 0, 0.000)"),
    ("Power", 0.15, 0.4, 0.6, 0.3, 0.2, 0.13, "rgba(255, 153, 0, 0.900)"),
    ("HighCurrent", 0.2, 0.8, 0.6, 0.3, 0.2, 0.13, "rgba(255, 0, 0, 0.900)"),
    ("RF_50R", 0.2, 0.30, 0.45, 0.2, 0.3, 0.2, "rgba(0, 200, 0, 0.900)"),
    ("USB_90R", 0.15, 0.22, 0.45, 0.2, 0.22, 0.13, "rgba(0, 120, 255, 0.900)"),
    ("MIPI_100R", 0.15, 0.17, 0.45, 0.2, 0.17, 0.13, "rgba(180, 0, 255, 0.900)"),
]
PATTERNS = [  # (netclass, pattern) - first match wins in KiCad order
    ("HighCurrent", "VBAT_LTE"), ("HighCurrent", "SYS"), ("HighCurrent", "BAT"), ("HighCurrent", "/power/BATN"),
    ("HighCurrent", "VBUS"), ("HighCurrent", "/power/CHG_SW"), ("HighCurrent", "/power/PROT_D"),
    ("HighCurrent", "/power/CHG_PMID"), ("HighCurrent", "/power/BB_LX*"),
    ("Power", "3V3"), ("Power", "3V3_*"), ("Power", "VDD_*"), ("Power", "1V8_IO6"), ("Power", "/mcu/HP_SW"),
    ("Power", "/camera_ir/IR_*"), ("Power", "/camera_ir/IRCUT_[AB]"), ("Power", "/lte/MDM_1V8"), ("Power", "/lte/USIM_VDD"),
    ("RF_50R", "/lte/RF_*"), ("RF_50R", "/lte/ANT_*"),
    ("USB_90R", "USB_D?"), ("USB_90R", "/mcu/P4_USB_D?"), ("USB_90R", "/power/CHG_D?"),
    ("MIPI_100R", "CSI_D?_?"), ("MIPI_100R", "CSI_CK_?"), ("MIPI_100R", "/mcu/P4_CSI_D?_?"), ("MIPI_100R", "/mcu/P4_CSI_CK_?"),
]


def project_rules():
    p = json.loads(PRO.read_text(encoding="utf-8"))
    ds = p["board"]["design_settings"]
    ds.setdefault("rules", {}).update({
        "min_clearance": 0.1, "min_track_width": 0.1, "min_connection": 0.1, "min_via_annular_width": 0.1,
        "min_via_diameter": 0.45, "min_through_hole_diameter": 0.2, "min_hole_to_hole": 0.25, "min_hole_clearance": 0.2,
        "min_copper_edge_clearance": 0.3, "min_silk_clearance": 0.0, "min_text_height": 0.8, "min_text_thickness": 0.12,
        "solder_mask_to_copper_clearance": 0.0, "min_microvia_diameter": 0.2, "min_microvia_drill": 0.1,
        "max_error": 0.005, "allow_blind_buried_vias": False, "allow_microvias": False})
    ds["track_widths"] = [0.0, 0.1, 0.127, 0.17, 0.2, 0.22, 0.3, 0.4, 0.6, 0.8, 1.0, 1.5]
    ds["via_dimensions"] = [{"diameter": 0.0, "drill": 0.0}, {"diameter": 0.45, "drill": 0.2},
                            {"diameter": 0.6, "drill": 0.3}, {"diameter": 0.8, "drill": 0.4}]
    ds["diff_pair_dimensions"] = [{"gap": 0.0, "via_gap": 0.0, "width": 0.0}, {"gap": 0.13, "via_gap": 0.25, "width": 0.22},
                                  {"gap": 0.13, "via_gap": 0.25, "width": 0.17}]
    base = p["net_settings"]["classes"][0]
    classes = []
    for i, (n, cl, tw, vd, vdr, dw, dg, col) in enumerate(NETCLASSES):
        c = dict(base); c.update({"name": n, "clearance": cl, "track_width": tw, "via_diameter": vd, "via_drill": vdr,
                                  "diff_pair_width": dw, "diff_pair_gap": dg, "diff_pair_via_gap": 0.25, "pcb_color": col,
                                  "priority": 2147483647 if n == "Default" else i})
        classes.append(c)
    p["net_settings"]["classes"] = classes
    p["net_settings"]["netclass_patterns"] = [{"netclass": c, "pattern": pat} for c, pat in PATTERNS]
    PRO.write_text(json.dumps(p, indent=2), encoding="utf-8")


DRU = """(version 1)
# Custom DRC rules - ESP32-P4 LTE camera (JLC 4-layer, Standard PCBA)

(rule "P4 0.35 mm QFN fan-out"
  (condition "A.intersectsCourtyard('U1')")
  (constraint clearance (min 0.09))
  (constraint track_width (min 0.09)))

(rule "RF CPWG ground gap"
  (condition "A.NetClass == 'RF_50R' && B.Type != 'Pad'")
  (constraint clearance (min 0.2)))

(rule "USB diff pair"
  (condition "A.inDiffPair('*USB_D*')")
  (constraint diff_pair_gap (min 0.12) (opt 0.13) (max 0.14))
  (constraint diff_pair_uncoupled (max 3))
  (constraint skew (max 0.15)))

(rule "MIPI CSI diff pairs"
  (condition "A.inDiffPair('*CSI_*')")
  (constraint diff_pair_gap (min 0.12) (opt 0.13) (max 0.14))
  (constraint diff_pair_uncoupled (max 2))
  (constraint skew (max 0.3)))   # 0.3 mm ~ 2 ps: far inside the D-PHY intra-pair budget

(rule "MIPI lane-to-lane matching"
  (condition "A.NetClass == 'MIPI_100R'")
  (constraint length (max 40)))

(rule "High-current via size"
  (condition "A.Type == 'Via' && A.NetClass == 'HighCurrent'")
  (constraint hole_size (min 0.3)))

(rule "Board edge copper"
  (constraint edge_clearance (min 0.3)))
"""


def main():
    board = pcbnew.LoadBoard(str(PCB))
    outline(board); holes(board); title(board)
    if "--with-gnd-plane" in sys.argv:       # planes are poured by KiCadRoutingTools route_planes (Phase 5)
        gnd_plane(board)
    board.SetCopperLayerCount(4)
    board.BuildConnectivity(); pcbnew.SaveBoard(str(PCB), board)
    stackup_text(); project_rules()
    (ROOT / "esp32p4_lte_cam.kicad_dru").write_text(DRU, encoding="utf-8")
    print("board setup done", flush=True)
    import os; os._exit(0)   # pcbnew SWIG teardown can segfault after a successful save


if __name__ == "__main__":
    main()
