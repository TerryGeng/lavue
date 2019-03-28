# Copyright (C) 2017  DESY, Notkestr. 85, D-22607 Hamburg
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
#     Jan Kotanski <jan.kotanski@desy.de>
#     Christoph Rosemann <christoph.rosemann@desy.de>
#

""" Horizontal HistogramWidget """


import pyqtgraph as _pg
from pyqtgraph import QtCore, QtGui
import numpy as np

#: ( (:obj:`str`,:obj:`str`,:obj:`str`) )
#:         pg major version, pg minor verion, pg patch version
_VMAJOR, _VMINOR, _VPATCH = _pg.__version__.split(".") \
    if _pg.__version__ else ("0", "9", "0")

_pg.graphicsItems.GradientEditorItem.Gradients['reversegrey'] = {
    'ticks': [(0.0, (255, 255, 255, 255)),
              (1.0, (0, 0, 0, 255)), ], 'mode': 'rgb'}
_pg.graphicsItems.GradientEditorItem.Gradients['highcontrast'] = {
    'ticks': [(0.0, (0, 0, 0, 255)),
              (1.0, (255, 255, 0, 255)), ], 'mode': 'rgb'}
_pg.graphicsItems.GradientEditorItem.Gradients['spectrum'] = {
    'ticks': [(0.0, (255, 0, 255, 255)),
              (1.0, (255, 0, 0, 255))], 'mode': 'hsv'}
_pg.graphicsItems.GradientEditorItem.Gradients['spectrumclip'] = {
    'ticks': [(0.0, (255, 0, 255, 255)),
              (.99, (255, 0, 0, 255)),
              (1.0, (255, 255, 255, 255))], 'mode': 'hsv'}
# define two new gradients of choice
_pg.graphicsItems.GradientEditorItem.Gradients['inverted'] = {
    'ticks': [(0.0, (255, 255, 255, 255)),
              (1.0, (0, 0, 0, 255)), ], 'mode': 'rgb'}
# _pg.graphicsItems.GradientEditorItem.Gradients['highcontrast'] = {
#    'ticks': [(0.0, (0, 0, 0, 255)),
#              (1.0, (255, 255, 0, 255)), ], 'mode': 'rgb'}

__all__ = ['HistogramHLUTWidget']


class HistogramHLUTWidget(_pg.widgets.GraphicsView.GraphicsView):

    """ Horizontal HistogramWidget """

    def __init__(self, parent=None, *args, **kargs):
        """ constructor

        :param parent: parent object
        :type parent: :class:`pyqtgraph.QtCore.QObject`
        :param args: HistogramHLUTItem parameters list
        :type args: :obj:`list` < :obj:`any`>
        :param kargs:  HistogramHLUTItem parameter dictionary
        :type kargs: :obj:`dict` < :obj:`str`, :obj:`any`>
        """
        background = kargs.get('background', 'default')
        _pg.widgets.GraphicsView.GraphicsView.__init__(
            self, parent, useOpenGL=False, background=background)
        #: (:class:`HistogramHLUTItem`) histogram item
        self.item = HistogramHLUTItem(*args, **kargs)
        self.setCentralItem(self.item)
        self.setSizePolicy(
            QtGui.QSizePolicy.Preferred, QtGui.QSizePolicy.Expanding)
        self.setMinimumWidth(95)

    def sizeHint(self):
        """ sets size hint
        """
        return QtCore.QSize(115, 200)

    def __getattr__(self, attr):
        """ gets attribute of HistogramHLUTItem
        :param attr: attribute name
        :type attr: :obj:`str`
        :returns: attribute value
        :rtype: :obj:`any`
        """
        return getattr(self.item, attr)

    def setAutoFactor(self, factor):
        """ sets auto level factor

        :param factor: auto level factor of maximal peak
        :type factor: :obj:`float`
        """
        self.item.autolevelfactor = factor


class GradientEditorItemWS(
        _pg.graphicsItems.GradientEditorItem.GradientEditorItem):

    """ gradient editor item with a signal on loadPreset """

    #: (:class:`pyqtgraph.QtCore.pyqtSignal`) minimum level changed signal
    sigNameChanged = QtCore.pyqtSignal(str)

    def __init__(self, *args, **kargs):
        """ constructor

        :param args: GradientEditorItem parameters list
        :type args: :obj:`list` < :obj:`any`>
        :param kargs:  GradientEditorItem parameter dictionary
        :type kargs: :obj:`dict` < :obj:`str`, :obj:`any`>
        """
        _pg.graphicsItems.GradientEditorItem.GradientEditorItem.__init__(
            self, *args, **kargs)

    def loadPreset(self, name):
        """ loads a predefined gradient and emits sigNameChanged

        :param name: gradient name
        :type name: :obj:`str`
        """
        _pg.graphicsItems.GradientEditorItem.GradientEditorItem.loadPreset(
            self, name)
        self.sigNameChanged.emit(name)


class HistogramHLUTItem(_pg.HistogramLUTItem):

    #: (:class:`pyqtgraph.QtCore.pyqtSignal`) automatic levels changed signal
    autoLevelsChanged = QtCore.pyqtSignal(int)  # bool does not work...

    """ Horizontal HistogramItem """

    def __init__(self, image=None, fillHistogram=True):
        """ constructor

        :param image: 2d image
        :type image: :class:`pyqtgraph.ImageItem`
        :param fillHistogram: histogram will be filled in
        :type fillHistogram: :obj:`bool`
        """
        _pg.graphicsItems.GraphicsWidget.GraphicsWidget.__init__(self)

        #: (:class:`numpy.ndarray`) look up table
        self.lut = None
        if _VMAJOR == '0' and int(_VMINOR) < 10 and int(_VPATCH) < 9:
            #: (:class:`weakref.ref` or :class:`pyqtgraph.ImageItem`)
            #: weakref to image item or image item itself  (for < 0.9.8)
            self.imageItem = None
        else:
            self.imageItem = lambda: None

        #: (:class:`PyQt5.QtGui.QGraphicsGridLayout`) grid layout
        self.layout = QtGui.QGraphicsGridLayout()
        self.setLayout(self.layout)
        self.layout.setContentsMargins(1, 1, 1, 1)
        self.layout.setSpacing(0)

        #: (:class:`pyqtgraph.graphicsItems.ViewBox.ViewBox`) view box
        self.vb = _pg.graphicsItems.ViewBox.ViewBox()
        # self.vb.setMaximumHeight(152)
        self.vb.setMinimumHeight(45)
        self.vb.setMouseEnabled(x=True, y=False)
        # self.vb.setMouseEnabled(x=False, y=True)

        #: (:class:`GradientEditorItemWS`) gradient editor item with a signal
        self.gradient = GradientEditorItemWS()
        self.gradient.setOrientation('bottom')
        self.gradient.loadPreset('grey')

        #: (:class:`pyqtgraph.graphicsItems.LinearRegionItem.LinearRegionItem`)
        #:    linear region item
        self.region = _pg.graphicsItems.LinearRegionItem.LinearRegionItem(
            [0, 1],
            _pg.graphicsItems.LinearRegionItem.LinearRegionItem.Vertical)
        self.region.setZValue(1000)
        self.vb.addItem(self.region)

        #: (:class:`pyqtgraph.graphicsItems.AxisItem.AxisItem`) axis item
        self.axis = _pg.graphicsItems.AxisItem.AxisItem(
            'top', linkView=self.vb, maxTickLength=-10, showValues=False)

        self.layout.addItem(self.axis, 0, 0)
        self.layout.addItem(self.vb, 1, 0)
        self.layout.addItem(self.gradient, 2, 0)
        self.range = None

        self.autolevelfactor = None
        self.gradient.setFlag(self.gradient.ItemStacksBehindParent)
        self.vb.setFlag(self.gradient.ItemStacksBehindParent)

        self.gradient.sigGradientChanged.connect(self.gradientChanged)
        self.region.sigRegionChanged.connect(self.regionChanging)
        self.region.sigRegionChangeFinished.connect(self.regionChanged)
        self.vb.sigRangeChanged.connect(self.viewRangeChanged)
        self.plot = _pg.graphicsItems.PlotDataItem.PlotDataItem()
        # self.plot.dataBounds(1, 0.9)
        # self.plot.dataBounds(0, 0.9)

        self.fillHistogram(fillHistogram)

        self.vb.addItem(self.plot)
        self.autoHistogramRange()

        if image is not None:
            self.setImageItem(image)
        # self.background = None

    def setGradientByName(self, name):
        """ sets gradient by name

        :param name: gradient name
        :type name: :obj:`str`
        """
        try:
            self.gradient.loadPreset(str(name))
        except Exception:
            self.gradient.loadPreset("highContrast")

    def paint(self, p, *args):
        """ paints the histogram item

        :param p: QPainter painter
        :type p: :class:`PyQt5.QtGui.QPainter`
        :param args: paint argument
        :type args: :obj:`list` < :obj:`any`>
        """

        pen = self.region.lines[0].pen
        rgn = self.getLevels()
        p1 = self.vb.mapFromViewToItem(
            self, _pg.Point(rgn[0], self.vb.viewRect().center().y()))
        p2 = self.vb.mapFromViewToItem(
            self, _pg.Point(rgn[1], self.vb.viewRect().center().y()))
        gradRect = self.gradient.mapRectToParent(
            self.gradient.gradRect.rect())
        for pen in [_pg.functions.mkPen('k', width=3), pen]:
            p.setPen(pen)
            p.drawLine(p1, gradRect.topLeft())
            p.drawLine(p2, gradRect.topRight())
            p.drawLine(gradRect.topLeft(), gradRect.bottomLeft())
            p.drawLine(gradRect.topRight(), gradRect.bottomRight())

    def setHistogramRange(self, mn, mx, padding=0.1):
        """sets the Y range on the histogram plot. This disables auto-scaling.

        :param mn: minimum range level
        :type mn: :obj:`float`
        :param mx: maximum range level
        :type mx: :obj:`float`
        :param padding: histogram padding
        :type padding: :obj:`float`
        """
        self.vb.enableAutoRange(self.vb.XAxis, False)
        self.vb.setYRange(mn, mx, padding)

    def __imageItem(self):
        """ provides imageItem independent of the pyqtgraph version

        :returns: image item
        :rtype: :class:`pyqtgraph.ImageItem`

        """
        if _VMAJOR == '0' and int(_VMINOR) < 10 and int(_VPATCH) < 9:
            #: (:class:`weakref.ref` or :class:`pyqtgraph.ImageItem`)
            #: weakref to image item or image item itself  (for < 0.9.8)
            return self.imageItem
        else:
            return self.imageItem()

    def imageChanged(self, autoLevel=False, autoRange=False):

        hx = None
        hy = None
        if self.autolevelfactor is not None:
            hx, hy = self.__imageItem().getHistogram()
            if hy is not None and hx is not None and hx.any() and hy.any():
                if abs(hx[0]) < 1.e-3 or abs(hx[0]+2.) < 1.e-3:
                    hx = hx[1:]
                    hy = hy[1:]
                if hx.any() and hy.any():
                    hmax = max(hy)
                    hmin = self.autolevelfactor*hmax/100.
                    mn, mx = self.__imageItem().levels
                    indexes = np.where(hy >= hmin)
                    ind1 = indexes[0][0]
                    ind2 = indexes[-1][-1]
                    self.region.setRegion([hx[ind1], hx[ind2]])
                    _pg.graphicsItems.HistogramLUTItem.HistogramLUTItem.\
                        imageChanged(
                            self, autoLevel=False, autoRange=autoRange)
        if hx is None or hy is None or not hx.any() or not hy.any():
            try:
                _pg.graphicsItems.HistogramLUTItem.HistogramLUTItem.\
                    imageChanged(
                        self, autoLevel=autoLevel, autoRange=autoRange)
            except Exception:
                pass
