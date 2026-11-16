# Requirements

### H1: Square body baseline sheds with high drag

WHEN aspect is 1, corner is 0, splitter is 0 and angle is 0, THE system SHALL show vortex shedding with cd between 1.4 and 2.8.

```prediction
[[prediction]]
id = "P1"
measurement = "cd"
range = [1.4, 2.8]
label = "inside"
[prediction.when]
aspect = 1.0
corner = 0.0
splitter = 0.0
angle = 0.0

[[prediction]]
id = "P2"
measurement = "shedding"
range = [0.5, 1.5]
label = "inside"
[prediction.when]
aspect = 1.0
corner = 0.0
splitter = 0.0
angle = 0.0
```

### H2: Longer body lowers drag

WHEN aspect rises from 0.5 to 3 with corner 0, splitter 0 and angle 0, THE system SHALL show falling cd, with cd at aspect 3 between 0.6 and 1.4 and cd at aspect 0.5 above 1.5.

```prediction
[[prediction]]
id = "P1"
measurement = "cd"
range = [0.6, 1.4]
label = "new-combination"
[prediction.when]
aspect = 3.0
corner = 0.0
splitter = 0.0
angle = 0.0

[[prediction]]
id = "P2"
measurement = "cd"
range = [1.5, 2.8]
label = "new-combination"
[prediction.when]
aspect = 0.5
corner = 0.0
splitter = 0.0
angle = 0.0
```

### H3: Rounded long body with plate or angle weakens shedding

WHEN aspect is 3 and corner is 1, THE system SHALL have lower cd and lower cl_amp than the aspect 3 square-cornered body (cd 1.29, cl_amp 0.22), and with a splitter of 3 THE system SHALL stop shedding.

```prediction
[[prediction]]
id = "P1"
measurement = "cd"
range = [0.5, 1.25]
label = "new-combination"
[prediction.when]
aspect = 3.0
corner = 1.0
splitter = 0.0
angle = 0.0

[[prediction]]
id = "P2"
measurement = "cl_amp"
range = [0.0, 0.2]
label = "new-combination"
[prediction.when]
aspect = 3.0
corner = 1.0
splitter = 0.0
angle = 0.0

[[prediction]]
id = "P3"
measurement = "cl_amp"
range = [0.0, 0.1]
label = "new-combination"
[prediction.when]
aspect = 3.0
corner = 1.0
splitter = 3.0
angle = 0.0
```

### H4: Splitter length of 2 suffices to stop shedding on the rounded long body, and shorter body with long plate also stops

WHEN aspect is 3, corner is 1 and splitter is 2, THE system SHALL not shed and give cd below that of splitter 3 plus 0.1.

```prediction
[[prediction]]
id = "P1"
measurement = "cl_amp"
range = [0.0, 0.01]
label = "new-combination"
[prediction.when]
aspect = 3.0
corner = 1.0
splitter = 2.0
angle = 0.0

[[prediction]]
id = "P2"
measurement = "cd"
range = [0.9, 1.12]
label = "new-combination"
[prediction.when]
aspect = 3.0
corner = 1.0
splitter = 2.0
angle = 0.0

[[prediction]]
id = "P3"
measurement = "cd"
range = [0.9, 1.4]
label = "new-combination"
[prediction.when]
aspect = 2.0
corner = 1.0
splitter = 3.0
angle = 0.0
```

### H5: Plate keeps shorter bodies steady, and small angle adds lift and drag

WHEN corner is 1 and splitter is 3, THE system SHALL stay steady at aspect 1.5 with cd between 0.9 and 1.25, and WHEN angle is 3 at aspect 2 THE system SHALL show cd above 0.993 and cl_mean above 0.1.

```prediction
[[prediction]]
id = "P1"
measurement = "cl_amp"
range = [0.0, 0.01]
label = "new-combination"
[prediction.when]
aspect = 1.5
corner = 1.0
splitter = 3.0
angle = 0.0

[[prediction]]
id = "P2"
measurement = "cd"
range = [0.9, 1.25]
label = "new-combination"
[prediction.when]
aspect = 1.5
corner = 1.0
splitter = 3.0
angle = 0.0

[[prediction]]
id = "P3"
measurement = "cl_mean"
range = [0.1, 1.5]
label = "new-combination"
[prediction.when]
aspect = 2.0
corner = 1.0
splitter = 3.0
angle = 3.0

[[prediction]]
id = "P4"
measurement = "cd"
range = [0.995, 1.6]
label = "new-combination"
[prediction.when]
aspect = 2.0
corner = 1.0
splitter = 3.0
angle = 3.0
```

### H6: Best point has cd near 0.99 or lower with no shedding

WHEN corner is 1, angle is 0 and the splitter is 2.2 at aspect 2, or 3 at aspect 1.7 or 2.5, THE system SHALL be steady with cd below 1.02.

```prediction
[[prediction]]
id = "P1"
measurement = "cd"
range = [0.9, 1.02]
label = "new-combination"
[prediction.when]
aspect = 2.0
corner = 1.0
splitter = 2.2
angle = 0.0

[[prediction]]
id = "P2"
measurement = "cd"
range = [0.9, 1.02]
label = "new-combination"
[prediction.when]
aspect = 1.7
corner = 1.0
splitter = 3.0
angle = 0.0

[[prediction]]
id = "P3"
measurement = "cd"
range = [0.9, 1.02]
label = "new-combination"
[prediction.when]
aspect = 2.5
corner = 1.0
splitter = 3.0
angle = 0.0
```
