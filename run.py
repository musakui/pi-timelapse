from picamera import PiCamera
from lapse.camserver import PiCamServer

if __name__ == '__main__':
    lapse_output = '/home/pi/images/{timestamp:%y%m%d-%H%M%S}.jpg'
    with PiCamera(resolution=(3280, 2464), framerate=6) as camera:
        with PiCamServer(('', 80)) as server:
            server.camera = camera
            server.lapse_output = lapse_output
            try:
                server.serve_forever()
            except KeyboardInterrupt:
                pass
