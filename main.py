import os
import ubinascii
from machine import Pin, ADC, RTC
from utime import sleep_ms

import picoweb

import amg88xx
import utils

led = Pin(13, Pin.OUT, value=0)
battery_adc = ADC(Pin(35, Pin.IN))
battery_adc.atten(ADC.ATTN_11DB)

amg = amg88xx.AMG88XX(None)
i2c = amg.i2c


app = picoweb.WebApp(__name__)

@app.route("/")
@app.route("/index.html")
def index(req, resp):
    req.parse_qs()
    mindegC = int(req.form.get('min', 0))
    maxdegC = int(req.form.get('max', 80))
    refreshms = float(req.form.get('refreshms', -1))

    yield from picoweb.start_response(resp)
    pixels = await amg.aread_pixels('int')

    bmpb64 = ubinascii.b2a_base64(amg.get_bmp(intpixels=pixels, mindegC=mindegC, maxdegC=maxdegC))
    stats = amg88xx.stats_from_pixels(pixels)
    yield from app.render_template(resp, "index.tpl", (stats['average']/4,
                                                       stats['min']/4,
                                                       stats['max']/4,
                                                       bmpb64.decode(),
                                                       mindegC,
                                                       maxdegC,
                                                       refreshms))

@app.route("/pixels")
def pixels(req, resp):
    req.parse_qs()
    if 'units' in req.form:
        outformat = req.form['units']
    else:
        outformat = 'degC'
    pixels = await amg.aread_pixels(outformat)

    dct = {'pixels':pixels, 'units':outformat}

    if 'stats' in req.form and req.form['stats'] not in ('0', 'false', 'False'):
        dct.update(amg88xx.stats_from_pixels(pixels))

    yield from picoweb.jsonify(resp, dct)

@app.route("/thermistor")
def thermistor(req, resp):
    thermistor_value = await amg.aget_thermistor()
    yield from picoweb.jsonify(resp, {'value':thermistor_value, 'units':'degC'})

@app.route("/bmp")
def bmp(req, resp):
    req.parse_qs()
    pixels = await amg.aread_pixels('int')
    bmpbytes = amg.get_bmp(intpixels=pixels,
                           mindegC=int(req.form.get('mindegC', 0)),
                           maxdegC=int(req.form.get('maxdegC', 80)))
    response_headers = {'Content-Length':str(len(bmpbytes)),
                        'Cache-Control': 'no-cache, no-store, must-revalidate'}

    if req.form.get('stats', None):
        stats = amg88xx.stats_from_pixels(pixels)
        response_headers['X-pixavg'] = str(stats['average']/4)
        response_headers['X-pixmin'] = str(stats['min']/4)
        response_headers['X-pixmax'] = str(stats['max']/4)

    yield from picoweb.start_response(resp, "image/bmp",
                                      headers=response_headers)
    yield from resp.awrite(bmpbytes)

@app.route("/battery")
def battery(req, resp):
    #read_volts = utils.ADC_to_voltage(battery_adc.read(), 11) # off by ~5-10% ?
    read_volts = battery_adc.read()*3.6/4095  # this seems to be ok to ~1% when comparing to multimeter...
    dt = RTC().datetime()
    yield from picoweb.jsonify(resp, {'battery_value':read_volts*2, 'units':'V', 'datetime_stamp':dt})


if __name__ == "__main__":
    for i in range(3):
        led.on()
        sleep_ms(75)
        led.off()
        sleep_ms(75)

    # delete compiled templates if they exist
    if 'templates' in os.listdir():
        for fn in os.listdir('templates'):
            if fn.endswith('.py'):
                os.remove('templates/' + fn)

    app.run(host='0.0.0.0', debug='debug' in os.listdir('/'), port=80)
