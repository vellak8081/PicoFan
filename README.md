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
- experimental support for multiple Dallas/Maxim DS18b20 digital temperature sensors
- easily reprogrammable - arguably, that's more a feature of CircuitPython though

A controller like this is mostly intended for custom or semi-custom open loop water cooling setups, but with very thin thermistors or some host side scripting this could easily be configured to control fan speeds on air cooled systems or systems with AIO liquid coolers.

# Fan/PWM Profiles
All configurable settings as of v0.8 are no longer defined in boot.py itself. 
They have now been moved to config.py to allow for easier interfacing by config generators, and makes things a little more user friendly.

Fan profiles are defined in the profileTemp, profileDC, and profileSensor lists.
'profileTemp' and 'ProfileDC' are lists of lists - with the inner lists corresponding to fan channels in the same order as the fanLabel list.

```python
thermLabel = [ "Rad in", "Rad out" ]
fanLabel = [ "front1", "front2", "front3", "top1", "top2", "top3", "pump1", "pump2" ]
profileTemp = [ [0, 30, 40, 50, 60], [0, 30, 40, 50, 60] ]
profileDC = [ [25, 40, 50, 70, 100], [25, 40, 50, 70, 100] ]
profileSensor = [ 0, 1 ]
overshoot = 5
```

'profileTemp' defines the temperature setpoints of the curve, in degrees celcius.
The first element of each inner list should really be 0, setting a default RPM setting, and allowing the controller to interpolate between there and the next point. The way the profile function is set up, if the sensed temperature is below the first element in the profileTemp list for that channel, the channel will be set to the duty cycle defined as the lowest in the profile. 

profileDC defines the pwm Duty Cycle setpoints of the curve, in percent. 
The first element of each inner list is the initial (default) PWM setting of the corresponding channel, with the last element of each inner list being the max PWM setting.

There is simple linear interpolation implemented in the fan curve profile follower function - so there won't be massive RPM changes with small temperature changes (unless you've set a large delta between steps), but it won't be a perfectly smooth curve either.

'profileSensor' defines which temperature sensor the given pwm channel uses for its temperature source when following the given fan curve.
'overshoot' is the amount by which the sensed temperature can exceed the max temperature set in the fan curve before the controller forces the fan to 100% duty cycle, in degrees celcius.

If you want your fans to be off below a set temperature, set the lowest duty cycle to between 1-5% as most fans won't spin at such a low PWM duty cycle. Set the second lowest temperature in the profile to the temp you want your fans to turn on at, and set the lowest temperature slightly below that, about 5c should be right. Your second pwm duty cycle definition should be over 25% to ensure your fans spin up. 

You do lose a bit of your curve by doing this, but with interpolation, you probably won't notice much.

# Board features
Board specific configuration options have been moved to bconf.py as of 0.9
'tach_mux' and 'therm_mux' indicate if the muxes are present.
'digitalTemp' indicates if you are using DS18b20 digital temperature sensors (experimental support).
'DtempOnboard' indicates if your board has a DS18b20 soldered to the fan controller board.
```python
tach_mux = True
therm_mux = False
digitalTemp = False
DtempOnboard = False
```
# Hardware
There's currently no official hardware available, but there is a reference hardware design being worked on over on CircuitMaker: https://workspace.circuitmaker.com/Projects/Details/KienanVella/PicoFan-v1

# To Do
One of the glaring omissions from the current featureset is DRGB strip support. This should be pretty easy to add, I just haven't implemented it as my personal use case doesn't have any RGB. ¯\\_(ツ)_/¯

Another glaring omission is that currently, there is no configuration client. However, it's being planned.
It will be cross platform - the current plan is to build a python backend with flask, with a  frontend running in any browser.
The intent is to also be able to use sensor data from the host OS and pass it to the controller over a simple serial link - though this will make the controller not standalone anymore. It's highly recommended that even once it's possible to use only on-die sensors, that you at least have a fluid temperature sensor somewhere in your loop as a safety feature.
Potentially, you could expose the frontend externally and run it on a tablet or some other auxiliary device as a semi-dedicated hardware monitoring panel.

If you have experience building cross platform desktop apps, collecting cpu/gpu temperature sensor data across platforms, working with Flask, or working with javascript - or you would like to otherwise contribute, get in touch!

Hardware. A reference design is being worked on - see the 'Hardware' section above.

# Notes
This is considered to be Alpha software. Use at your own risk, I take no responsibility for your actions or your system if you use this firmware and you overheat your system due to a bug or improper operation. 

Default fan curves are semi-sane, but you should set your own curves before using.

Without Muxes, only 6 PWM output channels are supported.

In order to use the tachometer on all 8 pwm fan channels requires the use of a 74HC4052 analog mux connected as follows

| tach mux pin | pico pin |
|---------|----------|
|    A    |    GP8   |
|    B    |    GP10   |
|    X    |    GP11  |
|    Y    |    GP13  |

The mux for thermistors is wired similarly, and uses the exact same 74HC4052 analog mux. Both muxes share the same control lines

| therm mux pin | pico pin |
|---------|----------------|
|    A    |    GP8         |
|    B    |    GP10         |
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
