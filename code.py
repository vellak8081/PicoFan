# Kienan Vella's PicoFan V0.9.1
# A digital PWM fan controller implemented in CircuitPython, interfaced over usb serial.
# Targeted at the pi pico, but readily adapdable to other MCUs.

import board
import supervisor
import microcontroller
import time
import math
import analogio
import digitalio
import countio
import pwmio

# import our config files
import config
import bconf

# If the beta feature flag is set in config, enable beta features. Else leave them disabled.
beta_features = config.beta or False

# if our board has an alarm speaker/buzzer installed
if bconf.alarm and beta_features:
    try:
        from audioio import AudioOut
    except ImportError:
        try:
            from audiopwmio import PWMAudioOut as AudioOut
        except ImportError:
            pass  # not always supported by every board!
    speaker = AudioOut(board.GP28)

# if our board has a DS18B20 onboard, set it up
if bconf.digitalTemp and beta_features:
    from adafruit_onewire.bus import OneWireBus
    from adafruit_ds18x20 import DS18X20
    ow_bus = OneWireBus(board.GP22)
    devices = ow_bus.scan()
    tempDigital = []
    dtnum = 0
    for device in devices:
        if device.family_code == 40:
            dtempSensor.append(adafruit_ds18x20.DS18X20(ow_bus, devices[dtnum]))
            dtnum += 1 #count number of devices

if bconf.tach_mux or bconf.therm_mux:
    # mux control pins - the 74HC4052 is a dual pole quad throw mux, so 8 tachometers can be sampled two at a time, in 4 pairs
    muxA = digitalio.DigitalInOut(board.GP8)
    muxB = digitalio.DigitalInOut(board.GP10)

    muxA.direction = digitalio.Direction.OUTPUT
    muxB.direction = digitalio.Direction.OUTPUT

# set up tachometer pins and flow sensor pin transition counters
# these tach channels either go directly to the fan tach outputs, or to one of the 74HC4052 muxes
tach0 = countio.Counter(board.GP11)
tach1 = countio.Counter(board.GP13)

if not bconf.tach_mux:
    tach2 = countio.Counter(board.GP7)
    tach3 = countio.Counter(board.GP9)
    # set up tachometer arrays for calculated rpm
    RPM = [0, 0, 0, 0]

elif bconf.tach_mux:
    RPM = [0, 0, 0, 0, 0, 0, 0, 0]
    mchan = 0 #used in the main loop for a mini state machine to cycle through mux channels

# populate any unlabeled fan channels with a default label
newlabel = {}
for f in RPM:
    try:
    	newlabel[f - 1] = fanLabel[f - 1]
    except:
    	newlabel[f - 1] = "Fan" + str(f - 1)
fanLabel = newlabel

# pwm out setup
freq = 1000
pct = config.defdc
spd = int(pct * 65535 / 100)
fan0 = pwmio.PWMOut(board.GP0, frequency=freq, duty_cycle=spd)
fan1 = pwmio.PWMOut(board.GP1, frequency=freq, duty_cycle=spd)
fan2 = pwmio.PWMOut(board.GP2, frequency=freq, duty_cycle=spd)
fan3 = pwmio.PWMOut(board.GP3, frequency=freq, duty_cycle=spd)
fan4 = pwmio.PWMOut(board.GP4, frequency=freq, duty_cycle=spd)
fan5 = pwmio.PWMOut(board.GP5, frequency=freq, duty_cycle=spd)

if bconf.tach_mux:
    maxch = 7
    fan6 = pwmio.PWMOut(board.GP6, frequency=freq, duty_cycle=spd)
    fan7 = pwmio.PWMOut(board.GP7, frequency=freq, duty_cycle=spd)

    # initialize fanspeed and dutycycle array
    fandc = [pct, pct, pct, pct, pct, pct, pct, pct]
    fanSpeed = [spd, spd, spd, spd, spd, spd, spd, spd]

elif not bconf.tach_mux:
    maxch = 5
    # initialize fanspeed and dutycycle array
    fandc = [pct, pct, pct, pct, pct, pct]
    fanSpeed = [spd, spd, spd, spd, spd, spd]

# thermistors
therm0 = analogio.AnalogIn(board.A0)
therm1 = analogio.AnalogIn(board.A1)

# thermistor temp storage
temp = []
tavg = []
if not bconf.therm_mux:
    maxtherm = 1
    temp.append([0.0, 0.0, 0.0, 0.0])
    temp.append([0.0, 0.0, 0.0, 0.0]) # initialize array for averaging/smoothing to prevent fan revving
    tavg.append(0.0)
    tavg.append(0.0) #averaged temps

if bconf.therm_mux:
    maxtherm = 7
    # initialize arrays for averaging/smoothing to prevent fan revving
    for i in range(maxtherm + 1):
        temp.append([0.0, 0.0, 0.0, 0.0])
        tavg.append(0.0) #averaged temps

# populate any unlabeled thermistor channels with a default label
newlabel = {}
for f in range(maxtherm + 1):
    try:
    	newlabel[f - 1] = thermLabel[f - 1]
    except:
    	newlabel[f - 1] = "Temp" + str(f - 1)
tempLabel = newlabel

# populate unfilled labels for digital temp sensors
if bconf.digitalTemp and beta_features:
    if bconf.DtempOnBoard and not config.DthermLabelOverride:
        newLabel = []
        newLabel.append("Interior")
        for i in range(dtnum + 1):
            try:
                newLabel.append(config.DthermLabel[i])
            except:
                newLabel.append("Temp" + str(maxtherm + 1 + i))
        config.DthermLabel = newLabel

# get time
initial = time.monotonic()

def temperature(r, Ro=10000.0, To=25.0, beta=3950.0):
    import math
    cel = math.log(r / Ro) / beta      # log(R/Ro) / beta
    cel += 1.0 / (To + 273.15)         # log(R/Ro) / beta + 1/To
    cel = (1.0 / cel) - 273.15   # Invert, convert to C
    return cel

def Pct2val(pct):
    val = int(pct * 65535 / 100)
    return val

def ReadATherm(chan):
    import analogio
    rotated = [ 0.0, temp[chan][0], temp[chan][1], temp[chan][2] ]
    if (chan == 0 and not bconf.therm_mux) or (0 <= chan <= 3 and bconf.therm_mux):
        rotated[0] = temperature(1000/(65535/therm0.value - 1))
    if (chan == 1 and not bconf.therm_mux) or (4 <= chan <= 7 and bconf.therm_mux):
        rotated[0] = temperature(1000/(65535/therm1.value - 1))
    temp[chan] = rotated
    val = (temp[chan][0] + temp[chan][1] + temp[chan][2] + temp[chan][3]) / 4
    return val

def ReadProfile(fan):
    probe = config.profileSensor[fan]
    # temp is under the upper bound of the profile
    if ( tavg[probe] <= config.profileTemp[fan][0] ):
        return config.profileDC[fan][0]
    # temp is over the upper bound of the profile
    if ( tavg[probe] >= config.profileTemp[fan][4] ):
        # if the temperature is more than the overshoot value above the max set temp...
        if ( tavg[probe] >= ( config.profileTemp[fan][4] + config.overshoot )):
            return 100
        else:
            # set channel to full speed if we're above overshoot threshold, else set channel to max permitted in profile
            return config.profileDC[fan][4]
    # cycle through the fan profile value lists
    for index in range(4):
        # compare current index to the next index
        if ( config.profileTemp[fan][index] <= tavg[probe] <= config.profileTemp[fan][index + 1] ):
            # build a value map
            fromSpan = config.profileTemp[fan][index + 1] - config.profileTemp[fan][index]
            toSpan = config.profileDC[fan][index + 1] - config.profileDC[fan][index]
            # calculate a scale factor for PWM value
            Scaled = float(tavg[probe] - config.profileTemp[fan][index]) / float(fromSpan)
            # calculate and return the scaled pwm value
            val = int(config.profileDC[fan][index] + (Scaled * toSpan))
            return val

def PrintHFan():
    print("Fan#\t%DC\tRPM")
    for f in range(maxch + 1):
        if (not bconf.tach_mux and f <= 2) or bconf.tach_mux:
            print(f'{config.fanLabel[f]}:\t{fandc[f]}%\t{RPM[f]} RPM')
        elif not bconf.tach_mux and f >= 3:
            print(f'{config.fanLabel[f]}:\t{fandc[f]}%')

def PrintHTemp():
    for t in range(maxtherm + 1):
        print(f'{config.thermLabel[t]}:\t{tavg[t]} C')

def PrintHDTemp():
    for dt in range(dtnum + 1):
        print(f'{config.DthermLabel[dt]}:\t{tempDigital[dt]} C')

def PrintHAlarm():
    print("This feature is not implemented. You shouldn't be here....")

# main loop
while True:
    if supervisor.runtime.serial_bytes_available:
        fanNumber = -1
        # read in text (@fanNum, %dutycycle)
        # input() will block until a newline is sent
        inText = input().strip()
        # Sometimes Windows sends an extra (or missing) newline - ignore them
        if inText == "":
            continue

        # print fan duty cycle, fan rpm
        if inText.lower().startswith("*"):
            PrintHFan()
            PrintHTemp()
            if beta_features:
                if bconf.digitalTemp:
                    PrintHDTemp()
                if bconf.alarm:
                    PrintHAlarm()

        # reload config
        if inText.lower().startswith("r"):
            microcontroller.reset()

        # choose fan to manipulate - if not given, all fans will be set to the same speed
        if inText.lower().startswith("@"):
            fanNumber = inText[1:]

        # set fan speed with a "%" symbol
        if inText.startswith("%"):
            pctText = inText[1:]
            spd = Pct2val(pctText)

            if not 0 < fanNumber < maxch:
                # when no fan selected, or selection out of range, adjust speed of all fans
                for i in range(maxch + 1):
                    fandc[i] = pctText
                    fanSpeed[i] = spd

            else:
                # adjust speed of selected fan
                fandc[fanNumber] = pctText
                fanSpeed[fanNumber] = spd

    else:
        # set fan pwm duty cycles
        fan0.duty_cycle = fanSpeed[0]
        fan1.duty_cycle = fanSpeed[1]
        fan2.duty_cycle = fanSpeed[2]
        fan3.duty_cycle = fanSpeed[3]
        fan4.duty_cycle = fanSpeed[4]
        fan5.duty_cycle = fanSpeed[5]
        if bconf.tach_mux == True:
            fan6.duty_cycle = fanSpeed[6]
            fan7.duty_cycle = fanSpeed[7]

    for f in range(maxch + 1):
        try:
            fandc[f] = ReadProfile(f)
            fanSpeed[f] = Pct2val(fandc[f])
        except:
            pass

    # time, flies like an arrow
    now = time.monotonic()

    # get fan speeds and temps twice a second
    if now - initial > 0.500:

        if bconf.digitalTemp and beta_features:
            i = 0
            for sensor in dtempsensor:
                tempDigital[i] = Sensor.temperature
                i += 1

        # read and then clear tach counts

        if not bconf.tach_mux:
            RPM[0] = (tach0.count * 60) # * 60 to account for two pole tach, this is a simplification of count * 120 / 2
            tach0.reset()                  # it's possible this will have to be configurable for different fan tach types
            RPM[1] = (tach1.count * 60)
            tach1.reset()
            RPM[2] = (tach2.count * 60)
            tach2.reset()
            RPM[3] = (tach3.count * 60)
            tach3.reset()

        if not bconf.therm_mux:
            # rotate arrays and read temp sensors
            tavg[0] = ReadATherm(0)
            tavg[1] = ReadATherm(1)

        if bconf.tach_mux or bconf.therm_mux:
            # get tach counts, then set mux channel selection for next measurement
            if mchan == 0:
                if bconf.tach_mux:
                    RPM[3] = (tach0.count * 60) # * 60 to account for two pole tach, this is a simplification of count * 120 / 2
                    RPM[7] = (tach1.count * 60) # it's possible this will have to be configurable for different fan tach types

                if bconf.therm_mux:
                    tavg[3] = ReadATherm(3)
                    tavg[7] = ReadATherm(7)

            # change muxes for next reading.
            # this is slightly confusing at first glance, but what's going on here is:
            # because we are using countio to read the tach transitions, we need to leave
            # the mux in a given configuration for 0.5 seconds to allow the count to accumulate.
            # so on a given run through this structure, we read the counts from the pwm hardware
            # first, then reconfigure for the next run, and finally reset the counters.
                muxA.value = False
                muxB.value = False

                if bconf.tach_mux:
                    # reset tach counts
                    tach0.reset()
                    tach1.reset()

            if mchan == 1:
                if bconf.tach_mux:
                    RPM[0] = (tach0.count * 60)
                    RPM[4] = (tach1.count * 60)

                if bconf.therm_mux:
                    tavg[0] = ReadATherm(0)
                    tavg[4] = ReadATherm(4)

                muxA.value = True
                muxB.value = False

                if bconf.tach_mux:
                    tach0.reset()
                    tach1.reset()

            if mchan == 2:
                if bconf.tach_mux:
                    RPM[1] = (tach0.count * 60)
                    RPM[5] = (tach1.count * 60)

                if bconf.therm_mux:
                    tavg[1] = ReadATherm(1)
                    tavg[5] = ReadATherm(5)

                muxA.value = False
                muxB.value = True

                if bconf.tach_mux:
                    tach0.reset()
                    tach1.reset()

            if mchan == 3:
                if bconf.tach_mux:
                    RPM[2] = (tach0.count * 60)
                    RPM[6] = (tach1.count * 60)

                if bconf.therm_mux:
                    tavg[2] = ReadATherm(2)
                    tavg[6] = ReadATherm(6)

                muxA.value = True
                muxB.value = True

                if bconf.tach_mux:
                    tach0.reset()
                    tach1.reset()

            if mchan < 3:
                mchan += 1
            else:
                mchan = 0

        # reset timer reference
        initial = now
