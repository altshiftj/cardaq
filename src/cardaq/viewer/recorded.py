"""Reading guides for the measurements written directly to a capture CSV."""

# A module name identifies which controller reported a reading. Both controllers
# can report the same underlying vehicle signal.
_STANDARD_GUIDES = {
    "engine_speed_rpm": (
        "Crankshaft revolutions per minute reported by the {module}.",
        "RPM near idle while road speed is zero marks a running stop. At the same cruising speed, "
        "higher RPM means the engine turns more times per kilometer.",
    ),
    "vehicle_speed_kph": (
        "Road speed reported by the {module} in whole kilometers per hour.",
        "A flat stretch marks a steady reported speed. A rising or falling line shows the "
        "car speeding up or slowing down. Small steps reflect the 1 km/h resolution.",
    ),
    "manifold_pressure_kpa": (
        "Absolute air pressure in the intake manifold, as reported by the {module}.",
        "On this Civic, opening the throttle usually brings manifold pressure closer to "
        "barometric pressure. A wider gap between the two means more intake vacuum.",
    ),
    "barometric_pressure_kpa": (
        "Atmospheric pressure reported by the {module}.",
        "A nearly level trace gives you a reference for intake manifold pressure. Elevation "
        "and weather can shift that reference between drives.",
    ),
    "control_module_voltage_v": (
        "Electrical supply voltage reported by the {module}.",
        "Compare key-on, cranking and running readings to see voltage sag and recovery. "
        "A brief starting dip can fall between samples.",
    ),
    "coolant_sensor_1_c": (
        "Engine coolant temperature at sensor 1, reported by the {module}. Both controllers can report this sensor.",
        "The starting value gives warm-up context. Compare the climb to the same temperature "
        "on another trip, especially after a cold soak or preheating.",
    ),
    "coolant_sensor_2_c": (
        "Engine coolant temperature at sensor 2, reported by the {module}. Both controllers can report this sensor.",
        "Compare the two coolant traces during warm-up. If sensor 2 rises later, the gap "
        "shows how much their temperatures differ at that point in the drive.",
    ),
}

RECORDED_GUIDES: dict[str, tuple[str, str]] = {
    f"{source}_{field}": (definition.format(module=module), interpretation)
    for source, module in (("ecm", "engine controller"), ("tcm", "transmission controller"))
    for field, (definition, interpretation) in _STANDARD_GUIDES.items()
}
RECORDED_GUIDES.update({
    "honda_vehicle_speed_kph": (
        "Road speed carried in both Honda transmission replies, in km/h.",
        "It puts the shaft readings at a particular road speed. Compare it with ECM vehicle speed "
        "during a launch, allowing for the time between queries.",
    ),
    "honda_engine_speed_rpm": (
        "Engine RPM reported alongside the shaft speeds in Honda transmission reply 2301.",
        "Compare it with the drive pulley at the same instant, or with the nearby turbine reading "
        "to see how closely those speeds follow the engine.",
    ),
    "candidate_drive_pulley_rpm": (
        "Estimated rotational speed of the CVT input pulley from Honda reply 2301.",
        "At steady road speed, a rise relative to output RPM suggests the CVT is using a "
        "shorter ratio. The pulley identification is provisional.",
    ),
    "candidate_driven_pulley_rpm": (
        "A speed field in Honda reply 2301 provisionally assigned to the CVT output pulley.",
        "It tends to track road speed. The shaft identity and gearing are still uncertain, "
        "so they also limit the accuracy of the pulley ratio estimate.",
    ),
    "candidate_honda_manifold_pressure_kpa": (
        "A field in Honda reply 2301 interpreted as intake manifold absolute pressure.",
        "Look for the same rises under throttle and falls on lift-off as in the standard "
        "ECM pressure trace. Agreement across loads supports the mapping.",
    ),
    "candidate_honda_barometric_pressure_kpa": (
        "A field in Honda reply 2301 interpreted as atmospheric pressure.",
        "Compare its level with standard ECM barometric pressure. Agreement as elevation "
        "or weather changes is a stronger check than one matching value.",
    ),
    "candidate_cvt_fluid_temperature_sensor_raw": (
        "An unscaled byte beside the proposed CVT fluid temperature in Honda reply 2301.",
        "Look for the count falling as the estimated fluid temperature rises. That inverse "
        "pattern supports a sensor relationship. The count has no verified voltage scale.",
    ),
    "candidate_cvt_fluid_temperature_c": (
        "Estimated CVT fluid temperature from a Honda reply byte, decoded by subtracting 40.",
        "Compare its warm-up curve with engine coolant to see which rises first and when "
        "they level off. The temperature scale still needs an independent check.",
    ),
    "candidate_secondary_shaft_1_rpm": (
        "The first of two speed fields in Honda reply 2322 tentatively assigned to the secondary shaft.",
        "Compare it with the proposed output pulley reading as speed changes. A consistent "
        "proportion is evidence that both follow the transmission output.",
    ),
    "candidate_secondary_shaft_2_rpm": (
        "The second proposed secondary shaft speed in Honda reply 2322.",
        "Compare it with shaft speed 1 at the same instant. A steady percentage difference "
        "across several road speeds is a clue to how these two fields are scaled.",
    ),
    "candidate_torque_converter_turbine_rpm": (
        "Estimated RPM of the torque converter turbine, which receives power from the engine.",
        "If this field tracks engine RPM closely through a steady stretch, their speed "
        "difference is small. Confirming lock-up would require a clutch-state reading.",
    ),
})
