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

    def __init__(self, address, handler):
        super().__init__(address, handler)

        self._camera = None

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


class PiCamHandler(BaseHTTPRequestHandler):

    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b'')


if __name__ == '__main__':
    PORT = 9000
    with PiCamera() as cam, PiCamServer(('', PORT), PiCamHandler) as server:
        cam.resolution = (3280, 2464)
        server.camera = cam
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
