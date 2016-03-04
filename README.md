eqtools
=======

Introduction
------------

Python tools for magnetic equilibria in tokamak plasmas.  Provides framework for portable, modular tools for manipulation of magnetic equilibria in tokamak plasmas, including mapping of flux surfaces into a variety of coordinate systems.  Includes tools for handling EFIT data stored in Alcator C-Mod MDSPlus trees, as well as eqdsk files.

Full documentation is available at http://eqtools.readthedocs.org/

Package Dependencies
--------------------
The following packages are required or recommended:

- NumPy: Required.
- SciPy: Required.
- F2PY: Optional, needed to build the optional `trispline` module.
- matplotlib: Optional, needed to produce plot of flux surfaces.
- MDSplus: Optional, needed to use data stored in MDSplus trees.

All of these should be available via pip (and should be installed automatically if you run `pip install eqtools` as described in the next section). If you wish to build in place, you may first need to run:
    
    pip install numpy scipy f2py matplotlib

Installation
------------

The easiest way to install the latest release version is with pip:
    
    pip install eqtools

To install from source, uncompress the source files and, from the directory containing `setup.py`, run the following command:
    
    python setup.py install

Or, to build in place, run:
    
    python setup.py build_ext --inplace

If you build in place, you will also need to add your eqtools folder to your PYTHONPATH shell variable:
    
    export PYTHONPATH=$PYTHONPATH:/path/to/where/you/put/eqtools/

Running Tests
-------------

Two tests are included:

- `test.py` uses the module `SolovievEFIT` to compare the result from `eqtools` to Soloviev's analytic solution to the Grad-Shafranov equation for circular flux surfaces. Running this script in an interactive Python session will yield a number of plots, where you can verify that the analytic and `eqtools` results agree.
- `unittests.py` contains many tests of the internal consistency of the coordinate mapping routines. By default, it will try to access data from the Alcator C-Mod tree. If this is not possible, it will try to load its data from the file `test_data.pkl`. You may wish to modify the script to pull in data from your own local site to make sure the specific version you need is working properly. To run these tests, from the directory containing `unittests.py` and `test_data.pkl`, run the command:
        
        python unittests.py

Summary of Files
----------------

The following files comprise the `eqtools` package:

- `LICENSE.md`: The license file. `eqtools` is released under the terms of the GNU General Public License (GPL), version 3.
- `README.md`: This readme file.
- `setup.py`: The `setuptools` setup file. See above for installation instructions.

The package contents itself are in the `eqtools` directory:

- `__init__.py`: Initialization file for the Python package.
- `core.py`: Contains the basic classes the package is built with.
- `EFIT.py`: Contains abstract classes to access data generated by the EFIT equilibrium reconstruction code.
- `CModEFIT.py`: Contains classes to access Alcator C-Mod data.
- `D3DEFIT.py`: Contains classes to access DIII-D data.
- `NSTXEFIT.py`: Contains classes to access NSTX data.
- `TCVLIUQE.py`: Contains classes to access TCV data.
- `FromArrays.py`: Contains classes to construct equilibria from arrays of data.
- `trispline.py`: Contains Python wrappers for the functions defined in `_tricub.pyf`.
- `_tricub.c`: C implementation of tricubic spline interpolation.
- `_tricub.pyf`: F2PY wrapper for `_tricub.c`.
- `afilereader.py`: Contains classes to read the data from EFIT "a" files.
- `pfilereader.py`: Contains classes to read EFIT "p" files.
- `eqdskreader.py`: Contains classes to read EFIT eqdsk files.
- `filewriter.py`: Contains classes to write EFIT eqdsk files.

Test scripts are provided in the `tests` directory:

- `SolovievEFIT.py`: Contains classes to construct analytic Soloviev equilibria with circular flux surfaces.
- `test.py`: Compares the analytical solution to the results from `eqtools` for Soloviev's solution to the Grad-Shafranov equation with circular flux surfaces.
- `unittests.py`: Conducts extensive consistency checks on all of the coordinate mapping routines.
- `demo.py`: Contains a very bare-bones demo to make sure `eqtools` is working. For a more detailed tutorial, refer to the documentation at http://eqtools.readthedocs.org/
