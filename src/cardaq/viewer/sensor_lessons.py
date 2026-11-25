"""Physical and controller-level context for the recorded Civic signals."""


def _lesson(plain: str, source: str, reading: str, caution: str) -> dict[str, str]:
    return {"plain": plain, "source": source, "reading": reading, "caution": caution}


# An OBD reply identifies the reporting controller. Two controllers can publish
# readings from one physical sensor. Supply the reporter explicitly in each lesson.
_SHARED = {
    "engine_speed_rpm": _lesson(
        "How fast is the engine spinning? At a red light the car can be standing still while this "
        "line stays up because the engine is still running.",
        "A pickup on the engine reads a rotating target on the crankshaft. The time between pulses "
        "gives shaft speed. This is the {module}'s report of that speed.",
        "At 1,800 rpm the crankshaft turns 30 times every second. If road speed stays level while RPM "
        "rises, look at pulley ratio and turbine speed to see where the extra turns occur.",
        "The published RPM averages rotation over time. Individual combustion events happen far faster "
        "than the logger polls this value.",
    ),
    "vehicle_speed_kph": _lesson(
        "Read this like your speedometer laid out across the drive. A flat line at 60 means you held "
        "60 km/h, and a flat line at zero marks a stop.",
        "The {module} publishes a vehicle-level estimate of road speed. Rotating wheels and "
        "transmission shafts provide speed information on this car. This reply does not identify "
        "which pickup supplied it.",
        "An indicated 72 km/h corresponds to 20 metres each second. Pick a level section of the "
        "trace to compare engine RPM or fuel rate at the same speed on another drive.",
        "Whole-km/h reporting produces stair steps. Tire rolling circumference affects the "
        "relationship between wheel rotation and true ground speed.",
    ),
    "manifold_pressure_kpa": _lesson(
        "This is the air pressure just before air enters the cylinders. Pressing the gas usually "
        "opens the engine’s air inlet wider, letting the pressure rise closer to the outside air.",
        "The manifold absolute pressure (MAP) sensor samples the air space downstream of the throttle, "
        "where the intake runners feed the cylinders. This value comes through the {module}.",
        "If the atmosphere is at 100 kPa and the manifold reads 35 kPa, the pressure drop is "
        "65 kPa. Watch the drop shrink as the throttle opens and air enters more freely.",
        "Pressure alone cannot tell you how many grams of air enter each second. Check the airflow "
        "trace and RPM at the same point.",
    ),
    "barometric_pressure_kpa": _lesson(
        "This is the pressure of the air around the car. It usually changes slowly, so it gives you a "
        "reference for the pressure inside the engine’s air inlet.",
        "Honda lists the atmospheric pressure sensor with the engine control module. The {module} "
        "reports the surrounding air pressure, the upstream reference for the intake system.",
        "With the engine off and the intake pressure equalized, compare this value with manifold "
        "pressure. Once the engine is idling, the manifold reading usually drops below it.",
        "Elevation and weather both affect atmospheric pressure. A weather app may show a pressure "
        "corrected to sea level, which uses a different reference.",
    ),
    "control_module_voltage_v": _lesson(
        "This is the voltage reaching the {module}. Look at startup for a dip as the starter uses "
        "power, then a rise as the charging system takes over.",
        "This is the supply voltage seen by the {module} through its power and ground wiring. "
        "It describes the electrical conditions at the controller.",
        "Find the transition from key-on to cranking to engine running. The starter draws current "
        "while cranking. The charging system then supplies the running car.",
        "Cable voltage drops and the interval between polls affect the lowest value you see. Battery "
        "capacity and starter current each require a different measurement.",
    ),
    "coolant_sensor_1_c": _lesson(
        "There’s a thermometer in the liquid that carries heat away from the engine. Its first "
        "reading tells you how warm the liquid near the engine already was when you started.",
        "On the 2.0 L Civic, the engine-side coolant temperature sensor samples the coolant at "
        "the engine's water passage. Its thermistor changes resistance with temperature. The "
        "{module} reports the converted temperature.",
        "Start at key-on, before engine RPM rises. A high first reading after an overnight soak "
        "can reveal a preheating head start. Then compare how many running minutes each drive takes "
        "to climb another 10 °C.",
        "A single probe describes coolant around its tip. Engine oil, cylinder metal and coolant "
        "in the radiator can all be at different temperatures.",
    ),
    "coolant_sensor_2_c": _lesson(
        "This thermometer is at the radiator, where the car sheds heat to the air. It can still read "
        "cold while the liquid inside the engine is warming up.",
        "The second coolant thermistor on the 2.0 L Civic samples the radiator side of the "
        "cooling circuit. The {module} converts or relays its temperature reading.",
        "Follow both coolant traces from startup. The engine can heat its local coolant while the "
        "radiator stays cooler. As hot coolant reaches the radiator, the second trace can rise.",
        "Road airflow, fan operation and coolant circulation all affect this curve. The exact moment "
        "the thermostat moves requires a separate observation.",
    ),
}

SENSOR_LESSONS = {
    f"{prefix}_{name}": {key: text.format(module=module) for key, text in lesson.items()}
    for prefix, module in (("ecm", "engine controller"), ("tcm", "transmission controller"))
    for name, lesson in _SHARED.items()
}

SENSOR_LESSONS.update({
    "honda_vehicle_speed_kph": _lesson(
        "The transmission computer includes a road-speed reading with its other numbers. Use it to "
        "find a stretch where the car held the same speed while the engine sped up or slowed down.",
        "The Honda transmission controller publishes vehicle speed within two groups of shaft data. "
        "The physical reference is the car's motion over the road. The packets omit pickup identity.",
        "Use the reading beside a pulley sample to distinguish a ratio change at constant road speed "
        "from all the shafts speeding up as the car accelerates.",
        "Both Honda packets can carry the same underlying speed. Close agreement between the packets "
        "shows consistent reporting.",
    ),
    "honda_engine_speed_rpm": _lesson(
        "This is how fast the engine is turning, as seen by the transmission computer. You can "
        "compare it with the spinning parts inside the transmission at nearly the same moment.",
        "Engine speed originates at the crankshaft. The transmission controller includes an RPM "
        "value in the same Honda 2301 reply as the two proposed pulley speeds.",
        "At a running stop the crank can keep turning while the wheels are still. Follow the RPM "
        "through launch and compare it with the proposed turbine speed on the gearbox side.",
        "A difference from a nearby standard engine RPM sample can come from the engine changing "
        "speed during the time between queries.",
    ),
    "candidate_drive_pulley_rpm": _lesson(
        "A metal belt runs around two wheels called pulleys inside the transmission. We think this "
        "line shows how fast the first wheel turns as it sets the belt moving.",
        "The drive pulley sits on the input side of the CVT's belt. Its moving faces change the "
        "radius at which the belt rides. We provisionally associate this Honda 2301 field with its shaft speed.",
        "Hold vehicle speed steady in the graph. More input turns for each output turn would make "
        "the engine turn faster at that road speed when the converter is coupled.",
        "The byte mapping and RPM scale need a reference measurement. The field gives no direct "
        "measurement of pulley diameter or belt clamping force.",
    ),
    "candidate_driven_pulley_rpm": _lesson(
        "Inside the transmission, the belt turns a second wheel that sends power toward the tires. We "
        "think this reading follows that end of the belt, so it should rise as the car gains speed.",
        "The belt drives the second pulley on its way to the final drive and wheels. This Honda "
        "2301 field is a candidate for rotation on that output side.",
        "Find two stretches at the same road speed. Similar output readings alongside different "
        "input readings are the pattern expected when the CVT chooses different ratios.",
        "Output gearing can make several shafts track road speed in fixed proportions. That pattern "
        "alone cannot identify which shaft Honda encoded.",
    ),
    "candidate_honda_manifold_pressure_kpa": _lesson(
        "We think this is another reading of air pressure just before air enters the cylinders. "
        "Compare it with the engine computer’s manifold pressure when you press and release the gas.",
        "The proposed quantity is air pressure between the throttle and intake valves. The "
        "transmission controller includes this byte in its 2301 data group.",
        "At idle, on a pedal press and on lift-off, compare the byte with standard ECM manifold "
        "pressure. Three matching changes are a stronger test than one matching cruise value.",
        "The pressure sensor belongs to the engine intake. This candidate channel may share that "
        "sensor's information. Its scaling still needs confirmation.",
    ),
    "candidate_honda_barometric_pressure_kpa": _lesson(
        "This number may be the transmission computer’s copy of the outside air pressure. If so, it "
        "should stay fairly steady when you press the gas, even as pressure inside the engine "
        "changes.",
        "Honda groups the ambient pressure sensor with the engine computer. This byte in the "
        "transmission's 2301 reply is a possible copy of that atmospheric reference.",
        "Compare it with standard barometric pressure on days with different weather or across "
        "elevations. It should stay relatively steady through a throttle change.",
        "A byte that barely changes on one commute is difficult to identify. Independent variation "
        "in the atmospheric reference makes a more informative comparison.",
    ),
    "candidate_cvt_fluid_temperature_sensor_raw": _lesson(
        "This may be the number behind the transmission’s fluid thermometer. Look for the count to "
        "fall as the fluid warms. The number itself is still in the sensor’s own units.",
        "The CVT uses a thermistor in its fluid circuit. Its electrical resistance falls as the "
        "fluid warms. This Honda 2301 byte is a candidate for a signal from that sensing circuit.",
        "Compare a cold-start count with a warmed-up count. A count that falls while the adjacent "
        "temperature field climbs fits the expected direction of the sensor signal.",
        "This axis is raw counts. Converting it to volts, ohms or degrees requires a verified "
        "transfer function. Even a strong correlation leaves the exact mapping open.",
    ),
    "candidate_cvt_fluid_temperature_c": _lesson(
        "This is our estimate of how warm the fluid inside the transmission is. Watch its first few "
        "minutes beside engine coolant to see whether the two warm up together.",
        "The relevant sensing element measures fluid temperature in the transmission. The viewer "
        "interprets a byte in the Honda 2301 response as degrees Celsius after subtracting 40.",
        "A byte of 90 would plot at 50 °C. Compare its starting point and subsequent climb with "
        "engine-side coolant to see how differently the two fluid circuits absorb heat.",
        "The location within the fluid circuit and the decoded temperature need independent "
        "verification. This trace cannot establish fluid level or condition.",
    ),
    "candidate_secondary_shaft_1_rpm": _lesson(
        "We think this line follows a spinning part on the way to the wheels. If you double your road "
        "speed, look for its reading to roughly double too.",
        "This is one of two speed-like values inside Honda transmission reply 2322. The working "
        "hypothesis puts it downstream of the belt, where shaft speed follows wheel speed through gearing.",
        "Compare steady stretches at 30 and 60 km/h. Doubling road speed should roughly double a "
        "shaft speed linked to the wheels by a fixed gear ratio.",
        "Several rotating parts can pass that test. A confirmed pickup location or an independent "
        "shaft RPM reading would distinguish them.",
    ),
    "candidate_secondary_shaft_2_rpm": _lesson(
        "Here’s a second clue about how fast parts turn on the wheel side of the transmission. "
        "Compare it with the first shaft reading as the car speeds up to see whether the two rise "
        "together.",
        "A separate field in the same 2322 transmission packet provides another candidate for a "
        "speed on the output side of the CVT. Its physical pickup is unresolved.",
        "Compare its value with candidate secondary shaft 1 across a range of speeds. A constant "
        "proportion points toward fixed gearing or different scaling of the same rotation.",
        "Two values in one packet need not come from two pickups. A difference in the numbers "
        "alone cannot establish mechanical slip.",
    ),
    "candidate_torque_converter_turbine_rpm": _lesson(
        "The engine pushes fluid against a bladed wheel called the turbine, which helps turn the "
        "transmission. We think this line shows that wheel’s speed. Compare it with engine speed as "
        "you pull away.",
        "The converter sits between the engine and gearbox. Engine rotation drives its pump, fluid "
        "transfers torque to the turbine, and the turbine drives the transmission input. This "
        "Honda 2322 field is the candidate turbine speed.",
        "Through a launch, compare engine speed with turbine speed. The engine can turn faster "
        "while fluid transfers torque. The two speeds can converge during steady cruising.",
        "This field's identity is provisional. Matching RPM leaves the clutch command unknown. "
        "Small offsets can also arise because the engine and turbine fields arrive at different times.",
    ),
    "ecm_calculated_load_pct": _lesson(
        "How much effort is the engine using at this moment? The line can climb on a hill even when "
        "the speedometer stays put.",
        "The engine computer calculates this percentage from its estimate of current demand "
        "relative to available engine load at this speed. It has no dedicated load probe.",
        "Compare a flat cruise with a climb at similar RPM. The car can maintain the same speed "
        "while admitting more air and reporting higher load to overcome the grade.",
        "A 50% reading refers to the computer's load scale at that operating point. Converting it "
        "to horsepower requires additional measurements.",
    ),
    "ecm_short_term_fuel_trim_pct": _lesson(
        "The car makes small fuel adjustments as you drive. Above zero means it’s adding a little "
        "extra fuel right now, and below zero means it’s taking some away.",
        "The engine computer uses feedback from the air/fuel sensor in the exhaust upstream of "
        "the catalyst to adjust injector delivery. This chart shows the immediate bank 1 correction.",
        "In normal closed-loop operation a +5% correction means that the computer scales fuel "
        "up for that adjustment. Watch whether the correction settles when cruise becomes steady.",
        "The four cylinders share bank 1. This percentage describes their combined feedback, so "
        "a change cannot single out cylinder 2.",
    ),
    "ecm_long_term_fuel_trim_pct": _lesson(
        "This is the fuel adjustment the car has learned to make in familiar conditions. For example, "
        "+5% at a warm stop means it has learned to add about 5% extra fuel there.",
        "This is a learned correction stored by the engine computer. Repeated exhaust feedback "
        "tells it how much to adjust its baseline injector delivery in a given operating region.",
        "Look separately at warm stops and steady cruise. A consistent upward change across warm "
        "stops means the controller has learned to add more fuel under those conditions.",
        "Different RPM and load regions can use different learned corrections. A step during a "
        "launch can mark a change of operating region.",
    ),
    "ecm_ignition_timing_deg": _lesson(
        "The spark plug lights the mixture of air and fuel as the piston nears the top of its travel. "
        "A higher reading means the computer fires the spark earlier in that movement.",
        "The engine computer uses crankshaft position to schedule ignition. The value gives "
        "cylinder 1 spark timing in degrees relative to the piston reaching the top of compression.",
        "A change from +10° to +20° means the spark happens ten crankshaft degrees earlier. "
        "Combustion takes time, so the controller changes timing as RPM and load change.",
        "This channel reports timing. Cylinder pressure, coil voltage and a dedicated knock "
        "retard reading would answer different questions about the combustion event.",
    ),
    "ecm_throttle_pct": _lesson(
        "There’s a little door that controls how much air can enter the engine. A higher line means "
        "the door opened farther. Compare it with the gas pedal to see how the car answered your "
        "foot.",
        "A position sensor in the throttle body follows the moving plate where the intake duct "
        "meets the manifold. An electric actuator opens and closes the plate.",
        "Overlay this reading mentally with pedal position at a launch. The pedal requests torque "
        "and the plate meters air, so their trajectories can differ.",
        "The absolute position scale can have an offset at idle. A reading of 20% is neither a "
        "20-degree plate angle nor a promise of 20% of maximum airflow.",
    ),
    "ecm_evap_purge_pct": _lesson(
        "Gasoline in the tank gives off vapor that the car saves to burn later. When this line rises, "
        "the computer is asking the valve to let more of that vapor reach the engine.",
        "Fuel vapor from the tank is collected in a charcoal canister. The engine computer "
        "commands a purge valve in the path between that canister and the engine intake.",
        "A step from 0% to 25% means a higher commanded purge fraction. Compare the timing with "
        "short-term fuel trim to see whether fueling changes as purge begins.",
        "Actual vapor delivery depends on pressure difference and the canister's contents. The "
        "command alone gives no measured grams of vapor.",
    ),
    "ecm_catalyst_temperature_c": _lesson(
        "A part in the exhaust helps clean up the gases leaving the engine. This is how hot the "
        "computer says that part is. Watch how quickly it heats up after startup.",
        "The location represented is the first catalyst temperature channel on bank 1 in the "
        "exhaust. The engine computer publishes this value and may model catalyst heat from operating conditions.",
        "Track its climb after startup beside coolant. Hot exhaust can heat the catalyst on a "
        "different timescale from the liquid circulating through the engine.",
        "A location label on this PID does not establish a physical temperature probe. Testing "
        "catalyst conversion efficiency requires additional evidence.",
    ),
    "ecm_accelerator_pedal_pct": _lesson(
        "This follows your foot on the gas pedal. Look for the line to rise as you ask for more "
        "power, then fall back to its resting level when you lift off.",
        "Position sensors in the accelerator pedal assembly in the driver's footwell follow "
        "pedal travel. Channel D is one reported position signal from that assembly.",
        "Find the released-pedal level during a coast. A rise above that baseline shows how early "
        "the driver asked for power, before the road speed had time to change.",
        "The percentage uses the channel's calibrated scale. The driver's foot force and the "
        "engine's delivered torque each describe a different physical quantity.",
    ),
    "ecm_mass_airflow_g_s": _lesson(
        "This counts the grams of air the engine draws in each second. A higher line means the engine "
        "is taking in more air, as it often does when you accelerate.",
        "The airflow meter sits in the clean intake-air path ahead of the throttle. It measures "
        "how much air mass passes into the engine each second.",
        "If flow stays at 10 g/s for five seconds, about 50 grams of air passes the meter. "
        "Compare flow at matched RPM to see when the engine takes in more air per turn.",
        "The meter sees the combined intake stream. It cannot measure the charge in one cylinder "
        "or account directly for air entering downstream of the meter.",
    ),
    "ecm_intake_air_temperature_c": _lesson(
        "This thermometer measures the air on its way into the engine. After a stop it can read "
        "warmer than the weather outside because the air under the hood has heated up.",
        "On this engine the intake temperature element shares the airflow meter assembly. It "
        "senses the air in the inlet, upstream of the throttle.",
        "Look at the first reading after parking and the change once moving. A warm engine bay "
        "can heat the inlet while parked, then fresh airflow can cool the sensing element.",
        "Its local surroundings can differ from outdoor air and from air entering the cylinder. "
        "An independent outdoor reading is useful when comparing seasons.",
    ),
    "ecm_engine_fuel_rate_g_s": _lesson(
        "How quickly are you using gasoline right now? If the line holds at one gram per second for "
        "ten seconds, the car reports using ten grams of fuel.",
        "The engine computer reports its fueling rate for the engine as a whole. This is a "
        "controller value associated with injector delivery. The capture identifies no in-line fuel flow meter.",
        "At a steady 0.5 g/s, ten seconds contributes about 5 grams of fuel. That same rate at "
        "a stop and while moving gives different fuel used per kilometre.",
        "The reported rate depends on the controller's calculation and update cadence. It cannot "
        "identify how much fuel any one injector actually delivered.",
    ),
    "ecm_odometer_km": _lesson(
        "This is the car’s total distance since new, in kilometers. The difference between the first "
        "and last readings tells you how far the car says it traveled during the recording.",
        "The vehicle maintains a running distance total from vehicle motion. The engine controller "
        "returns that total through OBD. The value persists across trips.",
        "Subtract the reading at departure from the one at arrival. Compare the difference "
        "with the area under the speed-versus-time curve for the same portion of the trip.",
        "The odometer PID encodes tenths of a kilometre and can update in larger steps. Its "
        "accumulated distance can include movement during a logger outage.",
    ),
})
