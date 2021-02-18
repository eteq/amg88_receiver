import os
import picoweb
from amg88xx import AMG88XX

amg = AMG88XX(None)
i2c = amg.i2c


app = picoweb.WebApp(__name__)

@app.route("/")
def index(req, resp):
    pass

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
        mx = -1000000000
        mn = 1000000000
        total = n = 0
        for row in pixels:
            for elem in row:
                if elem > mx:
                    mx = elem
                if elem < mn:
                    mn = elem
                total += elem
                n += 1

        dct['average'] = total / n
        dct['min'] = mn
        dct['max'] = mx

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
    app.run(host='0.0.0.0', debug='debug' in os.listdir('/'), port=80)
