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
#

""" Provides abstraction for file writer """

import weakref
import time
import pytz
import datetime
import threading
import numpy


#: (:mod:`PNIWriter` or :mod:`H5PYWriter`or :mod:`H5CppWriter`)
#    default writer module
writer = None

#: (:class:`threading.Lock`) writer module
writerlock = threading.Lock()


def open_file(filename, readonly=False, **pars):
    """ open the new file

    :param filename: file name
    :type filename: :obj:`str`
    :param readonly: readonly flag
    :type readonly: :obj:`bool`
    :param pars: parameters
    :type pars: :obj:`dict` < :obj:`str`, :obj:`str`>
    :returns: file object
    :rtype: :class:`FTFile`
    """
    if 'writer' in pars.keys():
        wr = pars.pop('writer')
    else:
        with writerlock:
            wr = writer
    fl = wr.open_file(filename, readonly, **pars)
    if hasattr(fl, "writer"):
        fl.writer = wr
    return fl


def create_file(filename, overwrite=False, **pars):
    """ create a new file

    :param filename: file name
    :type filename: :obj:`str`
    :param overwrite: overwrite flag
    :type overwrite: :obj:`bool`
    :param pars: parameters
    :type pars: :obj:`dict` < :obj:`str`, :obj:`str`>
    :returns: file object
    :rtype: :class:`FTFile`
    """
    if 'writer' in pars.keys():
        wr = pars.pop('writer')
    else:
        with writerlock:
            wr = writer
    fl = wr.create_file(filename, overwrite, **pars)
    if hasattr(fl, "writer"):
        fl.writer = wr
    return fl


def link(target, parent, name):
    """ create link

    :param target: file name
    :type target: :obj:`str`
    :param parent: parent object
    :type parent: :class:`FTObject`
    :param name: link name
    :type name: :obj:`str`
    :returns: link object
    :rtype: :class:`FTLink`
    """
    node = parent
    wr = None
    while node:
        if hasattr(node, "writer"):
            wr = node.writer
            break
        else:
            if hasattr(node, "parent"):
                node = node.parent
            else:
                break
    if not wr:
        with writerlock:
            wr = writer
    return wr.link(target, parent, name)


def get_links(parent):
    """ get links

    :param parent: parent object
    :type parent: :class:`FTObject`
    :returns: list of link objects
    :rtype: :obj: `list` <:class:`FTLink`>
    """
    node = parent
    wr = None
    while node:
        if hasattr(node, "writer"):
            wr = node.writer
            break
        else:
            if hasattr(node, "parent"):
                node = node.parent
            else:
                break
    if not wr:
        with writerlock:
            wr = writer
    return wr.get_links(parent)


def data_filter(parent=None):
    """ create deflate filter

    :param parent: parent object
    :type parent: :class:`FTObject`
    :returns: deflate filter object
    :rtype: :class:`FTDeflate`
    """
    node = parent
    wr = None
    while node:
        if hasattr(node, "writer"):
            wr = node.writer
            break
        else:
            if hasattr(node, "parent"):
                node = node.parent
            else:
                break
    if not wr:
        with writerlock:
            wr = writer
    return wr.data_filter()


deflate_filter = data_filter


def setwriter(wr):
    """ sets writer

    :param wr: writer module
    :type wr: :mod:`PNIWriter` or :mod:`H5PYWriter` or :mod:`H5CppWriter`
    """
    global writer
    with writerlock:
        writer = wr


class FTObject(object):

    """ virtual file tree object
    """

    def __init__(self, h5object, tparent=None):
        """ constructor

        :param h5object: h5 object
        :type h5object: :obj:`any`
        :param tparent: tree parent
        :type tparent: :obj:`FTObject`
        """
        #: (:obj:`any`) h5 object
        self._h5object = h5object
        #: (:obj:`FTObject`) tree parent
        self._tparent = tparent
        #: (:obj:`list` < :obj:`FTObject` > ) weak references of children
        self.__tchildren = []
        if tparent:
            tparent.append(self)

    def append(self, child):
        """ append child weakref

        :param tparent: tree parent
        :type tparent: :obj:`FTObject`
        """
        self.__tchildren.append(weakref.ref(child))

    def __del__(self):
        """ removes weakref in parent object
        """
        if self._tparent:
            self._tparent.reload()

    def reload(self):
        """ reload a list of valid children
        """
        if self.__tchildren:
            self.__tchildren = [
                kd for kd in self.__tchildren if kd() is not None]

    def close(self):
        """ close element
        """
        for ch in self.__tchildren:
            if ch() is not None:
                ch().close()

    def _reopen(self):
        """ reopen elements and children
        """
        self.__tchildren = [ch for ch in self.__tchildren if ch() is not None]
        for ch in self.__tchildren:
            ch().reopen()

    @property
    def parent(self):
        """ return the parent object

        :returns: file tree group
        :rtype: :class:`FTGroup`
        """
        return self._tparent

    @property
    def h5object(self):
        """ provide object of native library

        :returns: pni object
        :rtype: :obj:`any`
        """
        return self._h5object

    @property
    def is_valid(self):
        """ check if attribute is valid

        :returns: valid flag
        :rtype: :obj:`bool`
        """
        return True


def first(array):
    """  get first element if the only

    :param array: numpy array
    :type array: :class:`numpy.ndarray`
    :returns: first element of the array
    :type array: :obj:`any`
    """
    if isinstance(array, numpy.ndarray) and len(array) == 1:
        return array[0]
    else:
        return array


class FTFile(FTObject):

    """ file tree file
    """

    def __init__(self, h5object, filename):
        """ constructor

        :param h5object: pni object
        :type h5object: :obj:`any`
        :param filename:  file name
        :type filename: :obj:`str`
        :param writer: writer module
        :type writer: :mod:`PNIWriter` or :mod:`H5PYWriter`
                        or :mod:`H5CppWriter`
        """
        FTObject.__init__(self, h5object, None)
        #: (:obj:`str`) file name
        self.name = filename
        #: (:mod:`PNIWriter` or :mod:`H5PYWriter` or :mod:`H5CppWriter`)
        # writer module
        self.writer = None

    def root(self):
        """ root object

        :returns: parent object
        :rtype: :class:`FTGroup`
        """

    def flush(self):
        """ flash the data
        """

    @property
    def readonly(self):
        """ check if file is readonly

        :returns: readonly flag
        :rtype: :obj:`bool`
        """

    def hasswmr(self):
        """ if has swmr_mode

        :returns: has swmr_mode
        :rtype: :obj:`bool`
        """
        return False

    def reopen(self, readonly=False, swmr=False, libver=None):
        """ reopen attribute

        :param readonly: readonly flag
        :type readonly: :obj:`bool`
        :param swmr: swmr flag
        :type swmr: :obj:`bool`
        :param libver:  library version, default: 'latest'
        :type libver: :obj:`str`
        """
        FTObject._reopen(self)

    @classmethod
    def currenttime(cls):
        """ returns current time string

        :returns: current time
        :rtype: :obj:`str`
        """
        tzone = time.tzname[0]
        tz = pytz.timezone(tzone)
        fmt = '%Y-%m-%dT%H:%M:%S.%f%z'
        starttime = tz.localize(datetime.datetime.now())
        return str(starttime.strftime(fmt))


class FTGroup(FTObject):

    """ file tree group
    """

    def __init__(self, h5object, tparent=None):
        """ constructor

        :param h5object: pni object
        :type h5object: :obj:`any`
        :param tparent: treee parent
        :type tparent: :obj:`FTObject`
        """
        FTObject.__init__(self, h5object, tparent)
        # : (:obj:`int`) current file id
        self.currentfileid = 0
        #: (:obj:`int`) steps per file
        self.stepsperfile = 0

    def open(self, name):
        """ open a file tree element

        :param name: element name
        :type name: :obj:`str`
        :returns: file tree object
        :rtype: :class:`FTObject`
        """

    def open_link(self, name):
        """ open a file tree element as link

        :param name: element name
        :type name: :obj:`str`
        :returns: file tree object
        :rtype: :class:`FTObject`
        """

    def create_group(self, n, nxclass=""):
        """ open a file tree element

        :param n: group name
        :type n: :obj:`str`
        :param nxclass: group type
        :type nxclass: :obj:`str`
        :returns: file tree group
        :rtype: :class:`FTGroup`
        """

    def create_field(self, name, type_code,
                     shape=None, chunk=None, dfilter=None):
        """ open a file tree element

        :param n: group name
        :type n: :obj:`str`
        :param type_code: nexus field type
        :type type_code: :obj:`str`
        :param shape: shape
        :type shape: :obj:`list` < :obj:`int` >
        :param chunk: chunk
        :type chunk: :obj:`list` < :obj:`int` >
        :param dfilter: filter deflater
        :type dfilter: :class:`FTDeflate`
        :returns: file tree field
        :rtype: :class:`FTField`
        """

    @property
    def size(self):
        """ group size

        :returns: group size
        :rtype: :obj:`int`
        """

    @property
    def attributes(self):
        """ return the attribute manager

        :returns: attribute manager
        :rtype: :class:`FTAttributeManager`
        """

    def exists(self, name):
        """ if child exists

        :param name: child name
        :type name: :obj:`str`
        :returns: existing flag
        :rtype: :obj:`bool`
        """

    def names(self):
        """ read the child names

        :returns: pni object
        :rtype: :obj:`list` <`str`>
        """

    def reopen(self):
        """ reopen attribute
        """
        FTObject._reopen(self)


class FTField(FTObject):

    """ file tree file
    """

    def __init__(self, h5object, tparent=None):
        """ constructor

        :param h5object: pni object
        :type h5object: :obj:`any`
        :param tparent: treee parent
        :type tparent: :obj:`FTObject`
        """
        FTObject.__init__(self, h5object, tparent)

    @property
    def attributes(self):
        """ return the attribute manager

        :returns: attribute manager
        :rtype: :class:`FTAttributeManager`
        """

    def grow(self, dim=0, ext=1):
        """ grow the field

        :param dim: growing dimension
        :type dim: :obj:`int`
        :param dim: size of the grow
        :type dim: :obj:`int`
        """

    def refresh(self):
        """ refresh the field

        :returns: refreshed
        :rtype: :obj:`bool`
        """

    def read(self):
        """ read the field value

        :returns: pni object
        :rtype: :obj:`any`
        """

    def write(self, o):
        """ write the field value

        :param o: pni object
        :type o: :obj:`any`
        """

    def __setitem__(self, t, o):
        """ set value

        :param t: slice tuple
        :type t: :obj:`tuple`
        :param o: pni object
        :type o: :obj:`any`
        """

    def __getitem__(self, t):
        """ get value

        :param t: slice tuple
        :type t: :obj:`tuple`
        :returns: pni object
        :rtype: :obj:`any`
        """

    @property
    def dtype(self):
        """ field data type

        :returns: field data type
        :rtype: :obj:`str`
        """

    @property
    def shape(self):
        """ field shape

        :returns: field shape
        :rtype: :obj:`list` < :obj:`int` >
        """

    @property
    def size(self):
        """ field size

        :returns: field size
        :rtype: :obj:`int`
        """

    def reopen(self):
        """ reopen attribute
        """
        FTObject._reopen(self)


class FTLink(FTObject):

    """ file tree link
    """

    def __init__(self, h5object, tparent=None):
        """ constructor

        :param h5object: pni object
        :type h5object: :obj:`any`
        :param tparent: treee parent
        :type tparent: :obj:`FTObject`
        """
        FTObject.__init__(self, h5object, tparent)

    @property
    def target_path(self):
        """ target path

        :returns: target path
        :rtype: :obj:`str`
        """

    def refresh(self):
        """ refresh the link

        :returns: refreshed
        :rtype: :obj:`bool`
        """

    def reopen(self):
        """ reopen attribute
        """
        FTObject._reopen(self)


class FTDataFilter(FTObject):

    """ file tree data filter
    """

    def __init__(self, h5object=None, tparent=None):
        """ constructor

        :param h5object: pni object
        :type h5object: :obj:`any`
        :param tparent: treee parent
        :type tparent: :obj:`FTObject`
        """
        FTObject.__init__(self, h5object, tparent)
        #: (:obj:`bool`) compression shuffle
        self._shuffle = False
        #: (:obj:`int`) compression rate
        self._rate = 0
        #: (:obj:`int`) compression filter id
        self._filterid = 1
        #: (:obj:`tuple` <:obj:`int`>) compression options
        self._options = tuple()

    @property
    def options(self):
        """ getter for compression options

        :returns: compression options
        :rtype: :obj:`tuple` <:obj:`int`>
        """
        return self._options

    @options.setter
    def options(self, value):
        """ setter for compression options

        :param value: compression options
        :type value: :obj:`tuple` <:obj:`int`>
        """
        self._options = value

    @property
    def rate(self):
        """ getter for compression rate

        :returns: compression rate
        :rtype: :obj:`int`
        """
        return self._rate

    @rate.setter
    def rate(self, value):
        """ setter for compression rate

        :param value: compression rate
        :type value: :obj:`int`
        """
        self._rate = value

    @property
    def filterid(self):
        """ getter for compression filter id

        :returns: compression rate
        :rtype: :obj:`int`
        """
        return self._filterid

    @filterid.setter
    def filterid(self, value):
        """ setter for compression filter id

        :param value: compression filter id
        :type value: :obj:`int`
        """
        self._filterid = value

    @property
    def shuffle(self):
        """ getter for compression shuffle

        :returns: compression shuffle
        :rtype: :obj:`bool`
        """
        return self._shuffle

    @shuffle.setter
    def shuffle(self, value):
        """ setter for compression shuffle

        :param value: compression shuffle
        :type value: :obj:`bool`
        """
        self._shuffle = value

    def reopen(self):
        """ reopen attribute
        """
        FTObject._reopen(self)


class FTDeflate(FTDataFilter):
    pass


class FTAttributeManager(FTObject):

    """ file tree attribute
    """

    def __init__(self, h5object, tparent=None):
        """ constructor

        :param h5object: pni object
        :type h5object: :obj:`any`
        :param tparent: treee parent
        :type tparent: :obj:`FTObject`
        """
        FTObject.__init__(self, h5object, tparent)

    def create(self, name, dtype, shape=None, overwrite=False):
        """ create a new attribute

        :param name: attribute name
        :type name: :obj:`str`
        :param dtype: attribute type
        :type dtype: :obj:`str`
        :param shape: attribute shape
        :type shape: :obj:`list`< :obj:`int`>
        :param overwrite: overwrite flag
        :type overwrite: :obj:`bool`
        :returns: attribute object
        :rtype: :class:`FTAtribute`
        """

    def __len__(self):
        """ number of attributes

        :returns: number of attributes
        :rtype: :obj:`int`
        """

    def __getitem__(self, name):
        """ get value

        :param name: attribute name
        :type name: :obj:`str`
        :returns: attribute object
        :rtype: :class:`FTAtribute`
        """

    def reopen(self):
        """ reopen attribute
        """
        FTObject._reopen(self)


class FTAttribute(FTObject):

    """ virtual file tree attribute
    """

    def __init__(self, h5object, tparent=None):
        """ constructor

        :param h5object: pni object
        :type h5object: :obj:`any`
        :param tparent: treee parent
        :type tparent: :obj:`FTObject`
        """
        FTObject.__init__(self, h5object, tparent)

    def read(self):
        """ read attribute value

        :returns: python object
        :rtype: :obj:`any`
        """

    def write(self, o):
        """ write attribute value

        :param o: python object
        :type o: :obj:`any`
        """

    def __setitem__(self, t, o):
        """ write attribute value

        :param t: slice tuple
        :type t: :obj:`tuple`
        :param o: python object
        :type o: :obj:`any`
        """

    def __getitem__(self, t):
        """ read attribute value

        :param t: slice tuple
        :type t: :obj:`tuple`
        :returns: python object
        :rtype: :obj:`any`
        """

    @property
    def dtype(self):
        """ attribute data type

        :returns: attribute data type
        :rtype: :obj:`str`
        """

    @property
    def shape(self):
        """ attribute shape

        :returns: attribute shape
        :rtype: :obj:`list` < :obj:`int` >
        """

    def reopen(self):
        """ reopen attribute
        """
        FTObject._reopen(self)
