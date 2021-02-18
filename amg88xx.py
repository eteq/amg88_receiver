import io
from machine import Pin, I2C
import uasyncio as asyncio
from utime import sleep_ms

class AMG88XX:
    def __init__(self, i2c, i2c_addr=0x69):
        if i2c is None:
            i2c = I2C(0, scl=Pin(22), sda=Pin(23), freq=400000)
        else:
            i2cs = repr(i2c)  # not the safest approach but 🤷
            freq = int(i2cs.split('freq=')[1].replace('(', ''))
            if freq != 400000:
                raise IOError('i2c must be 400 khz for AMG88xx')
        self.i2c = i2c
        self.i2c_addr = i2c_addr

        scanres = self.i2c.scan()
        if self.i2c_addr not in scanres:
            raise IOError('No AMG88xx found!')

        self._async_lock = asyncio.Lock()


        # normal power mode in case sleeping
        self.write(0x00, 0x00)
        self._asleep = False
        # reset
        self.write(0x01, 0x3f)
        sleep_ms(50) # not clear if this is necessary after a soft reset but datasheet suggests maybe
        self._mavg = bool(self.read(0x07)[0] & 0b00100000)  # should default to 0 but you never know

    def read(self, addr, nbytes=1):
        return self.i2c.readfrom_mem(self.i2c_addr, addr, nbytes, addrsize=8)

    def write(self, addr, buf):
        if not isinstance(buf, bytes):
            if isinstance(buf, int):
                buf = bytes([buf])
            else:
                buf = bytes(buf)
        self.i2c.writeto_mem(self.i2c_addr, addr, buf, addrsize=8)

    def sleep(self):
        self.write(0x00, 0x10)
        self._asleep = True

    def wake(self, wait=True):
        self.write(0x00, 0x00)
        self._asleep = False
        sleep_ms(50) # not clear if this is from sleep vs power-on, but seems safest to wait

    def frame_rate(self, rate):
        """
        frame rate must be either 1 or 10
        """
        if rate == 10:
            self.write(0x02, 0)
        elif rate == 1:
            self.write(0x02, 1)
        else:
            raise ValueError('frame rate can only be 1 or 10')

    def moving_average(self, mavg):
        """
        None for "get"
        """
        if mavg is None:
            return self._mavg
        else:
            if mavg:
                self.write(0x1f, 0x50)
                self.write(0x1f, 0x45)
                self.write(0x1f, 0x57)
                self.write(0x07, 0x20)
                self.write(0x1f, 0x00)
            else:
                self.write(0x1f, 0x50)
                self.write(0x1f, 0x45)
                self.write(0x1f, 0x57)
                self.write(0x07, 0x00)
                self.write(0x1f, 0x00)
            self._mavg = bool(self.read(0x07)[0] & 0b00100000)


    def get_thermistor(self):
        """
        in degC
        """
        l, u = self.read(0x0e, 2)
        return (l + (u << 8))/16.

    async def aget_thermistor(self):
        async with self._async_lock:
            return self.get_thermistor()

    def read_pixels(self, outformat='degC'):
        """
        outformat can be 'int', which is degC * 4, 'degC', or 'degF'
        """
        pixel_bytes = self.read(0x80, 128)
        rows = []
        for i in range(8):
            row = []
            offset = i*8
            for j in range(8):
                j2 = j*2
                low = pixel_bytes[offset + j2]
                high = pixel_bytes[offset + j2 + 1]
                row.append(low + (high << 8))

            rows.append(row)

        if outformat == 'int':
            return rows
        elif outformat == 'degC':
            return [[elem/4 for elem in row] for row in rows]
        elif outformat == 'degF':
            return [[elem*0.45 + 32 for elem in row] for row in rows]
        elif outformat == 'degK':
            return [[elem/4 + 273.15 for elem in row] for row in rows]
        else:
            raise ValueError('invalid output format "{}"!'.format(outformat))

    async def aread_pixels(self, outformat='degC'):
        async with self._async_lock:
            return self.read_pixels(outformat=outformat)

    def get_bmp(self, mindegC=0, maxdegC=80):
        """Create and return a grayscale BMP file.

        Args:
            pixels: A rectangular image stored as a sequence of rows.
                Each row must be an iterable series of integers in the
                range 0-255.
        """
        minint = mindegC * 4
        maxint = maxdegC * 4
        scaleint = 255/(maxint-minint)
        remap_elem = lambda e: max(min(scaleint*(e - minint), 255), 0)

        pixels = [[round(remap_elem(elem)) for elem in row]for row in self.read_pixels('int')]

        height = len(pixels)
        width = len(pixels[0])

        bmp = io.BytesIO()

        # BMP Header
        bmp.write(b'BM')

        # Next 4 bytes hold the file size as 32-bit.
        size_bookmark = bmp.tell()
        # little-endian integer. Zero placeholder for now.
        bmp.write(b'\x00\x00\x00\x00')

        # Unused 16-bit integer - should be zero.
        bmp.write(b'\x00\x00')
        # Unused 16-bit integer - should be zero.
        bmp.write(b'\x00\x00')

        # The next four bytes hold the integer offset.
        # to the pixel data. Zero placeholder for now.
        pixel_offset_bookmark = bmp.tell()
        bmp.write(b'\x00\x00\x00\x00')

        # Image header
        # Image header size in bytes - 40 decimal
        bmp.write(b'\x28\x00\x00\x00')
        # Image width in pixels
        bmp.write(_int32_to_bytes(width))
        # Image height in pixels
        bmp.write(_int32_to_bytes(height))
        # Number of image planes
        bmp.write(b'\x01\x00')
        # Bits per pixel 8 for grayscale
        bmp.write(b'\x08\x00')
        # No compression
        bmp.write(b'\x00\x00\x00\x00')
        # Zero for uncompressed images
        bmp.write(b'\x00\x00\x00\x00')
        # Unused pixels per meter
        bmp.write(b'\x00\x00\x00\x00')
        # Unused pixels per meter
        bmp.write(b'\x00\x00\x00\x00')
        # Use whole color table
        bmp.write(b'\x00\x00\x00\x00')
        # All colors are important
        bmp.write(b'\x00\x00\x00\x00')

        # Color palette - a linear grayscale
        for c in range(256):
            # Blue, Green, Red, Zero
            bmp.write(bytes((c, c, c, 0)))

        # Pixel data
        pixel_data_bookmark = bmp.tell()
        # BMP Files are bottom to top
        for row in reversed(pixels):
            row_data = bytes(row)
            bmp.write(row_data)
            # Pad row to multiple of four bytes
            padding = b'\x00' * ((4 - (len(row) % 4)) % 4)
            bmp.write(padding)

        # End of file
        eof_bookmark = bmp.tell()

        # Fill in file size placeholder
        bmp.seek(size_bookmark)
        bmp.write(_int32_to_bytes(eof_bookmark))

        # Fill in pixel offset placeholder
        bmp.seek(pixel_offset_bookmark)
        bmp.write(_int32_to_bytes(pixel_data_bookmark))

        return bmp.getvalue()

    async def aget_bmp(self, *args, **kwargs):
        async with self._async_lock:
            return self.get_bmp(*args, **kwargs)


def _int32_to_bytes(i):
    """Convert an integer to four bytes in little-endian formart."""
    return bytes((i & 0xff,
                  i >> 8 & 0xff,
                  i >> 16 & 0xff,
                  i >> 24 & 0xff))
