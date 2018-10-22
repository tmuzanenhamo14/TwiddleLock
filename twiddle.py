import spidev
import pigpio 
import time
import Adafruit_MCP3008
import Adafruit_GPIO.SPI as SPI
import threading
#GPIO Pins

START_SWITCH = 2
MODE_SWITCH = 3

#SPI

# GPIO SPI Pins
SPICLK = 11
SPIMISO = 9
SPIMOSI = 10
SPICS = 8

# Global variables
FREQ = 100 # Frequency of reading MCP
READ = True
POT_CHANNEL = 0
BUFFER_MAX = 16
SAMPLING_PERIOD = 0.2

LOCK_MODE = 0
TIMER = time.time()

pi =  pigpio.pi()
SPI_PORT = 0
SPI_DEVICE = 0
MCP = Adafruit_MCP3008.MCP3008(spi=SPI.SpiDev(SPI_PORT, SPI_DEVICE))
values = []
times = []

# Call back global variables
switch_cb, start_cb = 0, 0

def setup():
    
    # Set up the switch pins
    pi.set_mode(START_SWITCH, pigpio.INPUT)
    pi.set_mode(MODE_SWITCH, pigpio.INPUT)
    pi.set_pull_up_down(START_SWITCH, pigpio.PUD_DOWN)
    pi.set_pull_up_down(MODE_SWITCH, pigpio.PUD_DOWN)

def stop():
    READ = False

def ADCPOT(digicode):
    vref = 3.3
    levels = 1024
    vin = (vref*digicode)/ (levels-1)
    return vin

def reset():
    TIMER = time.time()


def secure_mode():

    #start Directions and Duration threads
    direc  = Directions(name = "Directions thread")
    durat  = Durations(name = "Durartions thread")
    
    direc.start()
    sleep(SAMPLING_PERIOD)
    durat.start()

def switch_lock_mode(gpio, level, tick):
    global LOCK_MODE
    sleep(0.5) # Debounce time of 0.5 seconds
    if LOCK_MODE == 0:
        LOCK_MODE = 1 # Change to unsecure mode
        print("Selected the unsecure mode")
    else:
        LOCK_MODE = 0 # Change to secure mode
        print("Selected the secure mode")

def main():
    global switch_cb, start_cb
    switch_cb = pi.callback(MODE_SWITCH, pigpio.FALLING_EDGE, switch_lock_mode) # Switch the mode
    start_cb = pi.callback(START_SWITCH, pigpio.FALLING_EDGE, start) # Start the selected mode
    secure_mode()

def start(gpio, level, pin):
    pass

def lock():
    pass


def unlock():
    pass


def sleep(secs):
    tic = time.monotonic()
    while (time.monotonic()-tic < secs):
        pass
#SECURE MODE


def updateBuffer(buffer):
    if len(buffer) > BUFFER_MAX:
        del buffer[16]


#UNSECURE MODE

DURATIONS = []
TICK = 0
TOCK = 0 
KEY = [1, 1, 2]

def unsecure_mode():
    global pi, TICK, DURATIONS
    print("Starting unsecure mode")
    reading = MCP.read(0) # POT is on channel 0
    while (round(ADCPOT(MCP.read(0)), 2) == reading):
        pass
    TICK = time.monotonic()
    print("Now taking readings")
    while(len(DURATIONS)< len(KEY)):
        while (reading != round(ADCPOT(MCP.read(0)), 2)):
            reading = MCP.read(0)
            time.sleep(1/FREQ)
        DURATIONS.append(time.monotonic() - TICK)
        while(reading == round(ADCPOT(MCP.read(0)), 2)):
            pass
    print("Code entered")
    DURATIONS.sort()
    print("Checking code")
    if (unsecure_check()):
        print("Code correct")
        unlock()
    else:
        print("Code incorrect")
        lock()

def unsecure_check():
    for i in range(len(KEY)):
        if KEY[i] != DURATIONS[i]:
            return False
    return True

class Durations(threading.Thread):
    def run(self):
        print("{} started!".format(self.getName()))
        while True:
            STATE_CHANGED = False
            TICK = time.monotonic()
            while(not STATE_CHANGED):              
                sleep(SAMPLING_PERIOD)
                if(values[0]-values[1] <-0.1 ):          #moving to right
                    while(values[0]-values[1] <-0.1):
                        sleep(0.05)                      #check whether it is still increasing
                        continue
                    times.insert(0,time.monotonic() - TICK)
                    updateBuffer(times)
                    print("Durations are :",times)
                    STATE_CHANGED = True
                elif( values[0]-values[1] >0.1 ):       #moving to left
                    while( values[0]-values[1] >0.1 ):
                        sleep(0.05)                     #check whether it is still increasing
                        continue
                    times.insert(0,time.monotonic() - TICK)
                    updateBuffer(times)
                    print("Durations are :",times)
                    STATE_CHANGED = True
                elif ( time.monotonic() - TICK>2  ):
                    exit_by_delay()



class Directions(threading.Thread):
    def run(self):
        print("{} started!".format(self.getName()))
        values.insert(0, ADCPOT(MCP.read_adc(POT_CHANNEL)))
        sleep(SAMPLING_PERIOD)
        while True:
            values.insert(0, ADCPOT(MCP.read_adc(POT_CHANNEL)))
            updateBuffer(values)
            #print("BUFFER: ",values)
            sleep(SAMPLING_PERIOD)
            if( values[0]-values[1]>0.1 ):                     #when values increase->left
                while(values[0]-values[1] >0.1):              #check whether it is still increasing
                    values.insert(0, ADCPOT(MCP.read_adc(POT_CHANNEL)))
                    sleep(SAMPLING_PERIOD)
                print("L")
            elif( abs(values[0]-values[1] )<0.1):
                while( abs(values[0]-values[1] )<0.1 ):              #check whether it is still increasing
                    values.insert(0, ADCPOT(MCP.read_adc(POT_CHANNEL)))
                    sleep(SAMPLING_PERIOD)
                print("constant")
            elif ( values[0]-values[1]<-0.1 ):                 #when values decrease->right
                while(values[0]-values[1] <-0.1):              #check whether it is still increasing
                    values.insert(0, ADCPOT(MCP.read_adc(POT_CHANNEL)))
                    sleep(SAMPLING_PERIOD)
                print("R")                          


def exit_by_delay():
    print("Exiting")
    pi.cleanup()
    exit()

if __name__ == "__main__":
    setup()
    main()
    pi.cleanup()
