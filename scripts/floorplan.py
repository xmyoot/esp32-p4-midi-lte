"""Phase-1 floor-plan fit check: draws block outlines on the 75x70 mm board -> docs/floorplan.png
Coordinates in mm, origin top-left, +y down. Top edge = FRONT (camera), bottom edge = USB-C."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

W, H, S, M = 75.0, 70.0, 12, 40          # board mm, px/mm, margin px
OUT = Path(__file__).resolve().parent.parent / "docs" / "floorplan.png"

# (label, x, y, w, h, kind)   kind -> colour group
BLOCKS = [
    # front edge
    ("J2 CAM FPC 22P", 29.5, 0.0, 16.0, 5.5, "conn"),
    ("D1", 3.0, 1.0, 3.8, 3.8, "ir"), ("D2", 10.0, 1.0, 3.8, 3.8, "ir"),
    ("D3", 61.2, 1.0, 3.8, 3.8, "ir"), ("D4", 68.2, 1.0, 3.8, 3.8, "ir"),
    ("PIR1 TO-5", 15.5, 0.8, 9.4, 9.4, "sense"),
    ("IR drv U12 + L", 50.0, 0.8, 9.5, 6.0, "pwr"),
    # wifi module, antenna at left edge
    ("U3 ESP32-C6-MINI-1", 0.0, 13.0, 16.6, 13.2, "rf"),
    ("C6 ANT keepout", 0.0, 13.0, 4.8, 13.2, "keep"),
    # SoC cluster
    ("U1 ESP32-P4 10x10", 22.0, 18.0, 10.0, 10.0, "soc"),
    ("P4 decap/fanout ring", 19.0, 15.0, 16.0, 16.0, "zone"),
    ("U2 FLASH SOIC8", 19.0, 32.0, 8.0, 6.0, "soc"),
    ("Y1 40M", 28.0, 32.5, 3.5, 3.0, "soc"),
    ("U7 VDD_HP DCDC", 26.0, 10.5, 8.0, 4.3, "pwr"),
    # storage / sim / misc right-top
    ("J3 microSD", 44.0, 10.0, 14.5, 15.0, "conn"),
    ("U13 IR-cut + J9", 59.5, 9.0, 9.5, 6.0, "pwr"),
    ("U10/U11 load sw", 59.5, 16.0, 9.5, 6.0, "pwr"),
    ("SW1/SW2", 36.5, 8.0, 6.0, 4.0, "misc"),
    # modem bottom-right
    ("U4 SIM7600G-H 30x30", 40.0, 35.0, 30.0, 30.0, "rf"),
    ("LTE bulk caps", 40.0, 29.5, 22.0, 5.0, "pwr"),
    ("J5 MAIN", 71.0, 58.5, 3.0, 3.0, "rfc"), ("J6 AUX", 71.0, 37.5, 3.0, 3.0, "rfc"),
    ("J7 GNSS", 63.0, 30.5, 3.0, 3.0, "rfc"),
    ("J4 nano-SIM", 26.0, 42.0, 13.0, 14.0, "conn"),
    # power, bottom-left
    ("U5 BQ25895 + L", 2.0, 44.0, 12.0, 10.0, "pwr"),
    ("U6 3V3 bb + L", 14.5, 44.0, 9.5, 7.0, "pwr"),
    ("U9 LTE sw", 14.5, 52.0, 9.5, 4.0, "pwr"),
    ("J8 BATT PH3", 6.5, 60.0, 10.0, 6.0, "conn"),
    ("U14 prot", 17.5, 60.0, 7.0, 4.5, "pwr"),
    ("J1 USB-C", 26.5, 62.6, 9.0, 7.4, "conn"),
    ("ESD/TVS", 26.5, 57.0, 9.0, 4.5, "misc"),
    ("TP debug", 0.5, 30.0, 12.0, 6.0, "misc"),
]
COL = {"conn": "#4C78A8", "ir": "#E45756", "sense": "#B279A2", "pwr": "#F58518", "rf": "#54A24B",
       "keep": "#FFFFFF", "soc": "#9467BD", "zone": None, "rfc": "#2E7D32", "misc": "#888888"}
HOLES = [(3.5, 3.5 + 6), (71.5, 3.5 + 6), (3.5, 66.5), (71.5, 66.5)]   # M2.5, shifted below IR LEDs top-left/right

def px(v): return M + v * S

img = Image.new("RGB", (int(W * S + 2 * M), int(H * S + 2 * M) + 30), "white")
d = ImageDraw.Draw(img)
try: f = ImageFont.truetype("arial.ttf", 13); fb = ImageFont.truetype("arialbd.ttf", 16)
except OSError: f = fb = ImageFont.load_default()
d.rounded_rectangle([px(0), px(0), px(W), px(H)], radius=2 * S, outline="black", width=3, fill="#E8F0E0")
area = 0
for lab, x, y, w, h, k in BLOCKS:
    box = [px(x), px(y), px(x + w), px(y + h)]
    if k == "zone":
        d.rectangle(box, outline="#9467BD", width=1); continue
    if k == "keep":
        d.rectangle(box, outline="red", width=2, fill="#FFE5E5"); d.text((box[0] + 3, box[1] + 3), "ANT\nKO", fill="red", font=f); continue
    area += w * h
    d.rectangle(box, outline="black", width=1, fill=COL[k])
    d.text((box[0] + 3, box[1] + 2), lab, fill="white" if k not in ("misc",) else "black", font=f)
for (x, y) in HOLES:
    d.ellipse([px(x) - 1.35 * S, px(y) - 1.35 * S, px(x) + 1.35 * S, px(y) + 1.35 * S], outline="black", width=2)
# overlap check
rects = [b for b in BLOCKS if b[5] not in ("zone", "keep")]
clash = []
for i, a in enumerate(rects):
    for b in rects[i + 1:]:
        if a[1] < b[1] + b[3] and b[1] < a[1] + a[3] and a[2] < b[2] + b[4] and b[2] < a[2] + a[4]:
            clash.append(f"{a[0]} x {b[0]}")
    if a[1] < 0 or a[2] < 0 or a[1] + a[3] > W + 0.01 or a[2] + a[4] > H + 0.01: clash.append(f"{a[0]} off-board")
d.text((M, 8), "FRONT EDGE (camera)  -  75 x 70 mm, top view", fill="black", font=fb)
d.text((M, int(H * S + M) + 8), f"BOTTOM EDGE (USB-C)   placed block area {area:.0f} mm2 of {W*H:.0f} ({100*area/(W*H):.0f}%)", fill="black", font=fb)
OUT.parent.mkdir(exist_ok=True); img.save(OUT)
print(f"area {area:.0f}/{W*H:.0f} = {100*area/(W*H):.0f}%"); print("clashes:", clash or "none")
# mounting-hole keep-out (3.2 mm pad dia + 0.5 clearance)
for (hx, hy) in HOLES:
    for b in rects:
        cx = min(max(hx, b[1]), b[1] + b[3]); cy = min(max(hy, b[2]), b[2] + b[4])
        if (cx - hx) ** 2 + (cy - hy) ** 2 < 2.1 ** 2: print("hole clash:", (hx, hy), b[0])
