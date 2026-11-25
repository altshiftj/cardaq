"""Reading notes for the per-trip statistics shown in the health history."""

_CRANK = (
    "A pickup at the engine's crankshaft reads a rotating target. The engine computer uses the "
    "timing of those pulses to report crankshaft revolutions per minute (RPM)."
)
_TRIM = (
    "An air/fuel sensor in the exhaust upstream of the catalytic converter senses oxygen left "
    "after combustion. In closed loop the engine computer uses this feedback to adjust fueling. "
    "The OBD value is the computer's correction for the cylinder bank as a whole."
)
_COOLANT = (
    "Engine coolant carries heat away from the metal around the cylinders. The engine computer "
    "reports coolant sensor 1 in the engine-side water passage on the 2.0 L Civic. It reads "
    "the fluid at the probe. Oil, cylinder walls and radiator coolant can warm at different rates."
)
_SLIP = (
    "Inside the torque converter, the engine turns an impeller. Fluid drives a turbine on the "
    "transmission side. A lock-up clutch can link the two. The Honda replies supply engine RPM "
    "and a shaft speed provisionally identified as turbine RPM."
)
_RATIO = (
    "The CVT changes the effective diameters at which the belt runs on the drive and driven "
    "pulleys. The recorder infers their speed ratio from candidate shaft readings in the "
    "transmission computer's reply. It cannot see the belt or measure pulley diameter."
)

FEATURE_LESSONS = {
    "engine_idle_rpm": {
        "plain": (
            "Picture waiting at a red light after the engine has warmed up. The car is still, but "
            "the engine keeps turning. Each dot shows its usual pace at stops on one drive. "
            "A dot at 700 means about 700 turns a minute."
        ),
        "source": _CRANK,
        "example": (
            "Order the warm, stopped RPM readings from low to high. The middle value is one dot "
            "for that trip. A dot at 700 rpm means half the qualifying readings were at or below "
            "700 and half at or above it."
        ),
        "compare": (
            "Look for a change in the usual idle speed over several similar trips. An air "
            "conditioner or different selector position can change idle load. Check RPM spread "
            "to see whether the idle also became less steady."
        ),
    },
    "engine_idle_rpm_iqr": {
        "plain": (
            "How steady was the engine while you waited at lights? A small number means the middle "
            "half of the sampled idle speeds sat close together. A bigger number means the pace varied "
            "more across the stops on that drive."
        ),
        "source": _CRANK,
        "example": (
            "Sort the warm, stopped RPM readings and take the middle half. If its ends are "
            "696 and 706 rpm, the interquartile range is 706 − 696 = 10 rpm. The dot shows "
            "the width of that range, even if the median idle speed stays the same."
        ),
        "compare": (
            "Repeatedly wider spreads mean the recorded idle speeds vary more. Accessory loads "
            "and mixing different stops can widen the range. This summary can miss a brief stumble "
            "between polls."
        ),
    },
}

for state in ("idle", "cruise_low", "cruise_high"):
    driving = {
        "idle": "while you were stopped with the engine warm",
        "cruise_low": "on steady highway stretches with the engine turning around 2,000 times a minute",
        "cruise_high": "on steady highway stretches with the engine turning around 3,500 times a minute",
    }[state]
    comparison = (
        "Compare the warm-stop result with the cruise result. If only the stopped readings move, "
        "look at intake airflow and purge activity at the same stops."
        if state == "idle" else
        "Compare repeated trips in this road-speed, load and RPM window. A different drive mode "
        "can move an entire journey into another RPM band, leaving too few samples here."
    )
    FEATURE_LESSONS[f"engine_{state}_stft_pct"] = {
        "plain": (
            "The car checks its exhaust to see whether to give the engine a little more or less fuel. "
            f"This dot shows the usual quick adjustment {driving}. A plus sign means it added fuel."
        ),
        "source": _TRIM,
        "example": (
            "Short-term trim is the immediate correction. A trip median of +5% means the "
            "typical qualifying reading called for about 5% more fuel than the underlying "
            "command. A negative sign means the computer was taking fuel away."
        ),
        "compare": comparison + " Read short-term trim alongside its learned long-term correction.",
    }
    FEATURE_LESSONS[f"engine_{state}_ltft_pct"] = {
        "plain": (
            "If the car keeps making the same small fuel adjustment, it can remember it for next time. "
            f"This dot shows the adjustment it had learned to use {driving}. "
            "A negative number means it had learned to use less fuel than its starting estimate."
        ),
        "source": _TRIM,
        "example": (
            "Long-term trim is the correction learned over time. A median of −5% means the "
            "learned correction typically reduced fueling by about 5% in these conditions. "
            "Short-term correction can stay near zero while this learned offset persists."
        ),
        "compare": comparison + " A change in this percentage alone cannot identify a particular injector.",
    }

for band in ("low", "high"):
    FEATURE_LESSONS[f"engine_cruise_{band}_coolant_c"] = {
        "plain": (
            "Coolant is the liquid that carries heat away from the engine. Each dot shows how hot "
            "that liquid usually was during steady highway driving after the engine had been running "
            "for at least ten minutes."
        ),
        "source": _COOLANT,
        "example": (
            "This dot is the middle sensor-1 temperature during qualifying cruise after at "
            "least ten minutes of continuously observed engine operation. For example, an "
            "80 °C dot describes that part of the trip. Cold startup samples are excluded."
        ),
        "compare": (
            "Compare trips at similar outside temperatures, starting coolant temperatures and "
            "loads. Use the drive viewer's warm-up curve to investigate a block heater's "
            "effect at startup."
        ),
    }

for low, high in ((1500, 2500), (2500, 4000)):
    FEATURE_LESSONS[f"cvt_slip_rpm_{low}_{high}"] = {
        "plain": (
            "The engine spins a wheel that pushes fluid against a second wheel. That second wheel, "
            "called the turbine, helps turn the transmission. A higher dot means their speeds appeared "
            "farther apart during steady cruising. We’re still checking which reading comes from that second wheel."
        ),
        "source": _SLIP,
        "example": (
            "Subtract candidate turbine RPM from engine RPM in each matched pair. A difference "
            "of either +40 or −40 counts as 40 rpm here. The trip dot is the median of those "
            "magnitudes during qualifying steady cruise."
        ),
        "compare": (
            "A larger dot means the two reported speeds differed more in this RPM band. "
            "Examine the signed trace, sample timing, and selector mode. A lock-up command "
            "and verified shaft mapping would be needed to assess clutch behavior."
        ),
    }
    FEATURE_LESSONS[f"cvt_ratio_rate_{low}_{high}"] = {
        "plain": (
            "Think of changing gears on a bike. You can pedal faster or slower for the same wheel "
            "speed. Your Civic can make that change smoothly. A higher dot means the two speed "
            "readings suggest it was adjusting faster during steady cruising."
        ),
        "source": _RATIO,
        "example": (
            "Divide candidate drive RPM by driven RPM at each sample. When that ratio goes "
            "from 0.80 to 0.84 in one second, the logarithmic change rate is about 4.9%/s. "
            "Reversing those two values gives the same magnitude. Each dot summarizes the "
            "median magnitude across qualifying cruise samples."
        ),
        "compare": (
            "Near zero means the ratio usually held steady during the selected stretches. A "
            "larger value means more movement. Grade, load and mode can all prompt a ratio "
            "adjustment. Check the signed trace for direction."
        ),
    }
