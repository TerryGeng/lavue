# Copyright (C) 2017  DESY, Christoph Rosemann, Notkestr. 85, D-22607 Hamburg
#
# lavue is an image viewing program for photon science imaging detectors.
# Its usual application is as a live viewer using hidra as data source.
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation in  version 2
# of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor,
# Boston, MA  02110-1301, USA.
#
# Authors:
#     Christoph Rosemann <christoph.rosemann@desy.de>
#     Jan Kotanski <jan.kotanski@desy.de>
#

""" image widget """


import math

from PyQt4 import QtCore, QtGui

from . import imageDisplayWidget


class ImageWidget(QtGui.QWidget):

    """
    The part of the GUI that incorporates the image view.
    """

    roiCoordsChanged = QtCore.pyqtSignal()
    cutCoordsChanged = QtCore.pyqtSignal()

    def __init__(self, parent=None):
        QtGui.QWidget.__init__(self, parent)

        self.nparray = None
        self.imageItem = None
        self.img_widget = imageDisplayWidget.ImageDisplayWidget(parent=self)
        self.currentroimapper = QtCore.QSignalMapper(self)
        self.roiregionmapper = QtCore.QSignalMapper(self)
        self.currentcutmapper = QtCore.QSignalMapper(self)
        self.cutregionmapper = QtCore.QSignalMapper(self)

        verticallayout = QtGui.QVBoxLayout()
        filenamelayout = QtGui.QHBoxLayout()

        filelabel = QtGui.QLabel("Image/File name: ")
        filelabel.setToolTip("image or/and file name")

        filenamelayout.addWidget(filelabel)
        self.filenamedisplay = QtGui.QLineEdit()
        self.filenamedisplay.setReadOnly(True)
        self.filenamedisplay.setToolTip("image or/and file name")
        filenamelayout.addWidget(self.filenamedisplay)
        self.cnfButton = QtGui.QPushButton("Configuration")
        self.cnfButton.setToolTip("image viewer configuration")
        self.quitButton = QtGui.QPushButton("&Quit")
        self.quitButton.setToolTip("quit the image viewer")
        filenamelayout.addWidget(self.cnfButton)
        filenamelayout.addWidget(self.quitButton)

        verticallayout.addLayout(filenamelayout)
        verticallayout.addWidget(self.img_widget)

        self.pixelComboBox = QtGui.QComboBox()
        self.pixelComboBox.addItem("Intensity")
        self.pixelComboBox.addItem("ROI")
        self.pixelComboBox.addItem("LineCut")
        self.pixelComboBox.setToolTip(
            "select the image tool for the mouse pointer,"
            " i.e. Intensity, ROI, LineCut")

        pixelvaluelayout = QtGui.QHBoxLayout()
        self.pixellabel = QtGui.QLabel("Pixel position and intensity: ")
        self.pixellabel.setToolTip(
            "coordinate info display for the mouse pointer")

        self.infodisplay = QtGui.QLineEdit()
        self.infodisplay.setReadOnly(True)
        self.infodisplay.setToolTip(
            "coordinate info display for the mouse pointer")

        self.roiLabel = QtGui.QLabel("ROI alias(es): ")
        self.roiLabel.setToolTip(
            "ROI alias or aliases related to sardana experimental channels")
        self.labelROILineEdit = QtGui.QLineEdit("")
        self.labelROILineEdit.setToolTip(
            "ROI alias or aliases related to Sardana Pool "
            "experimental channels")
        self.roiSpinBox = QtGui.QSpinBox()
        self.roiSpinBox.setMinimum(-1)
        self.roiSpinBox.setValue(1)
        self.roiSpinBox.setToolTip(
            "number of ROIs to add, -1 means remove ROI aliases from sardana")
        self.cutSpinBox = QtGui.QSpinBox()
        self.cutSpinBox.setMinimum(0)
        self.cutSpinBox.setValue(1)
        self.cutSpinBox.setToolTip(
            "number of Line Cuts")
        self.fetchROIButton = QtGui.QPushButton("Fetch")
        self.fetchROIButton.setToolTip(
            "fetch ROI aliases from the Door environment")
        self.applyROIButton = QtGui.QPushButton("Add")
        self.applyROIButton.setToolTip(
            "add ROI aliases to the Door environment "
            "as well as to Active MntGrp")

        pixelvaluelayout.addWidget(self.pixellabel)
        pixelvaluelayout.addWidget(self.infodisplay)
        pixelvaluelayout.addWidget(self.roiLabel)
        pixelvaluelayout.addWidget(self.labelROILineEdit)
        pixelvaluelayout.addWidget(self.roiSpinBox)
        pixelvaluelayout.addWidget(self.cutSpinBox)
        pixelvaluelayout.addWidget(self.applyROIButton)
        pixelvaluelayout.addWidget(self.fetchROIButton)
        pixelvaluelayout.addWidget(self.pixelComboBox)
        verticallayout.addLayout(pixelvaluelayout)

        self.setLayout(verticallayout)
        self.img_widget.currentMousePosition.connect(self.infodisplay.setText)

        self.roiregionmapper.mapped.connect(self.roiRegionChanged)
        self.currentroimapper.mapped.connect(self.currentROIChanged)
        self.img_widget.roi[0].sigHoverEvent.connect(self.currentroimapper.map)
        self.img_widget.roi[0].sigRegionChanged.connect(
            self.roiregionmapper.map)
        self.currentroimapper.setMapping(self.img_widget.roi[0], 0)
        self.roiregionmapper.setMapping(self.img_widget.roi[0], 0)

        self.roiSpinBox.valueChanged.connect(self.roiNrChanged)
        self.labelROILineEdit.textEdited.connect(self.updateROIButton)
        self.updateROIButton()

        self.cutregionmapper.mapped.connect(self.cutRegionChanged)
        self.currentcutmapper.mapped.connect(self.currentCutChanged)
        self.img_widget.cut[0].sigHoverEvent.connect(self.currentcutmapper.map)
        # self.img_widget.cut[0].sigRegionChanged.connect(self.currentcutmapper.map)
        self.img_widget.cut[0].sigRegionChanged.connect(
            self.cutregionmapper.map)
        self.currentcutmapper.setMapping(self.img_widget.cut[0], 0)
        self.cutregionmapper.setMapping(self.img_widget.cut[0], 0)

        self.cutSpinBox.valueChanged.connect(self.cutNrChanged)

        
    @QtCore.pyqtSlot(int)
    def roiRegionChanged(self, _):
        self.roiChanged()

    @QtCore.pyqtSlot(int)
    def cutRegionChanged(self, cid):
        self.cutChanged()

    @QtCore.pyqtSlot(int)
    def currentROIChanged(self, rid):
        oldrid = self.img_widget.currentroi
        if rid != oldrid:
            self.img_widget.currentroi = rid
            self.roiCoordsChanged.emit()

    @QtCore.pyqtSlot(int)
    def currentCutChanged(self, cid):
        oldcid = self.img_widget.currentcut
        if cid != oldcid:
            self.img_widget.currentcut = cid
            self.cutCoordsChanged.emit()

    @QtCore.pyqtSlot()
    def updateROIButton(self):
        if not str(self.labelROILineEdit.text()).strip():
            self.applyROIButton.setEnabled(False)
        else:
            self.applyROIButton.setEnabled(True)

    @QtCore.pyqtSlot(int)
    def roiNrChanged(self, rid, coords=None):
        if rid < 0:
            self.applyROIButton.setText("Remove")
            self.applyROIButton.setToolTip(
                "remove ROI aliases from the Door environment"
                " as well as from Active MntGrp")
        else:
            self.applyROIButton.setText("Add")
            self.applyROIButton.setToolTip(
                "add ROI aliases to the Door environment "
                "as well as to Active MntGrp")
        if coords:
            for i, crd in enumerate(self.img_widget.roi):
                if i < len(coords):
                    self.img_widget.roicoords[i] = coords[i]
                    crd.setPos([coords[i][0], coords[i][1]])
                    crd.setSize(
                        [coords[i][2] - coords[i][0],
                         coords[i][3] - coords[i][1]])
        while rid > len(self.img_widget.roi):
            if coords and len(coords) >= len(self.img_widget.roi):
                self.img_widget.addROI(coords[len(self.img_widget.roi)])
            else:
                self.img_widget.addROI()
            self.img_widget.roi[-1].sigHoverEvent.connect(
                self.currentroimapper.map)
            self.img_widget.roi[-1].sigRegionChanged.connect(
                self.roiregionmapper.map)
            self.currentroimapper.setMapping(
                self.img_widget.roi[-1],
                len(self.img_widget.roi) - 1)
            self.roiregionmapper.setMapping(
                self.img_widget.roi[-1],
                len(self.img_widget.roi) - 1)
        if rid <= 0:
            self.img_widget.currentroi = -1
        elif self.img_widget.currentroi >= rid:
            self.img_widget.currentroi = 0
        while max(rid, 0) < len(self.img_widget.roi):
            self.currentroimapper.removeMappings(self.img_widget.roi[-1])
            self.roiregionmapper.removeMappings(self.img_widget.roi[-1])
            self.img_widget.removeROI()
        self.roiCoordsChanged.emit()
        self.roiSpinBox.setValue(rid)

    @QtCore.pyqtSlot(int)
    def cutNrChanged(self, cid, coords=None):
        if coords:
            for i, crd in enumerate(self.img_widget.cut):
                if i < len(coords):
                    self.img_widget.cutcoords[i] = coords[i]
                    crd.setPos([coords[i][0], coords[i][1]])
                    crd.setSize(
                        [coords[i][2] - coords[i][0],
                         coords[i][3] - coords[i][1]])
        while cid > len(self.img_widget.cut):
            if coords and len(coords) >= len(self.img_widget.cut):
                self.img_widget.addCut(coords[len(self.img_widget.cut)])
            else:
                self.img_widget.addCut()
            self.img_widget.cut[-1].sigHoverEvent.connect(
                self.currentcutmapper.map)
            self.img_widget.cut[-1].sigRegionChanged.connect(
                self.cutregionmapper.map)
            self.currentcutmapper.setMapping(
                self.img_widget.cut[-1],
                len(self.img_widget.cut) - 1)
            self.cutregionmapper.setMapping(
                self.img_widget.cut[-1],
                len(self.img_widget.cut) - 1)
        if cid <= 0:
            self.img_widget.currentcut = -1
        elif self.img_widget.currentcut >= cid:
            self.img_widget.currentcut = 0
        while max(cid, 0) < len(self.img_widget.cut):
            self.currentcutmapper.removeMappings(self.img_widget.cut[-1])
            self.cutregionmapper.removeMappings(self.img_widget.cut[-1])
            self.img_widget.removeCut()
        self.cutCoordsChanged.emit()
        self.cutSpinBox.setValue(cid)

    def roiChanged(self):
        try:
            rid = self.img_widget.currentroi
            state = self.img_widget.roi[rid].state
            ptx = int(math.floor(state['pos'].x()))
            pty = int(math.floor(state['pos'].y()))
            szx = int(math.floor(state['size'].x()))
            szy = int(math.floor(state['size'].y()))
            self.img_widget.roicoords[rid] = [ptx, pty, ptx + szx, pty + szy]
            self.roiCoordsChanged.emit()
        except Exception as e:
            print("Warning: %s" % str(e))

    def cutChanged(self):
        try:
            cid = self.img_widget.currentcut
            print("cc %s" %cid)
            state = self.img_widget.cut[cid].state
            print(state)
            ptx = int(math.floor(state['pos'].x()))
            pty = int(math.floor(state['pos'].y()))
            szx = int(math.floor(state['size'].x()))
            szy = int(math.floor(state['size'].y()))
            self.img_widget.cutcoords[cid] = [ptx, pty, ptx + szx, pty + szy]
            self.cutCoordsChanged.emit()
        except Exception as e:
            print("Warning: %s" % str(e))

    def showROIFrame(self):
        self.img_widget.vLine.hide()
        self.img_widget.hLine.hide()
        self.fetchROIButton.show()
        self.applyROIButton.show()
        self.roiSpinBox.show()
        self.cutSpinBox.hide()
        self.labelROILineEdit.show()
        self.pixellabel.setText("[x1, y1, x2, y2]: ")
        self.roiLabel.show()
        for roi in self.img_widget.roi:
            roi.show()
        for cut in self.img_widget.cut:
            cut.hide()
        self.img_widget.cutenable = False
        self.img_widget.roienable = True
        self.img_widget.roi[0].show()
        self.infodisplay.setText("")
        
    def showIntensityFrame(self):
        self.pixellabel.setText("Pixel position and intensity: ")
        for roi in self.img_widget.roi:
            roi.hide()
        for cut in self.img_widget.cut:
            cut.hide()
        self.fetchROIButton.hide()
        self.labelROILineEdit.hide()
        self.applyROIButton.hide()
        self.roiSpinBox.hide()
        self.cutSpinBox.hide()
        self.roiLabel.hide()
        self.img_widget.roienable = False
        self.img_widget.cutenable = False
        self.img_widget.vLine.show()
        self.img_widget.hLine.show()
        self.infodisplay.setText("")
        
    def showLineCutFrame(self):
        self.pixellabel.setText("Pixel position and intensity: ")
        for roi in self.img_widget.roi:
            roi.hide()
        for cut in self.img_widget.cut:
            cut.show()
        self.fetchROIButton.hide()
        self.labelROILineEdit.hide()
        self.applyROIButton.hide()
        self.cutSpinBox.show()
        self.roiSpinBox.hide()
        self.roiLabel.hide()
        self.img_widget.roienable = False
        self.img_widget.cutenable = True
        self.img_widget.vLine.show()
        self.img_widget.hLine.show()
        self.infodisplay.setText("")
        
            
    def plot(self, array, name=None):
        if array is None:
            return
        if name is not None:
            self.filenamedisplay.setText(name)

        self.img_widget.updateImage(array)

    @QtCore.pyqtSlot(int)
    def setAutoLevels(self, autoLvls):
        self.img_widget.setAutoLevels(autoLvls)

    @QtCore.pyqtSlot(float)
    def setMinLevel(self, level=None):
        self.img_widget.setDisplayMinLevel(level)

    @QtCore.pyqtSlot(float)
    def setMaxLevel(self, level=None):
        self.img_widget.setDisplayMaxLevel(level)

    @QtCore.pyqtSlot(str)
    def changeGradient(self, name):
        self.img_widget.updateGradient(name)
