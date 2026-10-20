"""Netlist -> PCB sync (a scriptable 'Update PCB from Schematic').
- adds new footprints in a staging grid to the right of the board
- keeps position/rotation/side of footprints already on the board (matched by reference)
- updates value, LCSC/MPN fields, DNP / BOM attributes, schematic links and pad nets
- removes footprints that left the schematic (except board-setup items: H*, FID*, LOGO*)
Run:  $KICAD_CLI sch export netlist ... -o analysis/esp32p4_lte_cam.net ; $PY scripts/build_pcb.py"""
import re, sys
from pathlib import Path
import pcbnew
from kisch import parse, kids, kid, ROOT

PCB = ROOT / "esp32p4_lte_cam.kicad_pcb"
NET = ROOT / "analysis" / "esp32p4_lte_cam.net"
KICAD_FP = Path(r"C:/Program Files/KiCad/10.0/share/kicad/footprints")
RELOAD = "--reload" in sys.argv          # re-pull every footprint from its library, keeping placement
KEEP = re.compile(r"^(H|FID|LOGO|MH)\d*")


def fp_libs():
    libs = {}
    t = parse((ROOT / "fp-lib-table").read_text(encoding="utf-8"))
    for lib in kids(t, "lib"):
        libs[str(kid(lib, "name")[1])] = str(kid(lib, "uri")[1]).replace("${KIPRJMOD}", str(ROOT))
    return libs


def mm(v):
    return pcbnew.FromMM(v)


def main():
    nl = parse(NET.read_text(encoding="utf-8"))
    comps = kids(kid(nl, "components"), "comp")
    nets = kids(kid(nl, "nets"), "net")
    board = pcbnew.LoadBoard(str(PCB))
    libs = fp_libs()
    have = {fp.GetReference(): fp for fp in board.GetFootprints()}
    want = set()
    stage_x, stage_y, col_w = 110.0, 0.0, 0.0
    added = updated = 0
    for c in comps:
        ref = str(kid(c, "ref")[1]); want.add(ref)
        val = str(kid(c, "value")[1]); fpid = str(kid(c, "footprint")[1]) if kid(c, "footprint") else ""
        props = {str(kid(p, "name")[1]): (str(kid(p, "value")[1]) if kid(p, "value") else "") for p in kids(c, "property")}
        if not fpid:
            print(f"!! {ref} has no footprint"); continue
        nick, name = fpid.split(":", 1)
        fp = have.get(ref)
        if fp is not None and (RELOAD or str(fp.GetFPID().GetUniStringLibId()) != fpid):
            pos, rot, side = fp.GetPosition(), fp.GetOrientationDegrees(), fp.IsFlipped()
            board.Delete(fp); fp = None
        else:
            pos = None
        if fp is None:
            path = libs.get(nick) or str(KICAD_FP / f"{nick}.pretty")
            fp = pcbnew.FootprintLoad(path, name)
            if fp is None:
                print(f"!! cannot load {fpid} for {ref}"); continue
            fp.SetFPID(pcbnew.LIB_ID(nick, name))
            board.Add(fp)
            if pos is not None:
                fp.SetPosition(pos); fp.SetOrientationDegrees(rot)
                if side: fp.Flip(pos, pcbnew.FLIP_DIRECTION_TOP_BOTTOM)
            else:
                bb = fp.GetBoundingBox(False)
                w, h = pcbnew.ToMM(bb.GetWidth()) + 2, pcbnew.ToMM(bb.GetHeight()) + 2
                if stage_y + h > 120:
                    stage_x += col_w; stage_y = 0; col_w = 0
                fp.SetPosition(pcbnew.VECTOR2I(mm(stage_x + w / 2), mm(stage_y + h / 2)))
                stage_y += h; col_w = max(col_w, w)
            added += 1
        else:
            updated += 1
        fp.SetReference(ref); fp.SetValue(val)
        sp = kid(c, "sheetpath"); ts = str(kid(c, "tstamps")[1])
        fp.SetPath(pcbnew.KIID_PATH(str(kid(sp, "tstamps")[1]) + ts))
        fp.SetSheetname(props.get("Sheetname", "")); fp.SetSheetfile(props.get("Sheetfile", ""))
        for k in ("LCSC", "MPN", "Note"):
            if k in props:
                f = fp.GetField(k)
                if f is None:
                    f = pcbnew.PCB_FIELD(fp, fp.GetNextFieldOrdinal(), k)
                    f.SetLayer(pcbnew.F_Fab); f.SetVisible(False); fp.Add(f)
                f.SetText(props[k])
        attrs = fp.GetAttributes()
        attrs = attrs | pcbnew.FP_DNP if "dnp" in props else attrs & ~pcbnew.FP_DNP
        attrs = attrs | pcbnew.FP_EXCLUDE_FROM_BOM if ("exclude_from_bom" in props or ref.startswith("TP")) else attrs
        fp.SetAttributes(attrs)
        if ref.startswith("TP"):
            fp.SetExcludedFromPosFiles(True)
    removed = [r for r in have if r not in want and not KEEP.match(r)]
    for r in removed:
        board.Delete(have[r])
    # nets
    byref = {fp.GetReference(): fp for fp in board.GetFootprints()}
    for fp in byref.values():
        if KEEP.match(fp.GetReference()):
            continue
        for pad in fp.Pads():
            pad.SetNet(board.FindNet(""))  # clear; re-assigned below
    nnets = 0
    for n in nets:
        name = str(kid(n, "name")[1])
        ni = board.FindNet(name)
        if ni is None:
            ni = pcbnew.NETINFO_ITEM(board, name); board.Add(ni)
        nnets += 1
        for node in kids(n, "node"):
            fp = byref.get(str(kid(node, "ref")[1]))
            if fp is None:
                continue
            pin = str(kid(node, "pin")[1])
            for pad in fp.Pads():
                if pad.GetNumber() == pin:
                    pad.SetNet(ni)
    board.BuildConnectivity()
    pcbnew.SaveBoard(str(PCB), board)
    print(f"footprints: {added} added, {updated} kept, {len(removed)} removed; nets: {nnets}")
    unl = [f"{fp.GetReference()}.{p.GetNumber()}" for fp in byref.values() for p in fp.Pads()
           if p.GetNumber() and p.GetNetCode() == 0 and not KEEP.match(fp.GetReference()) and p.IsOnCopperLayer() and p.GetAttribute() != pcbnew.PAD_ATTRIB_NPTH]
    print(f"pads without net: {len(unl)}", unl[:15], flush=True)
    import os; os._exit(0)   # avoid pcbnew SWIG teardown segfault


if __name__ == "__main__":
    main()
