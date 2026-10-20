"""Schematic source of truth for the ESP32-P4 LTE camera board.
Run:  $PY scripts/build_sch.py      (writes *.kicad_sch into the project root)
Every value below is traceable to docs/ARCHITECTURE.md and the datasheets in datasheets/."""
import sys
from kisch import Design, ROOT

D = Design("ESP32-P4 LTE Camera Board", rev="A")
D.power_nets |= {"VBUS", "SYS", "BAT", "3V3", "VDD_HP", "1V8_IO6", "VDD_FLASH", "VDD_PSRAM", "VDD_MIPI",
                 "3V3_CAM", "3V3_SD", "VBAT_LTE"}

R0402 = "Resistor_SMD:R_0402_1005Metric"
NC = "NC"

# =====================================================================================  POWER
s = D.sheet("power", "Power - USB-C, charger, battery protection, 3V3 / 1V8 rails")
s.notes += ["USB-C: sink-only, 5.1k Rd on CC1/CC2. D+/D- shared by ESP32-P4 USB-Serial/JTAG and BQ25895 BC1.2 detection.",
            "BQ25895: ILIM 120R -> ~3 A max input; TS divider 5.23k/30.1k for 103AT NTC (JEITA) per datasheet sec. 9.2.2.",
            "Cell protection: DW01A + FS8205A in the battery negative leg (BATN = cell -, GND = pack -)."]
# USB-C
j = s.add("J1", "Connector:USB_C_Receptacle_USB2.0_16P", "USB-C (bottom edge)",
          "Connector_USB:USB_C_Receptacle_HRO_TYPE-C-31-M-12", LCSC="C165948", MPN="TYPE-C-31-M-12")
j.wire({"VBUS": "VBUS", "GND": "GND", "SHIELD": "GND", "CC1": "USB_CC1", "CC2": "USB_CC2",
        "D+": "USB_DP", "D-": "USB_DN", "SBU1": NC, "SBU2": NC})
s.R("5.1k", "USB_CC1", "GND"); s.R("5.1k", "USB_CC2", "GND")
s.flag("VBUS", "GND", "SYS", "BAT", "BATN", "DW_VCC")
s.add("D?", "Device:D_Zener", "SMF5.0A (TVS)", "Diode_SMD:D_SOD-123F", LCSC="C193402", MPN="SMF5.0A").wire({"K": "VBUS", "A": "GND"})
s.add("U17", "Power_Protection:TPD4E05U06DQA", "TPD4E05U06", "Package_SON:USON-10_2.5x1.0mm_P0.5mm",
      LCSC="C138714", MPN="TPD4E05U06DQAR").wire(
    {"1": "USB_DP", "2": "USB_DN", "4": "USB_CC1", "5": "USB_CC2", "3": "GND", "8": "GND", "6": NC, "7": NC, "9": NC, "10": NC})
# Charger
s.group()
u = s.add("U5", "Battery_Management:BQ25895RTW", "BQ25895RTWR",
          "Package_DFN_QFN:Texas_RTW_WQFN-24-1EP_4x4mm_P0.5mm_EP2.7x2.7mm_ThermalVias", LCSC="C80200", MPN="BQ25895RTWR")
u.wire({"VBUS": "VBUS", "D+": "CHG_DP", "D-": "CHG_DN", "STAT": NC, "SCL": "SYS_SCL", "SDA": "SYS_SDA",
        "~{INT}": "CHG_INT", "OTG": "GND", "~{CE}": "GND", "ILIM": "CHG_ILIM", "TS": "CHG_TS", "~{QON}": "CHG_QON",
        "BAT": "BAT", "SYS": "SYS", "PGND": "GND", "SW": "CHG_SW", "BTST": "CHG_BTST", "REGN": "CHG_REGN",
        "PMID": "CHG_PMID", "DSEL": NC})
s.C("1u", "VBUS", size="0603", v="25V")
s.R("0", "CHG_DP", "USB_DP"); s.R("0", "CHG_DN", "USB_DN")   # remove to isolate BC1.2 detection at bring-up
s.C("10u", "CHG_PMID", size="0805", v="25V")
s.C("4.7u", "CHG_REGN", size="0603", v="10V")
s.C("47n", "CHG_BTST", "CHG_SW", v="16V")
s.L("2.2uH", "CHG_SW", "SYS", "lcsc:IND-SMD_L5.0-W5.0_SMNR5030", LCSC="C189797", MPN="SMNR5030-2R2N")
s.C("10u", "SYS", size="0805", v="10V"); s.C("10u", "SYS", size="0805", v="10V")
s.C("10u", "BAT", size="0805", v="10V")
s.R("120", "CHG_ILIM", "GND")
s.R("5.23k", "CHG_REGN", "CHG_TS"); s.R("30.1k", "CHG_TS", "GND")
s.add("RT?", "Device:Thermistor_NTC", "10k B3435 (DNP)", "Resistor_SMD:R_0603_1608Metric", dnp=True,
      LCSC="C13564", MPN="NCP18XH103F03RB").wire({"1": "CHG_TS", "2": "GND"})
s.R("10k", "SYS_SDA", "3V3"); s.R("10k", "SYS_SCL", "3V3"); s.R("10k", "CHG_INT", "3V3")
s.TP("CHG_QON")
# Battery + protection
s.group()
s.add("J8", "Connector_Generic:Conn_01x03", "BATT (+ / NTC / -)", "Connector_JST:JST_PH_S3B-PH-SM4-TB_1x03-1MP_P2.00mm_Horizontal",
      LCSC="C265101", MPN="S3B-PH-SM4-TB(LF)(SN)").wire({"1": "BAT", "2": "CHG_TS", "3": "BATN"})
s.add("U14", "Battery_Management:DW01A", "DW01A", "Package_TO_SOT_SMD:SOT-23-6", LCSC="C351410", MPN="DW01A").wire(
    {"VCC": "DW_VCC", "GND": "BATN", "OD": "PROT_OD", "OC": "PROT_OC", "CS": "DW_CS", "TD": NC})
s.add("Q?", "lcsc:FS8205A_C2830320", "FS8205A", "lcsc:SOT-23-6_L2.9-W1.6-P0.95-LS2.8-BR", LCSC="C2830320", MPN="FS8205A").wire(
    {"1": "BATN", "6": "PROT_OD", "3": "GND", "4": "PROT_OC", "2": "PROT_D", "5": "PROT_D"})
s.R("100", "BAT", "DW_VCC"); s.C("100n", "DW_VCC", "BATN"); s.R("1k", "DW_CS", "GND")
# 3V3 buck-boost
s.group()
s.add("U6", "lcsc:TPS631000DRLR", "TPS631000", "lcsc:SOT-583-8_L2.1-W1.2-P0.50-LS1.6-BL", LCSC="C5219190",
      MPN="TPS631000DRLR").wire({"VIN": "SYS", "EN": "SYS", "MODE": "GND", "GND": "GND", "LX1": "BB_LX1",
                                 "LX2": "BB_LX2", "VOUT": "3V3", "FB": "BB_FB"})
s.C("22u", "SYS", size="0805", v="10V")
s.L("1uH", "BB_LX1", "BB_LX2", "Inductor_SMD:L_1008_2520Metric", LCSC="C98348", MPN="WPN252012H1R0MT")
s.R("560k", "3V3", "BB_FB"); s.R("100k", "BB_FB", "GND"); s.C("10p", "3V3", "BB_FB", dnp=True)
s.C("22u", "3V3", size="0805", v="10V"); s.C("22u", "3V3", size="0805", v="10V"); s.C("100n", "3V3")
# 1V8 for VDD_IO_6 (modem UART domain)
s.group()
s.add("U8", "lcsc:TPS7A0218DBVR", "TPS7A0218", "lcsc:SOT-23-5_L3.0-W1.7-P0.95-LS2.8-BL", LCSC="C5144851",
      MPN="TPS7A0218DBVR").wire({"IN": "3V3", "EN": "3V3", "GND": "GND", "NC": NC, "OUT": "1V8_IO6"})
s.C("1u", "3V3"); s.C("1u", "1V8_IO6")

# =====================================================================================  MCU
s = D.sheet("mcu", "ESP32-P4 core - SoC, flash, clocks, core DC-DC, reset/boot")
s.notes += ["Chip rev v3.x (ESP32-P4NRW32X): VDD_HP_1 on pin 54; DC-DC feedback 499k/499k/22pF populated (HDG fig. 5).",
            "VDD_MIPI_DPHY fed from internal VDDO_3 (2.5 V) as on ESP32-P4-Function-EV v1.5.2. VDD_USBPHY unused (HS PHY not used).",
            "VDD_IO_6 = 1.8 V: GPIO49-54 talk to the SIM7600 UART natively. Keep these pins hi-Z while VBAT_LTE is off."]
u = s.add("U1", "espressif:ESP32-P4X", "ESP32-P4NRW32X", "espressif:ESP32-P4", LCSC="C54540373",
          MPN="ESP32-P4NRW32X", Note="Consigned - zero JLC stock at design time")
u.wire({  # power
    "VDD_LP": "3V3", "VDD_IO_0": "3V3", "VDD_IO_4": "3V3", "VDD_IO_5": "3V3", "VDD_IO_6": "1V8_IO6",
    "VDD_ANA": "3V3", "VDD_BAT": "3V3", "VDD_LDO": "3V3", "VDD_DCDCC": "3V3",
    "VDD_HP_0": "VDD_HP", "VDD_HP_1": "VDD_HP", "VDD_HP_2": "VDD_HP", "VDD_HP_3": "VDD_HP",
    "VDDO_FLASH": "VDD_FLASH", "VDD_FLASH_IO": "VDD_FLASH", "VDDO_PSRAM": "VDD_PSRAM",
    "VDD_PSRAM_0": "VDD_PSRAM", "VDD_PSRAM_1": "VDD_PSRAM", "VDDO_3": "VDD_MIPI", "VDD_MIPI_DPHY": "VDD_MIPI",
    "VDDO_4": "VDDO_4", "VDD_USBPHY": NC, "GND": "GND",
    "49": NC, "50": NC,                                   # HS USB PHY unused
    "DSI_REXT": NC, "DSI_DATAP0": NC, "DSI_DATAN0": NC, "DSI_DATAP1": NC, "DSI_DATAN1": NC, "DSI_CLKP": NC, "DSI_CLKN": NC,
    "CSI_DATAP0": "P4_CSI_D0_P", "CSI_DATAN0": "P4_CSI_D0_N", "CSI_DATAP1": "P4_CSI_D1_P", "CSI_DATAN1": "P4_CSI_D1_N",
    "CSI_CLKP": "P4_CSI_CK_P", "CSI_CLKN": "P4_CSI_CK_N", "CSI_REXT": "CSI_REXT",
    "FLASH_CS": "P4_FL_CS", "FLASH_Q": "P4_FL_Q", "FLASH_WP": "P4_FL_WP", "FLASH_HOLD": "P4_FL_HOLD",
    "FLASH_CK": "P4_FL_CK", "FLASH_D": "P4_FL_D",
    "XTAL_N": "XTAL_N", "XTAL_P": "XTAL_P", "CHIP_PU": "CHIP_PU", "EN_DCDC": "EN_DCDC", "FB_DCDC": "FB_DCDC",
    # GPIO map (docs/ARCHITECTURE.md sec. 5)
    "GPIO0": "XTAL32_N", "GPIO1": "XTAL32_P", "GPIO2": "PIR_OUT", "GPIO3": "CHG_INT", "GPIO4": "MODEM_RI_3V3",
    "GPIO5": "SYS_SDA", "GPIO6": "SYS_SCL", "GPIO7": "MODEM_PWRKEY_CTL", "GPIO8": "MODEM_PWR_EN", "GPIO9": "C6_EN",
    "GPIO10": "C6_WAKE", "GPIO11": "MODEM_RESET_CTL", "GPIO12": "TP_GPIO12", "GPIO13": "TP_GPIO13",
    "GPIO14": "SDIO_D0", "GPIO15": "SDIO_D1", "GPIO16": "SDIO_D2", "GPIO17": "SDIO_D3", "GPIO18": "SDIO_CLK",
    "GPIO19": "SDIO_CMD", "GPIO20": "CAM_SDA", "GPIO21": "CAM_SCL", "GPIO22": "CAM_IO0", "GPIO23": "CAM_PWR_EN",
    "GPIO24": "P4_USB_DN", "GPIO25": "P4_USB_DP", "GPIO26": "C6_BOOT", "GPIO27": "IRCUT_NSLEEP",
    "GPIO28": "SD_PWR_EN", "GPIO29": "CAM_IO1", "GPIO30": "IRCUT_IN1", "GPIO31": "IRCUT_IN2", "GPIO32": "IR_LED_PWM",
    "GPIO33": "TP_GPIO33", "GPIO34": NC, "GPIO35": "BOOT", "GPIO36": NC, "GPIO37": "UART0_TX", "GPIO38": "UART0_RX",
    "GPIO39": "SD_D0", "GPIO40": "SD_D1", "GPIO41": "SD_D2", "GPIO42": "SD_D3", "GPIO43": "SD_CLK", "GPIO44": "SD_CMD",
    "GPIO45": "SD_DET", "GPIO46": NC, "GPIO47": NC, "GPIO48": NC,
    "GPIO49": "MDM_RXD", "GPIO50": "MDM_TXD", "GPIO51": "MDM_RTS", "GPIO52": "MDM_CTS", "GPIO53": "MDM_STATUS",
    "GPIO54": "MDM_DTR"})
# decoupling (HDG checklist sec. 1)
for net in ["3V3"] * 7:
    s.C("100n", net)
s.C("10u", "3V3", size="0603", v="10V"); s.C("10u", "3V3", size="0603", v="10V")
s.C("10u", "3V3", size="0603", v="10V")                              # VDD_BAT bulk
for _ in range(4):
    s.C("100n", "VDD_HP")
s.C("10u", "VDD_HP", size="0603", v="10V")
s.C("1u", "VDD_FLASH"); s.C("100n", "VDD_FLASH")
s.C("1u", "VDD_PSRAM"); s.C("100n", "VDD_PSRAM"); s.C("100n", "VDD_PSRAM"); s.C("1u", "VDD_PSRAM")
s.C("1u", "VDD_MIPI"); s.C("100n", "VDD_MIPI"); s.C("10n", "VDD_MIPI")
s.C("1u", "VDDO_4")
s.C("100n", "1V8_IO6"); s.C("1u", "1V8_IO6")
s.R("4.02k", "CSI_REXT", "GND")
# core DC-DC (TLV62569, HDG fig. 5)
s.group()
s.add("U7", "Regulator_Switching:TLV62569DBV", "TLV62569", "Package_TO_SOT_SMD:SOT-23-5", LCSC="C141836",
      MPN="TLV62569DBVR").wire({"VIN": "3V3", "EN": "EN_DCDC", "GND": "GND", "SW": "HP_SW", "FB": "FB_DCDC"})
s.C("4.7u", "3V3", size="0603", v="10V")
s.L("2.2uH", "HP_SW", "VDD_HP", "Inductor_SMD:L_1008_2520Metric", LCSC="C5832372", MPN="FTC252012S2R2MBCA")
s.R("499k", "VDD_HP", "FB_DCDC"); s.R("499k", "FB_DCDC", "GND"); s.C("22p", "VDD_HP", "FB_DCDC")
s.C("22u", "VDD_HP", size="0805", v="10V")
s.flag("VDD_HP")
# flash with 0R tuning pads
s.group()
s.add("U2", "Memory_Flash:W25Q128JVS", "W25Q128JVSIQ", "Package_SO:SOIC-8_5.3x5.3mm_P1.27mm", LCSC="C97521",
      MPN="W25Q128JVSIQ").wire({"~{CS}": "FL_CS", "DO/IO_{1}": "FL_Q", "~{WP}/IO_{2}": "FL_WP", "DI/IO_{0}": "FL_D",
                                "CLK": "FL_CK", "~{HOLD}/~{RESET}/IO_{3}": "FL_HOLD", "VCC": "VDD_FLASH", "GND": "GND"})
for sig in ("CS", "Q", "WP", "HOLD", "CK", "D"):
    s.R("0", f"P4_FL_{sig}", f"FL_{sig}")
s.R("10k", "FL_CS", "VDD_FLASH"); s.C("100n", "VDD_FLASH")
# clocks
s.group()
s.add("Y1", "Device:Crystal_GND24", "40MHz 10ppm", "Crystal:Crystal_SMD_3225-4Pin_3.2x2.5mm", LCSC="C9010",
      MPN="X322540MPB4SI").wire({"1": "XTAL_P", "3": "XTAL_N", "2": "GND", "4": "GND"})
s.C("22p", "XTAL_P"); s.C("22p", "XTAL_N")
s.add("Y2", "Device:Crystal", "32.768kHz", "Crystal:Crystal_SMD_3215-2Pin_3.2x1.5mm", LCSC="C32346",
      MPN="Q13FC13500004").wire({"1": "XTAL32_P", "2": "XTAL32_N"})
s.C("18p", "XTAL32_P"); s.C("18p", "XTAL32_N")
# reset / boot / USB series / MIPI series
s.group()
s.add("U15", "Power_Supervisor:TPS3839DBZ", "TPS3839G33 (3.08V)", "Package_TO_SOT_SMD:SOT-23", LCSC="C485802",
      MPN="TPS3839G33DBZR").wire({"VDD": "3V3", "GND": "GND", "~{RESET}": "SUP_RST"})
s.R("1k", "SUP_RST", "CHIP_PU"); s.R("10k", "CHIP_PU", "3V3"); s.C("100n", "CHIP_PU")
s.add("SW?", "lcsc:TS-1088C-02026", "RESET", "lcsc:SW-SMD_L4.0-W2.9-P4.15-EH", LCSC="C455278",
      MPN="TS-1088C-02026").wire({"1": "CHIP_PU", "2": "GND"})
s.add("SW?", "lcsc:TS-1088C-02026", "BOOT", "lcsc:SW-SMD_L4.0-W2.9-P4.15-EH", LCSC="C455278",
      MPN="TS-1088C-02026").wire({"1": "BOOT", "2": "GND"})
s.R("10k", "BOOT", "3V3")
s.R("22", "P4_USB_DP", "USB_DP"); s.R("22", "P4_USB_DN", "USB_DN")
for lane in ("D0_P", "D0_N", "CK_P", "CK_N", "D1_P", "D1_N"):
    s.R("0", f"P4_CSI_{lane}", f"CSI_{lane}")
for tp in ("UART0_TX", "UART0_RX", "BOOT", "CHIP_PU", "TP_GPIO12", "TP_GPIO13", "TP_GPIO33"):
    s.TP(tp)

# =====================================================================================  WIFI
s = D.sheet("wifi", "Wi-Fi 6 / BLE - ESP32-C6-MINI-1 over SDIO (esp-hosted)")
s.notes += ["SDIO slave pins fixed on the C6 (IO18 CMD, IO19 CLK, IO20-23 D0-D3); P4 side matches ESP32-P4-Function-EV.",
            "Antenna end of the module overhangs / keeps out at the LEFT board edge (see docs/ARCHITECTURE.md sec. 7)."]
u = s.add("U3", "RF_Module:ESP32-C6-MINI-1", "ESP32-C6-MINI-1", "espressif:ESP32-C6-MINI-1", LCSC="C5453904",
          MPN="ESP32-C6-MINI-1-N4", Note="Consigned - zero JLC stock at design time")
u.wire({"GND": "GND", "3V3": "3V3", "NC": NC, "EN": "C6_EN", "IO18": "SDIO_CMD", "IO19": "SDIO_CLK",
        "IO20": "SDIO_D0", "IO21": "SDIO_D1", "IO22": "SDIO_D2", "IO23": "SDIO_D3", "IO9": "C6_BOOT", "IO8": "C6_IO8",
        "IO2": "C6_WAKE", "TXD0": "C6_TXD0", "RXD0": "C6_RXD0", "IO12": "C6_USB_DN", "IO13": "C6_USB_DP",
        "IO0": NC, "IO1": NC, "IO3": NC, "IO4": NC, "IO5": NC, "IO6": NC, "IO7": NC, "IO14": NC, "IO15": NC})
s.C("10u", "3V3", size="0603", v="10V"); s.C("100n", "3V3")
s.R("10k", "C6_EN", "3V3"); s.C("1u", "C6_EN")
s.R("10k", "C6_IO8", "3V3"); s.R("10k", "C6_BOOT", "3V3")
for n in ("SDIO_CMD", "SDIO_D0", "SDIO_D1", "SDIO_D2", "SDIO_D3"):
    s.R("10k", n, "3V3")
for tp in ("C6_TXD0", "C6_RXD0", "C6_EN", "C6_BOOT", "C6_USB_DN", "C6_USB_DP"):
    s.TP(tp)

# =====================================================================================  LTE
s = D.sheet("lte", "LTE Cat-4 + GNSS - SIM7600G-H, nano-SIM, antennas")
s.notes += ["VBAT_LTE from SYS via TPS22965 (16 mOhm). >=300 uF bulk at VBAT pins per SIMCom HW design sec. 3.1 (2 A GSM bursts).",
            "UART/STATUS/DTR are 1.8 V and connect straight to ESP32-P4 GPIO49-54 (VDD_IO_6 = 1V8_IO6).",
            "COEX1/COEX3/BOOT_CFG0 must not be pulled up before power-up -> left NC.  Pi-networks: series 0R, shunts DNP."]
u = s.add("U4", "lcsc:SIM7600G-H_C5355477", "SIM7600G-H", "lcsc:COMM-SMD_135P-L30.0-W30.0_SIM7600G", LCSC="C5355477",
          MPN="SIM7600G-H")
lte_nc = [6, 7, 8, 9, 16, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 44, 45, 46, 47, 48, 50, 51, 52,
          54, 55, 56, 70, 73, 74, 75, 76, 83, 84, 85, 86, 87, 94, 95, 96, 97, 107, 108, 109, 112, 113, 114, 115, 116, 117, 119]
u.wire({str(n): NC for n in lte_nc})
u.wire({"GND": "GND", "VBAT": "VBAT_LTE", "3": "MDM_PWRKEY", "4": "MDM_RESET", "11": "MDM_USB_VBUS", "12": "MDM_USB_DN",
        "13": "MDM_USB_DP", "15": "MDM_1V8", "17": "USIM_DATA", "18": "USIM_RST", "19": "USIM_CLK", "20": "USIM_VDD",
        "42": "MDM_DBG_TXD", "106": "MDM_DBG_RXD", "49": "MDM_STATUS", "53": "USIM_DET", "66": "MDM_RTS", "67": "MDM_CTS",
        "68": "MDM_RXD", "69": "MDM_RI", "71": "MDM_TXD", "72": "MDM_DTR", "59": "ANT_AUX", "79": "ANT_GNSS",
        "82": "ANT_MAIN"})
s.add("C?", "Device:C_Polarized", "220u 6.3V", "Capacitor_Tantalum_SMD:CP_EIA-3528-21_Kemet-B", LCSC="C30242",
      MPN="TLJB227M006R0500").wire({"1": "VBAT_LTE", "2": "GND"})
s.add("C?", "Device:C_Polarized", "220u 6.3V", "Capacitor_Tantalum_SMD:CP_EIA-3528-21_Kemet-B", LCSC="C30242",
      MPN="TLJB227M006R0500").wire({"1": "VBAT_LTE", "2": "GND"})
s.C("10u", "VBAT_LTE", size="0603", v="10V"); s.C("100n", "VBAT_LTE"); s.C("33p", "VBAT_LTE"); s.C("10p", "VBAT_LTE")
s.C("1u", "MDM_1V8"); s.TP("MDM_1V8")
# power switch
s.group()
s.add("U9", "lcsc:TPS22965DSGR", "TPS22965", "lcsc:UDFN-8_L2.0-W2.0-P0.50-TL-EP", LCSC="C122837", MPN="TPS22965DSGR").wire(
    {"VIN": "SYS", "VBIAS": "3V3", "ON": "MODEM_PWR_EN", "GND": "GND", "EP": "GND", "CT": "LTE_CT", "VOUT": "VBAT_LTE"})
s.C("10u", "SYS", size="0805", v="10V"); s.C("1n", "LTE_CT", v="25V"); s.R("100k", "MODEM_PWR_EN", "GND")
# PWRKEY / RESET open-drain drivers
for ctl, tgt in (("MODEM_PWRKEY_CTL", "MDM_PWRKEY"), ("MODEM_RESET_CTL", "MDM_RESET")):
    s.add("Q?", "Transistor_FET:2N7002", "2N7002", "Package_TO_SOT_SMD:SOT-23", LCSC="C8545", MPN="2N7002").wire(
        {"G": ctl, "S": "GND", "D": tgt})
    s.R("100k", ctl, "GND")
s.C("100n", "MDM_PWRKEY", v="16V")
# RI -> LP wake domain
s.add("U16", "Logic_LevelTranslator:SN74LVC1T45DBV", "SN74LVC1T45", "Package_TO_SOT_SMD:SOT-23-6", LCSC="C7843",
      MPN="SN74LVC1T45DBVR").wire({"VCCA": "1V8_IO6", "VCCB": "3V3", "GND": "GND", "A": "MDM_RI", "B": "MODEM_RI_3V3",
                                   "DIR": "1V8_IO6"})
s.R("100k", "MDM_RI", "1V8_IO6"); s.C("100n", "1V8_IO6"); s.C("100n", "3V3")
# USIM
s.group()
s.add("J4", "lcsc:NANOSIM7PH1.37", "Nano-SIM", "lcsc:SIM-SMD_NANO-SIM-7P-H1.37", LCSC="C7529384", MPN="NANO SIM 7P H1.37").wire(
    {"C1": "USIM_VDD", "C2": "SIM_RST", "C3": "SIM_CLK", "C5": "GND", "C6": NC, "C7": "SIM_IO", "CD": "USIM_DET", "GND": "GND"})
s.R("22", "USIM_RST", "SIM_RST"); s.R("22", "USIM_CLK", "SIM_CLK"); s.R("22", "USIM_DATA", "SIM_IO")
s.C("33p", "SIM_RST"); s.C("33p", "SIM_CLK"); s.C("33p", "SIM_IO"); s.C("100n", "USIM_VDD")
s.R("10k", "USIM_DET", "MDM_1V8")
s.add("U18", "Power_Protection:TPD4E05U06DQA", "TPD4E05U06", "Package_SON:USON-10_2.5x1.0mm_P0.5mm", LCSC="C138714",
      MPN="TPD4E05U06DQAR").wire({"1": "SIM_IO", "2": "SIM_CLK", "4": "SIM_RST", "5": "USIM_VDD", "3": "GND", "8": "GND",
                                  "6": NC, "7": NC, "9": NC, "10": NC})
# antennas: pi-match (shunt DNP) -> U.FL
for ant, ref in (("MAIN", "J5"), ("AUX", "J6"), ("GNSS", "J7")):
    s.group()
    s.add(ref, "lcsc:U.FL-R-SMT-1", f"U.FL {ant}", "lcsc:RF-SMD_FRF05002-JSS103M", LCSC="C88374",
          MPN="U.FL-R-SMT-1(80)").wire({"SIG": f"RF_{ant}", "GND": "GND"})
    s.C("DNP", f"ANT_{ant}", dnp=True); s.R("0", f"ANT_{ant}", f"RF_{ant}"); s.C("DNP", f"RF_{ant}", dnp=True)
s.L("47nH", "GNSS_BIAS", "RF_GNSS", "Inductor_SMD:L_0402_1005Metric", dnp=True, LCSC="C27151", MPN="SDCL1005C47NJTDF")
s.R("10", "3V3", "GNSS_BIAS", dnp=True)
for tp in ("MDM_USB_VBUS", "MDM_USB_DP", "MDM_USB_DN", "MDM_DBG_TXD", "MDM_DBG_RXD"):
    s.TP(tp)

# =====================================================================================  CAMERA + IR + PIR
s = D.sheet("camera_ir", "Camera (MIPI CSI-2, 2 lanes), IR illumination, IR-cut filter, PIR")
s.notes += ["J2: 22-pin 0.5 mm FPC, Raspberry Pi CM/Zero camera pinout; lanes 2/3 unused (ESP32-P4 CSI is 2-lane).",
            "IR LEDs: TPS61169 constant-current boost, 4 LEDs in series, I = 0.2 V / 0.68 R = 294 mA, PWM dimming on CTRL.",
            "Board faces the scene: PIR and IR LEDs on the top side next to the camera (front) edge."]
s.add("J2", "lcsc:05B20L22P", "CAM FPC 22P 0.5mm", "lcsc:CONN-SMD_05B20L22P", LCSC="C22459552", MPN="05B20L22P").wire({
    "1": "GND", "2": "CSI_D0_N", "3": "CSI_D0_P", "4": "GND", "5": "CSI_D1_N", "6": "CSI_D1_P", "7": "GND",
    "8": "CSI_CK_N", "9": "CSI_CK_P", "10": "GND", "11": NC, "12": NC, "13": "GND", "14": NC, "15": NC, "16": "GND",
    "17": "CAM_IO0", "18": "CAM_IO1", "19": "GND", "20": "CAM_SCL", "21": "CAM_SDA", "22": "3V3_CAM",
    "23": "GND", "24": "GND"})
s.R("2.2k", "CAM_SCL", "3V3_CAM"); s.R("2.2k", "CAM_SDA", "3V3_CAM")
s.R("10k", "CAM_IO0", "GND"); s.R("10k", "CAM_IO1", "GND", dnp=True)
s.C("10u", "3V3_CAM", size="0603", v="10V"); s.C("100n", "3V3_CAM")
s.add("U10", "lcsc:TPS22918DBVR", "TPS22918", "lcsc:SOT-23-6_L2.9-W1.6-P0.95-LS2.8-BR", LCSC="C131941",
      MPN="TPS22918DBVR").wire({"VIN": "3V3", "GND": "GND", "ON": "CAM_PWR_EN", "CT": "CAM_CT", "QOD": "3V3_CAM",
                                "VOUT": "3V3_CAM"})
s.R("100k", "CAM_PWR_EN", "GND"); s.C("1n", "CAM_CT", v="25V"); s.C("1u", "3V3")
# IR LED driver
s.group()
s.add("U12", "lcsc:TPS61169DCKR", "TPS61169", "lcsc:SC-70-5_L2.1-W1.3-P0.65-LS2.1-BR", LCSC="C71045",
      MPN="TPS61169DCKR").wire({"VIN": "SYS", "GND": "GND", "SW": "IR_SW", "FB": "IR_FB", "CTRL": "IR_LED_PWM"})
s.C("10u", "SYS", size="0805", v="10V")
s.L("10uH", "SYS", "IR_SW", "lcsc:IND-SMD_L4.0-W4.0", LCSC="C38117", MPN="SWPA4030S100MT")
s.add("D?", "Device:D_Schottky", "B5819W", "Diode_SMD:D_SOD-123", LCSC="C8598", MPN="B5819W SL").wire({"A": "IR_SW", "K": "IR_VOUT"})
s.C("4.7u", "IR_VOUT", size="0805", v="25V")
chain = ["IR_VOUT", "IR_K1", "IR_K2", "IR_K3", "IR_FB"]
for i in range(4):
    s.add("D?", "lcsc:M3838E1IRS1G09", "IR 850nm", "lcsc:LED-SMD_3P-L3.8-W3.8_M3838E1IRS1G09", LCSC="C2833567",
          MPN="M3838E1IRS1G09-850NM").wire({"A": chain[i], "C": chain[i + 1], "NC": NC})
s.add("R?", "Device:R", "0.68", "Resistor_SMD:R_0805_2012Metric", LCSC="C47389", MPN="0805W8F680LT5E").wire({"1": "IR_FB", "2": "GND"})
s.R("100k", "IR_LED_PWM", "GND")
# IR-cut filter H-bridge
s.group()
s.add("U13", "Driver_Motor:DRV8837", "DRV8837", "Package_SON:Texas_DSG0008A_WSON-8-1EP_2x2mm_P0.5mm_EP0.9x1.6mm",
      LCSC="C39159", MPN="DRV8837DSGR").wire({"VM": "SYS", "VCC": "3V3", "GND": "GND", "IN1": "IRCUT_IN1", "IN2": "IRCUT_IN2",
                                              "~{SLEEP}": "IRCUT_NSLEEP", "OUT1": "IRCUT_A", "OUT2": "IRCUT_B"})
s.C("10u", "SYS", size="0805", v="10V"); s.C("100n", "SYS", v="16V"); s.C("100n", "3V3")
s.R("100k", "IRCUT_NSLEEP", "GND")
s.add("J9", "Connector_Generic:Conn_01x02", "IR-CUT", "Connector_JST:JST_SH_SM02B-SRSS-TB_1x02-1MP_P1.00mm_Horizontal",
      LCSC="C160402", MPN="SM02B-SRSS-TB(LF)(SN)").wire({"1": "IRCUT_A", "2": "IRCUT_B"})
# PIR
s.group()
s.add("U19", "lcsc:PIR223D-S0", "XYC-PIR223D-S0", "lcsc:TO-5-3_L8.2-W8.2", LCSC="C2887901", MPN="XYC-PIR223D-S0").wire(
    {"VDD": "PIR_VDD", "REL": "PIR_OUT", "VSS": "GND"})
s.R("100", "3V3", "PIR_VDD"); s.flag("PIR_VDD"); s.C("4.7u", "PIR_VDD", size="0603", v="10V"); s.C("100n", "PIR_VDD")

# =====================================================================================  STORAGE
s = D.sheet("storage", "microSD (SDMMC slot 0, 4-bit, 3.3 V) with power switch")
s.notes += ["SDMMC slot 0 fixed pins GPIO39-44; VDD_IO_5 at 3.3 V (no UHS-I). Pull-ups go to the switched rail 3V3_SD."]
s.add("J3", "lcsc:TF-01A", "microSD", "lcsc:TF-SMD_TF-01A", LCSC="C91145", MPN="TF-01A").wire(
    {"1": "SD_D2", "2": "SD_D3", "3": "SD_CMD", "4": "3V3_SD", "5": "SD_CLK_C", "6": "GND", "7": "SD_D0", "8": "SD_D1",
     "9": "SD_DET", "GND": "GND"})
s.R("22", "SD_CLK", "SD_CLK_C"); s.C("DNP", "SD_CLK_C", dnp=True)
for n in ("SD_CMD", "SD_D0", "SD_D1", "SD_D2", "SD_D3"):
    s.R("10k", n, "3V3_SD")
s.R("10k", "SD_DET", "3V3")
s.C("10u", "3V3_SD", size="0603", v="10V"); s.C("100n", "3V3_SD")
s.add("U11", "lcsc:TPS22918DBVR", "TPS22918", "lcsc:SOT-23-6_L2.9-W1.6-P0.95-LS2.8-BR", LCSC="C131941",
      MPN="TPS22918DBVR").wire({"VIN": "3V3", "GND": "GND", "ON": "SD_PWR_EN", "CT": "SD_CT", "QOD": "3V3_SD",
                                "VOUT": "3V3_SD"})
s.R("100k", "SD_PWR_EN", "GND"); s.C("1n", "SD_CT", v="25V"); s.C("1u", "3V3")

if __name__ == "__main__":
    problems = D.check()
    for m in problems:
        print("CHECK:", m)
    D.write(ROOT)
    n = sum(len(s.parts) for s in D.sheets)
    print(f"wrote {len(D.sheets)} sheets, {n} parts")
