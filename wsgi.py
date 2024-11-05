from gevent.pywsgi import WSGIServer
from app import resapp
import app
import argparse

parser = argparse.ArgumentParser()
parser.add_argument('--no-cache', action='store_true', default=False, help='Disable caching')
args = parser.parse_args()

app.set_cache_enabled(not args.no_cache)

http_server = WSGIServer(('0.0.0.0', 5001), resapp)
http_server.serve_forever()
