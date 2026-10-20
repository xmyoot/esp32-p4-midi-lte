# Review 2 — Schematic (rev A draft)

Package: [`schematic_revA_draft.pdf`](schematic_revA_draft.pdf) · [`bom_revA_draft.csv`](bom_revA_draft.csv) · sources in `scripts/build_sch.py`

## What's in it

| Sheet | Contents | Parts (TP / DNP) |
|---|---|---|
| 2 Power | USB-C (sink, 5.1 k Rd), VBUS TVS, USB ESD, BQ25895 charger, DW01A + FS8205A protection, TPS631000 3V3 buck-boost, TPS7A0218 1V8 LDO | 42 (1 / 2) |
| 3 MCU | ESP32-P4NRW32X, W25Q128 flash with 0 Ω tuning pads, 40 MHz and 32 kHz crystals, TLV62569 VDD_HP DC-DC (v3 feedback), TPS3839 supervisor, RESET/BOOT buttons, MIPI 0 Ω series links | 73 (7 / 0) |
| 4 Wi-Fi | ESP32-C6-MINI-1 on SDIO with pull-ups, EN RC, C6 programming pads (UART + USB-JTAG) | 18 (6 / 0) |
| 5 LTE | SIM7600G-H, TPS22965 VBAT switch, 2 × 220 µF bulk, PWRKEY/RESET NMOS drivers, RI → LP-wake shifter, nano-SIM with ESD, 3 × U.FL with π-pads, GNSS bias tee (DNP) | 51 (6 / 8) |
| 6 Camera/IR | 22-pin CSI FPC, 3V3_CAM switch, TPS61169 4-LED IR driver (294 mA), DRV8837 IR-cut, PIR | 32 (0 / 1) |
| 7 Storage | microSD on SDMMC slot 0, 3V3_SD switch | 15 (0 / 1) |

**199 placements, 72 BOM lines. Every line has an LCSC number and an MPN.** Most passives are JLC basic parts.

## Verification done

| Check | Result |
|---|---|
| KiCad ERC (`--severity-all`) | **0 violations** |
| kicad-happy schematic analyzer | 0 errors. 9 warnings, all triaged below |
| ESP32-P4X symbol vs. datasheet pin table | All 105 pins match. The 15 name differences are aliases only (e.g. `GPIO16/ADC1_CHANNEL0`) |
| Imported symbols vs. datasheets | TPS631000, TPS22918, TPS22965, TPS7A02, TPS61169 pinouts match the TI/LCSC datasheets |
| SIM7600G-H footprint | 135 pads. The edge-pad sequence and corner pins match the SIMCom HW Design V1.00 Fig. 2 |
| P4 power and support circuitry | Follows the HDG checklist and Fig. 5 (v3 DC-DC), cross-checked against ESP32-P4-Function-EV v1.5.2 |

### Analyzer warnings, triaged

| Rule | Finding | Verdict |
|---|---|---|
| PU-001 ×7 | "Missing pull-up" on U14 OD, U4 RESET/USIM_RST/SCL/SDA/SGMII_RST_N, U5 STAT | **False positive.** DW01A OD is push-pull. Modem RESET has an internal 40 k pull-up to 1.8 V. USIM_RST is modem-driven. The rest are unused pins flagged NC |
| RS-001 | MDM_USB_VBUS has no source | **Expected.** It's a test pad, powered only during modem firmware updates |
| WL-001 | Verify the SIM wiring on the cellular module | **Done.** VDD, RST, CLK, IO and DET are routed with 22 Ω / 33 pF and TPD4E05U06 ESD |

ESD-audit info: microSD, camera FPC, U.FL, battery and IR-cut connectors have no ESD parts. They are all **inside the enclosure**. The user-touchable ports, USB-C and nano-SIM, are protected.

## Changes since Review 1

1. **GPIO10 is now C6_WAKE** (LP domain), so Wi-Fi traffic can wake the P4 from deep sleep. The IR-cut and IR-PWM signals moved to GPIO30–32.
2. **VDD_MIPI_DPHY is fed from the P4's internal VDDO_3 (2.5 V)**, as on Espressif's EV board.
3. **0 Ω links on the BQ25895 D+/D− (R-CHG_DP/DN).** BC1.2 detection shares the USB pair with USB-Serial/JTAG. If the two interfere at bring-up, removing the links isolates the charger.
4. On-board NTC is DNP by default. The pack's NTC comes in on J8 pin 2.

## Items to confirm before layout

- [ ] **IR LED current: 294 mA** (0.68 Ω sense). About 2.3 W of IR at full duty. PWM-dimmable.
- [ ] **Charger input limit: about 3 A** (ILIM 120 Ω). Firmware can lower it over I²C.
- [ ] **Battery:** 3-pin JST-PH pack (BAT+, NTC, BAT−), ≥2500 mAh, ≥1C discharge.
- [ ] **LP_I2C pin mux** (GPIO5/6 for the charger) to confirm against the ESP32-P4 TRM during firmware bring-up. A fallback to HP I²C on the same pins exists.

## Next: Phase 3 board setup

Outline 75 × 70 mm, JLC04161H-7628 stackup, net classes (90 Ω USB/MIPI diff pairs, 50 Ω CPWG RF, power widths), JLC DRC rules, mounting holes, and edge and antenna keep-outs. After that comes placement and Review 3.
