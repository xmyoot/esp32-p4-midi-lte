# Placement metrics (pad-to-pad, mm)

Decoupling caps within 3 mm of their owner pin: **22/62**. Over 6 mm: 7

## Switch-node loops

| Regulator | Part | Distance |
|---|---|---|
| U5 BQ25895 | L201 | 3.72 |
| U6 TPS631000 | L202 | 2.19 |
| U7 TLV62569 | L301 | 3.00 |
| U12 TPS61169 | L601 | 5.64 |
| U12 Schottky | D601 | 2.30 |

## Clocks and camera path

| Item | Distance |
|---|---|
| Y1 40 MHz to P4 XTAL_P | 4.61 |
| Y2 32 kHz to P4 GPIO1 | 3.52 |
| P4 CSI_CK_P pin to FPC pin (straight line) | 11.37 |

## Decoupling (cap pad to nearest owner pin on the same rail)

| Owner | Cap | Value | Rail | Distance | |
|---|---|---|---|---|---|
| J2 | C601 | 10u 10V | 3V3_CAM | 4.60 | check |
| J2 | C602 | 100n | 3V3_CAM | 5.03 | check |
| J3 | C702 | 10u 10V | 3V3_SD | 1.84 | OK |
| J3 | C703 | 100n | 3V3_SD | 3.25 | check |
| U1 | C301 | 100n | 3V3 | 1.67 | OK |
| U1 | C302 | 100n | 3V3 | 1.70 | OK |
| U1 | C303 | 100n | 3V3 | 1.58 | OK |
| U1 | C304 | 100n | 3V3 | 1.73 | OK |
| U1 | C305 | 100n | 3V3 | 3.18 | check |
| U1 | C306 | 100n | 3V3 | 3.14 | check |
| U1 | C307 | 100n | 3V3 | 5.44 | check |
| U1 | C308 | 10u 10V | 3V3 | 6.55 | FAR |
| U1 | C309 | 10u 10V | 3V3 | 7.52 | FAR |
| U1 | C310 | 10u 10V | 3V3 | 4.08 | check |
| U1 | C311 | 100n | VDD_HP | 3.79 | check |
| U1 | C312 | 100n | VDD_HP | 1.70 | OK |
| U1 | C313 | 100n | VDD_HP | 3.16 | check |
| U1 | C314 | 100n | VDD_HP | 7.12 | FAR |
| U1 | C315 | 10u 10V | VDD_HP | 3.42 | check |
| U1 | C316 | 1u | VDD_FLASH | 3.34 | check |
| U1 | C317 | 100n | VDD_FLASH | 2.52 | OK |
| U1 | C318 | 1u | VDD_PSRAM | 2.85 | OK |
| U1 | C319 | 100n | VDD_PSRAM | 1.71 | OK |
| U1 | C320 | 100n | VDD_PSRAM | 3.73 | check |
| U1 | C321 | 1u | VDD_PSRAM | 4.29 | check |
| U1 | C322 | 1u | VDD_MIPI | 1.71 | OK |
| U1 | C323 | 100n | VDD_MIPI | 4.77 | check |
| U1 | C324 | 10n | VDD_MIPI | 2.98 | OK |
| U1 | C325 | 1u | /mcu/VDDO_4 | 5.40 | check |
| U1 | C326 | 100n | 1V8_IO6 | 9.18 | FAR |
| U1 | C327 | 1u | 1V8_IO6 | 8.23 | FAR |
| U1 | C328 | 4.7u 10V | 3V3 | 4.74 | check |
| U1 | C330 | 22u 10V | VDD_HP | 3.93 | check |
| U1 | C331 | 100n | VDD_FLASH | 4.89 | check |
| U11 | C705 | 1u | 3V3 | 2.08 | OK |
| U12 | C605 | 10u 10V | SYS | 2.25 | OK |
| U12 | C607 | 10u 10V | SYS | 4.78 | check |
| U12 | C608 | 100n 16V | SYS | 5.29 | check |
| U13 | C604 | 1u | 3V3 | 1.55 | OK |
| U13 | C609 | 100n | 3V3 | 3.81 | check |
| U16 | C511 | 100n | 1V8_IO6 | 1.71 | OK |
| U16 | C512 | 100n | 3V3 | 1.88 | OK |
| U19 | C610 | 4.7u 10V | /camera_ir/PIR_VDD | 3.40 | check |
| U19 | C611 | 100n | /camera_ir/PIR_VDD | 5.00 | check |
| U3 | C401 | 10u 10V | 3V3 | 2.34 | OK |
| U3 | C402 | 100n | 3V3 | 2.84 | OK |
| U4 | C501 | 220u 6.3V | VBAT_LTE | 3.05 | check |
| U4 | C502 | 220u 6.3V | VBAT_LTE | 6.35 | FAR |
| U4 | C503 | 10u 10V | VBAT_LTE | 2.15 | OK |
| U4 | C504 | 100n | VBAT_LTE | 2.13 | OK |
| U4 | C505 | 33p | VBAT_LTE | 5.46 | check |
| U4 | C506 | 10p | VBAT_LTE | 4.64 | check |
| U5 | C201 | 1u 25V | VBUS | 1.97 | OK |
| U5 | C205 | 10u 10V | SYS | 3.96 | check |
| U5 | C206 | 10u 10V | SYS | 5.84 | check |
| U5 | C207 | 10u 10V | BAT | 3.45 | check |
| U5 | C209 | 22u 10V | SYS | 6.18 | FAR |
| U6 | C211 | 22u 10V | 3V3 | 4.26 | check |
| U6 | C212 | 22u 10V | 3V3 | 3.12 | check |
| U6 | C213 | 100n | 3V3 | 2.66 | OK |
| U6 | C214 | 1u | 3V3 | 4.56 | check |
| U9 | C508 | 10u 10V | SYS | 3.05 | check |
