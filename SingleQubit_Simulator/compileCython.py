from distutils.core import setup
from distutils.extension import Extension
from Cython.Build import cythonize
import numpy as np
extensions = [
    Extension("_integrateHNoNumpy_ForDriver", ["_integrateHNoNumpy_ForDriver.pyx"],
        include_dirs = [np.get_include()]),]
setup(
    ext_modules = cythonize(extensions))

# WIN: use same compiler as for python, Microsoft Build Tools for Visual Studio 2017 or 
# Microsoft Visual C++ Build Tools 2015.
# see https://wiki.python.org/moin/WindowsCompilers  
# run with python .\compileCython.py build_ext --inplace 

# MAC, Py3: run with python compileCython.py build_ext --inplace
                

