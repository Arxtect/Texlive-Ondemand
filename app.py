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
from typing import Dict


class FileCacheEntry:
    url: str
    """Corresponding file URL"""
    exists: bool
    """Boolean value indicating whether the file exists"""
    file_data: bytes
    """File data"""

    def __init__(self, url: str, exists: bool, file_data: bytes):
        """
        Initializes an instance of the FileCacheEntry class.

        :param url: The corresponding file URL
        :param exists: Boolean value indicating whether the file exists
        :param file_data: File data
        """
        self.url = url
        self.exists = exists
        self.file_data = file_data

    def __repr__(self):
        return f"FileCacheEntry(url={self.url}, exists={self.exists})"


app = Flask(__name__)

regex = re.compile(r'[^a-zA-Z0-9 _\-\.]')

file_status_cache: Dict[str, FileCacheEntry] = {}

file_data_cache = LRUCache(maxsize=3*10*1000)


def san(name):
    return regex.sub('', name)

def read_file_data(file_path):
    with open(file_path, 'rb') as f:
        return f.read()

@cached(file_data_cache)
def get_cached_file_data(file_path):
    print(f"File data cache miss: {file_path}")
    return read_file_data(file_path)

def cached_send_file(url, file_data):
    if file_data is None:
        file_data = get_cached_file_data(url)
    file_name = os.path.basename(url)
    file_stream = BytesIO(file_data)
    return send_file(file_stream, download_name=file_name, mimetype='application/octet-stream')


@app.route('/xetex/<int:fileformat>/<filename>')
@cross_origin()
def xetex_fetch_file(fileformat, filename):
    try:
        filename = san(filename)
        url = None
        has_file = False
        file_data = None
        sta_cache_key = f"xetex+{fileformat}+{filename}"
        sta_cached_entry = file_status_cache.get(sta_cache_key)
        if sta_cached_entry:
            url = sta_cached_entry.url
            has_file = sta_cached_entry.exists
            file_data = sta_cached_entry.file_data
        else:
            if filename == "swiftlatexxetex.fmt" or filename == "xetexfontlist.txt":
                url = filename
            else:
                url = pykpathsea_xetex.find_file(filename, fileformat)
            if url is not None:
                has_file = os.path.isfile(url)
            if has_file:
                file_data = get_cached_file_data(url)
            file_status_cache[sta_cache_key] = FileCacheEntry(url, has_file, file_data)
            print(f"File status cache miss: {sta_cache_key}")

        if url is None or not has_file:            
            return "File not found", 301
        else:
            response = make_response(cached_send_file(url, file_data))
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
        has_file = False
        file_data = None
        sta_cache_key = f"pdftex+{fileformat}+{filename}"
        sta_cached_entry = file_status_cache.get(sta_cache_key)
        if sta_cached_entry:
            url = sta_cached_entry.url
            has_file = sta_cached_entry.exists
            file_data = sta_cached_entry.file_data
        else:
            if filename == "swiftlatexpdftex.fmt":
                url = filename
            else:
                url = pykpathsea_pdftex.find_file(filename, fileformat)
            if url is not None:
                has_file = os.path.isfile(url)
            if has_file:
                file_data = get_cached_file_data(url)
            file_status_cache[sta_cache_key] = FileCacheEntry(url, has_file, file_data)
            print(f"File status cache miss: {sta_cache_key}")

        if url is None or not has_file:
            return "File not found", 301
        else:
            response = make_response(cached_send_file(url, file_data))
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
        url = None
        has_file = False
        file_data = None
        sta_cache_key = f"pdftex+pk+{dpi}+{filename}"
        sta_cached_entry = file_status_cache.get(sta_cache_key)
        if sta_cached_entry:
            url = sta_cached_entry.url
            has_file = sta_cached_entry.exists
            file_data = sta_cached_entry.file_data
        else:
            url = pykpathsea_pdftex.find_pk(filename, dpi)
            if url is not None:
                has_file = os.path.isfile(url)
            if has_file:
                file_data = get_cached_file_data(url)
            file_status_cache[sta_cache_key] = FileCacheEntry(url, has_file, file_data)
            print(f"File status cache miss: {sta_cache_key}")

        if url is None or not has_file:
            return "File not found", 301
        else:
            response = make_response(cached_send_file(url, file_data))
            response.headers['pkid'] = os.path.basename(url)
            response.headers['Access-Control-Expose-Headers'] = 'pkid'
            return response
    except Exception as e:
        print(f"Error in pdftex_fetch_pk: {e}")
        return "Internal Server Error", 500

