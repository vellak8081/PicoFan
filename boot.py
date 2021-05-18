# Kienan Vella's PicoFan V0.7
# A digital PWM fan controller implemented in CircuitPython, interfaced over usb serial.
# Targeted at the pi pico, but readily adapdable to other MCUs.

import board
import supervisor
import storage
import time
import math
import analogio
import digitalio
import countio
import pwmio

# settings
# without a mux, there are 6 channels of pwm out, with 4 of them having speed sensors
# with a mux for tachometers, you can have up to 8 channels with pwm out, and all 8 of them can have speed sensors.
# without a mux, there are 2 thermistor channels.
# with a mux connected for thermistors, you can have up to 8 thermistors.

tach_mux = True # only set this to true if you have a 74HC4052 connected to expand the number of tachometer channels.
therm_mux = False # only set this to true if you have a 74HC4052 connected to expand the number of thermistor channels.
thermLabel = [ "Loop 1", "Loop 2", "Ambient", "CPU", "CPU VRM", "Chipset", "GPU", "GPU VRM"  ] # there should be 2 labels here, or 8 if you have a thermistor mux.
fanLabel = [ "front1", "front2", "front3", "top1", "top2", "top3", "pump1", "pump2" ]  # there should be 6 labels here, or 8 if you have a tachometer mux connected.

# Fan profile - the profileTemp list is temperatures in degrees celcius, the profileDC list is fan pwm %, mapped to the profileTemp list.
# both outer lists need to have the same number of elements, corresponding to the fanLabel positions above.
# The profileSensor list ties a specific pwm channel to a specific temperature sensor, eg, if you have two loops, some block sensors, and an air sensor.
# ProfileSensor values should be 0 to 1 when there's no mux, and 0 to 7 when there is a mux in use.
# overshoot is the amount in degrees celcius to allow the temp probe to exceed the max fan profile preset before setting channel pwm dutycycle to 100%
# if you have 3  pin fans or non-pwm pumps attached for rpm monitoring, make sur they are at the end of the channel chain (eg, two 3 pin pumps in channel 6 and 7)
# these profiles will do nothing for 3 pin devices - there is NO voltage control implemented as of v0.3.
profileTemp = [ [0, 30, 40, 50, 60], [0, 30, 40, 50, 60] ]
profileDC = [ [25, 40, 50, 70, 100], [25, 40, 50, 70, 100] ]
profileSensor = [ 0, 1 ]
overshoot = 5

#### SETTINGS END HERE ####

# set up tachometer pins and flow sensor pin transition counters
if not tach_mux:
    tach0 = countio.Counter(board.GP7)
    tach1 = countio.Counter(board.GP9)
    tach2 = countio.Counter(board.GP11)
    tach3 = countio.Counter(board.GP13)
    # set up tachometer arrays for calculated rpm
    RPM = [0, 0, 0, 0]
elif tach_mux:
    # set up two tach input channels that our 74HC4052 mux will connect to
    tach0 = countio.Counter(board.GP11)
    tach1 = countio.Counter(board.GP13)
    # mux control pins - the 74HC4052 is a dual pole quad throw mux, so 8 tachometers can be sampled two at a time, in 4 pairs
    muxA = digitalio.DigitalInOut(board.GP8)
    muxB = digitalio.DigitalInOut(board.GP9)

    muxA.direction = digitalio.Direction.OUTPUT
    muxB.direction = digitalio.Direction.OUTPUT

    RPM = [0, 0, 0, 0, 0, 0, 0, 0]
    mchan = 0 #used in the main loop for a mini state machine to cycle through mux channels

# pwm out setup
freq = 1000
pct = 50
spd = int(pct * 65535 / 100)
fan0 = pwmio.PWMOut(board.GP0, frequency=freq, duty_cycle=spd)
fan1 = pwmio.PWMOut(board.GP1, frequency=freq, duty_cycle=spd)
fan2 = pwmio.PWMOut(board.GP2, frequency=freq, duty_cycle=spd)
fan3 = pwmio.PWMOut(board.GP3, frequency=freq, duty_cycle=spd)
fan4 = pwmio.PWMOut(board.GP4, frequency=freq, duty_cycle=spd)
fan5 = pwmio.PWMOut(board.GP5, frequency=freq, duty_cycle=spd)

if tach_mux:
    maxch = 7
    fan6 = pwmio.PWMOut(board.GP6, frequency=freq, duty_cycle=spd)
    fan7 = pwmio.PWMOut(board.GP7, frequency=freq, duty_cycle=spd)

    # initialize fanspeed and dutycycle array
    fandc = [pct, pct, pct, pct, pct, pct, pct, pct]
    fanSpeed = [spd, spd, spd, spd, spd, spd, spd, spd]

elif not tach_mux:
    maxch = 5
    # initialize fanspeed and dutycycle array
    fandc = [pct, pct, pct, pct, pct, pct]
    fanSpeed = [spd, spd, spd, spd, spd, spd]

# thermistors
therm0 = analogio.AnalogIn(board.A0)
therm1 = analogio.AnalogIn(board.A1)

# thermistor temp storage
if not therm_mux:
    temp = [ [0.0, 0.0, 0.0, 0.0], [0.0, 0.0, 0.0, 0.0] ] # array for averaging/smoothing to prevent fan revving
    tavg = [0.0, 0.0] #averaged temps
    maxtherm = 1
    
if therm_mux:
    # array for averaging/smoothing to prevent fan revving
    temp = [ [0.0, 0.0, 0.0, 0.0], [0.0, 0.0, 0.0, 0.0], [0.0, 0.0, 0.0, 0.0], [0.0, 0.0, 0.0, 0.0], [0.0, 0.0, 0.0, 0.0], [0.0, 0.0, 0.0, 0.0], [0.0, 0.0, 0.0, 0.0], [0.0, 0.0, 0.0, 0.0] ]
    tavg = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0] #averaged temps
    maxtherm = 7

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
    if (chan == 0 and not therm_mux) or (0 <= chan <= 3 and therm_mux):
        rotated[0] = temperature(1000/(65535/therm0.value - 1))
    if (chan == 1 and not therm_mux) or (4 <= chan <= 7 and therm_mux):
        rotated[0] = temperature(1000/(65535/therm1.value - 1))
    temp[chan] = rotated
    val = (temp[chan][0] + temp[chan][1] + temp[chan][2] + temp[chan][3]) / 4
    return val

def ReadProfile(fan):
    probe = profileSensor[fan]
    # temp is under the upper bound of the profile
    if ( tavg[probe] <= profileTemp[fan][0] ):
        return profileDC[fan][0]
    # temp is over the upper bound of the profile
    if ( tavg[probe] >= profileTemp[fan][4] ):
        # if the temperature is more than the overshoot value above the max set temp...
        if ( tavg[probe] >= ( profileTemp[fan][4] + overshoot )):
            return 100
        else:
            # set channel to full speed if we're above overshoot threshold, else set channel to max permitted in profile
            return profileDC[fan][4]
    # cycle through the fan profile value lists
    for index in range(4):
        # compare current index to the next index
        if ( profileTemp[fan][index] <= tavg[probe] <= profileTemp[fan][index + 1] ):
            # build a value map
            fromSpan = profileTemp[fan][index + 1] - profileTemp[fan][index]
            toSpan = profileDC[fan][index + 1] - profileDC[fan][index]
            # calculate a scale factor for PWM value
            Scaled = float(tavg[probe] - profileTemp[fan][index]) / float(fromSpan)
            # calculate and return the scaled pwm value
            val = int(profileDC[fan][index] + (Scaled * toSpan))
            return val

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
            print("Fan#    %DC    RPM")
            for f in range(maxch + 1):
                if (tach_mux == False and f <= 2) or tach_mux == True:
                    print(f'{fanLabel[f]}: {fandc[f]}% {RPM[f]} RPM')
                elif tach_mux == False and f >= 3:
                    print(f'{fanLabel[f]}: {fandc[f]}%')
            for t in range(maxtherm + 1):
                print(f'{thermLabel[t]}: {tavg[t]} C')

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
        if tach_mux == True:
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

    # get fan speeds twice a second
    if now - initial > 0.500:
        # read and then clear tach counts

        if not tach_mux:
            RPM[0] = (tach0.count * 60) # * 60 to account for two pole tach, this is a simplification of count * 120 / 2
            tach0.reset()                  # it's possible this will have to be configurable for different fan tach types
            RPM[1] = (tach1.count * 60)
            tach1.reset()
            RPM[2] = (tach2.count * 60)
            tach2.reset()
            RPM[3] = (tach3.count * 60)
            tach3.reset()

        if not therm_mux:
            # rotate arrays and read temp sensors
            tavg[0] = ReadATherm(0)
            tavg[1] = ReadATherm(1)

        if tach_mux or therm_mux:
            # get tach counts, then set mux channel selection for next measurement
            if mchan == 0:
                if tach_mux:
                    RPM[3] = (tach0.count * 60) # * 60 to account for two pole tach, this is a simplification of count * 120 / 2
                    RPM[7] = (tach1.count * 60) # it's possible this will have to be configurable for different fan tach types
                
                if therm_mux:
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
 
                if tach_mux:
                    # reset tach counts
                    tach0.reset()
                    tach1.reset()

            if mchan == 1:
                if tach_mux:
                    RPM[0] = (tach0.count * 60)
                    RPM[4] = (tach1.count * 60)
                
                if therm_mux:
                    tavg[0] = ReadATherm(0)
                    tavg[4] = ReadATherm(4)

                muxA.value = True
                muxB.value = False
                
                if tach_mux:
                    tach0.reset()
                    tach1.reset()

            if mchan == 2:
                if tach_mux:
                    RPM[1] = (tach0.count * 60)
                    RPM[5] = (tach1.count * 60)
                
                if therm_mux:
                    tavg[1] = ReadATherm(1)
                    tavg[5] = ReadATherm(5)
                
                muxA.value = False
                muxB.value = True
                
                if tach_mux:
                    tach0.reset()
                    tach1.reset()

            if mchan == 3:
                if tach_mux:
                    RPM[2] = (tach0.count * 60)
                    RPM[6] = (tach1.count * 60)
                
                if therm_mux:
                    tavg[2] = ReadATherm(2)
                    tavg[6] = ReadATherm(6)

                muxA.value = True
                muxB.value = True
                
                if tach_mux:
                    tach0.reset()
                    tach1.reset()

            if mchan < 3:
                mchan += 1
            else:
                mchan = 0

        # reset timer reference
        initial = now
