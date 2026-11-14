"""The mcu-hil v2 circuit: shared sheets plus the CM4/CM5 carrier and Pi HAT top levels.

Net names: Pi-side signals are named for their job (GPIO in docs/v2-pinmap.md); DUT-side signals are
named for the 16U2 pin (DUT_PB1, DUT_PD7, ...). Power: +5V (board 5 V), +3V3 (Pi/CM 3.3 V),
DUT_5V (switched DUT supply, before the shunt), DUT_VCC (after the shunt: the MCU only).

Population options: "CLK" clock override, "SI" Si5351 clock generator, "HV" high-voltage programming.
HV needs CLK (HVPP clocks XTAL1 through the clock buffer).
"""

from __future__ import annotations

from .core import NC, Part, Sheet

# ------------------------------------------------------------------------------------------- catalog
# Basic JLC parts unless noted. Checked with tools/jlc_search.py.
RES = {  # value -> LCSC, all 0402 1%
    "0R": "C17168", "22R": "C25092", "33R": "C25105", "75R": "C25133", "100R": "C25076", "470R": "C25117",
    "1k": "C11702", "1.5k": "C25867", "3.9k": "C51721", "4.7k": "C25900", "5.1k": "C25905",
    "10k": "C25744", "100k": "C25741",
}
CAP = {  # value -> (LCSC, footprint)
    "12p": ("C1547", "C_0402_1005Metric"), "100n": ("C1525", "C_0402_1005Metric"),
    "1n": ("C1523", "C_0402_1005Metric"), "1u": ("C52923", "C_0402_1005Metric"),
    "10u": ("C19702", "C_0603_1608Metric"), "10u/25V": ("C15850", "C_0805_2012Metric"),
    "22u/25V": ("C45783", "C_0805_2012Metric"),
}
LED_RED = dict(lcsc="C2286", mpn="KT-0603R", footprint="LED_SMD:LED_0603_1608Metric")


def R(sh: Sheet, value: str, a: str, b: str, option: str = "", note: str = "") -> Part:
    shown = value[:-1] + "Ω" if value.endswith("R") else value + "Ω"
    return sh.add(Part("Device:R", shown, {"1": a, "2": b},
                       footprint="Resistor_SMD:R_0402_1005Metric", lcsc=RES[value], option=option, note=note))


def C(sh: Sheet, value: str, a: str, b: str = "GND", option: str = "", note: str = "") -> Part:
    lcsc, fp = CAP[value]
    shown = value.replace("u", "µF").replace("n", "nF").replace("p", "pF")
    return sh.add(Part("Device:C", shown, {"1": a, "2": b}, footprint=f"Capacitor_SMD:{fp}", lcsc=lcsc,
                       option=option, note=note))


def LED(sh: Sheet, anode: str, cathode: str, note: str = "", option: str = "") -> Part:
    return sh.add(Part("Device:LED", "Red", {"A": anode, "K": cathode}, note=note, option=option, **LED_RED))


def NMOS(sh: Sheet, d: str, g: str, s: str = "GND", option: str = "", note: str = "") -> Part:
    return sh.add(Part("Transistor_FET:2N7002", "2N7002", {"D": d, "G": g, "S": s}, lcsc="C8545",
                       footprint="Package_TO_SOT_SMD:SOT-23", option=option, note=note))


def TP(sh: Sheet, net: str, note: str = "") -> Part:
    return sh.add(Part("Connector:TestPoint", net, {"1": net}, footprint="TestPoint:TestPoint_Pad_D1.0mm",
                       in_bom=False, note=note))


def FLAG(sh: Sheet, net: str) -> Part:
    return sh.add(Part("power:PWR_FLAG", "PWR_FLAG", {"1": net}, in_bom=False, on_board=False))


# ------------------------------------------------------------------------------------------- sheets
def sheet_dut() -> Sheet:
    sh = Sheet("dut", "DUT: ATmega16U2")
    sh.notes = [
        "ATmega16U2 at 5 V, 16 MHz. DUT_VCC is measured by the power meter; DUT_5V (before the shunt) feeds pull-ups.",
        "Software USB (V-USB): D+ = PC7 (INT4), D- = PC4. 75R series and 3.6 V zeners keep the lines at USB levels.",
        "Reset: the Pi side holds RESET low by default (pi_io sheet). The diode keeps 12 V (HVPP) off DUT_5V.",
    ]
    sh.add(Part("MCU_Microchip_ATmega:ATmega16U2-A", "ATmega16U2-AU", {
        "XTAL1": "DUT_XTAL1", "2": "DUT_XTAL2", "GND": "GND", "UGND": "GND",
        "VCC": "DUT_VCC", "AVCC": "DUT_VCC", "UVCC": "DUT_VCC", "UCAP": "DUT_UCAP",
        "D+": "DUT_DP_PIN", "D-": "DUT_DM_PIN",
        "PB0": "DUT_PB0", "PB1": "DUT_PB1", "PB2": "DUT_PB2", "PB3": "DUT_PB3",
        "PB4": "DUT_PB4", "PB5": "DUT_PB5", "PB6": "DUT_PB6", "PB7": "DUT_PB7",
        "PD0": "DUT_PD0", "PD1": "DUT_PD1", "PD2": "DUT_PD2", "PD3": "DUT_PD3", "PD4": "DUT_PD4",
        "PD5": "DUT_PD5", "PD6": "DUT_PD6", "13": "DUT_PD7",
        "24": "DUT_RESET", "PC2": "DUT_PC2", "PC4": "SWUSB_DM_PIN", "PC5": "DUT_PC5",
        "PC6": "DUT_PC6", "PC7": "SWUSB_DP_PIN",
    }, footprint="Package_QFP:TQFP-32_7x7mm_P0.8mm", lcsc="C59019", mpn="ATMEGA16U2-AU"))
    for _ in range(3):
        C(sh, "100n", "DUT_VCC")
    C(sh, "10u", "DUT_VCC")
    C(sh, "1u", "DUT_UCAP", note="UCAP: USB regulator output")
    sh.add(Part("Device:Crystal_GND24", "16MHz", {"1": "DUT_XTAL1", "3": "DUT_XTAL2", "2": "GND", "4": "GND"},
                footprint="Crystal:Crystal_SMD_3225-4Pin_3.2x2.5mm", lcsc="C13738", mpn="X322516MLB4SI"))
    C(sh, "12p", "DUT_XTAL1")
    C(sh, "12p", "DUT_XTAL2")
    R(sh, "22R", "DUT_DP_PIN", "DUT_USB_DP")
    R(sh, "22R", "DUT_DM_PIN", "DUT_USB_DM")
    # Software USB.
    R(sh, "75R", "SWUSB_DP_PIN", "SWUSB_DP", note="V-USB series resistor (68R in the reference; 75R is a no-fee JLC part)")
    R(sh, "75R", "SWUSB_DM_PIN", "SWUSB_DM")
    for net in ("SWUSB_DP", "SWUSB_DM"):
        sh.add(Part("Device:D_Zener", "3.6V", {"K": net, "A": "GND"}, footprint="Diode_SMD:D_SOD-123",
                    lcsc="C173412", mpn="BZT52C3V6"))
    R(sh, "1.5k", "SWUSB_DM", "DUT_5V", note="Low-speed attach pull-up on D-")
    # Reset pull-up path with reset LED (lit while reset is asserted).
    sh.add(Part("Diode:1N4148W", "1N4148W", {"A": "DUT_5V", "K": "RST_PU"}, lcsc="C81598",
                footprint="Diode_SMD:D_SOD-123", note="Blocks 12 V on RESET from DUT_5V"))
    R(sh, "10k", "RST_PU", "DUT_RESET")
    LED(sh, "RST_PU", "RST_LED_K", note="Reset asserted")
    R(sh, "1k", "RST_LED_K", "DUT_RESET")
    R(sh, "10k", "DUT_PD7", "DUT_5V", note="HWB idle high: no DFU unless the Pi asserts HWB")
    for net in ("DUT_PC2", "DUT_PC5", "DUT_PD0"):
        TP(sh, net, note="Spare DUT pin")
    return sh


def sheet_pi_io() -> Sheet:
    sh = Sheet("pi_io", "Pi to DUT: level translators, reset, HWB")
    sh.notes = [
        "Translators: A side on +3V3 (Pi), B side on DUT_5V, so they go Hi-Z (Ioff) whenever the DUT is off.",
        "Every enable defaults off through an external pull-down (docs/v2-pinmap.md).",
        "RESET: Q2 off (GPIO12 low, default) lets RST_GATE rise with DUT_5V, so Q1 holds RESET low.",
    ]
    sh.add(Part("mcu-hil:TXU0304", "TXU0304PWR", {
        "VCCA": "+3V3", "VCCB": "DUT_5V", "GND": "GND", "OE": "ISP_OE",
        "A1": "ISP_MOSI", "B1": "DUT_PB2", "A2": "ISP_SCK", "B2": "DUT_PB1",
        "A3": "GND", "B3": NC, "B4": "DUT_PB3", "A4": "ISP_MISO",
    }, lcsc="C4364118"))
    C(sh, "100n", "+3V3")
    C(sh, "100n", "DUT_5V")
    sh.add(Part("mcu-hil:TXU0202", "TXU0202DCUR", {
        "VCCA": "+3V3", "VCCB": "DUT_5V", "GND": "GND", "OE": "UART_OE",
        "A1": "PI_TXD", "B1": "DUT_PD2", "B2": "DUT_PD3", "A2": "PI_RXD",
    }, lcsc="C5186957"))
    C(sh, "100n", "+3V3")
    C(sh, "100n", "DUT_5V")
    R(sh, "100k", "ISP_OE", "GND")
    R(sh, "100k", "UART_OE", "GND")
    R(sh, "100k", "ISP_MOSI", "GND", note="Keeps translator inputs defined while the Pi pin is an input")
    R(sh, "100k", "ISP_SCK", "GND")
    R(sh, "100k", "DUT_PB3", "GND")
    R(sh, "100k", "PI_TXD", "+3V3", note="UART idle high")
    R(sh, "100k", "DUT_PD3", "DUT_5V", note="UART idle high")
    # Reset: Q1 pulls RESET low unless the Pi releases it.
    NMOS(sh, "DUT_RESET", "RST_GATE", note="Rated 60 V, safe with 12 V on RESET")
    R(sh, "100k", "RST_GATE", "DUT_5V")
    NMOS(sh, "RST_GATE", "RESET_RELEASE")
    R(sh, "100k", "RESET_RELEASE", "GND")
    # HWB (PD7) assert.
    NMOS(sh, "DUT_PD7", "HWB_ASSERT")
    R(sh, "100k", "HWB_ASSERT", "GND")
    return sh


def sheet_clock() -> Sheet:
    sh = Sheet("clock", "Clock override (option CLK) and Si5351 (option SI)")
    sh.notes = [
        "Two tri-state buffers drive XTAL1 over the crystal: GPCLK0 (GPIO4, enable GPIO18) or Si5351 CLK0",
        "(enable GPIO27). Both default off. Software must never enable both. HVPP pulses XTAL1 through U(GPCLK0).",
    ]
    for src, oe, opt in (("GPCLK0", "CLK_OE", "CLK"), ("SI_CLK0", "SI_CLK_OE", "SI")):
        sh.add(Part("74xGxx:74LVC1G126", "SN74LV1T126DBVR", {"1": oe, "2": src, "3": "GND", "4": f"{src}_BUF",
                                                             "5": "DUT_5V"},
                    footprint="Package_TO_SOT_SMD:SOT-23-5", lcsc="C2440228", option=opt,
                    note="TTL inputs: 3.3 V is a valid high at VCC = 5 V"))
        C(sh, "100n", "DUT_5V", option=opt)
        R(sh, "33R", f"{src}_BUF", "DUT_XTAL1", option=opt)
        R(sh, "100k", oe, "GND", option=opt)
    R(sh, "100k", "GPCLK0", "GND", option="CLK", note="Defined input while GPIO4 is an input")
    sh.add(Part("Oscillator:Si5351A-B-GT", "Si5351A-B-GTR", {
        "VDD": "+3V3", "VDDO": "+3V3", "GND": "GND", "XA": "SI_XA", "XB": "SI_XB",
        "SCL": "I2C_SCL", "SDA": "I2C_SDA", "CLK0": "SI_CLK0", "CLK1": "SI_CLK1", "CLK2": "SI_CLK2",
    }, lcsc="C504891", option="SI", ref_prefix="U"))
    C(sh, "100n", "+3V3", option="SI")
    C(sh, "100n", "+3V3", option="SI")
    sh.add(Part("Device:Crystal_GND24", "25MHz", {"1": "SI_XA", "3": "SI_XB", "2": "GND", "4": "GND"},
                footprint="Crystal:Crystal_SMD_3225-4Pin_3.2x2.5mm", lcsc="C448646", mpn="NX3225SA-25MHZ",
                option="SI", note="CL 10 pF; the Si5351 has internal load capacitance"))
    TP(sh, "SI_CLK1", note="Spare clock for a second DUT")
    TP(sh, "SI_CLK2", note="Spare clock")
    return sh


def sheet_dut_power() -> Sheet:
    sh = Sheet("dut_power", "DUT power switch and power meter")
    sh.notes = [
        "TPS22918: off by default (GPIO22 pull-down), set slew (CT), quick output discharge (QOD tied to VOUT).",
        "INA226 measures DUT_VCC (the MCU only) across the 1 ohm shunt: 81.9 mA full scale, 2.5 uA steps.",
        "INA228 (20-bit, same footprint and pinout) is a drop-in upgrade when JLC has stock: 164 mA, 0.3 uA steps.",
    ]
    sh.add(Part("mcu-hil:TPS22918DBV", "TPS22918DBVR", {
        "VIN": "+5V", "GND": "GND", "ON": "DUT_PWR_EN", "CT": "DUT_PWR_CT", "QOD": "DUT_5V", "VOUT": "DUT_5V",
    }, lcsc="C131941"))
    C(sh, "1u", "+5V")
    C(sh, "1n", "DUT_PWR_CT", note="Rise-time control")
    C(sh, "1u", "DUT_5V")
    R(sh, "100k", "DUT_PWR_EN", "GND")
    sh.add(Part("Device:R", "1Ω", {"1": "DUT_5V", "2": "DUT_VCC"}, footprint="Resistor_SMD:R_0603_1608Metric",
                lcsc="C22936", mpn="0603WAF100KT5E", note="Shunt, 1%"))
    sh.add(Part("Sensor_Energy:INA226", "INA226AIDGSR", {
        "A0": "GND", "A1": "GND", "~{Alert}": "PWR_ALERT", "SDA": "I2C_SDA", "SCL": "I2C_SCL",
        "VS": "+3V3", "GND": "GND", "Vbus": "DUT_VCC", "Vin-": "DUT_VCC", "Vin+": "DUT_5V",
    }, footprint="Package_SO:MSOP-10_3x3mm_P0.5mm", lcsc="C49851", note="I2C address 0x40"))
    C(sh, "100n", "+3V3")
    R(sh, "10k", "PWR_ALERT", "+3V3")
    FLAG(sh, "DUT_VCC")
    return sh


def sheet_hv() -> Sheet:
    sh = Sheet("hv", "High-voltage programming (option HV)")
    sh.notes = [
        "12 V boost (MT3608, GPIO26) and a switch that puts it on RESET (GPIO25). Both default off.",
        "FB divider 100k/5.1k: 12.36 V nominal. The 1k series resistor drops about 0.25 V at the 250 uA RESET current,",
        "so RESET sees 11.9-12.4 V (spec 11.5-12.5 V).",
        "TCA6416A: VCCP on +5V (always up before +3V3, as TI recommends). ~RESET is pulled up to DUT_5V, so the",
        "expander's ports are held as inputs (Hi-Z) whenever the DUT is off. I2C address 0x20.",
        "HVPP map (16U2 table 25-9): P0 = PB0-7 data; P10 PD1 RDY/BSY, P11 PD2 OE, P12 PD3 WR, P13 PD4 BS1,",
        "P14 PD5 XA0, P15 PD6 XA1, P16 PD7 PAGEL, P17 PC6 BS2.",
    ]
    hv = "HV"
    sh.add(Part("Regulator_Switching:MT3608", "MT3608", {
        "IN": "+5V", "GND": "GND", "EN": "HV_BOOST_EN", "SW": "HV_SW", "FB": "HV_FB",
    }, lcsc="C84817", option=hv))
    sh.add(Part("Device:L", "10µH", {"1": "+5V", "2": "HV_SW"}, footprint="mcu-hil:L_Sunlord_SWPA4030",
                lcsc="C38117", mpn="SWPA4030S100MT", option=hv))
    sh.add(Part("Device:D_Schottky", "B5819W", {"A": "HV_SW", "K": "HV_12V"}, footprint="Diode_SMD:D_SOD-123",
                lcsc="C8598", option=hv))
    R(sh, "100k", "HV_12V", "HV_FB", option=hv)
    R(sh, "5.1k", "HV_FB", "GND", option=hv)
    C(sh, "10u", "+5V", option=hv)
    C(sh, "10u/25V", "HV_12V", option=hv)
    C(sh, "10u/25V", "HV_12V", option=hv)
    R(sh, "100k", "HV_BOOST_EN", "GND", option=hv)
    sh.add(Part("Transistor_FET:AO3401A", "AO3401A", {"S": "HV_12V", "G": "HV_GATE", "D": "HV_OUT"},
                lcsc="C15127", option=hv, note="Gate divider limits VGS to -6 V"))
    R(sh, "10k", "HV_12V", "HV_GATE", option=hv)
    R(sh, "10k", "HV_GATE", "HV_PULL", option=hv)
    NMOS(sh, "HV_PULL", "HV_APPLY", option=hv)
    R(sh, "100k", "HV_APPLY", "GND", option=hv)
    R(sh, "1k", "HV_OUT", "DUT_RESET", option=hv)
    FLAG(sh, "HV_12V")
    ports = {f"P0{i}": f"DUT_PB{i}" for i in range(8)}
    ports.update({"P10": "DUT_PD1", "P11": "DUT_PD2", "P12": "DUT_PD3", "P13": "DUT_PD4",
                  "P14": "DUT_PD5", "P15": "DUT_PD6", "P16": "DUT_PD7", "P17": "DUT_PC6"})
    sh.add(Part("mcu-hil:TCA6416A_RTW", "TCA6416ARTWR", {
        "VCCI": "+3V3", "VCCP": "+5V", "GND": "GND", "EP": "GND", "ADDR": "GND",
        "SCL": "I2C_SCL", "SDA": "I2C_SDA", "~{INT}": "HV_EXP_INT", "~{RESET}": "HV_EXP_RST", **ports,
    }, lcsc="C182336", option=hv))
    C(sh, "100n", "+3V3", option=hv)
    C(sh, "100n", "+5V", option=hv)
    R(sh, "10k", "HV_EXP_RST", "DUT_5V", option=hv)
    R(sh, "10k", "HV_EXP_INT", "+3V3", option=hv)
    TP(sh, "HV_EXP_INT")
    return sh


def sheet_usb(carrier: bool) -> Sheet:
    sh = Sheet("usb", "USB path switch")
    if carrier:
        sh.notes = [
            "USB_S0 (GPIO20) low: CM USB to the USB-C port (rpiboot; CM is a device). High: to the DUT side, and",
            "Q pulls USB_OTG_ID low so the CM becomes the host. USB_S1 (GPIO21): low = 16U2 hardware USB, high = software USB.",
        ]
        sw1 = {"D+": "CM_USB_DP", "D-": "CM_USB_DM", "1D+": "USBC_DP", "1D-": "USBC_DM",
               "2D+": "SW2_DP", "2D-": "SW2_DM", "S": "USB_S0"}
        sw2 = {"D+": "SW2_DP", "D-": "SW2_DM", "1D+": "DUT_USB_DP", "1D-": "DUT_USB_DM",
               "2D+": "SWUSB_DP", "2D-": "SWUSB_DM", "S": "USB_S1"}
        switches = [sw1, sw2]
    else:
        sh.notes = ["USB_S0 (GPIO20) low: the loopback USB-C port to the 16U2 hardware USB. High: to software USB."]
        switches = [{"D+": "HAT_USB_DP", "D-": "HAT_USB_DM", "1D+": "DUT_USB_DP", "1D-": "DUT_USB_DM",
                     "2D+": "SWUSB_DP", "2D-": "SWUSB_DM", "S": "USB_S0"}]
    for sw in switches:
        sh.add(Part("mcu-hil:TS3USB221A", "TS3USB221ARSER", {"VCC": "+3V3", "GND": "GND", "~{OE}": "GND", **sw},
                    lcsc="C128396"))
        C(sh, "100n", "+3V3")
    R(sh, "100k", "USB_S0", "GND")
    if carrier:
        R(sh, "100k", "USB_S1", "GND")
        NMOS(sh, "CM_USB_OTG_ID", "USB_S0", note="Host mode whenever the DUT side is selected")
    return sh


# ------------------------------------------------------------------------------------------- carrier
CM_GPIO = {
    "GPIO2": "I2C_SDA", "GPIO3": "I2C_SCL", "GPIO4": "GPCLK0", "GPIO9": "ISP_MISO", "GPIO10": "ISP_MOSI",
    "GPIO11": "ISP_SCK", "GPIO12": "RESET_RELEASE", "GPIO13": "HWB_ASSERT", "GPIO14": "PI_TXD",
    "GPIO15": "PI_RXD", "GPIO16": "ISP_OE", "GPIO17": "UART_OE", "GPIO18": "CLK_OE", "GPIO19": "PWR_ALERT",
    "GPIO20": "USB_S0", "GPIO21": "USB_S1", "GPIO22": "DUT_PWR_EN", "GPIO24": "STATUS_LED",
    "GPIO25": "HV_APPLY", "GPIO26": "HV_BOOST_EN", "GPIO27": "SI_CLK_OE",
}


def _cm_nets(csv_rows, conn: str) -> dict[str, str]:
    special = {
        "GND": "GND", "+5V (Input)": "+5V", "CM4_3.3V (Output)": "+3V3", "GPIO_VREF": "+3V3",
        "Ethernet_Pair0_P": "ETH_0P", "Ethernet_Pair0_N": "ETH_0N", "Ethernet_Pair1_P": "ETH_1P",
        "Ethernet_Pair1_N": "ETH_1N", "Ethernet_Pair2_P": "ETH_2P", "Ethernet_Pair2_N": "ETH_2N",
        "Ethernet_Pair3_P": "ETH_3P", "Ethernet_Pair3_N": "ETH_3N",
        "Ethernet_nLED2": "ETH_nLED_SPEED", "Ethernet_nLED3": "ETH_nLED_ACT",
        "USB_P": "CM_USB_DP", "USB_N": "CM_USB_DM", "USB_OTG_ID": "CM_USB_OTG_ID",
        "SD_CLK": "SD_CLK", "SD_CMD": "SD_CMD", "SD_DAT0": "SD_DAT0", "SD_DAT1": "SD_DAT1",
        "SD_DAT2": "SD_DAT2", "SD_DAT3": "SD_DAT3", "SD_PWR_ON": "SD_PWR_ON",
        "nRPIBOOT": "nRPIBOOT", "Pi_nLED_Activity": "LED_nACT", "RUN_PG": "CM_RUN_PG",
        "GLOBAL_EN": "CM_GLOBAL_EN",
        **CM_GPIO,
    }
    out = {}
    for r in csv_rows:
        if r["connector"] != conn:
            continue
        out[r["pin"]] = special.get(r["cm4_name"], NC)
    return out


def sheet_cm(csv_rows) -> list[Sheet]:
    sh = Sheet("cm", "Compute Module 4/5 connectors", paper="A2")
    sh.notes = [
        "Hirose DF40C-100DS-0.4V(51), 1.5 mm stack. CM4 and CM5 share every pin used here.",
        "GPIO_VREF to +3V3 (3.3 V GPIO). ID_SD/ID_SC, GLOBAL_EN/PMIC_EN, EEPROM_nWP and the 1.8 V outputs are unused.",
        "CM5's USB-C CC pins (94/96) are left open: the carrier's own 5.1k Rd works for both CM4 and CM5",
        "(CM5 then runs without 5 A PD negotiation).",
    ]
    for conn in ("J1A", "J1B"):
        sh.add(Part(f"mcu-hil:CM4_CM5_{conn}", f"DF40C-100DS-0.4V(51)", _cm_nets(csv_rows, conn),
                    lcsc="C597931", mpn="DF40C-100DS-0.4V(51)", ref_prefix="J"))
    for net in ("CM_RUN_PG", "CM_GLOBAL_EN"):
        TP(sh, net)
    return [sh]


def sheet_carrier_io() -> Sheet:
    sh = Sheet("carrier_io", "Carrier: USB-C power and rpiboot, Ethernet, microSD, LEDs")
    sh.notes = [
        "USB-C: 5 V input for the whole board and the CM's rpiboot/data port. Rd 5.1k on CC1/CC2 (sink).",
        "Ethernet: 1:1 gigabit MagJack. PHY-side centre tap to GND through 100 nF; LEDs from +3V3 into the CM's open-drain nLED pins.",
        "microSD (CM Lite): SD power through a second TPS22918 switched by SD_PWR_ON (CM4 needs the external pull-up).",
    ]
    sh.add(Part("Connector:USB_C_Receptacle_USB2.0_16P", "TYPE-C-31-M-12", {
        "GND": "GND", "VBUS": "+5V", "CC1": "USBC_CC1", "CC2": "USBC_CC2", "D+": "USBC_DP", "D-": "USBC_DM",
        "SBU1": NC, "SBU2": NC, "SHIELD": "GND",
    }, footprint="Connector_USB:USB_C_Receptacle_HRO_TYPE-C-31-M-12", lcsc="C165948"))
    R(sh, "5.1k", "USBC_CC1", "GND")
    R(sh, "5.1k", "USBC_CC2", "GND")
    sh.add(Part("Power_Protection:USBLC6-2SC6", "USBLC6-2SC6", {
        "1": "USBC_DP", "6": "USBC_DP", "3": "USBC_DM", "4": "USBC_DM", "GND": "GND", "VBUS": "+5V"},
        lcsc="C7519"))
    C(sh, "22u/25V", "+5V")
    C(sh, "22u/25V", "+5V")
    FLAG(sh, "+5V")
    FLAG(sh, "GND")
    # Ethernet.
    sh.add(Part("mcu-hil:HR911130C", "HR911130C", {
        "MDI0+": "ETH_0P", "MDI0-": "ETH_0N", "MDI1+": "ETH_1P", "MDI1-": "ETH_1N",
        "MDI2+": "ETH_2P", "MDI2-": "ETH_2N", "MDI3+": "ETH_3P", "MDI3-": "ETH_3N",
        "TCT": "ETH_TCT", "CHS_GND": "GND", "SHIELD": "GND",
        "LED1_A": "+3V3", "LED1_K": "ETH_LED1_K", "LED2_A": "+3V3", "LED2_K": "ETH_LED2_K",
    }, lcsc="C50933"))
    C(sh, "100n", "ETH_TCT")
    R(sh, "470R", "ETH_LED1_K", "ETH_nLED_ACT")
    R(sh, "470R", "ETH_LED2_K", "ETH_nLED_SPEED")
    # microSD.
    sh.add(Part("mcu-hil:TPS22918DBV", "TPS22918DBVR", {
        "VIN": "+3V3", "GND": "GND", "ON": "SD_PWR_ON", "CT": NC, "QOD": "SD_VDD", "VOUT": "SD_VDD",
    }, lcsc="C131941"))
    R(sh, "10k", "SD_PWR_ON", "+3V3", note="Needed by CM4 to boot from SD")
    C(sh, "10u", "SD_VDD")
    C(sh, "100n", "SD_VDD")
    sh.add(Part("Connector:Micro_SD_Card_Det_Hirose_DM3AT", "DM3AT-SF-PEJM5", {
        "DAT2": "SD_DAT2", "DAT3/CD": "SD_DAT3", "CMD": "SD_CMD", "VDD": "SD_VDD", "CLK": "SD_CLK",
        "VSS": "GND", "DAT0": "SD_DAT0", "DAT1": "SD_DAT1", "DET_A": NC, "DET_B": NC, "SHIELD": "GND",
    }, footprint="Connector_Card:microSD_HC_Hirose_DM3AT-SF-PEJM5", lcsc="C114218"))
    # rpiboot button and LEDs.
    sh.add(Part("Switch:SW_Push", "TS-1187A-B-A-B", {"1": "nRPIBOOT", "2": "GND"},
                footprint="Button_Switch_SMD:SW_Push_1P1T_XKB_TS-1187A", lcsc="C318884",
                note="Hold while powering up to enter rpiboot"))
    LED(sh, "+3V3", "PWR_LED_K", note="Power (CM 3.3 V)")
    R(sh, "1k", "PWR_LED_K", "GND")
    LED(sh, "+3V3", "ACT_LED_K", note="CM activity")
    R(sh, "1k", "ACT_LED_K", "LED_nACT")
    LED(sh, "STATUS_LED_A", "GND", note="Status (GPIO24)")
    R(sh, "1k", "STATUS_LED", "STATUS_LED_A")
    for i in range(4):
        sh.add(Part("Mechanical:MountingHole_Pad", "M2.5", {"1": "GND"},
                    footprint="MountingHole:MountingHole_2.7mm_M2.5_Pad", in_bom=False))
    return sh


# ------------------------------------------------------------------------------------------- HAT
HAT_HEADER = {  # 40-pin header pin -> net
    1: "+3V3", 2: "+5V", 3: "I2C_SDA", 4: "+5V", 5: "I2C_SCL", 6: "GND", 7: "GPCLK0", 8: "PI_TXD",
    9: "GND", 10: "PI_RXD", 11: "UART_OE", 12: "CLK_OE", 13: "SI_CLK_OE", 14: "GND", 15: "DUT_PWR_EN",
    16: NC, 17: "+3V3", 18: "STATUS_LED", 19: "ISP_MOSI", 20: "GND", 21: "ISP_MISO", 22: "HV_APPLY",
    23: "ISP_SCK", 24: NC, 25: "GND", 26: NC, 27: "ID_SD", 28: "ID_SC", 29: NC, 30: "GND", 31: NC,
    32: "RESET_RELEASE", 33: "HWB_ASSERT", 34: "GND", 35: "PWR_ALERT", 36: "ISP_OE", 37: "HV_BOOST_EN",
    38: "USB_S0", 39: "GND", 40: NC,
}


def sheet_hat_io() -> Sheet:
    sh = Sheet("hat_io", "HAT: 40-pin header, ID EEPROM, USB-C loopback, LED")
    sh.notes = [
        "HAT+ rules: ID_SD/ID_SC carry only the EEPROM and 3.9k pull-ups to 3.3 V. EEPROM WP has a 1k pull-up;",
        "bridge JP1 (or drive the test point low) to write it. The HAT never powers the Pi.",
        "USB-C here is a data port only: a short cable back to one of the Pi's USB host ports. Its VBUS is not used.",
        "GPIO2/3 already have ~2k pull-ups on the Pi. STANDBY (5 V up, 3.3 V down) is safe: every enable defaults off.",
    ]
    sh.add(Part("Connector_Generic:Conn_02x20_Odd_Even", "Pi 40-pin", {str(k): v for k, v in HAT_HEADER.items()},
                footprint="Connector_PinSocket_2.54mm:PinSocket_2x20_P2.54mm_Vertical", lcsc="C5124634",
                ref_prefix="J"))
    FLAG(sh, "+5V")
    FLAG(sh, "+3V3")
    FLAG(sh, "GND")
    sh.add(Part("Memory_EEPROM:24LC32", "M24C32-RMN6TP", {
        "A0": "GND", "A1": "GND", "A2": "GND", "GND": "GND", "SDA": "ID_SD", "SCL": "ID_SC",
        "WP": "ID_WP", "VCC": "+3V3"}, footprint="Package_SO:SOIC-8_3.9x4.9mm_P1.27mm", lcsc="C79920",
        note="I2C 0x50. 24LC32 symbol, same SOIC-8 pinout"))
    C(sh, "100n", "+3V3")
    R(sh, "3.9k", "ID_SD", "+3V3")
    R(sh, "3.9k", "ID_SC", "+3V3")
    R(sh, "1k", "ID_WP", "+3V3")
    sh.add(Part("Jumper:SolderJumper_2_Open", "WP", {"A": "ID_WP", "B": "GND"},
                footprint="Jumper:SolderJumper-2_P1.3mm_Open_RoundedPad1.0x1.5mm", in_bom=False,
                note="Bridge to write the ID EEPROM"))
    TP(sh, "ID_WP")
    sh.add(Part("Connector:USB_C_Receptacle_USB2.0_16P", "TYPE-C-31-M-12", {
        "GND": "GND", "VBUS": "HAT_USB_VBUS", "CC1": "HATC_CC1", "CC2": "HATC_CC2",
        "D+": "HAT_USB_DP", "D-": "HAT_USB_DM", "SBU1": NC, "SBU2": NC, "SHIELD": "GND",
    }, footprint="Connector_USB:USB_C_Receptacle_HRO_TYPE-C-31-M-12", lcsc="C165948"))
    R(sh, "5.1k", "HATC_CC1", "GND")
    R(sh, "5.1k", "HATC_CC2", "GND")
    sh.add(Part("Power_Protection:USBLC6-2SC6", "USBLC6-2SC6", {
        "1": "HAT_USB_DP", "6": "HAT_USB_DP", "3": "HAT_USB_DM", "4": "HAT_USB_DM", "GND": "GND",
        "VBUS": "HAT_USB_VBUS"}, lcsc="C7519"))
    LED(sh, "STATUS_LED_A", "GND", note="Status (GPIO24)")
    R(sh, "1k", "STATUS_LED", "STATUS_LED_A")
    for i in range(4):
        sh.add(Part("Mechanical:MountingHole_Pad", "M2.5", {"1": "GND"},
                    footprint="MountingHole:MountingHole_2.7mm_M2.5_Pad", in_bom=False))
    return sh


def shared_sheets(carrier: bool) -> list[Sheet]:
    return [sheet_dut(), sheet_pi_io(), sheet_clock(), sheet_dut_power(), sheet_hv(), sheet_usb(carrier)]


VARIANTS = {"no HV": {"HV"}, "minimal": {"HV", "CLK", "SI"}}
