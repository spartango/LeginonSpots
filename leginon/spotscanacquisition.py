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
    settingsclass = leginondata.SpotScanAcquisitionSettingsData
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

        for newpresetname in presetnames:
            if self.alreadyAcquired(targetdata, newpresetname):
                continue

            # Check that these are sane
            if spotsize >= 9 or spotsize <= 1 or spotcount < 0:
                self.logger.error('Invalid spot parameters')
                return

            # Generate rastered points
            # Bounding box from camera frame
            bound_x, bound_y = self.targetShape(targetdata)

        #   Grab coordinates for the target
            center_x, center_y = self.targetPoint(targetdata)

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
                        sub_target = leginondata.AcquisitionImageTargetData(initializer=targetdata)
                        sub_target['delta row']    = point_x
                        sub_target['delta column'] = point_y

                        if subtarget is not None and subtarget['type'] != 'simulated' and self.settings['adjust for transform'] != 'no':
                            if self.settings['drift between'] and self.goodnumber > 0:
                                self.declareDrift('between targets')
                            targetonimage = subtarget['delta column'],subtarget['delta row']
                            subtarget = self.adjustTargetForTransform(subtarget)
                            self.logger.info('target adjusted by (%.1f,%.1f) (column, row)' % (subtarget['delta column']-targetonimage[0],subtarget['delta row']-targetonimage[1]))
                        offset = {'x':self.settings['target offset col'],'y':self.settings['target offset row']}
                        if offset['x'] or offset['y']:
                            subtarget = self.makeTransformTarget(subtarget,offset)
                        ### determine how to move to target
                        try:
                            emtarget = self.targetToEMTargetData(subtarget)
                        except acquisition.InvalidStagePosition:
                            return 'invalid'

                        presetdata = self.presetsclient.getPresetByName(newpresetname)

                        self.instrument.tem['spot size'] = spotsize

                        ### acquire film or CCD
                        self.startTimer('acquire')
                        ret = self.acquire(presetdata, emtarget, attempt=attempt, target=subtarget)
                        self.stopTimer('acquire')
                        # in these cases, return immediately
                        if ret in ('aborted', 'repeat'):
                            self.reportStatus('acquisition', 'Acquisition state is "%s"' % ret)
                            break
                        if ret == 'repeat':
                            return repeat

        self.reportStatus('processing', 'Processing complete')

        return ret

    # Overrides
    def _processTargetList(self, targetlist):
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

        for target in targets:

        #   Bounding box from camera frame
            bound_x, bound_y = targetShape(target)

        #   Grab coordinates for the target
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

        spottargetlist = self.newTargetList(image=targets.image)

        self.publish(spottargetlist, database=True)

        for spottarget in newtargets:
            spottarget['list']  = spottargetlist
            spottarget['image'] = targets.image
            spottarget['scope'] = targets.image['scope']
            self.publish(spottarget, database=True)

        # set the spot size
        self.instrument.tem['spot size'] = spotsize

        # Call processTargetList
        acquisition.Acquisition.processTargetList(spottargetlist)
