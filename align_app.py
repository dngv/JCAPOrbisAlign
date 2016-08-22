import sys
import os
import struct
import binascii
import math

from PyQt4 import QtCore, QtGui
from time import strftime, localtime
# from struct import pack
# from binascii import hexlify, unhexlify
# from math import atan, sin, cos
from numpy import argmax, isnan

from gui import Ui_MainWindow
from aux_fcns import *
from settings import *


class MyApp(QtGui.QMainWindow):
    def __init__(self, parent=None):
        QtGui.QWidget.__init__(self, parent)
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

        # Start of user interaction code
        self.ui.pb_run.clicked.connect(self.openrundir)
        self.ui.pb_map.clicked.connect(self.choosemappath)
        self.ui.pb_alignsave.clicked.connect(self.saveoutput)
        self.ui.pb_preview.clicked.connect(self.calcoutput)
        self.ui.le_atskip.setReadOnly(True)

        self.msglist = []


    def logmsg(self, msg):
        """Helper method for adding timestamped prefix to log messages."""
        tsmsg = '[' + strftime('%H:%M', localtime()) + '] ' + msg
        self.msglist.append(tsmsg)

    def printlog(self):
        """Prints log messages to GUI text browser."""
        self.msglist.append('\n')
        self.ui.br_outputlog.setText('\n'.join(self.msglist))

    def openrundir(self):
        """Check for valid serial number in directory name or parent directory name
        in case 'run' folder is specified. If valid (checksum), read platemap from
        database storage and get map ID. Otherwise, manually select map file."""
        self.ui.le_run.setText(QtGui.QFileDialog.getExistingDirectory(self, 'Select Run Directory', rundir))
        self.rundir=str(self.ui.le_run.text())
        if any([runstatus in self.rundir for runstatus in ['.done', '.run', '.invalid', '.copied']]):
            basedir=os.path.basename(os.path.dirname(self.rundir))
        else:
            basedir=os.path.basename(self.rundir)
        try:
            serial=basedir.replace('-', '_').split('_')[-1]
            plateid=serial[:-1]
            checksum=serial[-1]
            float(serial)
        except:
            self.logmsg('Serial number not found in folder path.')
        if sum(int(i) for i in plateid) % 10 == int(checksum):
            plateidpath=os.path.join(platedir, plateid)
            platemaps=[fn for fn in os.listdir(plateidpath) if fn.endswith('.map')]
            if len(platemaps)>1:
                timestamps=[float(''.join([a for a in pm.split('-')[2] if a in '0123456789'])) for pm in platemaps]
                self.logmsg('Multiple prints found, loading most recent print map unless specified.')
                self.ui.le_map.setText(os.path.join(plateidpath, platemaps[argmax(timestamps)]))
            else:
                self.logmsg('Print map found.')
                self.ui.le_map.setText(os.path.join(plateidpath, platemaps[0]))
            infod=readrcp(os.path.join(plateidpath, os.path.basename(plateidpath) + '.info'))
            lastmap=max([int(s.split('__')[-1]) for s in infod['prints'].keys()])
            self.openmaptxt(usemap=infod['prints']['prints__'+str(lastmap)]['map_id'])
        else:
            self.logmsg('Bad checksum for serial number in folder path.')

    def choosemappath(self):
        """Manual plate map selection."""
        self.ui.le_map.setText(QtGui.QFileDialog.getOpenFileName(self, 'Select Platemap File', mapdir, 'Platemap files (*.txt)'))
        self.openmaptxt()

    def openmaptxt(self, usemap=0):
        """Read plate map text file and populate filter fields in GUI. Work around for
        not having to deal with empty fields."""
        mapdir=str(self.ui.le_map.text())
        self.mapdlist=readsingleplatemaptxt(mapdir)
        if usemap:
            self.map_id=str(usemap)
        else:
            self.map_id=str(int(os.path.basename(mapdir).split('-')[0]))
        self.ui.le_xmin.setText(str(min([d['x'] for d in self.mapdlist])))
        self.ui.le_xmax.setText(str(max([d['x'] for d in self.mapdlist])))
        self.ui.le_ymin.setText(str(min([d['y'] for d in self.mapdlist])))
        self.ui.le_ymax.setText(str(max([d['y'] for d in self.mapdlist])))
        self.ui.le_sampleskip.setText(str(0))
        self.ui.le_colskip.setText(str(0))
        self.ui.le_rowskip.setText(str(0))
        self.ui.le_atskip.setText(str(1))
        self.ui.le_samplemin.setText(str(min([d['Sample'] for d in self.mapdlist])))
        self.ui.le_samplemax.setText(str(max([d['Sample'] for d in self.mapdlist])))


    def calcoutput(self):
        """Read stage inputs for alignment, apply sample filters, then calculate aligned positions."""
        self.getguiparams()
        self.applyfilter()
        self.applyskip()
        self.applymaplim()
        self.applysamplelim()
        self.alignmap()
        filteroutput = 'Mapped ' + str(self.counter) + ' locations.'
        alignoutput1 = 'rot = ' + str(self.rot) + ', y-offset = ' + str(self.yoff)
        alignoutput2 = 'x-skew = ' + str(self.skx) + ', y-skew = ' + str(self.sky)
        self.logmsg(filteroutput)
        self.logmsg(alignoutput1)
        self.logmsg(alignoutput2)
        self.printlog()

    def saveoutput(self):
        """Write files this time."""
        self.calcoutput()
        self.writefiles()

    def writefiles(self):
        """Write map-aligned '.STG' file using current datetime as filename. Include
        'sample_no.txt' containing list of sample numbers and save both files to
        run directory selected in GUI."""
        self.genbytecode()
        try:
            fn=strftime('%Y%m%d.%H%M%S', localtime()) + '_map' + str(self.map_id) + '_pts' + str(self.counter) + '.stg'
            p=os.path.join(self.rundir, fn)
            fo=open(p, mode='wb')
            fo.write(self.bytecode)
            fo.close()
            self.logmsg('Wrote ' + fn + ' to run directory.')
        except:
            self.logmsg('Error writing ' + fn + ' to run directory.')
        try:
            ps=os.path.join(self.rundir, 'sample_no.txt')
            fs=open(ps, mode='w')
            fs.write('\n'.join(self.samplelist))
            fs.close()
            self.logmsg('Wrote sample_no.txt to run directory.')
        except:
            self.logmsg('Error writing sample_no.txt to run directory.')

    def getguiparams(self):
        """Read GUI fields into object variables."""
        self.paramd = {}
        self.aligntoprint=self.ui.tb_align.currentIndex() == 0
        for linetxt in self.findChildren(QtGui.QLineEdit):
            try:
                self.paramd[str(linetxt.objectName())[3:]]=float(linetxt.text())
            except ValueError:
                self.paramd[str(linetxt.objectName())[3:]]=str(linetxt.text())
        snums = ['sample_a', 'sample_b', 'sample_c']
        xkeys = ['stagx_a', 'stagx_b', 'stagx_c']
        ykeys = ['stagy_a', 'stagy_b', 'stagy_c']
        self.staged = {}
        for i in range(len(snums)):
            try:
                self.staged[snums[i]] = int(self.ui.tw_stage.item(i,0).text())
            except AttributeError:
                self.logmsg('Sample field is empty. Ignore and assume wafer alignment.')
                self.ui.tb_align.setCurrentIndex(1)
                break
            except ValueError:
                self.logmsg('Invalid sample number.')
                self.ui.tb_align.setCurrentIndex(1)
                break
        for i in range(len(xkeys)):
            try:
                self.staged[xkeys[i]] = float(self.ui.tw_stage.item(i,1).text())
            except ValueError:
                self.logmsg('Invalid sample x-coord in stage table.')
        for i in range(len(ykeys)):
            try:
                self.staged[ykeys[i]] = float(self.ui.tw_stage.item(i,2).text())
            except ValueError:
                self.logmsg('Invalid sample y-coord in stage table.')
        self.rotonly=self.ui.cb_rotonly.isChecked()

    def applyfilter(self):
        """ """
        codelist = [int(code) for code in self.paramd['keepcode'].replace(',', ' ').replace('\t', ' ').split()]
        chanlist = [chan for chan in self.paramd['omitch'].replace(',', ' ').replace('\t', ' ').split()]
        if not any([codelist, chanlist]):
            self.filterdlist = self.mapdlist
        elif codelist and not chanlist:
            self.filterdlist = [d for d in self.mapdlist if d['code'] in codelist]
        elif chanlist and not codelist:
            self.filterdlist = [d for d in self.mapdlist if all([d[chan]==0 for chan in chanlist])]
        else:
            self.filterdlist = [d for d in self.mapdlist if ((d['code'] in codelist) and all([d[chan]==0 for chan in chanlist]))]

    def applyskip(self):
        """ """
        xs=[d['x'] for d in self.mapdlist]
        ys=[d['y'] for d in self.mapdlist]
        setx=list(set(xs))
        setx.sort()
        sety=list(set(ys))
        sety.sort(reverse=True)
        getcol = lambda xval: [i for i in range(len(setx)) if setx[i]==xval][0]
        getrow = lambda yval: [i for i in range(len(sety)) if sety[i]==yval][0]
        for key in ['sampleskip', 'colskip', 'rowskip']:
            if self.paramd[key]=='':
                self.paramd[key]=0
        if self.paramd['atskip']=='':
            self.paramd['atskip']=0.01

        myint = lambda x: 1 if isnan(x) else int(x)

        self.filterdlist = [d for d in self.filterdlist if (d['Sample'] % (self.paramd['sampleskip']+1)==0 and \
                                                            getcol(d['x']) % (self.paramd['colskip']+1)==0 and \
                                                            getrow(d['y']) % (self.paramd['rowskip']+1)==0)] #and \
                                                            #all([myint(d[chan]*100) % int(self.paramd['atskip']*100)==0 for chan in ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H']]))]

    def applymaplim(self):
        """ """
        self.filterdlist = [d for d in self.filterdlist if (d['x'] >= self.paramd['xmin'] and \
                                                            d['x'] <= self.paramd['xmax'] and \
                                                            d['y'] >= self.paramd['ymin'] and \
                                                            d['y'] <= self.paramd['ymax'])]

    def applysamplelim(self):
        """ """
        slist = [int(s) for s in str(self.ui.te_samplelist.toPlainText()).replace(',', ' ').replace('\t', ' ').replace('\n', ' ').split()]
        allsamples = [d['Sample'] for d in self.mapdlist]
        try:
            smin = int(self.paramd['samplemin'])
        except:
            smin = 0
        try:
            smax = int(self.paramd['samplemax'])
        except:
            smax = max(allsamples)

        if len(slist) > 0:
            self.filterdlist = [d for d in self.filterdlist if d['Sample'] in slist]

        self.filterdlist = [d for d in self.filterdlist if (d['Sample']>=smin and d['Sample']<=smax)]

    def alignmap(self):
        """ """
        if self.aligntoprint: # align map to print
            self.yoff = 0
            slist=[d['Sample'] for d in self.mapdlist]
            aind=slist.index(self.staged['sample_a'])
            bind=slist.index(self.staged['sample_b'])
            cind=slist.index(self.staged['sample_c'])
            pax=self.mapdlist[aind]['x']
            pay=self.mapdlist[aind]['y']
            pbx=self.mapdlist[bind]['x']
            pby=self.mapdlist[bind]['y']
            pcx=self.mapdlist[cind]['x']
            pcy=self.mapdlist[cind]['y']

            pbax=pax-pbx
            pbay=pay-pby
            pba=(pbax**2+pbay**2)**0.5
            pbcx=pcx-pbx
            pbcy=pcy-pby
            pbc=(pbcx**2+pbcy**2)**0.5

            #Orbis x & y diffs (origin sample A)
            sbax=self.staged['stagx_b']-self.staged['stagx_a']
            sbay=self.staged['stagy_a']-self.staged['stagy_b']
            sba=(sbax**2+sbay**2)**0.5
            sbcx=self.staged['stagx_b']-self.staged['stagx_c']
            sbcy=self.staged['stagy_c']-self.staged['stagy_b']
            sbc=(sbcx**2+sbcy**2)**0.5

            self.rot=math.atan(sbcy/sbcx) #epson printer has non-linear elongation in y, use x instead
            if self.rotonly:
                self.skx=1
                self.sky=1
            else:
                self.skx=sbc/pbc
                self.sky=sba/pba
        else: # align map to wafer
            sbcx=self.staged['stagx_b']-self.staged['stagx_c']
            sbcy=self.staged['stagy_c']-self.staged['stagy_b']
            # y-position of wafer diameter || to flat (y=0)
            hh=47.3
            # full wafer diameter
            hw=50.0
            # Si wafer width/2
            self.rot=math.atan(sbcy/sbcx)
            self.yoff=self.staged['stagy_a']-hh
            self.skx=1
            self.sky=1

        self.counter=0
        self.index=''
        self.positions=''
        self.samplelist=[]

        for d in self.filterdlist:
            if self.aligntoprint:
                # offset to map point B before stretch
                xn=d['x']-pbx
                yn=d['y']-pby
                # apply stretch
                xsk=xn*self.skx
                ysk=yn*self.sky
                # rotate around map point B
                xr=xsk*math.cos(self.rot)-ysk*math.sin(self.rot)
                yr=xsk*math.sin(self.rot)+ysk*math.cos(self.rot)
                xstg=self.staged['stagx_b']-xr
                ystg=self.staged['stagy_b']+yr
            else:
                xn=d['x']-hw
                yn=d['y']-hh
                xr=xn*math.cos(self.rot)-yn*math.sin(self.rot)+hw
                yr=xn*math.sin(self.rot)+yn*math.cos(self.rot)+hh
                # offset pm by point A coord
                xstg=self.staged['stagx_a']-xr
                ystg=self.yoff+yr

            checkx = stagx_min<=xstg<=stagx_max
            checky = stagy_min<=ystg<=stagy_max

            if checkx and checky:
                self.counter+=1
                i=struct.pack('<h', self.counter)# entry index (16-bit short?, 2 bytes), don't use sample number in case we remove out-of-range samples
                i+=struct.pack('<h', 0) # entry type (00 for point, 01 for line, 02 for matrix)
                i+=struct.pack('<h', 1)*2   # (1) num points to scan (01 for point, for line length, matrix width)
                                            # (2) num points to scan (01 for point & line, matrix height)
                l=str(int(d['Sample']))+' '*(16-len(str(int(d['Sample'])))) # use sample number for stage label, max 16 characters
                i=binascii.hexlify('Center  '+l)+i.encode('hex')
                x=struct.pack('<f', xstg)
                y=struct.pack('<f', ystg)
                z=struct.pack('<f', self.paramd['stagz'])
                p=x+y+x+y+z+z # x start, y start, x end, y end, z start, z end
                p+=struct.pack('x')*4 # 4 byte padding (probably for rotation info but our stage doesn't have that)
                p=p.encode('hex')
                self.index+=i
                self.positions+=p
                self.samplelist+=[str(d['Sample'])]

    def genbytecode(self):
        """ """
        # assemble long strings of bytes (as hex) then unhexlify and write to binary file
        seperator='0000DD24664052B8884298AEC04285EBB140BE9F3A40486186422F1DC242C3F590400000'
        seperator=seperator+(struct.pack('x')*60).encode('hex')

        # form header string, need to know # of in-range samples so this comes after for loop
        header=struct.pack('<b',15)
        header+=struct.pack('x')*15
        header+=struct.pack('x')*2
        header+=struct.pack('<h', self.counter)
        header+=struct.pack('x')*20
        header=header.encode('hex')

        # concatenate hex string and convert to byte code
        self.bytecode=binascii.unhexlify(header+self.index+seperator+self.positions)

if __name__ == "__main__":
    app = QtGui.QApplication(sys.argv)
    myapp = MyApp()
    myapp.show()
    sys.exit(app.exec_())
