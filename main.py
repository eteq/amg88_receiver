import os
import ubinascii
from machine import Pin
from utime import sleep_ms

import picoweb
import amg88xx

led = Pin(13, Pin.OUT, value=0)

amg = amg88xx.AMG88XX(None)
i2c = amg.i2c


app = picoweb.WebApp(__name__)

@app.route("/")
@app.route("/index.html")
def index(req, resp):
    req.parse_qs()
    mindegC=int(req.form.get('min', 0))
    maxdegC=int(req.form.get('max', 80))

    yield from picoweb.start_response(resp)
    pixels = await amg.aread_pixels('int')

    bmpb64 = ubinascii.b2a_base64(amg.get_bmp(intpixels=pixels, mindegC=mindegC, maxdegC=maxdegC))
    stats = amg88xx.stats_from_pixels(pixels)
    yield from app.render_template(resp, "index.tpl", (stats['average']/4,
                                                       stats['min']/4,
                                                       stats['max']/4,
                                                       bmpb64.decode(),
                                                       mindegC,
                                                       maxdegC))

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
    bmpbytes = await amg.aget_bmp(mindegC=int(req.form.get('mindegC', 0)),
                                  maxdegC=int(req.form.get('maxdegC', 80)))
    yield from picoweb.start_response(resp, "image/bmp",
                                      headers={'Content-Length':str(len(bmpbytes))})
    yield from resp.awrite(bmpbytes)

if __name__ == "__main__":
    for i in range(3):
        led.on()
        sleep_ms(75)
        led.off()
        sleep_ms(75)

    app.run(host='0.0.0.0', debug='debug' in os.listdir('/'), port=80)
