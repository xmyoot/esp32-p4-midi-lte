"""Placement quality metrics -> docs/review/placement/metrics.md
Decoupling: pad-to-pad distance from each rail cap to the nearest same-net pin of its owner IC.
Loops: switch-node part spacing for every regulator.  Clocks/high-speed: crystal and CSI path lengths."""
import math, os, sys
import pcbnew
from kisch import ROOT
sys.path.insert(0, str(ROOT / "scripts"))
from place import SHEET_OWNER, DECAP_OWNER

b = pcbnew.LoadBoard(str(ROOT / "esp32p4_lte_cam.kicad_pcb"))
fps = {fp.GetReference(): fp for fp in b.GetFootprints()}
mm = pcbnew.ToMM


def d(p, q):
    return math.hypot(mm(p.x - q.x), mm(p.y - q.y))


def pad_dist(a, b_ref, net):
    pa = [p for p in fps[a].Pads() if p.GetNetname() == net]
    pb = [p for p in fps[b_ref].Pads() if p.GetNetname() == net]
    return min((d(x.GetPosition(), y.GetPosition()) for x in pa for y in pb), default=float("nan"))


rows, worst = [], []
for ref, fp in sorted(fps.items()):
    if not ref.startswith("C"):
        continue
    nets = {p.GetNetname() for p in fp.Pads()}
    rail = [n for n in nets if n != "GND"]
    if "GND" not in nets or len(rail) != 1:
        continue
    owner = DECAP_OWNER.get(rail[0]) or SHEET_OWNER.get((fp.GetSheetfile(), rail[0]))
    if not owner:
        continue
    dist = pad_dist(ref, owner, rail[0])
    rows.append((owner, ref, fp.GetValue(), rail[0], dist))
loops = [("U5 BQ25895", "U5", "L201", "/power/CHG_SW"), ("U6 TPS631000", "U6", "L202", "/power/BB_LX1"),
         ("U7 TLV62569", "U7", "L301", "/mcu/HP_SW"), ("U12 TPS61169", "U12", "L601", "/camera_ir/IR_SW"),
         ("U12 Schottky", "U12", "D601", "/camera_ir/IR_SW")]
out = ["# Placement metrics (pad-to-pad, mm)", "", "## Switch-node loops", "", "| Regulator | Part | Distance |", "|---|---|---|"]
for name, ic, part, net in loops:
    out.append(f"| {name} | {part} | {pad_dist(ic, part, net):.2f} |")
out += ["", "## Clocks and camera path", "", "| Item | Distance |", "|---|---|",
        f"| Y1 40 MHz to P4 XTAL_P | {pad_dist('Y1', 'U1', '/mcu/XTAL_P'):.2f} |",
        f"| Y2 32 kHz to P4 GPIO1 | {pad_dist('Y2', 'U1', '/mcu/XTAL32_P'):.2f} |",
        f"| P4 CSI_CK_P pin to FPC pin (straight line) | {d([p for p in fps['U1'].Pads() if p.GetNetname()=='/mcu/P4_CSI_CK_P'][0].GetPosition(), [p for p in fps['J2'].Pads() if p.GetNetname()=='CSI_CK_P'][0].GetPosition()):.2f} |",
        "", "## Decoupling (cap pad to nearest owner pin on the same rail)", "",
        "| Owner | Cap | Value | Rail | Distance | |", "|---|---|---|---|---|---|"]
for owner, ref, val, rail, dist in sorted(rows):
    flag = "OK" if dist <= 3.0 else ("check" if dist <= 6.0 else "FAR")
    out.append(f"| {owner} | {ref} | {val} | {rail} | {dist:.2f} | {flag} |")
    if dist > 6.0:
        worst.append(f"{ref}->{owner} {dist:.1f}")
ok = sum(1 for r in rows if r[4] <= 3.0)
out.insert(2, f"Decoupling caps within 3 mm of their owner pin: **{ok}/{len(rows)}**. Over 6 mm: {len(worst)}\n")
p = ROOT / "docs" / "review" / "placement" / "metrics.md"
p.write_text("\n".join(out) + "\n", encoding="utf-8")
print(f"decaps <=3mm {ok}/{len(rows)}; >6mm: {worst}")
print("\n".join(l for l in out if l.startswith("| U") and "|" in l)[:1500], flush=True)
os._exit(0)
