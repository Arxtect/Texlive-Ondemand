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
from typing import Dict, Optional


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

class ThreadSafeLRUCache:
    def __init__(self, cache):
        self._cache = cache
        self._lock = Lock()

    def get(self, key, default=None):
        with self._lock:
            return self._cache.get(key, default)

    def __setitem__(self, key, value):
        with self._lock:
            self._cache[key] = value

    def __repr__(self):
        with self._lock:
            return repr(self._cache)

lookup_table = {}
try:
    with open('lookupTable.txt', 'r') as f:
        for line in f:
            line = line.strip()
            if '@' in line:
                parts = line.split('@', 1)
                if len(parts) == 2:
                    fname = parts[0].strip()
                    path = parts[1].strip()
                    if fname and path:
                        lookup_table[fname] = path
except Exception as e:
    print(f"Error reading lookupTable.txt: {e}")

resapp = Flask(__name__)

regex = re.compile(r'[^a-zA-Z0-9 _\-\.]')

useCache: bool = True

file_status_cache = ThreadSafeLRUCache(LRUCache(maxsize=3*1*1000))

file_data_cache = LRUCache(maxsize=3*1*1000)
file_data_cache_lock = Lock()

static_base_dir = os.path.realpath(os.path.abspath(os.path.join(os.path.dirname(__file__), 'public')))
engine_base_dir = os.path.join(static_base_dir, "engine")

ENGINE_TEXLIVE_OVERRIDE_FILES = {
    "swiftlatexxetex.js",
    "swiftlatexpdftex.js",
    "swiftlatexdvipdfm.js",
}
TEXLIVE_ENDPOINT_ENV_VAR = "TEXLIVE_ENDPOINT"
TEXLIVE_ENDPOINT_PATTERN = re.compile(
    r'(self\.texlive_endpoint\s*=\s*)(\s*)(["\'])(.*?)(\3)(\s*);',
    re.DOTALL,
)
TEX_WASM_BINARY_PATTERN = re.compile(
    r'(function\s+findWasmBinary\s*\(\s*\)\s*\{)'
    r'(\s*)'
    r'(return\s+locateFile\s*\(\s*)'
    r'(["\'])([^"\']+\.wasm)(\4)'
    r'(\s*\)\s*;)'
    r'(\s*\})',
    re.DOTALL,
)

def _ensure_trailing_slash(url: str) -> str:
    return url if url.endswith("/") else url + "/"

def _get_configured_texlive_endpoint() -> Optional[str]:
    configured = os.environ.get(TEXLIVE_ENDPOINT_ENV_VAR)
    if not configured:
        return None
    return _ensure_trailing_slash(configured)

configured_texlive_endpoint = _get_configured_texlive_endpoint()
if configured_texlive_endpoint:
    print(f"Using texlive endpoint: {configured_texlive_endpoint}")
else:
    print("TEXLIVE_ENDPOINT not set")


def set_cache_enabled(enabled: bool):
    global useCache
    useCache = enabled

def san(name):
    return regex.sub('', name)

def read_file_data(file_path):
    with open(file_path, 'rb') as f:
        return f.read()

@cached(file_data_cache, lock=file_data_cache_lock)
def get_cached_file_data(file_path):
    print(f"File data cache miss: {file_path}")
    return read_file_data(file_path)

def cached_send_file(url, file_data):
    if file_data is None:
        file_data = get_cached_file_data(url)
    file_name = os.path.basename(url)
    file_stream = BytesIO(file_data)
    return send_file(file_stream, download_name=file_name, mimetype='application/octet-stream')

def no_cache_send_file(url, file_data):
    if file_data is None:
        file_data = read_file_data(url)
    file_name = os.path.basename(url)
    file_stream = BytesIO(file_data)
    return send_file(file_stream, download_name=file_name, mimetype='application/octet-stream')

def _is_engine_js(file_path: str) -> bool:
    try:
        real_path = os.path.realpath(file_path)
        if os.path.commonpath([engine_base_dir, real_path]) != engine_base_dir:
            return False
        return os.path.basename(real_path) in ENGINE_TEXLIVE_OVERRIDE_FILES
    except (ValueError, FileNotFoundError, OSError):
        return False

def _apply_texlive_endpoint_override(file_path: str, content: bytes) -> bytes:
    if configured_texlive_endpoint is None or content is None or not _is_engine_js(file_path):
        return content
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError:
        return content
    modified = False    
    def _replace_endpoint(match: re.Match) -> str:
        prefix, spacing, quote_char, _current_value, trailing_spacing = match.group(1, 2, 3, 4, 6)
        return f"{prefix}{spacing}{quote_char}{configured_texlive_endpoint}{quote_char}{trailing_spacing};"

    updated, count = TEXLIVE_ENDPOINT_PATTERN.subn(_replace_endpoint, text, count=1)
    if count > 0:
        modified = True
        text = updated

    def _replace_wasm_binary(match: re.Match) -> str:
        func_start = match.group(1)
        spacing1 = match.group(2)
        quote_char = match.group(4)
        wasm_filename = match.group(5)
        func_end = match.group(8)        
        new_body = (
            f'{func_start}\n'
            f'  var url = self.texlive_endpoint + "static/engine/" + {quote_char}{wasm_filename}{quote_char};\n'
            f'  return url;\n'
            f'{func_end}'
        )
        return new_body

    updated, count = TEX_WASM_BINARY_PATTERN.subn(_replace_wasm_binary, text)
    if count > 0:
        modified = True
        text = updated

    if not modified:
        return content
    return text.encode("utf-8")


@resapp.route('/xetex/<int:fileformat>/<filename>')
@cross_origin()
def xetex_fetch_file(fileformat, filename):
    try:
        filename = san(filename)
        url = None
        has_file = False
        file_data = None
        sta_cache_key = f"xetex+{fileformat}+{filename}"
        sta_cached_entry = file_status_cache.get(sta_cache_key) if useCache else None
        if sta_cached_entry:
            url = sta_cached_entry.url
            has_file = sta_cached_entry.exists
            file_data = sta_cached_entry.file_data
        else:
            if filename in lookup_table:
                url = lookup_table[filename]
            elif filename == "swiftlatexxetex.fmt" or filename == "xetexfontlist.txt":
                url = filename
            else:
                url = pykpathsea_xetex.find_file(filename, fileformat)
            if url is not None:
                has_file = os.path.isfile(url)
            if useCache:
                if has_file:
                    file_data = get_cached_file_data(url)
                file_status_cache[sta_cache_key] = FileCacheEntry(url, has_file, file_data)
                print(f"File status cache miss: {sta_cache_key}")

        if url is None or not has_file:            
            return "File not found", 301
        else:
            response = make_response(cached_send_file(url, file_data) if useCache else no_cache_send_file(url, file_data))
            response.headers['fileid'] = os.path.basename(url)
            response.headers['Access-Control-Expose-Headers'] = 'fileid'
            return response
    except Exception as e:
        print(f"Error in xetex_fetch_file: {e}")
        return "Internal Server Error", 500

@resapp.route('/pdftex/<int:fileformat>/<filename>')
@cross_origin()
def pdftex_fetch_file(fileformat, filename):
    try:
        filename = san(filename)
        url = None
        has_file = False
        file_data = None
        sta_cache_key = f"pdftex+{fileformat}+{filename}"
        sta_cached_entry = file_status_cache.get(sta_cache_key) if useCache else None
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
            if useCache:
                if has_file:
                    file_data = get_cached_file_data(url)
                file_status_cache[sta_cache_key] = FileCacheEntry(url, has_file, file_data)
                print(f"File status cache miss: {sta_cache_key}")

        if url is None or not has_file:
            return "File not found", 301
        else:
            response = make_response(cached_send_file(url, file_data) if useCache else no_cache_send_file(url, file_data))
            response.headers['fileid'] = os.path.basename(url)
            response.headers['Access-Control-Expose-Headers'] = 'fileid'
            return response
    except Exception as e:
        print(f"Error in pdftex_fetch_file: {e}")
        return "Internal Server Error", 500

@resapp.route('/pdftex/pk/<int:dpi>/<filename>')
@cross_origin()
def pdftex_fetch_pk(dpi, filename):
    try:
        filename = san(filename)
        url = None
        has_file = False
        file_data = None
        sta_cache_key = f"pdftex+pk+{dpi}+{filename}"
        sta_cached_entry = file_status_cache.get(sta_cache_key) if useCache else None
        if sta_cached_entry:
            url = sta_cached_entry.url
            has_file = sta_cached_entry.exists
            file_data = sta_cached_entry.file_data
        else:
            url = pykpathsea_pdftex.find_pk(filename, dpi)
            if url is not None:
                has_file = os.path.isfile(url)
            if useCache:
                if has_file:
                    file_data = get_cached_file_data(url)
                file_status_cache[sta_cache_key] = FileCacheEntry(url, has_file, file_data)
                print(f"File status cache miss: {sta_cache_key}")

        if url is None or not has_file:
            return "File not found", 301
        else:
            response = make_response(cached_send_file(url, file_data) if useCache else no_cache_send_file(url, file_data))
            response.headers['pkid'] = os.path.basename(url)
            response.headers['Access-Control-Expose-Headers'] = 'pkid'
            return response
    except Exception as e:
        print(f"Error in pdftex_fetch_pk: {e}")
        return "Internal Server Error", 500


@resapp.route('/static/<category>/<filename>')
@cross_origin()
def static_fetch_file(category, filename):
    try:
        safe_category = san(category)
        safe_filename = san(filename)
        url = None
        has_file = False
        file_data = None
        sta_cache_key = f"static+{safe_category}+{safe_filename}"
        sta_cached_entry = file_status_cache.get(sta_cache_key) if useCache else None
        if sta_cached_entry:
            url = sta_cached_entry.url
            has_file = sta_cached_entry.exists
            file_data = sta_cached_entry.file_data
        else:
            if not safe_category or not safe_filename:
                return "File not found", 404
            if safe_category != category or safe_filename != filename:
                return "File not found", 404
            file_path = os.path.realpath(os.path.join(static_base_dir, safe_category, safe_filename))
            try:
                if os.path.commonpath([static_base_dir, file_path]) != static_base_dir:
                    return "File not found", 404
            except ValueError:
                return "File not found", 404
        
            url = file_path
            if url is not None:
                has_file = os.path.isfile(url)
            if useCache:
                if has_file:
                    file_data = get_cached_file_data(url)
                    file_data = _apply_texlive_endpoint_override(url, file_data)
                file_status_cache[sta_cache_key] = FileCacheEntry(url, has_file, file_data)
                print(f"File status cache miss: {sta_cache_key}")

        if url is None or not has_file:
            return "File not found", 301
        else:
            if useCache:
                response = make_response(cached_send_file(url, file_data))
            else:
                file_data_to_send = read_file_data(url)
                file_data_to_send = _apply_texlive_endpoint_override(url, file_data_to_send)
                response = make_response(no_cache_send_file(url, file_data_to_send))
            response.headers['fileid'] = os.path.basename(url)
            response.headers['Access-Control-Expose-Headers'] = 'fileid'
            return response
    except Exception as e:
        print(f"Error in static_fetch_file: {e}")
        return "Internal Server Error", 500
