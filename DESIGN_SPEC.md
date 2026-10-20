# ESP32-P4 LTE Camera Board — Design Spec & Plan

Self-initiated portfolio design, built to a public job brief ("ESP32-P4 Camera Board, MIPI + LTE").
Not affiliated with that client; designed from scratch.

**Tool chain:** KiCad 10.0.7 · kicad-happy 2.3.1 (review/BOM/JLCPCB) · KiCadRoutingTools (bulk routing) · KiCad bundled Python 3.11

---

## 1. Requirements (from the brief)

| # | Requirement |
|---|---|
| R1 | ESP32-P4 main MCU, ESP32-C6 for Wi-Fi/BLE, SIM7600G-H LTE Cat-4 modem + GNSS |
| R2 | MIPI CSI camera connector on the **front edge** |
| R3 | 1S Li-ion charging + protection, **NTC charge-temperature cutoff** |
| R4 | microSD |
| R5 | **Soldered PIR sensor** (replaces the old PIR header) |
| R6 | **4 IR LEDs + driver** (night vision) |
| R7 | **Small motor driver for an IR-cut filter** |
| R8 | **Single USB-C on the bottom edge** (second USB port removed). No status LEDs (two removed) |
| R9 | ~**75 × 70 mm**, **4 layers**, JLCPCB stackup |
| R10 | Antenna placement handled properly. Better battery life than the prototype |
| R11 | Deliverables: KiCad project passing DRC, Gerbers, BOM with LCSC part numbers, CPL, STEP |

## 2. Locked decisions

| Area | Choice | Why |
|---|---|---|
| Main MCU | **ESP32-P4NRW32 chip-down** (QFN-104, 32 MB PSRAM in package) + 16 MB QSPI flash + 40 MHz crystal | Densest option and the strongest layout showcase |
| Wi-Fi | **ESP32-C6-MINI-1** module (PCB antenna) via SDIO (esp-hosted) | Pre-certified RF. Just needs a correct edge keep-out |
| Charger | **TI BQ25895** (I²C, 3 A, power path, JEITA NTC, ADC) | Battery telemetry and temperature cutoff in one part |
| Camera | **22-pin 0.5 mm FPC**, 2-lane CSI (Pi Zero/CM pinout) | Compact on the front edge |
| Antennas | **u.FL × 3** (LTE main, LTE diversity, GNSS), 50 Ω CPWG with π-match pads | Standard for a product in an enclosure |

## 3. Architecture

```
USB-C (bottom edge) ──5V──► BQ25895 ──SYS 3.5–4.35V──┬──► 3V3 buck-boost ──► P4, C6, flash, SD, sensors, camera
   │ D+/D-                  │  ▲ TS ◄── NTC 10k        ├──► LTE load switch ──► SIM7600G-H VBAT (2 A bursts)
   ▼                        ▼ BAT                      ├──► IR LED constant-current driver ──► 4× 850 nm LEDs
ESP32-P4 USB               1S Li-ion + DW01A/FS8205    └──► IR-cut H-bridge (DRV8837-class)
                           (protection)
ESP32-P4 ──SDIO──► ESP32-C6-MINI-1
         ──SDMMC 4-bit──► microSD
         ──MIPI CSI 2-lane + I²C──► 22p FPC camera
         ──UART + ctrl (1.8V level-shift)──► SIM7600G-H ──► nano-SIM, u.FL ×3
         ──LP GPIO (wake)◄── digital PIR
         ──I²C──► BQ25895
```

**Battery-life strategy:** The P4 deep-sleeps and the PIR wakes it on an LP GPIO. The LTE modem, IR driver and camera are each power-gated by a load switch or enable pin. The 3V3 regulator is chosen for low Iq.

## 4. Open items — resolved in Phase 1, with datasheets

- ESP32-P4 power-rail scheme (VDD_HP core supply, external DC-DC vs. internal LDO) per the Espressif *ESP32-P4 Hardware Design Guidelines*. Also confirm the silicon revision and orderable MPN on LCSC.
- USB-C wiring: P4 USB-Serial/JTAG (easy bring-up) vs. HS OTG. Expose the other on test pads?
- 3V3 regulator: buck-boost (TPS63802-class) vs. 100%-duty buck. Battery range 3.0–4.2 V.
- IR LED driver topology: constant-current boost driving 4 LEDs in series vs. a PWM low-side current sink.
- PIR part: digital PIR with a direct output (e.g. Senba S16-L221D class). Check LCSC stock.
- SIM7600G-H sourcing: probably **not** in JLCPCB's library, so plan for a consigned/global-sourced part. SIM7600 I/O is 1.8 V, so it needs level translation.
- Fit check: 75 × 70 mm with an LCC modem (30 × 30 mm), C6 module, FPC, SIM, SD and battery connector. Do a floor-plan sketch before the schematic is final.

## 5. PCB stackup & rules (JLCPCB JLC04161H-7628, 1.6 mm)

| Layer | Use |
|---|---|
| L1 F.Cu | Components, RF, MIPI, USB, short high-speed |
| L2 In1 | **Solid GND** (reference for everything on L1) |
| L3 In2 | Power pours (SYS, 3V3, VBAT_LTE) + low-speed signals |
| L4 B.Cu | Signals, secondary components, GND fill |

Impedance targets: MIPI CSI **100 Ω differential** (D-PHY), USB **90 Ω differential**, RF feeds **50 Ω CPWG** (L1 over L2). Final geometry and rules are in [docs/BOARD_SETUP.md](docs/BOARD_SETUP.md).

## 6. Phased plan with review gates

| Phase | Work | Gate / output |
|---|---|---|
| 0 Setup | git repo, KiCad project skeleton, local symbol/footprint libraries (JLC/LCSC parts), install KiCadRoutingTools | Repo builds, `kicad-cli` checks run |
| 1 Architecture | Resolve §4 items, power budget, P4 GPIO pin map, floor-plan sketch | **Review 1:** parts + pin map |
| 2 Schematic | Hierarchical sheets: Power · P4 core · Wi-Fi · LTE · Camera/IR · Storage/USB/Sensors. Every part gets an LCSC field | ERC clean + kicad-happy review → **Review 2: schematic review** |
| 3 Board setup | 75×70 outline, stackup, net classes, diff-pair rules, JLC DRC rules, mounting holes, edge keep-outs | — |
| 4 Placement | Fixed-edge parts first (FPC front, USB-C bottom, u.FL/antennas), then RF, power, P4 fan-out | 3D render → **Review 3: placement review** |
| 5 Routing | Critical nets by hand/scripted (RF, MIPI, USB, LTE power, switcher loops), bulk via KiCadRoutingTools, GND pours + stitching | — |
| 6 Verification | DRC 0 errors, kicad-happy full review, EMC + thermal pre-checks, impedance check | Review report |
| 7 Fab output | Gerbers + drill, JLC BOM/CPL (rotation-checked), STEP, fab notes, schematic PDF | `fab/` folder ready to upload |
| 8 Portfolio | Renders, block diagram, schematic PDF, write-up (decisions + trade-offs), README, GitHub | Portfolio page |

## 7. Risks

- **Density:** QFN-104 fan-out plus MIPI plus an LCC modem on 4 layers at 75×70 is tight. The floor-plan in Phase 1 de-risks this.
- **Modem sourcing:** SIM7600G-H assembly is likely consigned, which affects the JLC BOM.
- **Unbuilt hardware:** In the portfolio, present this as "designed to production-ready, not yet fabricated" unless boards are ordered.
