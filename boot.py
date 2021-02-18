# This file is executed on every boot (including wake-boot from deepsleep)
#import esp
#esp.osdebug(None)

import network, utime, machine
sta_if = network.WLAN(network.STA_IF)
sta_if.active(True)
sta_if.connect("<NETWORK NAME>", "<NETWORK_PW>") # Connect to an AP

timeout_ms = 10000
time_passed = 0
while not sta_if.isconnected():
    utime.sleep_ms(500)
    time_passed += 500
    if time_passed >= timeout_ms:
        sta_if.disconnect()
        break
# blink once if connect succeeded, twice if fails
led_pin = machine.Pin(13, machine.Pin.OUT)
if sta_if.isconnected():
    print('Wifi connected')
    led_pin.value(1)
    utime.sleep_ms(200)
    led_pin.value(0)
else:
    print('Wifi did not connect')
    led_pin.value(1)
    utime.sleep_ms(100)
    led_pin.value(0)
    utime.sleep_ms(100)
    led_pin.value(1)
    utime.sleep_ms(100)
    led_pin.value(0)

import webrepl
webrepl.start()                   # Check for successful connection


# if we can try to set the RTC
if sta_if.isconnected():
    from utils import set_time_from_nist
    set_time_from_nist()