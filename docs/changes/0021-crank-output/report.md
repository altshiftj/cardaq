# Estimating crank output from recorded replies

The Civic captures preserve Mode 01 indicated torque (62), reference torque (63), friction torque (8E), and engine RPM (0C). These channels arrive in separate polls. The November 24 and 25 examples at 118 km/h have different reference values, 204 and 185 N·m. A fixed rated torque would lose that difference.

CARB describes using the reference torque and the difference between indicated and friction fractions to calculate net brake torque in a medium-duty diesel test. Applying the relationship to this Civic gives a provisional ECU-based estimate. The scale still needs independent vehicle validation. [CARB calculation, page 217](https://ww2.arb.ca.gov/sites/default/files/barcu/regact/2015/obdii2015/finalregorder2.pdf#page=217)
