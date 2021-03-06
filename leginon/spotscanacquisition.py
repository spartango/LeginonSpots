#!/usr/bin/python

import leginondata
import acquisition
import numpy
import time
import math
import pyami.quietscipy
import gui.wx.SpotScanAcquisition
from scipy import ndimage

class SpotScanAcquisition(acquisition.Acquisition):
    panelclass      = gui.wx.SpotScanAcquisition.Panel
    settingsclass   = leginondata.SpotScanAcquisitionSettingsData
    defaultsettings = acquisition.Acquisition.defaultsettings

    eventinputs  = acquisition.Acquisition.eventinputs
    eventoutputs = acquisition.Acquisition.eventoutputs

    defaultsettings.update({
        'spot size':    5,
        'spot spacing': 1.0, 
        'spot count':   3,
        'spot pattern': 'square'
        })

    def __init__(self, id, session, managerlocation, **kwargs):
        self.spotX = 0
        self.spotX = 0
        acquisition.Acquisition.__init__(self, id, session, managerlocation, **kwargs)

    def setImageFilename(self, imagedata, spot_x=None, spot_y=None):
        acquisition.setImageFilename(imagedata)
        if spot_x is None or spot_y is None:
            spot_x = imagedata['spot_x']
            spot_y = imagedata['spot_y']
        if spot_x is not None and spot_y is not None:
            imagedata['filename'] = imagedata['filename'] + '_%02d_%02d' % (spot_x, spot_y, )
        else:
            imagedata['filename'] = imagedata['filename'] + '_%02d_%02d' % (self.spotX, self.spotY, )
        self.logger.info('Filename -> %s' % imagedata['filename'])

    # Utilities
    def targetPoint(self, target):
        return target['delta row'],target['delta column']

    def targetPoints(self, targets):
        return map(targetPoint, targets)

    def targetShape(self, target):
        if target['image'] is None:
            return 4096, 4096
        else:
            dims = target['image']['camera']['dimension']
            return dims['y'],dims['x']

    # Overrides
    def simulateTarget(self):
        self.setStatus('processing')
        currentpreset = self.presetsclient.getCurrentPreset()
        if currentpreset is None:
            try:
                self.validatePresets()
            except acquisition.InvalidPresetsSequence:
                self.logger.error('Configure at least one preset in the settings for this node.')
                return
            presetnames = self.settings['preset order']
            currentpreset = self.presetsclient.getPresetByName(presetnames[0])
        targetdata = self.newSimulatedTarget(preset=currentpreset,grid=self.grid)
        self.publish(targetdata, database=True)
        ## change to 'processing' just like targetwatcher does
        proctargetdata = self.reportTargetStatus(targetdata, 'processing')

        ret = self.processTargetData(targetdata, attempt=1)
   
        self.reportTargetStatus(proctargetdata, 'done')
        self.logger.info('Done with simulated target, status: %s (repeat will not be honored)' % (ret,))
        self.setStatus('idle')

    def acquireSpot(self, targetdata, newpresetname, point_x, point_y):
        subtarget = leginondata.AcquisitionImageTargetData(initializer=targetdata)
                        
        self.spotX = point_x
        self.spotY = point_y

        subtarget['spot_x'] = point_x
        subtarget['spot_y'] = point_y
        
        self.logger.info('subtarget -> %d, %d' % (point_x, point_y))

        # Shift the target
        target_offset = {'x': point_x, 'y': point_y}
        subtarget = self.makeTransformTarget(subtarget, target_offset)
        
        offset = {'x':self.settings['target offset col'],'y':self.settings['target offset row']}
        if offset['x'] or offset['y']:
            subtarget = self.makeTransformTarget(subtarget,offset)
        ### determine how to move to target
        try:
            emtarget = self.targetToEMTargetData(subtarget)
        except acquisition.InvalidStagePosition:
            return 'invalid'

        presetdata = self.presetsclient.getPresetByName(newpresetname)

        ### acquire film or CCD
        self.startTimer('acquire')
        # Load up the preset and acquire
        ret = self.acquire(presetdata, emtarget, attempt=attempt, target=subtarget)
        self.stopTimer('acquire')
        return ret

    # Overrides
    def processTargetData(self, targetdata, attempt=None):
        '''
        This is called by TargetWatcher.processData when targets available
        If called with targetdata=None, this simulates what occurs at
        a target (going to presets, acquiring images, etc.)
        '''

        try:
            self.validatePresets()
        except acquisition.InvalidPresetsSequence, e:
            if targetdata is None or targetdata['type'] == 'simulated':
                ## don't want to repeat in this case
                self.logger.error(str(e))
                return 'aborted'
            else:
                raise

        presetnames = self.settings['preset order']
        ret = 'ok'
        self.onTarget = False

        # Get the spot size parameters
        spotsize    = self.settings['spot size']
        spotcount   = self.settings['spot count']
        spotspacing = self.settings['spot spacing']
        spotpattern = self.settings['spot pattern']

        for newpresetname in presetnames:
            if self.alreadyAcquired(targetdata, newpresetname):
                continue

            # Check that these are sane
            if spotsize >= 9 or spotsize <= 1 or spotcount < 0:
                self.logger.error('Invalid spot parameters')
                return

            # Generate rastered points

            # Grab coordinates for the target
            center_x, center_y = self.targetPoint(targetdata)
            self.logger.info(('Subtargets for %d, %d' % (center_x, center_y)))

            # Hexagonal vs Square Pattern
            if spotpattern == 'hexagon':

                # Generate hexagonal pattern
                maxspots = 2*spotcount - 1
                
                for row in (range(spotcount, maxspots) + range(maxspots, spotcount-1, -1)):  # 1 2 3 ... N ... 3 2 1 
                    point_y = spotspacing * row
                    for col in range(math.floor(abs(row) / -2), math.floor(abs(row) / 2) + 1):
                        offset = 0
                        if row % 2 == 0:
                            offset = spotspacing / 2
                        point_x = spotspacing * col + offset

                        ret = self.acquireSpot(targetdata, newpresetname, point_x, point_y)
                        
                        if ret in ('aborted', 'repeat'):
                            self.reportStatus('acquisition', 'Acquisition state is "%s"' % ret)
                            # Need to exit here completely, no more rastering
                            return ret
                        if ret == 'repeat':
                            return repeat

            else: # Default to square pattern

                # Corner points
                start_x = -(spotcount/2) * spotspacing
                start_y = -(spotcount/2) * spotspacing

                end_x = (spotcount/2) * spotspacing
                end_y = (spotcount/2) * spotspacing

                self.logger.info(('Interval: %d, %d  -> %d, %d' % (start_x, start_y, end_x, end_y)))
            
                # Generate new coordinates around point
                for point_x in range(start_x, end_x, spotspacing):# left bound to right bound
                    for point_y in range(start_y, end_y, spotspacing): # top to bottom bound
                        
                        ret = self.acquireSpot(targetdata, newpresetname, point_x, point_y)
                        
                        # in these cases, return immediately
                        if ret in ('aborted', 'repeat'):
                            self.reportStatus('acquisition', 'Acquisition state is "%s"' % ret)
                            # Need to exit here completely, no more rastering
                            return ret
                        if ret == 'repeat':
                            return repeat

        self.reportStatus('processing', 'Processing complete')

        return ret
