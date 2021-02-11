import board
import busio
import digitalio
import adafruit_rfm69

DEFAULT_ENCRYPTION = b'radioplusIRiscoo'


class AMG88xxReceiver:
    def __init__(self, cspin=board.D16, resetpin=board.D13, spinum=1, freq=433.0):
        cs = digitalio.DigitalInOut(cspin)
        reset = digitalio.DigitalInOut(resetpin)
        if spinum==0:
            suffix = ''
        else:
            suffix = '_' + str(spinum)
        sck = getattr(board, 'SCK' + suffix)
        mosi = getattr(board, 'MOSI' + suffix)
        miso = getattr(board, 'MISO' + suffix)
        spi = busio.SPI(sck, MOSI=mosi, MISO=miso)

        rfm69 = adafruit_rfm69.RFM69(spi, cs, reset, freq,
                                    encryption_key=DEFAULT_ENCRYPTION)
        print('rfm69 started')
        self.rfm69 = rfm69

    def get_messages(self, n):
        messages = []
        rec = self.rfm69.receive  # for a bit more speed get a local var
        for i in range(n):
            msg = rec()
            if msg is None:
                return messages
            else:
                messages.append(msg)
        return messages

    def get_frame_sequence(self, msg_window):
        messages = self.get_messages(msg_window)
        message_nums = [m[1] for m in messages]
        for i, n in enumerate(message_nums):
            if n==0:
                # candidate
                if (i + 7) < msg_window: # don't fall off the end of the message sequence
                    for j in range(8):
                        if j != message_nums[i+j]:
                            break
                    else:
                        # did not break: success!
                        return messages[i:(i+8)]
        raise ValueError(f"Found no complete frame sequence! Frame numbers: {message_nums}")

    def decode_row(self, byteseq, degF=False):
        """
        converts from byte-pair to deg C (or F if degF is True)
        """
        assert byteseq[0] == 42
        rownum = byteseq[1]

        degc = []
        for i in range((len(byteseq)-2)//2):
            low = byteseq[(i+1)*2]
            high = byteseq[(i+1)*2 + 1]
            degc.append((low + (high << 8))/4)

        return degc, rownum

    def get_temp_array(self, msg_window=16, asarray=True):
        rows = self.get_frame_sequence(msg_window=msg_window)

        amgarray = [self.decode_row(row)[0] for row in rows]
        if asarray:
            # to not make numpy strict requirement
            import numpy as np
            return np.array(amgarray)
        else:
            return amgarray

    def interpolated_temp_array(self, gridsize, amgarray=None, **spline_kwargs):
        # to not make scipy/numpy strict requirement
        import numpy as np
        from scipy.interpolate import RectBivariateSpline

        if amgarray is None:
            amgarray = 16
        if isinstance(amgarray, int):
            amgarray = self.get_temp_array(msg_window=amgarray, asarray=True)

        xarr = np.arange(amgarray.shape[0])
        yarr = np.arange(amgarray.shape[1])
        spline = RectBivariateSpline(xarr, yarr, amgarray, **spline_kwargs)

        return spline(np.linspace(0, amgarray.shape[0]-1, gridsize),
                      np.linspace(0, amgarray.shape[1]-1, gridsize), grid=True)

    @staticmethod
    def deg_c_to_f(degc):
        return degc*1.8 + 32

    def make_plot(self, gridsize, amgarray=None, savefn=None, degF=False):
        from matplotlib import pyplot as plt # to not make matplotlib a strict requirement

        degarr = self.interpolated_temp_array(gridsize, amgarray)
        if degF:
            degarr = self.deg_c_to_f(degarr)

        fig = plt.figure(figsize=(10, 8))
        plt.imshow(degarr, interpolation='nearest')
        plt.colorbar(orientation='vertical').set_label('deg ' + ('F' if degF else 'C'))

        min = degarr.min()
        max = degarr.max()
        mean = degarr.mean()
        plt.title(f'Min,Max={min:.2f},{max:.2f} Mean={mean:.2f}')

        plt.xticks([])
        plt.yticks([])

        if savefn:
            fig.savefig(savefn)