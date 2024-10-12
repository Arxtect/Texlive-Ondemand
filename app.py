from flask import Flask, send_file, make_response, send_from_directory
from threading import Lock
import time
import os.path
import pykpathsea_xetex
import pykpathsea_pdftex
from flask_cors import cross_origin
import re
import os
from cachetools import cached, LRUCache
from io import BytesIO

app = Flask(__name__)

regex = re.compile(r'[^a-zA-Z0-9 _\-\.]')

cache = LRUCache(maxsize=3*10*1000)


def san(name):
    return regex.sub('', name)

def read_file_data(file_path):
    with open(file_path, 'rb') as f:
        return f.read()

@cached(cache)
def get_cached_file_data(file_path):
    print(f"Cache miss: {file_path}")
    return read_file_data(file_path)

def cached_send_file(url):
    file_data = get_cached_file_data(url)
    file_stream = BytesIO(file_data)
    file_stream.seek(0)
    return send_file(url, mimetype='application/octet-stream')

@app.route('/xetex/<int:fileformat>/<filename>')
@cross_origin()
def xetex_fetch_file(fileformat, filename):
    try:
        filename = san(filename)
        url = None
        if filename == "swiftlatexxetex.fmt" or filename == "xetexfontlist.txt":
            url = filename
        else:
            url = pykpathsea_xetex.find_file(filename, fileformat)

        if url is None or not os.path.isfile(url):
            return "File not found", 301
        else:
            response = make_response(cached_send_file(url))
            response.headers['fileid'] = os.path.basename(url)
            response.headers['Access-Control-Expose-Headers'] = 'fileid'
            return response
    except Exception as e:
        print(f"Error in xetex_fetch_file: {e}")
        return "Internal Server Error", 500

@app.route('/pdftex/<int:fileformat>/<filename>')
@cross_origin()
def pdftex_fetch_file(fileformat, filename):
    try:
        filename = san(filename)
        url = None
        if filename == "swiftlatexpdftex.fmt":
            url = filename
        else:
            url = pykpathsea_pdftex.find_file(filename, fileformat)

        if url is None or not os.path.isfile(url):
            return "File not found", 301
        else:
            response = make_response(cached_send_file(url))
            response.headers['fileid'] = os.path.basename(url)
            response.headers['Access-Control-Expose-Headers'] = 'fileid'
            return response
    except Exception as e:
        print(f"Error in pdftex_fetch_file: {e}")
        return "Internal Server Error", 500

@app.route('/pdftex/pk/<int:dpi>/<filename>')
@cross_origin()
def pdftex_fetch_pk(dpi, filename):
    try:
        filename = san(filename)
        
        url = pykpathsea_pdftex.find_pk(filename, dpi)

        if url is None or not os.path.isfile(url):
            return "File not found", 301
        else:
            response = make_response(cached_send_file(url))
            response.headers['pkid'] = os.path.basename(url)
            response.headers['Access-Control-Expose-Headers'] = 'pkid'
            return response
    except Exception as e:
        print(f"Error in pdftex_fetch_pk: {e}")
        return "Internal Server Error", 500

