# Kienan Vella's PicoFan V0.5
# A digital PWM fan controller implemented in CircuitPython, interfaced over usb serial.
# Targeted at the pi pico, but readily adapdable to other MCUs.

import board
import supervisor
import time
import math
import analogio
import digitalio
import countio
import pwmio

# settings
# without a mux, there are 6 channels of pwm out, with 4 of them having speed sensors
# with a mux, you can have up to 8 channels with pwm out, and all 8 of them can have speed sensors.

mux = True # only set this to true if you have a 74HC4052 connected. The MAX4692 should also be compatible, though packaging is not very accessible for most hobbyists.
thermLabel = [ "Rad in", "Rad out" ]
fanLabel = [ "front1", "front2", "front3", "top1", "top2", "top3", "pump1", "pump2" ]  # there should be 6 labels here, or 8 if you have a mux connected.

# Fan profile - the profileTemp list is temperatures in degrees celcius, the profileDC list is fan pwm %, mapped to the profileTemp list.
# The profileSensor list ties a specific pwm channel to a specific temperature sensor, eg, if you have two loops.
# both lists need to have the same number of elements, corresponding to the fanLabel positions above.
# if you have 3  pin fans or non-pwm pumps attached for rpm monitoring, make sure they are at the end of the channel chain (eg, two 3 pin pumps in channel 6 and 7)
# these profiles will do nothing for 3 pin devices - there is NO voltage control implemented as of v0.3.
profileTemp = [ [0, 30, 40, 50, 60], [0, 30, 40, 50, 60] ]
profileDC = [ [25, 40, 50, 70, 100], [25, 40, 50, 70, 100] ]
profileSensor = [ 0, 1, 0, 1, 0, 1, 0, 1 ]

# set up tachometer pins and flow sensor pin transition counters
if mux == False:
    tach0 = countio.Counter(board.GP7)
    tach1 = countio.Counter(board.GP9)
    tach2 = countio.Counter(board.GP11)
    tach3 = countio.Counter(board.GP13)
    # set up tachometer arrays for pulse counts and calculated rpm
    RPM = [0, 0, 0, 0]
elif mux == True:
    # set up two tach input channels that our 74HC4052 mux will connect to
    tach0 = countio.Counter(board.GP11)
    tach1 = countio.Counter(board.GP13)
    # mux control pins - the 74HC4052 is a dual pole quad throw mux, so 8 tachometers can be sampled two at a time, in 4 pairs
    muxA = digitalio.DigitalInOut(board.GP8)
    muxB = digitalio.DigitalInOut(board.GP9)
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

if mux == True:
    maxch = 7
    fan6 = pwmio.PWMOut(board.GP6, frequency=freq, duty_cycle=spd)
    fan7 = pwmio.PWMOut(board.GP7, frequency=freq, duty_cycle=spd)

    # initialize fanspeed and dutycycle array
    fandc = [pct, pct, pct, pct, pct, pct, pct, pct]
    fanSpeed = [spd, spd, spd, spd, spd, spd, spd, spd]

elif mux == False:
    maxch = 5
    # initialize fanspeed and dutycycle array
    fandc = [pct, pct, pct, pct, pct, pct]
    fanSpeed = [spd, spd, spd, spd, spd, spd]

# thermistors
therm0 = analogio.AnalogIn(board.A0)
therm1 = analogio.AnalogIn(board.A1)

# thermistor temp storage
temp = [0.0, 0.0]

# get time
initial = time.monotonic()

def temperature(r, Ro=10000.0, To=25.0, beta=3950.0):
    import math
    cel = math.log(r / Ro) / beta      # log(R/Ro) / beta
    cel += 1.0 / (To + 273.15)         # log(R/Ro) / beta + 1/To
    cel = (1.0 / cel) - 273.15   # Invert, convert to C
    return cel

def Pct2val(pct):
    import math
    val = int(int(pct) * 65535 / 100)
    return val

def ReadProfile(fan):
    index = 0
    while index <= 3  # cycle through the fan profile value lists
        if profileTemp[fan][index] => temp[0] => profileTemp[fan][index + 1]:  # compare current index to the next index
            fromSpan = profileTemp[fan][index + 1] - profileTemp[fan][index]   # build a value map
            toSpan = profileDC[fan][index + 1] - profileDC[fan][index]

            Scaled = float(temp[ profileSensor[fan] ] - profileTemp[fan][index]) / float(fromSpan) # calculate a scale factor for PWM value

            return int(profileDC[fan][index] + ( Scaled * toSpan )) # calculate and return the scaled pwm value

        index += 1

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
            for f in range(maxch):
                if (mux == False and f <= 2) or mux == True:
                    print(f'{fanLabel[f]}: {fandc[f]}%  {RPM[f]} RPM')
                elif mux == False and f >= 3:
                    print(f'{fanLabel[f]}: {fandc[f]}%')
            for t in range(1):
                print(f'{thermLabel[t]}: {temp[t]} C')

        # choose fan to manipulate - if not given, all fans will be set to the same speed
        if inText.lower().startswith("@"):
            fanNumber = inText[1:]

        # set fan speed with a "%" symbol
        if inText.startswith("%"):
            pctText = inText[1:]
            spd = Pct2val(int(pcText)

            if ((fanNumber < 0) or (fanNumber > maxch)):
                # when no fan selected, or selection out of range, adjust speed of all fans
                for i in range(maxch):
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
        if mux == True:
            fan6.duty_cycle = fanSpeed[6]
            fan7.duty_cycle = fanSpeed[7]

    for f in range(maxch):
        try:
            fanDC[f] = ReadProfile(f)
            fanSpeed[f] = Pct2val(fanDC[f])
        except:
            False

    # time, flies like an arrow
    now = time.monotonic()

    # get fan speeds twice a second
    if now - initial > 0.500:
        # read and then clear tach and flowrate counts

        if mux == False:
            RPM[0] = (tach0.count * 60) # * 60 to account for two pole tach, this is a simplification of count * 120 / 2
            tach0.reset()                  # it's possible this will have to be configurable for different fan tach types
            RPM[1] = (tach1.count * 60)
            tach1.reset()
            RPM[2] = (tach2.count * 60)
            tach2.reset()
            RPM[3] = (tach3.count * 60)
            tach3.reset()

        elif mux == True:
            # get tach counts, then set mux channel selection for next measurement
            if mchan == 0:
                RPM[3] = (tach0.count * 60) # * 60 to account for two pole tach, this is a simplification of count * 120 / 2
                RPM[7] = (tach1.count * 60) # it's possible this will have to be configurable for different fan tach types
                # change mux for next reading
                muxA.value = False
                muxB.value = False
                # reset tach counts
                tach0.reset()
                tach1.reset()

            if mchan == 1:
                RPM[0] = (tach0.count * 60)
                RPM[4] = (tach1.count * 60)

                muxA.value = True
                muxB.value = False

                tach0.reset()
                tach1.reset()

            if mchan == 2:
                RPM[1] = (tach0.count * 60)
                RPM[5] = (tach1.count * 60)

                muxA.value = False
                muxB.value = True

                tach0.reset()
                tach1.reset()

            if mchan == 3:
                RPM[2] = (tach0.count * 60)
                RPM[6] = (tach1.count * 60)

                muxA.value = True
                muxB.value = True

                tach0.reset()
                tach1.reset()

            if mchan < 3:
                mchan += 1
            else:
                mchan = 0

        # read temp sensors
        temp[0] = temperature(1000/(65535/therm0.value - 1))
        temp[1] = temperature(1000/(65535/therm1.value - 1))

        # reset timer reference
        initial = now
