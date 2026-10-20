"""Silkscreen reference tidy: KiCadRoutingTools beautify_labels (1.0 mm, down to 0.8 mm), then hide any
designator that has no legal spot or still collides per KiCad DRC. Every reference stays on F.Fab
(assembly drawing).  KEEP_VISIBLE refs get a hand-chosen position instead of being hidden."""
import json, os, re, subprocess, sys
from kisch import ROOT

ENV = dict(os.environ)
PY = sys.executable
KRT = r"C:/Users/hecto/Documents/KiCAD_Projects/_tools/KiCadRoutingTools"
CLI = r"C:/Program Files/KiCad/10.0/bin/kicad-cli.exe"
PCB = str(ROOT / "esp32p4_lte_cam.kicad_pcb")
RPT = str(ROOT / "analysis" / "drc.rpt")
# key parts whose designator must stay visible: (x, y, rot) in board mm, chosen in clear space
KEEP_VISIBLE = {"U1": (33.0, 21.0, 90), "U4": (53.5, 37.6, 0), "U3": (64.0, 20.0, 0), "U5": (15.5, 43.6, 0),
                "J2": (37.5, 7.4, 0), "J1": (16.5, 61.6, 0), "J3": (12.5, 21.0, 90), "J4": (29.8, 55.4, 0)}


def hide(refs):
    code = ("import pcbnew,os,sys\nb=pcbnew.LoadBoard(r'%s')\nrefs=set(sys.argv[1:])\n"
            "for fp in b.GetFootprints():\n  if fp.GetReference() in refs: fp.Reference().SetVisible(False)\n"
            "pcbnew.SaveBoard(r'%s',b)\nsys.stdout.flush(); os._exit(0)\n") % (PCB, PCB)
    subprocess.run([PY, "-c", code, *refs], check=False, capture_output=True)


def pin_labels():
    r = subprocess.run([PY, str(ROOT / "scripts" / "silk_pin.py"), PCB, json.dumps(KEEP_VISIBLE)], capture_output=True, text=True)
    for line in r.stdout.splitlines():
        if "leak" not in line:
            print(line)


def drc_label_refs():
    subprocess.run([CLI, "pcb", "drc", PCB, "-o", RPT], capture_output=True)
    txt = open(RPT, encoding="utf-8").read()
    blocks = re.split(r"\n(?=\[)", txt)
    return {m for b in blocks if b.startswith("[silk") for m in re.findall(r"Reference field of (\S+)", b)} - set(KEEP_VISIBLE)


def main():
    rep = str(ROOT / "analysis" / "labels.json")
    subprocess.run([PY, f"{KRT}/py_placer/beautify_labels.py", PCB, PCB, "--size", "1.0", "--min-size", "0.8",
                    "--thickness", "0.15", "--report-json", rep], capture_output=True)
    unplaced = [r["reference"] for r in json.load(open(rep)) if r["action"] == "unchanged" and r["reference"] not in KEEP_VISIBLE]
    hide(unplaced); pin_labels()
    total = len(unplaced)
    for _ in range(4):
        refs = drc_label_refs()
        if not refs:
            break
        hide(refs); total += len(refs)
    print(f"silk: {total} designators hidden (kept on F.Fab), {len(KEEP_VISIBLE)} pinned")


if __name__ == "__main__":
    main()
