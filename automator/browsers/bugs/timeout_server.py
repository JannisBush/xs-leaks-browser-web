from http.server import BaseHTTPRequestHandler,HTTPServer
import time

class Handler(BaseHTTPRequestHandler):
    def do_GET( self ):
        time.sleep(6000)
        self.send_response(200)
        self.send_header( 'Content-type', 'text/html' )
        self.end_headers()

httpd = HTTPServer( ('127.0.0.1', 8080), Handler )
httpd.serve_forever()
