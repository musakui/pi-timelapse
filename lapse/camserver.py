from time import sleep
from io import BytesIO
from json import dumps, loads
from mimetypes import types_map
from urllib.parse import urlparse
from threading import Thread, Condition
from datetime import datetime, timedelta
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler

from picamera import PiCamera

CAM_ATTRS = {
    'iso': int,
    'rotation': int,
    'awb_mode': str,
    'contrast': int,
    'resolution': str,
    'brightness': int,
    'meter_mode': str,
    'framerate': float,
    'exposure_mode': str,
    'shutter_speed': int,
    'exposure_speed': int,
}


class PiCamServer(ThreadingHTTPServer):

    stream_port = 2
    stream_size = (300, 225)

    def __init__(self, address, handler):
        super().__init__(address, handler)

        self.count = 0
        self.frame = b''
        self.condition = Condition()

        self._b = BytesIO()
        self._camera = None
        self._lapse_t = None
        self._lapse_r = False
        self._lapse_d = timedelta(seconds=2)

    @property
    def camera(self):
        if self._camera is None:
            return None
        return {k: v(getattr(self._camera, k)) for k, v in CAM_ATTRS.items()}

    @camera.setter
    def camera(self, val):
        if isinstance(val, PiCamera):
            self._camera = val
            return
        for k, v in val.items():
            ktype = CAM_ATTRS.get(k, str)
            if k == 'awb_mode' and v == 'fix':
                self.fix_awb()
                v = 'off'
            try:
                setattr(self._camera, k, ktype(v))
            except Exception as e:
                print(e)

    @property
    def stream(self):
        return self._camera.recording

    @stream.setter
    def stream(self, v):
        if v and not self._camera.recording:
            stream_args = ('mjpeg', self.stream_size, self.stream_port)
            self._camera.start_recording(self, *stream_args)
        elif not v and self._camera.recording:
            self._camera.stop_recording(self.stream_port)

    @property
    def lapse(self):
        return self._lapse_r

    @lapse.setter
    def lapse(self, v):
        if v == self._lapse_r:
            return

        self._lapse_r = v
        if v:
            self._lapse_t = Thread(target=self._run_lapse)
            self._lapse_t.start()

    @property
    def interval(self):
        return self._lapse_d.total_seconds()

    @interval.setter
    def interval(self, val):
        if isinstance(val, timedelta):
            self._lapse_d = val
        elif isinstance(val, dict):
            self._lapse_d = timedelta(**val)
        else:
            try:
                s = float(val)
            except ValueError:
                pass
            self._lapse_d = timedelta(seconds=s)

    @property
    def status(self):
        return {
            'interval': self.interval,
            'camera': self.camera,
            'stream': self.stream,
            'lapse': self.lapse,
            'count': self.count,
        }

    @status.setter
    def status(self, val):
        for k, v in val.items():
            try:
                setattr(self, k, v)
            except Exception as e:
                print(e)

    def _run_lapse(self):
        self.count = 0
        output = BytesIO()
        target = datetime.now()

        while self._lapse_r:
            self._camera.capture(output, 'jpeg')
            output.truncate()
            output.seek(0)

            self.count += 1
            target += self._lapse_d

            now = datetime.now()
            sleep((target - now).total_seconds())

    def fix_awb(self):
        g = self._camera.awb_gains
        self._camera.awb_mode = 'off'
        self._camera.awb_gains = g

    def write(self, buf):
        """Handle stream from PiCamera"""
        if buf.startswith(b'\xff\xd8'):
            self._b.truncate()
            with self.condition:
                self.frame = self._b.getvalue()
                self.condition.notify_all()
            self._b.seek(0)
        return self._b.write(buf)


class PiCamHandler(BaseHTTPRequestHandler):

    static_path = 'static'
    content_type = 'multipart/x-mixed-replace; boundary=FRAME'

    def send_frame(self):
        frame = self.server.frame
        self.wfile.write(b'--FRAME\r\n')
        self.send_header('Content-Type', 'image/jpeg')
        self.send_header('Content-Length', len(frame))
        self.end_headers()
        self.wfile.write(frame)
        self.wfile.write(b'\r\n')

    def send_stream(self):
        self.send_response(200)
        self.send_header('Age', 0)
        self.send_header('Pragma', 'no-cache')
        self.send_header('Content-Type', self.content_type)
        self.send_header('Cache-Control', 'no-cache, private')
        self.end_headers()

        self.send_frame()
        try:
            while self.server.stream:
                with self.server.condition:
                    self.server.condition.wait()
                self.send_frame()
        except Exception as e:
            if e.args[0] != 32:
                print(e)

    def get_thing(self, thing):
        if isinstance(thing, dict):
            content = dumps(thing).encode('utf-8')
            ext = '.json'
        else:
            try:
                with open('%s/%s' % (self.static_path, thing), 'rb') as f:
                    content = f.read()
            except OSError:
                return None
            ext = '.' + thing.rsplit('.', 1)[1].lower()

        ctype = types_map.get(ext, 'application/octet-stream')
        self.send_response(200)
        self.send_header('Content-Type', ctype)
        self.send_header('Content-Length', len(content))
        self.end_headers()
        return content

    def do_GET(self):
        url = urlparse(self.path)
        path = url.path[1:]
        content = None

        if path == 'status':
            content = self.get_thing(self.server.status)
        elif path == 'shutdown':
            self.server.shutdown()
        elif path == 'stream.mjpg':
            self.send_stream()
        else:
            if path == '':
                path = 'index.html'
            content = self.get_thing(path)

        if content is None:
            self.send_response(404)
            self.end_headers()
        else:
            self.wfile.write(content)

    def do_POST(self):
        clen = int(self.headers.get('Content-Length', 0))
        if clen:
            data = self.rfile.read(clen).decode('utf-8')
            try:
                self.server.status = loads(data)
            except Exception as e:
                print(e)
        self.wfile.write(self.get_thing(self.server.status))


if __name__ == '__main__':
    PORT = 9000
    with PiCamera() as cam, PiCamServer(('', PORT), PiCamHandler) as server:
        cam.resolution = (3280, 2464)
        server.camera = cam
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
