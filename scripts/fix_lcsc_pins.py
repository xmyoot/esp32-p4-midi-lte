"""Assign real electrical pin types to EasyEDA-imported symbols (they import as 'unspecified').
Re-run after every scripts/import_lcsc.sh.  Types follow each part's datasheet pin table."""
import re
from kisch import parse, fmt, kids, kid, LOCAL_LIBS

PI, PO, IN, OUT, BI, PA, NCT = "power_in", "power_out", "input", "output", "bidirectional", "passive", "no_connect"
RULES = {   # symbol -> [(regex on pin name, type)], first match wins; default given by "*"
    "SIM7600G-H_C5355477": [(r"^VBAT$|^GND$", PI), (r"^VDD_1V8$|^USIM_VDD$|^VDD_AUX$", PO),
                            (r"^(STATUS|TXD|CTS|RI|DCD|NETLIGHT|DBG_TXD)", OUT),
                            (r"^(RXD|RTS|DTR|PWRKEY|RESET|DBG_RXD|USB_VBUS)$", IN),
                            (r"_ANT$", PA), (r"^NC$", NCT), ("*", BI)],
    "TPS631000DRLR": [(r"^VIN$|^GND$", PI), (r"^VOUT$", PO), (r"^(EN|MODE|FB)$", IN), ("*", PA)],
    "TPS7A0218DBVR": [(r"^IN$|^GND$", PI), (r"^OUT$", PO), (r"^EN$", IN), (r"^NC$", NCT), ("*", PA)],
    "TPS22965DSGR": [(r"^(VIN|VBIAS|GND|EP)$", PI), (r"^VOUT$", PO), (r"^ON$", IN), ("*", PA)],  # pin 8 -> passive below
    "TPS22918DBVR": [(r"^(VIN|GND)$", PI), (r"^VOUT$", PO), (r"^ON$", IN), ("*", PA)],
    "TPS61169DCKR": [(r"^(VIN|GND)$", PI), (r"^(FB|CTRL)$", IN), ("*", PA)],
    "PIR223D-S0": [(r"^(VDD|VSS)$", PI), (r"^REL$", OUT), ("*", PA)],
    "M3838E1IRS1G09": [(r"^NC$", NCT), ("*", PA)],
    "*": [("*", PA)],   # connectors, switches, FETs, inductors
}


def main():
    path = LOCAL_LIBS["lcsc"]
    lib = parse(path.read_text(encoding="utf-8"))
    changed = 0
    for sym in kids(lib, "symbol"):
        rules = RULES.get(sym[1], RULES["*"])
        for unit in kids(sym, "symbol"):
            for pin in kids(unit, "pin"):
                name = str(kid(pin, "name")[1])
                if sym[1] == "TPS22965DSGR" and str(kid(pin, "number")[1]) == "8":
                    name = "_VOUT2"   # only one power_out per net
                for pat, typ in rules:
                    if pat == "*" or re.search(pat, name):
                        if pin[1] != typ:
                            pin[1] = typ; changed += 1
                        break
    path.write_text(fmt(lib) + "\n", encoding="utf-8")
    print(f"updated {changed} pin types in {path.name}")
    # vendored Espressif symbol: VDD_ANA / VDD_BAT are supply inputs (datasheet table 2-1), not bidirectional
    ep = LOCAL_LIBS["espressif"]
    elib, n = parse(ep.read_text(encoding="utf-8")), 0
    for sym in kids(elib, "symbol"):
        for unit in kids(sym, "symbol"):
            for pin in kids(unit, "pin"):
                if str(kid(pin, "name")[1]) in ("VDD_ANA", "VDD_BAT") and pin[1] != PI:
                    pin[1] = PI; n += 1
    ep.write_text(fmt(elib) + "\n", encoding="utf-8")
    print(f"espressif: fixed {n} supply pin types")


if __name__ == "__main__":
    main()


def fix_footprints():
    """EasyEDA imports model plastic locating pegs as zero-annular PTH pads -> make them NPTH.
    TO-5 PIR courtyard imports self-intersecting -> replace with a clean circle (body dia 9.2 + 0.25)."""
    import re as _re
    pretty = LOCAL_LIBS["lcsc"].with_suffix(".pretty")
    peg = _re.compile(r'\(pad "" thru_hole (circle|oval) (\(at [^)]*\)) \(size ([\d.]+) ([\d.]+)\) \(drill ([\d.]+)\)')
    for f in sorted(pretty.glob("*.kicad_mod")):
        t = f.read_text(encoding="utf-8"); n0 = t
        t = peg.sub(lambda m: m.group(0).replace("thru_hole", "np_thru_hole")
                    if abs(float(m.group(3)) - float(m.group(5))) < 0.02 else m.group(0), t)
        if f.name.startswith("TO-5-3"):
            t = "\n".join(l for l in t.splitlines() if "F.CrtYd" not in l)
            t = t.rstrip().rstrip(")") + "\n\t(fp_circle (center 0 -1.27) (end 4.85 -1.27) (layer F.CrtYd) (width 0.05))\n)\n"
        if t != n0:
            f.write_text(t, encoding="utf-8"); print("fixed footprint", f.name)


if __name__ == "__main__":
    fix_footprints()
