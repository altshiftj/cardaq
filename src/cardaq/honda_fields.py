# SPDX-License-Identifier: CC-BY-SA-4.0
"""Honda Civic field mappings adapted from OBDb/Honda-Civic. See THIRD_PARTY_NOTICES.md."""

# Each tuple gives the byte offset after the DID, the width in bytes and the additive adjustment.
HONDA_FIELDS = {
    b"222301": {
        "honda_vehicle_speed_kph": (4, 1, 0),
        "honda_engine_speed_rpm": (7, 2, 0),
        "candidate_drive_pulley_rpm": (9, 2, 0),
        "candidate_driven_pulley_rpm": (11, 2, 0),
        "candidate_honda_manifold_pressure_kpa": (22, 1, 0),
        "candidate_honda_barometric_pressure_kpa": (24, 1, 0),
        "candidate_cvt_fluid_temperature_sensor_raw": (25, 1, 0),
        "candidate_cvt_fluid_temperature_c": (26, 1, -40),
    },
    b"222322": {
        "honda_vehicle_speed_kph": (4, 1, 0),
        "candidate_secondary_shaft_1_rpm": (9, 2, 0),
        "candidate_torque_converter_turbine_rpm": (13, 2, 0),
        "candidate_secondary_shaft_2_rpm": (15, 2, 0),
    },
}
