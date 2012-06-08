import rctacquisition
import leginondata
import gui.wx.RCTSpotAcquisition
import numpy
import acquisition

class RCTSpotAcquisition(rctacquisition.RCTAcquisition):
    panelclass      = gui.wx.RCTSpotAcquisition.Panel
    settingsclass   = leginondata.RCTSpotAcquisitionSettingsData
    defaultsettings = acquisition.Acquisition.defaultsettings
    defaultsettings.update({
        'tilts': '(-45, 45)',
        'stepsize': 42.0,
        'pause': 1.0,
        'lowfilt': 1.0,
        'medfilt': 2,
        'minsize': 50,
        'maxsize': 0.8,
        'drift threshold': 0.0,
        'drift preset': None,
        'spot size':    5,
        'spot spacing': 1.0, 
        'spot count':   3
        })

    eventinputs  = acquisition.Acquisition.eventinputs
    eventoutputs = acquisition.Acquisition.eventoutputs

    def __init__(self, id, session, managerlocation, **kwargs):
        acquisition.Acquisition.__init__(self, id, session, managerlocation, **kwargs)
        self.tiltnumber = 0
        self.tiltseries = None

    # Overrides
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

        for target in targets:

        #   Bounding box from camera frame
            bound_x, bound_y = targetShape(target)

        #   Grab coordinates for the target
            center_x, center_y = targetPoint(target)

        #   Corner points
            start_x = -(spotcount/2) * spotspacing
            start_y = -(spotcount/2) * spotspacing

            end_x = (spotcount/2) * spotspacing
            end_y = (spotcount/2) * spotspacing

            self.logger.info(('Subtargets for %d, %d' % (center_x, center_y)))
            self.logger.info(('Interval: %d, %d  -> %d, %d' % (start_x, start_y, end_x, end_y)))
      
        #   Generate new coordinates around point
            for point_x in range(start_x, end_x, spotspacing):# left bound to right bound
                for point_y in range(start_y, end_y, spotspacing): # top to bottom bound
                    
                    subtarget = leginondata.AcquisitionImageTargetData(initializer=targetdata)
                    
                    self.spotX = point_x
                    self.spotY = point_y

                    subtarget['spot_x'] = point_x
                    subtarget['spot_y'] = point_y
                    
                    self.logger.info('subtarget -> %d, %d' % (point_x, point_y))

                    # Shift the target
                    target_offset = {'x': point_x, 'y': point_y}
                    subtarget = self.makeTransformTarget(subtarget, target_offset)

                    new_targets.append(sub_target)

        spottargetlist = self.newTargetList(image=targets.image)

        self.publish(spottargetlist, database=True)

        for spottarget in newtargets:
            spottarget['list']  = spottargetlist
            spottarget['image'] = targets.image
            spottarget['scope'] = targets.image['scope']
            self.publish(spottarget, database=True)

        # Call processTargetList
        rctacquisition.RCTAcquisition.processTargetList(spottargetlist)
