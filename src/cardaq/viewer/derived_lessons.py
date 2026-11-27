"""Reading guides for quantities calculated from recorded signals."""


def _lesson(plain: str, source: str, reading: str, caution: str) -> dict[str, str]:
    return {"plain": plain, "source": source, "reading": reading, "caution": caution}


DERIVED_LESSONS = {
    "derived_crank_torque_nm": _lesson(
        "How much turning effort does the engine deliver at the crankshaft after its own friction?",
        "At each positive PID 63 reference, subtract friction (PID 8E) from indicated torque (PID 62). "
        "Divide by 100 and multiply by that reference. Both percentage readings must be within 0.5 s.",
        "A 185 N·m reference, 68% indicated torque and 11% friction give 105.45 N·m. "
        "Negative values can occur when friction exceeds indicated torque on overrun.",
        "The estimate uses the engine computer's model. The Civic's changing reference still needs "
        "independent validation. Rapid throttle changes can occur between polls.",
    ),
    **{
        key: _lesson(
            "How quickly is the engine delivering mechanical work at the crankshaft?",
            "Multiply estimated crank torque in N·m by the nearest ECM RPM within 0.5 s of the reference "
            "reply and by 2π / 60,000 for kW. One mechanical horsepower is about 0.7457 kW.",
            "At 2,039 rpm, 105.45 N·m gives 22.5 kW, about 30 hp. Overlay engine speed or crank torque "
            "to see how the engine maintains power as its speed changes.",
            "This estimate precedes drivetrain losses. Negative power indicates net drag. Absolute values "
            "depend on the ECU's torque model and the timing of separate polls.",
        )
        for key in ("derived_crank_power_kw", "derived_crank_power_hp")
    },
    "derived_pulley_ratio": _lesson(
        "In an easy bicycle gear, your feet turn more times for each turn of the wheel. Here, "
        "a higher number means more turns on the engine side of the transmission for each turn on the "
        "wheel side, based on the two speeds we think we've identified.",
        "Divide the candidate input pulley RPM by the candidate output pulley RPM in the same Honda reply. "
        "For example, 1,500 RPM divided by 3,000 RPM gives 0.50 input turns per output turn.",
        "Pick a narrow road-speed band on both drives. A higher ratio there means the input turns more "
        "times for each output turn. Compare engine RPM to see how much of that difference reaches the engine.",
        "The chart starts at 10 km/h. Shaft identification and scaling need verification. Grade and pedal "
        "position can change the ratio even with the selector held in one mode.",
    ),
    "derived_torque_converter_slip_rpm": _lesson(
        "Fluid passes the engine's turning motion to a wheel called the turbine. When you pull away "
        "from a light, the engine can spin faster than that wheel. A shrinking gap means their speeds "
        "are getting closer.",
        "The converter carries rotation from the engine to a turbine. Subtract the candidate turbine speed "
        "from the Honda engine speed. An engine at 2,000 RPM and a turbine at 1,800 RPM give +200 RPM.",
        "Look across a launch and the cruise that follows. A positive gap that closes toward zero means "
        "the two reported speeds converge. A negative gap means the turbine reading is higher.",
        "The turbine field is provisional. Replies can be 150 ms apart, so rapidly changing RPM can create "
        "an apparent gap. Near-zero slip alone cannot confirm that the lock-up clutch was commanded on.",
    ),
    "derived_drive_minus_turbine_rpm": _lesson(
        "Two parts help pass the engine's motion along. A wheel pushed by fluid turns a pulley that "
        "moves a belt. Near zero, their reported speeds match. Above zero, the pulley appears to turn "
        "faster.",
        "Subtract candidate turbine RPM from candidate drive-pulley RPM. For example, 1,560 minus 1,500 "
        "gives +60 RPM. This compares two reported transmission speeds downstream of the engine.",
        "Use a steady-speed section to see how closely the fields track. Then inspect a launch. Differences "
        "that appear mainly while both speeds change rapidly can help reveal sampling delay.",
        "The two fields come from separate replies up to 150 ms apart. Their identities and scales need "
        "confirmation before attributing a persistent gap to a mechanical component.",
    ),
    "derived_longitudinal_acceleration_m_s2": _lesson(
        "Pull away from a light and the line goes above zero. Slow down for the next light and it goes "
        "below zero. Even at highway speed, cruising at a steady pace puts you near zero.",
        "Compare vehicle speeds roughly 1.5 seconds before and after each point, then divide the change "
        "by elapsed time. A rise of 10.8 km/h in three seconds works out to +1 m/s².",
        "Positive values mean the car gained speed, negative values mean it lost speed, and a level "
        "cruise sits near zero. Find the same interval on road speed to see the slope the chart measures.",
        "Road-speed samples average over short maneuvers. A negative value alone cannot distinguish "
        "braking, coasting, or climbing a hill.",
    ),
    "derived_cvt_minus_coolant_c": _lesson(
        "Two liquids warm up as you drive. One flows inside the transmission. The other carries heat away "
        "from the engine. A reading of −10 means the transmission fluid appears to be 10 degrees cooler "
        "than the engine coolant.",
        "Subtract engine coolant sensor 1 from candidate CVT fluid temperature. Fluid at 35 °C and "
        "coolant at 50 °C produce −15 °C. The sign tells you which reading is warmer.",
        "Start at key-on and follow the gap through warm-up. A move from −15 to −5 °C means the "
        "temperatures drew closer. Open both temperature traces to see which one changed.",
        "Starting coolant can be elevated after preheating. These samples can be about half a second "
        "apart, and the fluid temperature conversion still needs independent verification.",
    ),
    "derived_converter_slip_pct": _lesson(
        "Imagine the engine making 100 turns. If the wheel that receives its motion through fluid makes "
        "95 turns in the same time, this shows +5%. Near zero, those two speeds almost match.",
        "Divide the engine-to-turbine RPM difference by engine RPM and multiply by 100. A 200 RPM gap "
        "at 2,000 RPM gives 10%. The same gap at 4,000 RPM gives 5%.",
        "Use this chart when engine speeds differ between trips. At +5%, the turbine reading is 95% "
        "of engine speed. Read it beside the RPM difference to see the actual size of the gap.",
        "The calculation requires engine speed of at least 500 RPM. A stopped turbine can yield 100% "
        "at idle in gear. Compare warm, moving conditions before drawing conclusions about coupling.",
    ),
    "derived_ratio_change_pct_s": _lesson(
        "This catches the moments when the transmission changes how many turns the engine side makes "
        "for each turn on the wheel side. An upward spike means more turns per turn, a downward dip "
        "means fewer, and a line near zero means the setting held steady.",
        "Compare consecutive estimated pulley ratios using 100 times the natural log of new ratio "
        "divided by old ratio, per elapsed second. From 0.50 to 0.55 in one second gives about +9.5%/s.",
        "A peak marks rapid adjustment. Near zero means the ratio held steady, whether its value was "
        "high or low. Inspect the ratio itself to see where the adjustment began and ended.",
        "The calculation spans positive ratios at most 2.5 seconds apart. Inspect a cluster of peaks "
        "against speed and throttle before attributing it to repeated transmission adjustments.",
    ),
    "derived_output_speed_change_pct_s": _lesson(
        "This follows how quickly the wheel side of the transmission appears to pick up or lose speed. "
        "Look at a pull away from a light. The line rises above zero as that part spins up, then "
        "settles near zero when you hold your speed.",
        "Use consecutive candidate output-shaft speeds to calculate their logarithmic change per "
        "second. From 1,000 to 1,100 RPM in two seconds gives about +4.8%/s.",
        "Compare this with ratio change at the same instant. If output speed rises about 5%/s while "
        "the ratio falls about 5%/s, the two changes cancel and input pulley speed stays nearly constant.",
        "A given RPM change produces a larger percentage at a lower starting speed. The chart uses "
        "moving samples with a valid pulley ratio, so a blank near a stop is expected.",
    ),
    "derived_manifold_vacuum_kpa": _lesson(
        "The engine draws air through a small door that opens when you ask for more power. With the "
        "door nearly closed, pressure behind it can fall well below outside air pressure. A taller line "
        "means a bigger pressure gap.",
        "Air pressure upstream of the engine is represented by the barometric reading. Subtract "
        "manifold absolute pressure from it. At 100 kPa ambient and 35 kPa manifold, vacuum is 65 kPa.",
        "Watch what happens as the throttle opens. When manifold pressure moves closer to ambient, "
        "the gap shrinks. On a closed-throttle coast the gap can grow again.",
        "Use barometric pressure from the same drive because elevation and weather affect it. The "
        "two sensors are polled separately, with readings matched within two seconds.",
    ),
    "derived_coolant_sensor_difference_c": _lesson(
        "One thermometer reads the liquid near the engine. Another reads it at the radiator, where the "
        "car sheds heat. A point at +20 means the engine-side liquid is 20 degrees warmer. Zero means "
        "the two readings match.",
        "Subtract ECM coolant sensor 2 from sensor 1 at the same timestamp. Readings of 70 °C and "
        "55 °C produce +15 °C. Zero means the two reported temperatures agree.",
        "Follow the two absolute temperatures through warm-up. A widening positive gap means sensor 1 "
        "pulled ahead, sensor 2 fell behind, or both. Their separate traces distinguish those cases.",
        "These are readings at different sensing points. Their separation alone cannot establish "
        "coolant flow, thermostat position, or whether either sensor needs service.",
    ),
    "derived_engine_coolant_warming_rate": _lesson(
        "Imagine writing down the engine coolant temperature once a minute. Going from 46 to 50 degrees "
        "in one minute puts this line at +4. A preheated engine can start warmer and still warm up more "
        "slowly once you drive.",
        "Compare coolant sensor 1 now with its reading about one minute earlier. A rise from 46 to "
        "50 °C in 60 seconds plots at +4 °C/min at the end of that minute.",
        "Separate the head start from the climb. A preheated engine can begin warmer and still show "
        "a gentler slope. Compare key-on coolant first, then compare rates at similar load and temperature.",
        "Each point describes the preceding minute. The first minute and the minute after a substantial "
        "data gap lack that history. Rate alone cannot isolate the effect of a block heater.",
    ),
    "derived_cvt_fluid_warming_rate": _lesson(
        "Think of checking the transmission fluid's temperature one minute apart. A point at +3 means "
        "it appears to have warmed by about three degrees in that minute. If the line falls from +3 to "
        "+1, the fluid is still warming, just more slowly.",
        "Use the change in candidate transmission-fluid temperature over about one minute. For "
        "example, 20 to 23 °C in one minute gives +3 °C/min.",
        "Compare this rate with the coolant warming rate at the same time. If both rise by 3 °C/min, "
        "their temperature gap holds steady even when the coolant began much warmer.",
        "This is a trailing average of a candidate reading. Changes in load, airflow, and starting "
        "temperature complicate comparisons between an outbound and a return drive.",
    ),
    "derived_catalyst_warming_rate": _lesson(
        "The exhaust passes through a part that helps clean up the gases. This shows how quickly the "
        "car thinks that part is warming. A line near zero after a long drive can mean the part is "
        "already hot and holding steady.",
        "Compare ECU-reported catalyst temperatures about one minute apart. A climb from 250 to "
        "310 °C over that window gives +60 °C/min.",
        "Check the absolute temperature beside the slope. Zero can describe a hot catalyst holding "
        "steady or a cold one that has yet to warm. Negative values indicate cooling over the window.",
        "The ECU's reported temperature and its change do not measure tailpipe emissions. Engine "
        "load and exhaust conditions can change considerably within the minute.",
    ),
    "derived_distance_km": _lesson(
        "This is a trip counter rebuilt from the car's speed readings. At 60 km/h, each minute of "
        "driving adds one kilometer. On the time chart the line climbs faster on the highway and goes "
        "flat at a red light.",
        "For each adjacent pair of speed readings, multiply their average speed by elapsed time and "
        "add the distance to the running total. A minute at 60 km/h adds 1 km.",
        "On the time axis, a steep rise marks fast travel and a horizontal stretch with speed samples "
        "at zero marks a stop. Use equal observed distance to compare progress through two commutes.",
        "Intervals longer than 1.5 seconds contribute no distance. Travel during a dropout is unknown. "
        "Equal distance on opposing routes can correspond to different physical locations.",
    ),
    "derived_engine_revolutions": _lesson(
        "Imagine a counter clicking each time the engine turns once. It keeps counting at a red light "
        "if the engine is still running. At the same trip distance, a higher total means the engine "
        "made more turns along the way.",
        "Average neighboring engine RPM readings and multiply by elapsed minutes. At a constant "
        "1,200 RPM, half a minute adds 600 crankshaft turns.",
        "On the time axis, the slope follows RPM. Compare totals at equal distance, then check engine-on "
        "stopped time to see how many opportunities one engine had to keep turning while stationary.",
        "Gaps longer than 1.5 seconds add no turns. The total measures rotation, and says little about "
        "load or wear without other evidence.",
    ),
    "derived_fuel_used_g": _lesson(
        "This adds up the fuel the car reports using. Picture one US gallon for about every 2,810 grams "
        "of gasoline. The exact weight varies by blend. Watch the total creep up at a red light while "
        "the engine keeps running.",
        "Average successive engine fuel-flow readings in grams per second and multiply by the seconds "
        "between them. At a steady 0.5 g/s for ten seconds, the total rises by 5 g.",
        "The height is fuel used since recording began. The slope on the time axis shows consumption "
        "rate. Compare the increase over equal distances, including fuel spent waiting at lights.",
        "This uses ECU-reported mass flow. Intervals longer than five seconds add no estimate. "
        "A longer recording gap can make an otherwise similar drive appear to use less fuel.",
    ),
    "derived_rolling_fuel_g_km": _lesson(
        "How much gas did it take to cover the last stretch of road? A higher line means more gas for "
        "the same distance. A long red light can show up here even after you pull away, because the "
        "stretch you just covered still includes the wait.",
        "Divide recent fuel mass by recent distance over a continuous stretch spanning at least "
        "0.5 km. If the engine used 25 g in 0.5 km, the result is 50 g/km.",
        "Think of each point as looking backward along the road. A stop can raise the value as fuel "
        "continues to accumulate, and can influence later points until it leaves the window.",
        "The same distance takes longer in traffic than at cruise. Compare similar speed profiles. "
        "A new continuous stretch needs enough distance before another point can appear.",
    ),
    "derived_rolling_revolutions_per_km": _lesson(
        "Imagine counting how many times the engine turns while you travel one kilometer. A higher line "
        "means more turns to cover the same ground. That can happen in Sport mode or after a wait with "
        "the engine running.",
        "Divide the crankshaft turns accumulated over at least the last 0.5 km by distance. A "
        "window with 900 turns over 0.5 km gives 1,800 rev/km.",
        "Compare steady stretches at the same road speed. More turns per kilometer alongside a higher "
        "pulley ratio can explain why Sport feels busier even when both drives cover ground equally fast.",
        "Idle time can increase the turn count inside the window. Check the recent speed trace before "
        "attributing a difference to CVT behavior.",
    ),
    "derived_rolling_fuel_per_1000_rev": _lesson(
        "Count off a thousand turns of the engine and ask how much gas "
        "those turns took. A higher number means the engine used more fuel per turn over that stretch.",
        "Divide fuel consumed by crankshaft turns across a continuous window of at least 1,000 turns, "
        "then scale to 1,000 turns. For example, 18 g over 1,200 turns gives 15 g/1,000 rev.",
        "Read this beside revolutions per kilometer. At a steady 2,000 rev/km and 15 g/1,000 rev, "
        "fuel use would be 30 g/km. Either more turns or more fuel per turn can raise trip consumption.",
        "The rolling charts use different windows and need steady conditions for that relationship "
        "to line up point by point. Fuel per turn also depends on engine load.",
    ),
    "derived_engine_on_stopped_s": _lesson(
        "Picture a stopwatch that runs only while the car is standing still with its engine on. Wait at "
        "a red light for half a minute and the total grows by about 30 seconds. When you pull away, it "
        "holds there until your next stop.",
        "Count elapsed time between successive zero-speed observations when each has a nearby engine "
        "reading of at least 500 RPM. One observed minute of stationary idle adds 60 seconds.",
        "The line rises while waiting and levels out while moving. Compare the increase at the "
        "start of the drive with later increases to distinguish parked warm-up from traffic stops.",
        "A flat stretch can also mean the engine was off. Inspect RPM and recording coverage. "
        "A missing interval supplies no evidence about how much time the engine spent idling.",
    ),
    "derived_engine_on_stopped_fuel_g": _lesson(
        "This adds up the gas you use while the engine runs and the car stays still. Each climb is fuel "
        "spent waiting, whether in the driveway or at a light. When you start moving, this counter "
        "pauses.",
        "Add the fuel delivered between fuel-flow samples lying inside observed engine-on stops. "
        "At a constant 0.25 g/s, 40 covered seconds add 10 g.",
        "Compare the rise with the increase in stopped time. If two sampled stops last equally long "
        "but one adds more grams, inspect its fuel rate, engine RPM, and coolant temperature.",
        "Brief stops can fall between fuel polls. Fuel intervals straddling a launch or a stop "
        "boundary are excluded, so short stops can contribute less than their actual fuel use.",
    ),
    "derived_positive_speed_energy_j_kg": _lesson(
        "Think of getting a bicycle back up to speed after every stop. This adds up each gain in the "
        "car's energy of motion, and braking leaves earlier gains on the tally. Speeding up downhill "
        "counts too, even with your foot off the gas.",
        "Smooth road speed, convert to meters per second, and sum each gain in speed squared divided "
        "by two (kinetic energy per kilogram). Increasing from 0 to 10 m/s adds 50 J/kg.",
        "Braking leaves the accumulated total in place. Repeating the same launch adds another "
        "50 J/kg. Compare equal-distance drives to see how repeated speed gains add up.",
        "Gravity can supply a downhill gain. Steady-speed cruising adds nothing while the engine may "
        "still burn fuel overcoming drag. This measure cannot give the engine's energy output.",
    ),
    "derived_air_mass_per_cylinder_mg": _lesson(
        "Each cylinder draws in a little gulp of air. This estimates the average size of one gulp from "
        "the air entering the whole engine. A higher line on a hill means the average gulp contained "
        "more air.",
        "A four-cylinder, four-stroke engine has two intake events per crankshaft turn. At 2,000 RPM "
        "that is about 66.7 intakes per second. Airflow of 10 g/s then gives 150 mg per intake.",
        "At a fixed RPM, an increase means more air was admitted per stroke on average. Compare "
        "a gentle cruise with an uphill pull at similar RPM and look at throttle and calculated load.",
        "One shared airflow reading supplies the average for all four cylinders. It cannot distinguish "
        "the air entering cylinder 2 or explain a cylinder-specific misfire.",
    ),
    "derived_fuel_cut_candidate": _lesson(
        "Lift your foot and coast. Sometimes the moving car keeps the engine turning while the car "
        "reports using no fuel. A 1 marks a stretch that fits that pattern. A 0 means the readings "
        "didn't meet all the checks.",
        "The recorder learns a near-rest pedal position from stationary running samples. Two adjacent "
        "zero-flow readings qualify when both have a near-rest pedal, at least 500 RPM, and at least 10 km/h.",
        "A run of 1s marks a candidate fuel-cut coast. Follow road speed and RPM across the run. The "
        "car can keep the engine turning through the transmission while reported fuel flow is zero.",
        "A 0 means the test did not qualify, and missing inputs can leave a gap. Fuel-flow resolution "
        "and polling limit the inference. Injector commands would verify a cutoff.",
    ),
}
