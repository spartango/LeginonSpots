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

    #def setImageFilename(self, imagedata):
    #    setImageFilename(imagedata)
    #    Spot series filenames
    #    TODO

    def targetPoint(target):
        return target['delta row'],target['delta column']

    def targetPoints(targets):
        return map(targetPoint, targets)

    def targetShape(target):
        dims = target['image']['camera']['dimension']
        return dims['y'],dims['x']

    def simulateTarget(self):
        self.setStatus('processing')
        currentpreset = self.presetsclient.getCurrentPreset()
        if currentpreset is None:
            try:
                self.validatePresets()
            except InvalidPresetsSequence:
                self.logger.error('Configure at least one preset in the settings for this node.')
                return
            presetnames = self.settings['preset order']
            currentpreset = self.presetsclient.getPresetByName(presetnames[0])
        targetdata = self.newSimulatedTarget(preset=currentpreset,grid=self.grid)
        self.publish(targetdata, database=True)
        ## change to 'processing' just like targetwatcher does
        proctargetdata = self.reportTargetStatus(targetdata, 'processing')
        try:
            ret = self.processTargetList(targetlist=[proctargetdata])
        except BadImageStatsPause, e:
            ''' FIX ME!!! need to pause and allow repeat? '''
            self.logger.error('processing target failed: %s' %e)
            ret = 'aborted'
        except BadImageStatsAbort, e:
            self.logger.error('processing target failed: %s' %e)
            ret = 'aborted'
        self.reportTargetStatus(proctargetdata, 'done')
        self.logger.info('Done with simulated target, status: %s (repeat will not be honored)' % (ret,))
        self.setStatus('idle')

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
        newtargets = []
        # For each target

        self.logger.info('Generating sub-targets');

        for target in targetlist:

        #   Bounding box
            bound_x, bound_y = targetShape(target)

        #   Grab coordinates
            center_x, center_y = targetPoint(target)

        #   Corner points
            start_x = center_x - (spotcount/2) * spotspacing
            start_y = center_y - (spotcount/2) * spotspacing

            end_x = center_x + (spotcount/2) * spotspacing
            end_y = center_y + (spotcount/2) * spotspacing

            self.logger.info('Subtargets for '+center_x+', '+center_y)
            self.logger.info('Interval: '+start_x+', '+start_y+' -> '+end_x+', '+end_y)
        
        #   Generate new coordinates around point
            for point_x in range(start_x, end_x, spotspacing):# left bound to right bound
                for point_y in range(start_y, end_y, spotspacing): # top to bottom bound
                    
                    # Check that coordinates are in frame
                    if point_x > 0.0 and point_x < bound_x and point_y > 0.0 and point_y < bound_y:
                        sub_target = leginondata.AcquisitionImageTargetData(initializer=target)
                        sub_target['delta row']    = point_x
                        sub_target['delta column'] = point_y

                        new_targets.append(sub_target)

        # set the spot size
        self.instrument.tem['spot size'] = spotsize

        # Call processTargetList
        acquisition.Acquisition.processTargetList(newTargetList)
