# ESP32-WROOM-32 Module

## Overview
The ESP32-WROOM-32 is a Wi-Fi and Bluetooth-enabled microcontroller
module manufactured by Espressif. It integrates an ESP32 SoC,
flash memory, crystal oscillator, and RF matching circuitry.

This module is commonly used on ESP32 development boards and
is fully supported by PlatformIO and the Arduino framework.

## Key Features
- Dual-core Xtensa LX6 CPU (up to 240 MHz)
- Integrated 2.4 GHz Wi-Fi (802.11 b/g/n)
- Bluetooth v4.2 (Classic + BLE)
- 4 MB SPI flash (typical)
- Operating voltage: 3.3V
- Integrated PCB antenna (or U.FL connector on 32U variants)

## Variants
| Variant | Antenna Type |
|------|-------------|
| ESP32-WROOM-32 | PCB antenna | <-- Current project uses this variant
| ESP32-WROOM-32D | PCB antenna (newer revision) |
| ESP32-WROOM-32U | External antenna (U.FL) |

All variants are software-compatible.

## Electrical Characteristics
- Supply voltage: 3.0 – 3.6 V
- Logic level: 3.3 V
- GPIO pins are NOT 5V tolerant

## Interfaces
- Wi-Fi
- Bluetooth / BLE
- UART
- SPI
- I²C
- I²S
- PWM
- ADC
- DAC
- Touch sensors

## Default ESP32 I²C Pins
- SDA: GPIO 21
- SCL: GPIO 22

## Programming & Toolchain
- PlatformIO board ID: `esp32dev`
- Supported frameworks:
  - Arduino
  - ESP-IDF

## Notes
- Some boards require holding the BOOT button during firmware upload
- Power stability is critical when using Wi-Fi
- Espressif specifies at least 500 mA of supply capacity at the module's 3.3 V rail. For the HK4 budget, measure each complete hub at its 5 V input with sensors and Wi-Fi active. [Espressif operating conditions, table 5](esp32-wroom-32_datasheet_en.pdf#page=15)
