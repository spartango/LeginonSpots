#!/bin/sh

#Install the spotscan files into the leginon install directory

echo Installing Spot Scan

cp leginon/spotscanacquisition.py /usr/lib/python2.6/site-packages/leginon/
cp leginon/gui/wx/SpotScanAcquisition.py /usr/lib/python2.6/site-packages/leginon/gui/wx/
cp leginon/allnodes.py /usr/lib/python2.6/site-packages/leginon/
cp leginon/leginondata.py /usr/lib/python2.6/site-packages/leginon/

cp leginon/rctspotacquisition.py /usr/lib/python2.6/site-packages/leginon/
cp leginon/gui/wx/RCTSpotAcquisition.py /usr/lib/python2.6/site-packages/leginon/gui/wx/

echo Done Installing
