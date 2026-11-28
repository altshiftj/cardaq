# ESP32 hub carrier header

The owner identified this ESP32-WROOM-32 carrier using the 30-pin development-board pinout and module note in `hardware/docs`. All GPIOs proposed for the hub appear on that header. The carrier manufacturer, PCB revision, regulator and USB/VIN power circuit still need identification. [Board pinout image](docs/ESP32-Pinout.png) · [Module identification](docs/ESP32-WROOM-32_Module.md) · [Espressif module pad functions, table 2](docs/esp32-wroom-32_datasheet_en.pdf#page=8)

## Find a header contact

Look at the **component side, antenna at the top and USB connector at the bottom**. Count down each 15-contact row starting at the antenna. `L01` and `R01` refer to that view throughout this package. They are CarDAQ position labels. Espressif uses a separate pad numbering system for the metal-can module soldered onto the carrier.

| Left position | Board marking | CarDAQ use | Right position | Board marking | CarDAQ use |
| --- | --- | --- | --- | --- | --- |
| L01 | EN | Enable, unused by harness | R01 | D23 | GPIO23 · SPI SDIO, bidirectional |
| L02 | VP | — | R02 | D22 | GPIO22 · mux B |
| L03 | VN | — | R03 | TX0 | — |
| L04 | D34 | GPIO34 · J5 microphone ADC1_CH6 | R04 | RX0 | — |
| L05 | D35 | GPIO35 · J6 microphone ADC1_CH7 | R05 | D21 | GPIO21 · mux A |
| L06 | D32 | — | R06 | D19 | GPIO19 · MISO for four-wire bench leads |
| L07 | D33 | — | R07 | D18 | GPIO18 · SPI clock |
| L08 | D25 | GPIO25 · J3 chip select | R08 | D5 | — |
| L09 | D26 | GPIO26 · J4 chip select | R09 | TX2 | — |
| L10 | D27 | GPIO27 · mux inhibit | R10 | RX2 | — |
| L11 | D14 | GPIO14 · J2 chip select | R11 | D4 | — |
| L12 | D12 | — | R12 | D2 | — |
| L13 | D13 | GPIO13 · J1 chip select | R13 | D15 | — |
| L14 | GND | Carrier ground | R14 | GND | Carrier ground |
| L15 | VIN | Proposed regulated 5 V hub input | R15 | 3V3 | 3.3 V rail for proposed sensor distribution |

On the supplied pinout the right-side GPIO21/22 headers also carry the default SDA/SCL aliases. The switched hub uses those GPIOs for digital mux selection. GPIO34 and GPIO35 are input-only ADC1 pins. Each microphone's OUT reaches its ADC pin through the hub's 4.7 kΩ series resistor, with a 10 kΩ resistor and 10 nF capacitor to ground at the ADC node. [Standard hub schematic](schematic/standard-hub.pdf)

## Before powering the hub

Match the physical board's VIN, 3V3, GND, D34 and D23 markings to the drawing in this orientation. The **3.0–3.6 V** supply specification applies to the WROOM-32 module. The proposed regulated 5 V branch from the VIOFO HK4 distribution goes to carrier VIN after checking the carrier supply circuit. Keep programming USB disconnected during that test. Establish whether VIN can backfeed USB VBUS and check the regulator rating before using both sources together. Measure the 3.3 V rail under sensor load with Wi-Fi active. Repeat the header and power checks for the other two hubs when their boards are selected. [Bench checkout](bench.md) · [Espressif module operating conditions, table 5](docs/esp32-wroom-32_datasheet_en.pdf#page=15)
