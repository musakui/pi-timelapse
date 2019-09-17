from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler


class PiCamServer(ThreadingHTTPServer):

    def __init__(self, address, handler):
        super().__init__(address, handler)


class PiCamHandler(BaseHTTPRequestHandler):

    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b'')


if __name__ == '__main__':
    PORT = 9000
    with PiCamServer(('', PORT), PiCamHandler) as server:
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
