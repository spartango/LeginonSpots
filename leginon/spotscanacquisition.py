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
        # TODO

    def setImageFilename(self, imagedata):
        setImageFilename(imagedata)
        # Spot series filenames
        # TODO

    def processTargetList(self, targetlist):
        # Check the target list
        targets = self.researchTargets(list=targetlist, status='new')
        if not targets:
            self.reportTargetListDone(tilt0targetlist, 'success')
            return

        # Get the spot size parameters

        # Generate a sub target list

        # set the spot size

        # Do a standard acquire for the new targetset

        pass