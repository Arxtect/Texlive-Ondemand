from distutils.core import setup, Extension

pdftex_module = Extension('pykpathsea_luatex', sources = ['pykpathsea_luatex.c'], libraries=["kpathsea"])

setup(name='pykpathsea_luatex',
      version='0.3.0',
      description='Kpathsea_luatex',
      ext_modules=[pdftex_module])
