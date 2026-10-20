"""Seat key designators (KEEP_VISIBLE in silk.py) at the clear spot nearest their preferred point:
no overlap with any pad (+0.2 mm), other visible silk text, or the board edge (0.5 mm)."""
import json, math, os, sys
import pcbnew

PCB = sys.argv[1]
want = json.loads(sys.argv[2])
b = pcbnew.LoadBoard(PCB)
MM = pcbnew.FromMM


def box(t):
    bb = t.GetBoundingBox(); return [bb.GetX(), bb.GetY(), bb.GetRight(), bb.GetBottom()]


pads = []
for fp in b.GetFootprints():
    for p in fp.Pads():
        bb = p.GetBoundingBox(); bb.Inflate(MM(0.2)); pads.append([bb.GetX(), bb.GetY(), bb.GetRight(), bb.GetBottom()])
texts = [box(fp.Reference()) for fp in b.GetFootprints() if fp.Reference().IsVisible() and fp.GetReference() not in want]
for fp in b.GetFootprints():                      # footprint silk art is an obstacle too
    for g in fp.GraphicalItems():
        if g.GetLayer() == pcbnew.F_SilkS and g.GetClass() in ("PCB_SHAPE", "PCB_TEXT"):
            bb = g.GetBoundingBox(); bb.Inflate(MM(0.15)); texts.append([bb.GetX(), bb.GetY(), bb.GetRight(), bb.GetBottom()])
edge = b.GetBoardEdgesBoundingBox(); edge.Inflate(-MM(0.5))


def clear(r):
    if r[0] < edge.GetX() or r[1] < edge.GetY() or r[2] > edge.GetRight() or r[3] > edge.GetBottom():
        return False
    return not any(r[0] < q[2] and q[0] < r[2] and r[1] < q[3] and q[1] < r[3] for q in pads + texts)


for fp in b.GetFootprints():
    ref = fp.GetReference()
    if ref not in want:
        continue
    x, y, a = want[ref]
    t = fp.Reference(); t.SetVisible(True); t.SetLayer(pcbnew.F_SilkS); t.SetTextAngleDegrees(a)
    t.SetTextSize(pcbnew.VECTOR2I(MM(1.2), MM(1.2))); t.SetTextThickness(MM(0.18))
    done = False
    for ring in range(0, 60):
        rr = ring * 0.25; n = max(1, int(2 * math.pi * rr / 0.25))
        for k in range(n):
            px, py = x + rr * math.cos(2 * math.pi * k / n), y + rr * math.sin(2 * math.pi * k / n)
            t.SetPosition(pcbnew.VECTOR2I(MM(px), MM(py)))
            r = box(t)
            if clear(r):
                texts.append(r); done = True; break
        if done:
            break
    print(f"{ref}: {'seated' if done else 'NO SPOT - hidden'}", flush=True)
    if not done:
        t.SetVisible(False)
pcbnew.SaveBoard(PCB, b)
sys.stdout.flush(); os._exit(0)
