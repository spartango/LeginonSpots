#!/usr/bin/python

import leginondata
import acquisition
import libCVwrapper
import numpy
import time
import math
import pyami.quietscipy
import gui.wx.SpotScanAcquisition
from scipy import ndimage

def targetShape(target):
    dims = target['image']['camera']['dimension']
    return dims['y'],dims['x']


class SpotScanAcquisition(acquisition.Acquisition):
    panelclass = gui.wx.SpotScanAcquisition.Panel
    settingsclass = leginondata.AcquisitionSettingsData
    defaultsettings = acquisition.Acquisition.defaultsettings

    eventinputs = acquisition.Acquisition.eventinputs
    eventoutputs = acquisition.Acquisition.eventoutputs

    defaultsettings.update({
        'spot size':    5,
        'spot spacing': 1.0, 
        'spot count':   3
        })

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
            self.reportTargetListDone(targetlist, 'success')
            return

        # Get the spot size parameters
        spotsize    = self.settings['spot size']
        spotcount   = self.settings['spot count']
        spotspacing = self.settings['spot spacing']

        # Check that these are sane
        if spotsize >= 9 or spotsize <= 1 or spotcount < 0:
            self.logger.error('Invalid spot parameters')
            return

        # Generate a sub target list
        # For each target
        #   Grab coordinates
        #   Generate new coordinates around point
        #   Add to new Target list

        # set the spot size
        self.instrument.tem['spot size'] = spotsize

        # Call processTargetList
        acquisition.Acquisition.processTargetList(newTargetList)