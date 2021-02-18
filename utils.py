import math
import utime
import usocket
from machine import Pin, ADC, RTC

# https://docs.espressif.com/projects/esp-idf/en/latest/api-reference/peripherals/adc.html says 0 dB is 1.1 V
ADC_to_voltage = lambda adc, attendb=0: 1.1*10**(attendb/20)*adc.read()/4095

def read_battery_voltage(pin=35):
    adc = ADC(Pin(pin))
    adc.atten(ADC.ATTN_11DB)
    return 2*ADC_to_voltage(adc, 11)


def set_time_from_nist(assume_day=0, init_rtc=True):
    addr = usocket.getaddrinfo('time.nist.gov', 13)[0][-1]
    s = usocket.socket(usocket.AF_INET, usocket.SOCK_STREAM)
    s.connect(addr)
    result = s.recv(1024)
    s.close()

    yr, mo, day = result[7:15].split(b'-')
    hr, mn, sec = result[16:24].split(b':')

    yr = int(yr)+2000
    mo = int(mo)
    day = int(day)
    dayofweek = doomsday_of_week(yr, mo, day)

    tt = (yr, mo, day, dayofweek, int(hr), int(mn), int(sec), 0)

    if init_rtc:
        RTC().init(tt)

    return tt

def doomsday_of_week(year, month, day):
    t = [0, 3, 2, 5, 0, 3, 5, 1, 4, 6, 2, 4]
    year -= month < 3
    return (year + int(year/4) - int(year/100) + int(year/400) + t[month-1] + day - 1) % 7

