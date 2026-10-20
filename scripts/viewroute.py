"""Draw pads / tracks / vias (no pours) for a board region -> PNG.  F.Cu red, In1 green, In2 orange, B.Cu blue.
usage: $PY scripts/viewroute.py board.kicad_pcb out.png x0 y0 x1 y1 [px_per_mm] [--nets pattern,...]"""
import fnmatch, os, sys
import pcbnew
from PIL import Image, ImageDraw, ImageFont

pcb, out, x0, y0, x1, y1 = sys.argv[1], sys.argv[2], *map(float, sys.argv[3:7])
S = float(sys.argv[7]) if len(sys.argv) > 7 and not sys.argv[7].startswith("--") else 40.0
pats = sys.argv[sys.argv.index("--nets") + 1].split(",") if "--nets" in sys.argv else None
b = pcbnew.LoadBoard(pcb)
mm = pcbnew.ToMM
COL = {pcbnew.F_Cu: (220, 40, 40), pcbnew.In1_Cu: (40, 160, 40), pcbnew.In2_Cu: (230, 140, 0), pcbnew.B_Cu: (40, 90, 230)}
img = Image.new("RGB", (int((x1 - x0) * S), int((y1 - y0) * S)), (18, 18, 18))
d = ImageDraw.Draw(img, "RGBA")
try:
    font = ImageFont.truetype("arial.ttf", max(9, int(S * 0.22)))
except OSError:
    font = ImageFont.load_default()


def P(x, y):
    return ((x - x0) * S, (y - y0) * S)


def want(net):
    return pats is None or any(fnmatch.fnmatch(net, p) for p in pats)


for fp in b.GetFootprints():
    for p in fp.Pads():
        bb = p.GetBoundingBox()
        if mm(bb.GetRight()) < x0 or mm(bb.GetX()) > x1 or mm(bb.GetBottom()) < y0 or mm(bb.GetY()) > y1:
            continue
        col = (120, 120, 120, 200) if p.IsOnLayer(pcbnew.F_Cu) else (70, 70, 150, 160)
        d.rectangle([P(mm(bb.GetX()), mm(bb.GetY())), P(mm(bb.GetRight()), mm(bb.GetBottom()))], fill=col)
    c = fp.GetPosition()
    if x0 <= mm(c.x) <= x1 and y0 <= mm(c.y) <= y1:
        d.text(P(mm(c.x), mm(c.y)), fp.GetReference(), fill=(255, 255, 255, 140), font=font)
for t in b.GetTracks():
    if not want(t.GetNetname()):
        continue
    if t.GetClass() == "PCB_VIA":
        c = t.GetPosition(); r = mm(t.GetWidth(pcbnew.F_Cu)) / 2
        d.ellipse([P(mm(c.x) - r, mm(c.y) - r), P(mm(c.x) + r, mm(c.y) + r)], fill=(230, 230, 60, 230))
    else:
        a, e = t.GetStart(), t.GetEnd()
        col = COL.get(t.GetLayer(), (200, 200, 200))
        d.line([P(mm(a.x), mm(a.y)), P(mm(e.x), mm(e.y))], fill=col + (220,), width=max(1, int(mm(t.GetWidth()) * S)))
img.save(out)
sys.stdout.flush(); os._exit(0)
