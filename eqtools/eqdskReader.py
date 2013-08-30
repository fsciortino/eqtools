# This program is distributed under the terms of the GNU General Purpose License (GPL).
# Refer to http://www.gnu.org/licenses/gpl.txt
#
# This file is part of EqTools.
#
# EqTools is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# EqTools is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with EqTools.  If not, see <http://www.gnu.org/licenses/>.

"""
This module contains the EQDSKReader class, which creates Equilibrium class
functionality for equilibria stored in eqdsk files from EFIT(a- and g-files).

Classes:
    EQDSKReader: class inheriting Equilibrium reading g- and a-files for
        equilibrium data.
"""

import scipy
import glob
import re
import csv
import matplotlib.pyplot as plt
from collections import namedtuple
from core import Equilibrium
from AFileReader import AFileReader


class EQDSKReader(Equilibrium):
    """
    Equilibrium subclass working from eqdsk ASCII-file equilibria.

    Inherits mapping and structural data from Equilibrium, populates equilibrium
    and profile data from g- and a-files for a selected shot and time window.
    """
    def __init__(self,shot,time,gfilename=None,afilename=None,length_unit='m'):
        """
        Create instance of EQDSKReader.

        Generates object and reads data from selected g-file (either manually set or
        autodetected based on user shot and time selection), storing as object
        attributes for usage in Equilibrium mapping methods.

        Args:
            shot: Int.  Shot index.
            time: Int.  Time index (typically ms).  Shot and Time used to autogenerate filenames.

        Kwargs:
            gfilename: String.  Manually selects ASCII file for equilibrium read.
            afilename: String.  Manually selects ASCII file for time-history read.
            length_unit: String.  Flag setting length unit for equilibrium scales.
                Defaults to 'm' for lengths in meters.
        """
        # instantiate superclass, forcing time splining to false (eqdsk only contains single time slice)
        super(EQDSKReader,self).__init__(length_unit=length_unit,tspline=False)

        # dict to store default units of length-scale parameters, used by core._getLengthConversionFactor
        self._defaultUnits = {}

        # parse shot and time inputs into standard naming convention
        if len(str(time)) < 5:
            timestring = '0'*(5-len(str(time))) + str(time)
        elif len(str(time)) > 5:
            timestring = str(time)[-5:]
            print('Time window string greater than 5 digits.  Masking to last 5 digits.  \
                  If this does not match the selected EQ files, \
                  please use explicit filename inputs.')
        else:   #exactly five digits
            timestring = str(time)

        name = str(shot)+'.'+timestring

        # if explicit filename for g-file is not set, check current directory for files matching name
        # if multiple valid files or no files are found, trigger ValueError
        if gfilename is None:   #attempt to generate filename
            print('Searching directory for file g'+name+'.')
            gcurrfiles = glob.glob('g'+name+'*')
            if len(gcurrfiles) == 1:
                self._gfilename = gcurrfiles[0]
                print('File found: '+self._gfilename)
            elif len(gcurrfiles) > 1:
                raise ValueError('Multiple valid g-files detected in directory.  \n\
                                  Please select a file with explicit \n\
                                  input or clean directory.')
            else:   # no files found
                raise ValueError('No valid g-files detected in directory.  \n\
                                  Please select a file with explicit input or \n\
                                  ensure file is in directory.')
        else:   # check that given file is in directory
            gcurrfiles = glob.glob(gfilename)
            if len(gcurrfiles) < 1:
                raise ValueError('No g-file with the given name detected in directory.  \n\
                                  Please ensure the file is in the active directory or \n\
                                  that you have supplied the correct name.')
            else:
                self._gfilename = gfilename

        # and likewise for a-file name.  However, we can operate at reduced capacity
        # without the a-file.  If no file with explicitly-input name is found, or 
        # multiple valid files (with no explicit input) are found, raise ValueError.
        # otherwise (no autogenerated files found) set hasafile flag false and 
        # nonfatally warn user.
        if afilename is None:
            print('Searching directory for file a'+name+'.')
            acurrfiles = glob.glob('a'+name+'*')
            if len(acurrfiles) == 1:
                self._afilename = acurrfiles[0]
                print('File found: '+self._afilename)
                self._hasafile = True
            elif len(acurrfiles) > 1:
                raise ValueError('Multiple valid a-files detected in directory.  \
                                  Please select a file with explicit \
                                  input or clean directory.')
            else:   # no files found
                print('No valid a-files detected in directory.  \
                      Please select a file with explicit input or \
                      ensure file in in directory.  Disabling a-file \
                      read functions.')
                self._afilename = None
                self._hasafile = False
        else:   # check that given file is in directory
            acurrfiles = glob.glob(afilename)
            if len(acurrfiles) < 1:
                raise ValueError('No a-file with the given name detected in directory.  \
                                  Please ensure the file is in the active directory or \
                                  that you have supplied the correct name.')
            else:
                self._afilename = afilename

        # now we start reading the g-file
        with open(self._gfilename,'r') as gfile:
            reader = csv.reader(gfile)  # skip the CSV delimiter, let split or regexs handle parsing.
                                        # use csv package for error handling.
            # read the header line, containing grid size, mfit size, and type data
            line = next(reader)[0].split()
            self._date = line[1]                            # (str) date of g-file generation, MM/DD/YYYY
            self._shot = int(re.split('\D',line[-5])[-1])   # (int) shot index
            timestring = line[-4]                           # (str) time index, with units (e.g. '875ms')
            imfit = int(line[-3])                           # not sure what this is supposed to be...
            nw = int(line[-2])                              # width of flux grid (dim(R))
            nh = int(line[-1])                              # height of flux grid (dim(Z))

            #extract time, units from timestring
            time = re.findall('\d+',timestring)[0]
            self._tunits = timestring.split(time)[1]
            timeConvertDict = {'ms':1000.,'s':1}
            self._time = scipy.array(float(time)*timeConvertDict[self._tunits]) # returns time in seconds as array
            
            # next line - construction values for RZ grid
            line = next(reader)[0]
            line = re.findall('-?\d\.\d*E[-+]\d*',line)     # regex magic!
            xdim = float(line[0])     # width of R-axis in grid
            zdim = float(line[1])     # height of Z-axis in grid
            rzero = float(line[2])    # zero point of R grid
            rgrid0 = float(line[3])   # start point of R grid
            zmid = float(line[4])     # midpoint of Z grid

            # construct EFIT grid
            self._rGrid = scipy.linspace(rgrid0,rgrid0 + xdim,nw)
            self._zGrid = scipy.linspace(zmid - zdim/2.0,zmid + zdim/2.0,nh)
            drefit = (self._rGrid[-1] - self._rGrid[0])/(nw-1)
            dzefit = (self._zGrid[-1] - self._zGrid[0])/(nh-1)
            self._defaultUnits['_rGrid'] = 'm'
            self._defaultUnits['_zGrid'] = 'm'

            # read R,Z of magnetic axis, psi at magnetic axis and LCFS, and bzero
            line = next(reader)[0]
            line = re.findall('-?\d\.\d*E[-+]\d*',line)
            self._rmaxis = scipy.array(float(line[0]))
            self._zmaxis = scipy.array(float(line[1]))
            self._psiAxis = scipy.array(float(line[2]))
            self._psiLCFS = scipy.array(float(line[3]))
            self._bzero = scipy.array(float(line[4]))
            self._defaultUnits['_psiAxis'] = 'Wb/rad'
            self._defaultUnits['_psiLCFS'] = 'Wb/rad'

            # read EFIT-calculated plasma current, psi at magnetic axis (duplicate), 
            # dummy, R of magnetic axis (duplicate), dummy
            line = next(reader)[0]
            line = re.findall('-?\d\.\d*E[-+]\d*',line)
            self._IpCalc = scipy.array(float(line[0]))
            self._defaultUnits['_IpCalc'] = 'A'

            # read Z of magnetic axis (duplicate), dummy, psi at LCFS (duplicate), dummy, dummy
            line = next(reader)[0]
            # don't actually need anything from this line

            # start reading fpol, next nw inputs
            nrows = nw/5
            if nw % 5 != 0:     # catch truncated rows
                nrows += 1

            self._fpol = []
            for i in range(nrows):
                line = next(reader)[0]
                line = re.findall('-?\d\.\d*E[-+]\d*',line)
                for val in line:
                    self._fpol.append(float(val))
            self._fpol = scipy.array(self._fpol)

            # and likewise for pressure
            self._fluxPres = []
            for i in range(nrows):
                line = next(reader)[0]
                line = re.findall('-?\d\.\d*E[-+]\d*',line)
                for val in line:
                    self._fluxPres.append(float(val))
            self._fluxPres = scipy.array(self._fluxPres)
            self._defaultUnits['_fluxPres'] = 'Pa'

            # geqdsk written as negative for positive plasma current
            # ffprim, pprime input with correct EFIT sign
            self._ffprim = []
            for i in range(nrows):
                line = next(reader)[0]
                line = re.findall('-?\d\.\d*E[-+]\d*',line)
                for val in line:
                    self._ffprim.append(float(val))
            self._ffprim = scipy.array(self._ffprim)

            self._pprime = []
            for i in range(nrows):
                line = next(reader)[0]
                line = re.findall('-?\d\.\d*E[-+]\d*',line)
                for val in line:
                    self._pprime.append(float(val))
            self._pprime = scipy.array(self._pprime)

            # read the 2d [nw,nh] array for psiRZ
            # start by reading nw x nh points into 1D array,
            # then repack in column order into final array
            npts = nw*nh
            nrows = npts/5
            if npts % 5 != 0:
                nrows += 1

            psis = []
            for i in range(nrows):
                line = next(reader)[0]
                line = re.findall('-?\d\.\d*E[-+]\d*',line)
                for val in line:
                    psis.append(float(val))
            self._psiRZ = scipy.array(psis).reshape((nw,nh),order='C')
            self._defaultUnits['_psiRZ'] = 'Wb/rad'

            # read q(psi) profile, nw points (same basis as fpol, pres, etc.)
            nrows = nw/5
            if nw % 5 != 0:
                nrows += 1

            self._qpsi = []
            for i in range(nrows):
                line = next(reader)[0]
                line = re.findall('-?\d\.\d*E[-+]\d*',line)
                for val in line:
                    self._qpsi.append(float(val))
            self._qpsi = scipy.array(self._qpsi)

            # read nbbbs, limitr
            line = next(reader)[0].split()
            nbbbs = int(line[0])
            limitr = int(line[1])

            # next data reads as 2 x nbbbs array, then broken into
            # rbbbs, zbbbs (R,Z locations of LCFS)
            npts = 2*nbbbs
            nrows = npts/5
            if npts % 5 != 0:
                nrows += 1
            bbbs = []
            for i in range(nrows):
                line = next(reader)[0]
                line = re.findall('-?\d\.\d*E[-+]\d*',line)
                for val in line:
                    bbbs.append(float(val))
            bbbs = scipy.array(bbbs).reshape((2,nbbbs),order='F')
            self._RLCFS = bbbs[0,:]
            self._ZLCFS = bbbs[1,:]
            self._defaultUnits['_RLCFS'] = 'm'
            self._defaultUnits['_ZLCFS'] = 'm'

            # next data reads as 2 x limitr array, then broken into
            # xlim, ylim (locations of limiter)(?)
            npts = 2*limitr
            nrows = npts/5
            if npts % 5 != 0:
                nrows += 1
            lim = []
            for i in range(nrows):
                line = next(reader)[0]
                line = re.findall('-?\d\.\d*E[-+]\d*',line)
                for val in line:
                    lim.append(float(val))
            lim = scipy.array(lim).reshape((2,limitr),order='C')
            self._xlim = lim[0,:]
            self._ylim = lim[1,:]

            # this is the extent of the original g-file read.
            # attempt to continue read for newer g-files; exception
            # handler sets relevant parameters to None for older g-files
            try:
                # read kvtor, rvtor, nmass
                line = next(reader)[0].split()
                kvtor = int(line[0])
                rvtor = float(line[1])
                nmass = int(line[2])

                # read kvtor data if present
                if kvtor > 0:
                    nrows = nw/5
                    if nw % 5 != 0:
                        nrows += 1
                    self._presw = []
                    for i in range(nrows):
                        line = next(reader)[0]
                        line = re.findall('-?\d.\d*E[-+]\d*',line)
                        for val in line:
                            self._presw.append(float(val))
                    self._presw = scipy.array(self._presw)
                    self._preswp = []
                    for i in range(nrows):
                        line = next(reader)[0]
                        line = re.findall('-?\d.\d*E[-+]\d*',line)
                        for val in line:
                            self._preswp.append(float(val))
                    self._preswp = scipy.array(self._preswp)
                else:
                    self._presw = scipy.array([0])
                    self._preswp = scipy.array([0])

                # read ion mass density if present
                if nmass > 0:
                    nrows = nw/5
                    if nw % 5 != 0:
                        nrows += 1
                    self._dmion = []
                    for i in range(nrows):
                        line = next(reader)[0]
                        line = re.findall('-?\d.\d*E[-+]\d*',line)
                        for val in line:
                            self._dmion.append(float(val))
                    self._dmion = scipy.array(self._dmion)
                else:
                    self._dmion = scipy.array([0])

                # read rhovn
                nrows = nw/5
                if nw % 5 != 0:
                    nrows += 1
                self._rhovn = []
                for i in range(nrows):
                    line = next(reader)[0]
                    line = re.findall('-?\d.\d*E[-+]\d*',line)
                    for val in line:
                        self._rhovn.append(float(val))
                self._rhovn = scipy.array(self._rhovn)

                # read keecur; if >0 read workk
                line = gfile.readline.split()
                keecur = int(line[0])
                if keecur > 0:
                    self._workk = []
                    for i in range(nrows):
                        line = next(reader)[0]
                        line = re.findall('-?\d.\d*E[-+]\d*',line)
                        for val in line:
                            self._workk.append(float(val))
                    self._workk = scipy.array(self._workk)
                else:
                    self._workk = scipy.array([0])
            except:
                self._presw = scipy.array([0])
                self._preswp = scipy.array([0])
                self._rhovn = scipy.array([0])
                self._dmion = scipy.array([0])
                self._workk = scipy.array([0])

            # read through to end of file to get footer line
            try:
                r = ''
                for row in reader:
                    r = row
                self._efittype = r.split()[-1]
            except:
                self._efittype = None
            

        # toroidal current density on (r,z,t) grid typically not
        # written to g-files.  Override getter method and initialize
        # to none.
        self._Jp = None

        # initialize data stored in a-file
        # fields
        self._btaxp = None
        self._btaxv = None
        self._bpolav = None
        self._defaultUnits['_btaxp'] = 'T'
        self._defaultUnits['_btaxv'] = 'T'
        self._defaultUnits['_bpolav'] = 'T'

        # currents
        self._IpMeas = None
        self._defaultUnits['_IpMeas'] = 'A'

        # safety factor parameters
        self._q0 = None
        self._q95 = None
        self._qLCFS = None
        self._rq1 = None
        self._rq2 = None
        self._rq3 = None
        self._defaultUnits['_rq1'] = 'cm'
        self._defaultUnits['_rq2'] = 'cm'
        self._defaultUnits['_rq3'] = 'cm'

        # shaping parameters
        self._kappa = None
        self._dupper = None
        self._dlower = None

        # dimensional geometry parameters
        self._rmag = None
        self._zmag = None
        self._aLCFS = None
        self._areaLCFS = None
        self._RmidLCFS = None
        self._defaultUnits['_rmag'] = 'cm'
        self._defaultUnits['_zmag'] = 'cm'
        self._defaultUnits['_aLCFS'] = 'cm'
        self._defaultUnits['_areaLCFS'] = 'cm^2'
        self._defaultUnits['_RmidLCFS'] = 'm'

        # calc. normalized pressure values
        self._betat = None
        self._betap = None
        self._Li = None

        # diamagnetic measurements
        self._diamag = None
        self._betatd = None
        self._betapd = None
        self._WDiamag = None
        self._tauDiamag = None
        self._defaultUnits['_diamag'] = 'Vs'
        self._defaultUnits['WDiamag'] = 'J'
        self._defaultUnits['_tauDiamag'] = 'ms'

        # calculated energy
        self._WMHD = None
        self._tauMHD = None
        self._Pinj = None
        self._Wbdot = None
        self._Wpdot = None
        self._defaultUnits['_WMHD'] = 'J'
        self._defaultUnits['_tauMHD'] = 'ms'
        self._defaultUnits['_Pinj'] = 'W'
        self._defaultUnits['_Wbdot'] = 'W'
        self._defaultUnits['_Wpdot'] = 'W'

        # fitting parameters
        self._volLCFS = None
        self._fluxVol = None
        self._RmidPsi = None
        self._defaultUnits['_volLCFS'] = 'cm^3'
        self._defaultUnits['_fluxVol'] = 'm^3'
        self._defaultUnits['_RmidPsi'] = 'm'

        # attempt to populate these parameters from a-file
        if self._afilename is not None:
            try:
                self.readAFile(self._afilename)
            except IOError:
                print('a-file data not loaded.')
        else:
            print('a-file data not loaded.')
                    
    def __str__(self):
        if self._efittype is None:
            eq = 'equilibrium'
        else:
            eq = self._efittype+' equilibrium'
        return 'G-file '+eq+' from '+str(self._gfilename)
        
    def getInfo(self):
        """
        returns namedtuple of equilibrium information
        outputs:
        namedtuple containing
            shot:       shot index
            time:       time point of g-file
            nr:         size of R-axis of spatial grid
            nz:         size of Z-axis of spatial grid
            efittype:   EFIT calculation type (magnetic, kinetic, MSE)
        """
        data = namedtuple('Info',['shot','time','nr','nz','efittype'])
        try:
            nr = len(self._rGrid)
            nz = len(self._zGrid)
            shot = self._shot
            time = self._time
            efittype = self._efittype
        except TypeError:
            nr,nz,shot,time=0
            efittype=None
            print 'failed to load data from g-file.'
        return data(shot=shot,time=time,nr=nr,nz=nz,efittype=efittype)

    def readAFile(self,afile):
        """
        Reads a-file (scalar time-history data) to pull additional equilibrium data
        not found in g-file, populates remaining data (initialized as None) in object.

        Args:
            afile: String.  Path to ASCII a-file.

        Raises:
            IOError: If afile is not found.
        """
        try:
            afr = AFileReader(afile)

            # fields
            self._btaxp = scipy.array(afr.btaxp)
            self._btaxv = scipy.array(afr.btaxv)
            self._bpolav = scipy.array(afr.bpolav)

            # currents
            self._IpMeas = scipy.array(afr.pasmat)

            # safety factor parameters
            self._q0 = scipy.array(afr.qqmin)
            self._q95 = scipy.array(afr.qpsib)
            self._qLCFS = scipy.array(afr.qout)
            self._rq1 = scipy.array(afr.aaq1)
            self._rq2 = scipy.array(afr.aaq2)
            self._rq3 = scipy.array(afr.aaq3)

            # shaping parameters
            self._kappa = scipy.array(afr.eout)
            self._dupper = scipy.array(afr.doutu)
            self._dlower = scipy.array(afr.doutl)

            # dimensional geometry parameters
            self._rmag = scipy.array(afr.rmagx)
            self._zmag = scipy.array(afr.zmagx)
            self._aLCFS = scipy.array(afr.aout)
            self._areaLCFS = scipy.array(afr.areao)
            self._RmidLCFS = scipy.array(afr.rmidout)

            # calc. normalized pressure values
            self._betat = scipy.array(afr.betat)
            self._betap = scipy.array(afr.betap)
            self._Li = scipy.array(afr.ali)

            # diamagnetic measurements
            self._diamag = scipy.array(afr.diamag)
            self._betatd = scipy.array(afr.betatd)
            self._betapd = scipy.array(afr.betapd)
            self._WDiamag = scipy.array(afr.wplasmd)
            self._tauDiamag = scipy.array(afr.taudia)

            # calculated energy
            self._WMHD = scipy.array(afr.wplasm)
            self._tauMHD = scipy.array(afr.taumhd)
            self._Pinj = scipy.array(afr.pbinj)
            self._Wbdot = scipy.array(afr.wbdot)
            self._Wpdot = scipy.array(afr.wpdot)

            # fitting parameters
            self._volLCFS = scipy.array(afr.vout)
            self._fluxVol = None
            self._RmidPsi = None    # not written in g- or a-file, not used by fitting parameters

        except IOError:
            raise IOError('no file "%s" found.' % afile)

    def getTimeBase(self):
        """
        Returns EFIT time point
        """
        return self._time.copy()

    def getCurrentSign(self):
        """
        Returns the sign of the current, based on the check in Steve Wolfe's
        IDL implementation efit_rz2psi.pro.
        """
        if self._currentSign is None:
            self._currentSign = 1 if scipy.mean(self.getIpMeas()) > 1e5 else -1
        return self._currentSign

    def getFluxGrid(self):
        """
        Returns EFIT flux grid, [r,z]
        """
        return self._psiRZ.copy()

    def getRGrid(self,length_unit=1):
        """
        Returns EFIT R-axis [r]
        """
        unit_factor = self._getLengthConversionFactor(self._defaultUnits['_rGrid'],length_unit)
        return unit_factor * self._rGrid.copy()

    def getZGrid(self,length_unit=1):
        """
        Returns EFIT Z-axis [z]
        """
        unit_factor = self._getLengthConversionFactor(self._defaultUnits['_zGrid'],length_unit)
        return unit_factor * self._zGrid.copy()

    def getFluxAxis(self):
        """
        Returns psi on magnetic axis
        """
        return scipy.array(self._psiAxis)

    def getFluxLCFS(self):
        """
        Returns psi at separatrix
        """
        return scipy.array(self._psiLCFS)

    def getRLCFS(self,length_unit=1):
        """
        Returns array of R-values of LCFS
        """
        unit_factor = self._getLengthConversionFactor(self._defaultUnits['_RLCFS'],length_unit)
        return unit_factor * self._RLCFS.copy()

    def getZLCFS(self,length_unit=1):
        """
        Returns array of Z-values of LCFS
        """
        unit_factor = self._getLengthConversionFactor(self._defaultUnits['_ZLCFS'],length_unit)
        return unit_factor * self._ZLCFS.copy()

    def getFluxVol(self):
        #returns volume contained within a flux surface as function of psi, volp(psi,t)
        raise NotImplementedError()

    def getVolLCFS(self,length_unit=3):
        """
        Returns volume with LCFS.

        Raises:
            ValueError: if a-file data is not read.
        """
        if self._volLCFS is None:
            raise ValueError('must read a-file for this data.')
        else:
            unit_factor = self._getLengthConversionFactor(self._defaultUnits['_volLCFS'],length_unit)
            return unit_factor * self._volLCFS.copy()

    def getRmidPsi(self):
        """
        Returns outboard-midplane major radius of flux surfaces.
        Data not read from a/g-files, not implemented for eqdskReader.

        Raises:
            NotImplementedError: RmidPsi not read from a/g-files.
        """
        raise NotImplementedError('RmidPsi not read from a/g-files.')

    def getFluxPres(self):
        """
        Returns pressure on flux surface p(psi)
        """
        return self._fluxPres.copy()

    def getElongation(self):
        """
        Returns elongation of LCFS.

        Raises:
            ValueError: if a-file data is not read.
        """
        if self._kappa is None:
            raise ValueError('must read a-file for this data.')
        else:
            return self._kappa.copy()

    def getUpperTriangularity(self):
        """
        Returns upper triangularity of LCFS.

        Raises:
            ValueError: if a-file data is not read.
        """
        if self._dupper is None:
            raise ValueError('must read a-file for this data.')
        else:
            return self._dupper.copy()

    def getLowerTriangularity(self):
        """
        Returns lower triangularity of LCFS.

        Raises:
            ValueError: if a-file data is not read.
        """
        if self._dlower is None:
            raise ValueError('must read a-file for this data.')
        else:
            return self._dlower.copy()

    def getShaping(self):
        """
        Pulls LCFS elongation, upper/lower triangularity.
        Returns namedtuple containing [kappa,delta_u,delta_l].

        Raises:
            ValueError: if a-file data is not read.
        """
        try:
            kap = self.getElongation()
            du = self.getUpperTriangularity()
            dl = self.getLowerTriangularity()
            data = namedtuple('Shaping',['kappa','delta_u','delta_l'])
            return data(kappa=kap,delta_u=du,delta_l=dl)
        except ValueError:
            raise ValueError('must read a-file for this data.') 

    def getMagR(self,length_unit=1):
        """
        Returns major radius of magnetic axis.

        Raises:
            ValueError: if a-file data is not read.
        """
        if self._rmag is None:
            raise ValueError('must read a-file for this data.')
        else:
            unit_factor = self._getLengthConversionFactor(self._defaultUnits['_rmag'],length_unit)
            return unit_factor * self._rmag.copy()

    def getMagZ(self,length_unit=1):
        """
        Returns Z of magnetic axis.

        Raises:
            ValueError: if a-file data is not read.
        """
        if self._zmag is None:
            raise ValueError('must read a-file for this data.')
        else:
            unit_factor = self._getLengthConversionFactor(self._defaultUnits['_zmag'],length_unit)
            return unit_factor * self._zmag.copy()

    def getAreaLCFS(self,length_unit=2):
        """
        Returns surface area of LCFS.

        Raises:
            ValueError: if a-file data is not read.
        """
        if self._areaLCFS is None:
            raise ValueError('must read a-file for this data.')
        else:
            unit_factor = self._getLengthConversionFactor(self._defaultUnits['_areaLCFS'],length_unit)
            return unit_factor * self._areaLCFS.copy()

    def getAOut(self,length_unit=1):
        """
        Returns outboard-midplane minor radius of LCFS.

        Raises:
            ValueError: if a-file data is not read.
        """
        if self._aLCFS is None:
            raise ValueError('must read a-file for this data.')
        else:
            unit_factor = self._getLengthConversionFactor(self._defaultUnits['_aLCFS'],length_unit)
            return unit_factor * self._aLCFS.copy()

    def getRmidOut(self,length_unit=1):
        """
        Returns outboard-midplane major radius of LCFS.

        Raises:
            ValueError: if a-file data is not read.
        """
        if self._RmidLCFS is None:
            raise ValueError('must read a-file for this data.')
        else:
            unit_factor = self._getLengthConversionFactor(self._defaultUnits['_RmidLCFS'],length_unit)
            return unit_factor * self._RmidLCFS.copy()

    def getGeometry(self,length_unit=None):
        """
        Pulls dimensional geometry parameters.
        Returns namedtuple containing [Rmag,Zmag,AreaLCFS,aOut,RmidOut]

        Kwargs:
            length_unit: TODO

        Raises:
            ValueError: if a-file data is not read.
        """
        try:
            Rmag = self.getMagR(length_unit=(length_unit if length_unit is not None else 1))
            Zmag = self.getMagZ(length_unit=(length_unit if length_unit is not None else 1))
            AreaLCFS = self.getAreaLCFS(length_unit=(length_unit if length_unit is not None else 2))
            aOut = self.getAOut(length_unit=(length_unit if length_unit is not None else 1))
            RmidOut = self.getRmidOut(length_unit=(length_unit if length_unit is not None else 1))
            data = namedtuple('Geometry',['Rmag','Zmag','AreaLCFS','aOut','RmidOut'])
            return data(Rmag=Rmag,Zmag=Zmag,AreaLCFS=AreaLCFS,aOut=aOut,RmidOut=RmidOut)
        except ValueError:
            raise ValueError('must read a-file for this data.')

    def getQProfile(self):
        """
        Returns safety factor q(psi).
        """
        return self._qpsi.copy()

    def getQ0(self):
        """
        Returns safety factor q on-axis, q0.

        Raises:
            ValueError: if a-file data is not read.
        """
        if self._q0 is None:
            raise ValueError('must read a-file for this data.')
        else:
            return self._q0.copy()

    def getQ95(self):
        """
        Returns safety factor q at 95% flux surface.

        Raises:
            ValueError: if a-file data is not read.
        """
        if self._q95 is None:
            raise ValueError('must read a-file for this data.')
        else:
            return self._q95.copy()

    def getQLCFS(self):
        """
        Returns safety factor q at LCFS (interpolated).

        Raises:
            ValueError: if a-file data is not loaded.
        """
        if self._qLCFS is None:
            raise ValueError('must read a-file for this data.')
        else:
            return self._qLCFS.copy()

    def getQ1Surf(self,length_unit=1):
        """
        Returns outboard-midplane minor radius of q=1 surface.

        Raises:
            ValueError: if a-file data is not read.
        """
        if self._rq1 is None:
            raise ValueError('must read a-file for this data.')
        else:
            unit_factor = self._getLengthConversionFactor(self._defaultUnits['_rq1'],length_unit)
            return unit_factor * self._rq1.copy()
    
    def getQ2Surf(self,length_unit=1):
        """
        Returns outboard-midplane minor radius of q=2 surface.

        Raises:
            ValueError: if a-file data is not read.
        """
        if self._rq2 is None:
            raise ValueError('must read a-file for this data.')
        else:
            unit_factor = self._getLengthConversionFactor(self._defaultUnits['_rq2'],length_unit)
            return unit_factor * self._rq2.copy()

    def getQ3Surf(self,length_unit=1):
        """
        Returns outboard-midplane minor radius of q=3 surface.

        Raises:
            ValueError: if a-file data is not read.
        """
        if self._rq3 is None:
            raise ValueError('must read a-file for this data.')
        else:
            unit_factor = self._getLengthConversionFactor(self._defaultUnits['_rq3'],length_unit)
            return unit_factor * self._rq3.copy()

    def getQs(self):
        """
        Pulls q-profile data.
        Returns namedtuple containing [q0,q95,qLCFS,rq1,rq2,rq3]

        Raises:
            ValueError: if a-file data is not read.
        """
        try:
            q0 = self.getQ0()
            q95 = self.getQ95()
            qLCFS = self.getQLCFS()
            rq1 = self.getQ1Surf(length_unit=length_unit)
            rq2 = self.getQ2Surf(length_unit=length_unit)
            rq3 = self.getQ3Surf(length_unit=length_unit)
            data = namedtuple('Qs',['q0','q95','qLCFS','rq1','rq2','rq3'])
            return data(q0=q0,q95=q95,qLCFS=qLCFS,rq1=rq1,rq2=rq2,rq3=rq3)
        except ValueError:
            raise ValueError('must read a-file for this data.')

    def getBtVac(self):
        """
        Returns vacuum toroidal field on-axis.

        Raises:
            ValueError: if a-file data is not read.
        """
        if self._btaxv is None:
            raise ValueError('must read a-file for this data.')
        else:
            return self._btaxv.copy()

    def getBtPla(self):
        """
        Returns plasma toroidal field on-axis.

        Raises:
            ValueError: if a-file data is not read.
        """
        if self._btaxp is None:
            raise ValueError('must read a-file for this data.')
        else:
            return self._btaxp.copy()

    def getBpAvg(self):
        """
        Returns average poloidal field.

        Raises:
            ValueError: if a-file data is not read.
        """
        if self._bpolav is None:
            raise ValueError('must read a-file for this data.')
        else:
            return self._bpolav.copy()

    def getFields(self):
        """
        Pulls vacuum and plasma toroidal field, poloidal field data.
        Returns namedtuple containing [BtVac,BtPla,BpAvg]

        Raises:
            ValueError: if a-file data is not read.
        """
        try:
            btaxv = self.getBtVac()
            btaxp = self.getBtPla()
            bpolav = self.getBpAvg()
            data = namedtuple('Fields',['BtVac','BtPla','BpAvg'])
            return data(BtVac=btaxv,BtPla=btaxp,BpAvg=bpolav)
        except ValueError:
            raise ValueError('must read a-file for this data.')

    def getIpCalc(self):
        """
        Returns EFIT-calculated plasma current.
        """
        return self._IpCalc.copy()

    def getIpMeas(self):
        """
        Returns measured plasma current.

        Raises:
            ValueError: if a-file data is not read.
        """
        if self._IpMeas is None:
            raise ValueError('must read a-file for this data.')
        else:
            return self._IpMeas.copy()

    def getJp(self):
        """
        Returns (r,z) grid of toroidal plasma current density.
        Data not read from g-file, not implemented for eqdskReader.

        Raises:
            NotImplementedError: Jp not read from g-file.
        """
        raise NotImplementedError('Jp not read from g-file.')

    def getBetaT(self):
        """
        Returns EFIT-calculated toroidal beta.

        Raises:
            ValueError: if a-file data is not read.
        """
        if self._betat is None:
            raise ValueError('must read a-file for this data.')
        else:
            return self._betat.copy()

    def getBetaP(self):
        """
        Returns EFIT-calculated poloidal beta.

        Raises:
            ValueError: if a-file data is not read
        """
        if self._betap is None:
            raise ValueError('must read a-file for this data.')
        else:
            return self._betap.copy()

    def getLi(self):
        """
        Returns internal inductance of plasma.

        Raises:
            ValueError: if a-file data is not read.
        """
        if self._Li is None:
            raise ValueError('must read a-file for this data.')
        else:
            return self._Li.copy()

    def getBetas(self):
        """
        Pulls EFIT-calculated betas and internal inductance.
        Returns a namedtuple containing [betat,betap,Li]

        Raises:
            ValueError: if a-file data is not read.
        """
        try:
            betat = self.getBetaT()
            betap = self.getBetaP()
            Li = self.getLi()
            data = namedtuple('Betas',['betat','betap','Li'])
            return data(betat=betat,betap=betap,Li=Li)
        except ValueError:
                raise ValueError('must read a-file for this data.')
            
    def getDiamagFlux(self):
        """
        Returns diamagnetic flux.

        Raises:
            ValueError: if a-file data is not read.
        """
        if self._diamag is None:
            raise ValueError('must read a-file for this data.')
        else:
            return self._diamag.copy()

    def getDiamagBetaT(self):
        """
        Returns diamagnetic-loop measured toroidal beta.

        Raises:
            ValueError: if a-file data is not read.
        """
        if self._betatd is None:
            raise ValueError('must read a-file for this data.')
        else:
            return self._betatd.copy()

    def getDiamagBetaP(self):
        """
        Returns diamagnetic-loop measured poloidal beta.

        Raises:
            ValueError: if a-file data is not read.
        """
        if self._betapd is None:
            raise ValueError('must read a-file for this data.')
        else:
            return self._betapd.copy()

    def getDiamagTauE(self):
        """
        Returns diamagnetic-loop energy confinement time.

        Raises:
            ValueError: if a-file data is not read.
        """
        if self._tauDiamag is None:
            raise ValueError('must read a-file for this data.')
        else:
            return self._tauDiamag.copy()

    def getDiamagWp(self):
        """
        Returns diamagnetic-loop measured stored energy.

        Raises:
            ValueError: if a-file data is not read.
        """
        if self._WDiamag is None:
            raise ValueError('must read a-file for this data.')
        else:
            return self._WDiamag.copy()

    def getDiamag(self):
        """
        Pulls diamagnetic flux, diamag. measured toroidal and poloidal beta, stored energy, and energy confinement time.
        Returns a namedtuple containing [diaFlux,diaBetat,diaBetap,diaTauE,diaWp]

        Raises:
            ValueError: if a-file data is not read
        """
        try:
            dFlux = self.getDiamagFlux()
            betatd = self.getDiamagBetaT()
            betapd = self.getDiamagBetaP()
            dTau = self.getDiamagTauE()
            dWp = self.getDiamagWp()
            data = namedtuple('Diamag',['diaFlux','diaBetat','diaBetap','diaTauE','diaWp'])
            return data(diaFlux=dFLux,diaBetat=betatd,diaBetap=betapd,diaTauE=dTau,diaWp=dWp)
        except ValueError:
                raise ValueError('must read a-file for this data.')

    def getWMHD(self):
        """
        Returns EFIT-calculated stored energy.

        Raises:
            ValueError: if a-file data is not read.
        """
        if self._WMHD is None:
            raise ValueError('must read a-file for this data.')
        else:
            return self._WMHD.copy()

    def getTauMHD(self):
        """
        Returns EFIT-calculated energy confinement time.

        Raises:
            ValueError: if a-file data is not read.
        """
        if self._tauMHD is None:
            raise ValueError('must read a-file for this data.')
        else:
            return self._tauMHD.copy()

    def getPinj(self):
        """
        Returns EFIT injected power.

        Raises:
            ValueError: if a-file data is not read.
        """
        if self._Pinj is None:
            raise ValueError('must read a-file for this data.')
        else:
            return self._Pinj.copy()

    def getWbdot(self):
        """
        Returns EFIT d/dt of magnetic stored energy

        Raises:
            ValueError: if a-file data is not read.
        """
        if self._Wbdot is None:
            raise ValueError('must read a-file for this data.')
        else:
            return self._Wbdot.copy()

    def getWpdot(self):
        """
        Returns EFIT d/dt of plasma stored energy.

        Raises:
            ValueError: if a-file data is not read.
        """
        if self._Wpdot is None:
            raise ValueError('must read a-file for this data.')
        else:
            return self._Wpdot.copy()

    def getEnergy(self):
        """
        Pulls EFIT stored energy, energy confinement time, injected power, and d/dt of magnetic and plasma stored energy.
        Returns namedtuple containing [WMHD,tauMHD,Pinj,Wbdot,Wpdot]

        Raises:
            ValueError: if a-file data is not read.
        """
        try:
            WMHD = self.getWMHD()
            tauMHD = self.getTauMHD()
            Pinj = self.getPinj()
            Wbdot = self.getWbdot()
            Wpdot = self.getWpdot()
            data = namedtuple('Energy',['WMHD','tauMHD','Pinj','Wbdot','Wpdot'])
            return data(WMHD=WMHD,tauMHD=tauMHD,Pinj=Pinj,Wbdot=Wbdot,Wpdot=Wpdot)
        except ValueError:
            raise ValueError('must read a-file for this data.')

    def getParam(self,name):
        """
        Backup function, applying a direct path input for tree-like data storage access
        for parameters not typically found in Equilbrium object.  Directly calls attributes
        read from g/a-files in copy-safe manner.

        Args:
            name: String.  Parameter name for value stored in EQDSKReader instance.

        Raises:
            AttributeError: raised if no attribute is found.
        """
        try:
            return super(EQDSKReader,self).__getattribute__(name)
        except AttributeError:
            try:
                attr = super(EQDSKReader,self)._getattribute__('_'+name)
                if type(attr) is scipy.array:
                    return attr.copy()
                else:
                    return attr
            except AttributeError:
                raise AttributeError('No attribute "_%s" found' % name)
        
    def getMachineCrossSection(self):
        """
        Method to pull machine cross-section from data storage, convert to standard format for plotting routine.
        Not implemented for eqdsk class.
        """
        raise NotImplementedError('no machine cross section stored in g-files.')
        
    def plotFlux(self):
        """
        streamlined plotting of flux contours directly from psi grid
        """
        plt.ion()

        try:
            psiRZ = self.getFluxGrid()
            rGrid = self.getRGrid()
            zGrid = self.getZGrid()

            RLCFS = self.getRLCFS()
            ZLCFS = self.getZLCFS()
        except ValueError:
            raise AttributeError('cannot plot EFIT flux map.')

        fluxPlot = plt.figure(figsize=(6,11))
        plt.xlabel('$R$ (m)')
        plt.ylabel('$Z$ (m)')
        fillcont = plt.contourf(rGrid,zGrid,psiRZ,50)
        cont = plt.contour(rGrid,zGrid,psiRZ,50,colors='k',linestyles='solid')
        LCFS = plt.plot(RLCFS,ZLCFS,'r',linewidth=3)
        plt.show()
                



                







