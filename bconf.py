# Board config - this file defines what features are implemented on your board.
# without a mux, there are 6 channels of pwm out, with 4 of them having speed sensors
# with a mux for tachometers, you can have up to 8 channels with pwm out, and all 8 of them can have speed sensors.
# without a mux, there are 2 thermistor channels.
# with a mux connected for thermistors, you can have up to 8 thermistors.

tach_mux = True # only set this to true if you have a 74HC4052 connected to expand the number of tachometer channels.
therm_mux = False # only set this to true if you have a 74HC4052 connected to expand the number of thermistor channels.
digitalTemp = False # only set this to true if you are using DS18B20 devices, including any fitted onboard.
DtempOnboard = False # only set this to true if your board has a DS18B20 fitted onboard
