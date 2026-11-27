# Automatic vehicle identity

Managed filenames currently encode UTC time and a random recording ID. A note or an explicit profile can describe a trip, but neither identifies the connected vehicle. Standard CAN OBD service 09 PID 02 supplies a 17-character VIN across three ISO-TP frames. Multiple controllers may respond. [ELM327 multi-line responses](https://www.elmelectronics.com/wp-content/uploads/2016/07/ELM327DSH.pdf)

Public VIN patterns identify the two vehicle models in this library. A complete VIN distinguishes individual cars within each pattern. [2020 Civic, Indiana](https://vpic.nhtsa.dot.gov/api/vehicles/DecodeVinValues/19XFC2F6*L?format=json) · [2020 Civic, Canada](https://vpic.nhtsa.dot.gov/api/vehicles/DecodeVinValues/2HGFC2F6*L?format=json) · [2021 RAV4](https://vpic.nhtsa.dot.gov/api/vehicles/DecodeVinValues/JTMP1RFV*M?format=json)
