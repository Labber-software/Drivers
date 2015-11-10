from distutils.core import setup
from distutils.extension import Extension
from Cython.Build import cythonize
import numpy as np
extensions = [
    Extension("_integrateHNoNumpy_ForDriver", ["_integrateHNoNumpy_ForDriver.pyx"],
        include_dirs = [np.get_include()]),]
setup(
    ext_modules = cythonize(extensions))

# run with python .\compileCython.py build_ext --inplace --compiler=mingw32

                            

