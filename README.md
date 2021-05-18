# PicoFan
An open source 6 to 8 channel PWM fan controller written in CircuitPython for the Raspberry Pi pico

This firmware is intended to be used to build a high end DIY open source fan controller, similar to the Corsair Commander Pro or the Aquacomputer Octo.

# Features
- 6 to 8 PWM fan control channels
- 4 tachometer/flow meter channels without additional hardware, or up to 8 tachometer channels with an additional mux
- support for up to 2 thermistors without additional hardware, or up to 8 thermistors with an additional mux
- fully configurable fan and thermistor channel naming
- fully configurable fan speed curves based on thermistor readings
- fully independant from the host system
- interactive interface for listing current state
- easily reprogrammable - arguably, that's more a feature of CircuitPython though

A controller like this is mostly intended for custom or semi-custom open loop water cooling setups, but with very thin thermistors or some host side scripting this could easily be configured to control fan speeds on air cooled systems or systems with AIO liquid coolers.

# Fan/PWM Profiles
All configurable settings as of v0.7 are defined in code.py itself. 
Fan profiles are defined in the profileTemp, profileDC, and profileSensor lists.
'profileTemp' and 'ProfileDC' are lists of lists - with the inner lists corresponding to fan channels in the same order as the fanLabel list.
'profileTemp' defines the temperature part of the curve in degrees Celcius.
'profileDC' defines the PWM Duty Cycle at a given temperature within the curve, in percent.
'tach_mux' and 'therm_mux' indicate if the muxes are present

There is simple linear interpolation implemented in the fan curve profile follower function - so there won't be massive RPM changes with small temperature changes (unless you've set a large delta between steps), but it won't be a perfectly smooth curve either.

'profileSensor' defines which temperature sensor the given pwm channel uses for its temperature source when following the given fan curve.
'overshoot' is the amount by which the sensed temperature can exceed the max temperature set in the fan curve before the controller forces the fan to 100% duty cycle, in degrees celcius.

The way the profile function is set up, if the sensed temperature is below the first element in the profileTemp list for that channel, the channel will be set to the duty cycle defined as the lowest in the profile. 
If you want your fans to be off below a set temperature, set the lowest duty cycle to between 1-5%, most fans won't spin at such a low PWM duty cycle.

```python
tach_mux = True
therm_mux = False
thermLabel = [ "Rad in", "Rad out" ]
fanLabel = [ "front1", "front2", "front3", "top1", "top2", "top3", "pump1", "pump2" ]
profileTemp = [ [0, 30, 40, 50, 60], [0, 30, 40, 50, 60] ]
profileDC = [ [25, 40, 50, 70, 100], [25, 40, 50, 70, 100] ]
profileSensor = [ 0, 1 ]
overshoot = 5
```

profileTemp defines the temperature setpoints of the curve.
The first element of each inner list should really be 0, setting a default RPM setting.

profileDC defines the pwm Duty Cycle setpoints of the curve. 
The first element of each inner list is the initial (default) PWM setting of the corresponding channel, with the last element of each inner list being the max PWM setting.

profileSensor defines which thermistor each PWM channel uses to apply the profile.

# Notes
This is considered to be Alpha software. Use at your own risk, I take no responsibility for your actions or your system if you use this firmware and you overheat your system due to a bug or improper operation. 

Default fan curves are semi-sane, but you should set your own curves before using.

In order to use the tachometer on all 8 pwm fan channels requires the use of a 74HC4052 analog mux connected as follows

| tach mux pin | pico pin |
|---------|----------|
|    A    |    GP8   |
|    B    |    GP9   |
|    X    |    GP11  |
|    Y    |    GP13  |

The mux for thermistors is wired similarly, and uses the exact same 74HC4052 analog mux. Both muxes share the same control lines

| therm mux pin | pico pin |
|---------|----------------|
|    A    |    GP8         |
|    B    |    GP9         |
|    X    |    GP26 (A0)   |
|    Y    |    GP27 (A1)   |

It's quite possible that your mux chip's datasheet calls these pins something else. 
A and B in this case, are sometimes called S0 and S1 respectively, and are used for selecting which channel of the muxes are connected to the mux commons.
X and Y are sometimes called An and Bn, or 1Z and 2Z respectively, and are the mux common in/out. 
For the purpose of clarity, I'll be using X and Y from here forward, with X1 and Y1 being the first channel of each mux, etc. 
Whatever your mux calls them, that's what you need to connect.

Both muxes use the following channel mapping arrangement

| mux pin | therm/tach channel # |
|---------|----------------------|
|  X1     |         0            |
|  X2     |         1            |
|  X3     |         2            |
|  X4     |         3            |
|  Y1     |         4            |
|  Y2     |         5            |
|  Y3     |         6            |
|  Y4     |         7            |
