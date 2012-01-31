#!/usr/bin/python

import leginondata
import acquisition
import libCVwrapper
import numpy
import time
import math
import pyami.quietscipy
from scipy import ndimage

class SpotScanAcquisition(acquisition.Acquisition):
    
    def __init__(self, id, session, managerlocation, **kwargs):
        acquisition.Acquisition.__init__(self, id, session, managerlocation, **kwargs)
        # Spot series info

    def setImageFilename(self, imagedata):
        setImageFilename(imagedata)
        # Spot series filenames

    def processTargetList(self, targetlist):
        # Check the target list

        # Generate a sub target list

        # set the spot size

        # Do a standard acquire for the new targetset

        pass