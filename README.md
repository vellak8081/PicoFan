# PicoFan
An open source 6 to 8 channel PWM fan controller written in CircuitPython for the Raspberry Pi pico

This firmware is intended to be used to build a high end DIY open source fan controller, similar to the Corsair Commander Pro or the Aquacomputer Octo.

# Features
- 6 to 8 PWM fan control channels
- 4 to 8 tachometer/flow meter channels
- support for up to 2 thermistors for sensing air or liquid temperature
- fully configurable channel naming
- fully configurable fan speed curves based on thermistor readings
- fully independant from the host system
- easily reprogrammable - arguably, that's more a feature of CircuitPython though

A controller like this is mostly intended for custom or semi-custom open loop water cooling setups, but with very thin thermistors or some host side scripting this could easily be configured to control fan speeds on air cooled systems or systems with AIO liquid coolers.

# Fan/PWM Profiles
All configurable settings as of v0.5 are defined in code.py itself. 
Fan profiles are defined in the profileTemp, profileDC, and profileSensor lists.
profileTemp and ProfileDC are lists of lists - with the inner lists corresponding to fan channels in the same order as the fanLabel list.

```python
profileTemp = [ [0, 30, 40, 50, 60], [0, 30, 40, 50, 60] ]
profileDC = [ [25, 40, 50, 70, 100], [25, 40, 50, 70, 100] ]
profileSensor = [ 0, 1 ]
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

| mux pin | pico pin |
|---------|----------|
|    A    |    GP8   |
|    B    |    GP9   |
|    X    |    GP11  |
|    Y    |    GP13  |
