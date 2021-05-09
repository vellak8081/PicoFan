# PicoFan
An open source 6 to 8 channel PWM fan controller written in CircuitPython for the Raspberry Pi pico

This firmware is intended to be used to build a high end DIY open source fan controller, similar to the Corsair Commander Pro or the Aquacomputer Octo.

Features:
- 6 to 8 PWM fan control channels
- 4 to 8 tachometer/flow meter channels
- support for up to 2 thermistors for sensing air or liquid temperature
- fully configurable channel naming
- fully configurable fan speed curves based on thermistor readings (in development)
- fully independant from the host system
- easily reprogrammable - arguably, that's more a feature of CircuitPython though

A controller like this is mostly intended for custom or semi-custom open loop water cooling setups, but with very thin thermistors or some host side scripting this could easily be configured to control fan speeds on air cooled systems or systems with AIO liquid coolers.
