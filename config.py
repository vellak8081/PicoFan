# Settings

# If you have DS18B20 digital temperature sensors attached to the dtherm 3 pin header, these are defined in order from the controller.
# If your board has a sensor on it, that sensor will show before these, and is automatically listed as "Interior".
DthermLabel = [ "Intake", "Exhaust" ]

# If you would like to override the default label for the onboard sensor
# (eg, if you put the board in your case's PSU basement), uncomment the following line
#DthermLabelOverride = True

thermLabel = [ "Loop 1", "Loop 2", "Ambient", "CPU", "CPU VRM", "Chipset", "GPU", "GPU VRM"  ] # there should be 2 labels here, or 8 if you have a thermistor mux.
fanLabel = [ "front1", "front2", "front3", "top1", "top2", "top3", "pump1", "pump2" ]  # there should be 6 labels here, or 8 if you have a tachometer mux connected.

# Fan profile - the profileTemp list is temperatures in degrees celcius, the profileDC list is fan pwm %, mapped to the profileTemp list.
# both outer lists need to have the same number of elements, corresponding to the fanLabel positions above.
# The profileSensor list ties a specific pwm channel to a specific temperature sensor, eg, if you have two loops, some block sensors, and an air sensor.
# ProfileSensor values should be 0 to 1 when there's no mux, and 0 to 7 when there is a mux in use.
# overshoot is the amount in degrees celcius to allow the temp probe to exceed the max fan profile preset before setting channel pwm dutycycle to 100%
# if you have 3  pin fans or non-pwm pumps attached for rpm monitoring, make sur they are at the end of the channel chain (eg, two 3 pin pumps in channel 6 and 7)
# these profiles will do nothing for 3 pin devices - there is NO voltage control implemented as of v0.8.
profileTemp = [ [0, 30, 40, 50, 60], [0, 30, 40, 50, 60] ]
profileDC = [ [25, 40, 50, 70, 100], [25, 40, 50, 70, 100] ]
profileSensor = [ 0, 1 ]
overshoot = 5
defdc = 50 # default duty cycle to set fans to when no fan curve is defined. A desktop agent can be used to control fan speeds after boot completes.
