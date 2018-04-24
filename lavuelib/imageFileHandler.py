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
#     Andre Rothkirch <andre.rothkirch@desy.de>
#     Jan Kotanski <jan.kotanski@desy.de>
#

""" this a simple file handler that loads image files
    and delivers just the actual array """

import struct
import numpy as np

from . import filewriter

try:
    import fabio
    #: (:obj:`bool`) fabio can be imported
    FABIO = True
except ImportError:
    FABIO = False
try:
    import PIL
    import PIL.Image
    #: (:obj:`bool`) PIL can be imported
    PILLOW = True
except ImportError:
    PILLOW = False


#: (:obj:`dict` <:obj:`str`, :obj:`module`> ) nexus writer modules
WRITERS = {}
try:
    from . import pniwriter
    WRITERS["pni"] = pniwriter
except:
    pass
try:
    from . import h5pywriter
    WRITERS["h5py"] = h5pywriter
    SWMR = h5pywriter.SWMR
except:
    pass


class NexusFieldHandler(object):

    """Nexus file handler class.
       Reads image from file and returns the numpy array."""

    def __init__(self, fname=None, writer=None):
        """ constructor

        :param fname: file name
        :type fname: :obj:`str`
        :param writer: h5 writer module: "pni" or "h5py"
        :type writer: :obj:`str`
        """
        #: (:obj:`any`) module image object
        self.__image = None
        #: (:obj:`numpy.ndarray`) image data
        self.__data = None
        #: (:obj:`str`) file name
        self.__fname = fname
        #: (:obj:`dict` <:obj:`str`,  :obj:`dict` <:obj:`str`, :obj:`any`>>)
        #: image field dictionary
        self.__fields = {}
        # (:class:`lavuelib.filewriter.root`) nexus file root
        self.__root = None

        if not writer:
            writer = "h5py" if "h5py" in WRITERS.keys() else "pni"
        if writer not in WRITERS.keys():
            raise Exception("Writer '%s' cannot be opened" % writer)
        wrmodule = WRITERS[writer.lower()]
        if fname:
            try:
                fl = filewriter.open_file(
                    fname, writer=wrmodule, readonly=True,
                    libver='latest',
                    swmr=(True if writer == "h5py" else False)
                )
            except:
                try:
                    fl = filewriter.open_file(
                        fname, writer=wrmodule, readonly=True)
                except:
                    raise Exception("File '%s' cannot be opened \n" % (fname))
                # except Exception as e:
                #     raise Exception("File '%s' cannot be opened %s\n"
                #                % (fname, str(e)))

            self.__root = fl.root()

    def findImageFields(self):
        """ provides a dictionary with of all image fields

        :returns: dictionary of the field names and the field objects
        :rtype: :obj:`dict` <:obj:`str`,  :obj:`dict` <:obj:`str`, :obj:`any`>>
        """
        #: (:obj:`dict` <:obj:`str`,  :obj:`dict` <:obj:`str`, :obj:`any`>>)
        #: image field dictionary
        self.__fields = {}
        self.__parseimages(self.__root)
        return self.__fields

    @classmethod
    def __getpath(cls, path):
        """ converts full_path with NX_classes into nexus_path

        :param path: nexus full_path
        :type path: :obj:`str`
        """
        spath = path.split("/")
        return "/".join(
            [(dr if ":" not in dr else dr.split(":")[0])
             for dr in spath])

    def __addimage(self, node, tgpath):
        """adds the node into the description list

        :param node: nexus node
        :type node: :class:`pni.io.nx.h5.nxfield` or \
                    :class:`pni.io.nx.h5.nxgroup` or \
                    :class:`pni.io.nx.h5.nxlink` or \
                    :class:`pni.io.nx.h5.nxattribute` or \
                    :class:`pni.io.nx.h5.nxroot`
        :param path: path of the link target or `None`
        :type path: :obj:`str`
        """
        desc = {}
        path = filewriter.first(node.path)
        desc["full_path"] = str(path)
        desc["nexus_path"] = str(self.__getpath(path))
        if hasattr(node, "shape"):
            desc["shape"] = list(node.shape or [])
        else:
            return
        if len(desc["shape"]) < 2:
            return
        if hasattr(node, "dtype"):
            desc["dtype"] = str(node.dtype)
        else:
            return
        if node.is_valid:
            desc["node"] = node
        else:
            return

        self.__fields[desc["nexus_path"]] = desc

    def __parseimages(self, node, tgpath=None):
        """parses the node and add it into the description list

        :param node: nexus node
        :type node: :class:`pni.io.nx.h5.nxfield` or \
                    :class:`pni.io.nx.h5.nxgroup` or \
                    :class:`pni.io.nx.h5.nxlink` or \
                    :class:`pni.io.nx.h5.nxattribute` or \
                    :class:`pni.io.nx.h5.nxroot`
        :param path: path of the link target or `None`
        :type path: :obj:`str`
        """
        self.__addimage(node, tgpath)
        names = []
        if isinstance(node, filewriter.FTGroup):
            names = [
                (ch.name,
                 str(ch.target_path) if hasattr(ch, "target_path") else None)
                for ch in filewriter.get_links(node)]
        for nm in names:
            try:
                ch = node.open(nm[0])
                self.__parseimages(ch, nm[1])
#            except:
#                pass
            finally:
                pass

    def getNode(self, field):
        """ get node
        :param field: field path
        :type field: :obj:`str`
        :returns: nexus field node
        :rtype: :class:`pni.io.nx.h5.nxfield` or \
                :class:`pni.io.nx.h5.nxgroup` or \
                :class:`pni.io.nx.h5.nxlink` or \
                :class:`pni.io.nx.h5.nxattribute` or \
                :class:`pni.io.nx.h5.nxroot`
        """
        node = None
        if field is not None:
            sfield = str(field).split("/")
            node = self.__root
            for name in sfield:
                if name:
                    node = node.open(name)
        return node

    @classmethod
    def getLastFrame(cls, node, growing=0, refresh=True):
        """ provides the last frame number

        :param node: nexus field node
        :type node: :class:`pni.io.nx.h5.nxfield` or \
                    :class:`pni.io.nx.h5.nxgroup` or \
                    :class:`pni.io.nx.h5.nxlink` or \
                    :class:`pni.io.nx.h5.nxattribute` or \
                    :class:`pni.io.nx.h5.nxroot`
        :param growing: growing dimension
        :type growing: :obj:`int`
        :param refresh: refresh image node
        :type refresh: :obj:`bool`
        :returns: a number of frames
        :rtype: :obj:`int`
        """
        if refresh:
            node.refresh()
        if node:
            shape = node.shape
        if shape:
            if len(shape) > growing and growing > -1:
                return shape[growing]
        return 0

    @classmethod
    def getImage(cls, node, frame=-1, growing=0, refresh=True):
        """parses the field and add it into the description list

        :param node: nexus field node
        :type node: :class:`pni.io.nx.h5.nxfield` or \
                    :class:`pni.io.nx.h5.nxgroup` or \
                    :class:`pni.io.nx.h5.nxlink` or \
                    :class:`pni.io.nx.h5.nxattribute` or \
                    :class:`pni.io.nx.h5.nxroot`
        :param frame: frame to take, the last one is -1
        :type frame: :obj:`int`
        :param growing: growing dimension
        :type growing: :obj:`int`
        :param refresh: refresh image node
        :type refresh: :obj:`bool`
        :returns: get the image
        :rtype: :class:`numpy.ndarray`
        """
        if refresh:
            node.refresh()
        if node:
            shape = node.shape
        if shape:
            if len(shape) == 2:
                return node[...]
            elif len(shape) == 3:
                if growing == 0:
                    if frame < 0 or shape[0] > frame:
                        return node[frame, :, :]
                elif growing == 1:
                    if frame < 0 or shape[1] > frame:
                        return node[:, frame, :]
                else:
                    if frame < 0 or shape[2] > frame:
                        return node[:, :, frame]
            elif len(shape) == 4:
                if growing == 0:
                    if frame < 0 or shape[0] > frame:
                        return node[frame, :, :, :]
                elif growing == 1:
                    if frame < 0 or shape[1] > frame:
                        return node[:, frame, :, :]
                elif growing == 2:
                    if frame < 0 or shape[2] > frame:
                        return node[:, :, frame, :]
                else:
                    if frame < 0 or shape[3] > frame:
                        return node[:, :, :, frame]


class ImageFileHandler(object):

    """Simple file handler class.
       Reads image from file and returns the numpy array."""

    def __init__(self, fname):
        """ constructor

        :param fname: file name
        :type fname: :obj:`str`
        """
        #: (:obj:`any`) module image object
        self.__image = None
        #: (:obj:`numpy.ndarray`) image data
        self.__data = None
        try:
            if FABIO:
                self.__image = fabio.open(fname)
                self.__data = self.__image.data
            elif PILLOW:
                self.__image = PIL.Image.open(fname)
                self.__data = np.array(self.__image)
        except Exception:
            try:
                if FABIO and PILLOW:
                    self.__image = PIL.Image.open(fname)
                    self.__data = np.array(self.__image)
            except Exception:
                try:
                    self.__image = np.fromfile(str(fname), dtype='uint8')
                    if fname.endswith(".cbf"):
                        self.__data = CBFLoader().load(self.__image)
                    else:
                        self.__data = TIFLoader().load(self.__image)
                except Exception as e:
                    print(str(e))

    def getImage(self):
        """  provides the image data

        :returns: image data
        :rtype: :class:`numpy.ndarray`
        """
        return self.__data


class CBFLoader(object):

    """ CBF loader """

    @classmethod
    def load(cls, flbuffer):
        """ loads CBF file image data into numpy array

        :param flbuffer: numpy array with CBF file image data
        :type flbuffer: :class:`numpy.ndarray`
        :returns: image data
        :rtype: :class:`numpy.ndarray`
        """
        image = np.array([0])
        inpoint = np.array([26, 4, 213], dtype='uint8')
        outpoint = np.array(
            [45, 45, 67, 73, 70, 45, 66, 73, 78, 65, 82, 89, 45, 70,
             79, 82, 77, 65, 84, 45, 83, 69, 67, 84, 73, 79, 78, 45, 45, 45],
            dtype='uint8')
        flag = 0

        # check if byte offset compress
        boc = np.array(
            [120, 45, 67, 66, 70, 95, 66, 89, 84,
             69, 95, 79, 70, 70, 83, 69, 84],
            dtype='uint8')

        try:
            # iscbf
            flbuffer.tostring().index(boc.tostring()) // flbuffer.itemsize
        except Exception:
            flag = 1

        # additional parms for cross check if decompress worked out
        dset_num_ele = np.array(
            [88, 45, 66, 105, 110, 97, 114, 121, 45, 78, 117, 109, 98,
             101, 114, 45, 111, 102, 45, 69, 108, 101, 109, 101, 110,
             116, 115, 58],
            dtype='uint8')
        dset_fast_dim = np.array(
            [88, 45, 66, 105, 110, 97, 114, 121, 45, 83, 105, 122, 101, 45, 70,
             97, 115, 116, 101, 115, 116, 45, 68, 105, 109, 101, 110, 115, 105,
             111, 110, 58], dtype='uint8')
        dset_sec_dim = np.array(
            [88, 45, 66, 105, 110, 97, 114, 121, 45, 83, 105, 122, 101, 45, 83,
             101, 99, 111, 110, 100, 45, 68, 105, 109, 101, 110, 115, 105, 111,
             110, 58], dtype='uint8')
        dset_pad = np.array(
            [88, 45, 66, 105, 110, 97, 114, 121, 45, 83, 105, 122, 101, 45, 80,
             97, 100, 100, 105, 110, 103, 58], dtype='uint8')

        # search for data stream start
        if flag == 0:
            try:
                idstart = flbuffer.tostring().index(
                    inpoint.tostring()) // flbuffer.itemsize
                idstart += inpoint.size
            except Exception:
                flag = 1

            try:
                idstop = flbuffer.tostring().index(
                    outpoint.tostring()) // flbuffer.itemsize
                idstop -= 3  # cr / extra -1 due to '10B' -- linefeed
            except Exception:
                flag = 1

            vals = np.zeros(4, dtype='int')
            spos = np.zeros(5, dtype='int')
            spos[4] = idstart
            try:
                spos[0] = flbuffer.tostring().index(
                    dset_num_ele.tostring()) // flbuffer.itemsize
                spos[1] = flbuffer.tostring().index(
                    dset_fast_dim.tostring()) // flbuffer.itemsize
                spos[2] = flbuffer.tostring().index(
                    dset_sec_dim.tostring()) // flbuffer.itemsize
                spos[3] = flbuffer.tostring().index(
                    dset_pad.tostring()) // flbuffer.itemsize
# by A.R., Apr 24, 2017
                vals[0] = int(
                    flbuffer[
                        spos[0] + dset_num_ele.size:spos[1] - 2].tostring())
                vals[1] = int(
                    flbuffer[
                        spos[1] + dset_fast_dim.size:spos[2] - 2].tostring())
                vals[2] = int(
                    flbuffer[
                        spos[2] + dset_sec_dim.size:spos[3] - 2].tostring())
                vals[3] = int(
                    flbuffer[
                        spos[3] + dset_pad.size:spos[4] - 8].tostring())
            except Exception:
                flag = 1

            if flag == 0:
                image = 0
                image = cls._decompress_cbf_c(
                    flbuffer[idstart:idstop + 1], vals)
            else:
                image = np.array([0])
        return np.transpose(image)

    @classmethod
    def _decompress_cbf_c(cls, stream, vals):
        """ decompresses CBF

        :param stream: a part of cbf data
        :type stream: :class:`numpy.ndarray`
        :param val: decompress parameters, i.e. n_out, xdim, ydum padding
        :type val: :class:`numpy.ndarray`
        :returns: image data
        :rtype: :class:`numpy.ndarray`
        """
        xdim = long(487)
        ydim = 619
        padding = long(4095)
        n_out = xdim * ydim

        # simply assume content fits here
        if vals.size == 4 and sum(vals) != 0:
            xdim = vals[1]
            ydim = vals[2]
            padding = vals[3]
            n_out = vals[0]

        flbuffer = np.zeros(stream.size, dtype='int32') + stream
        mymap = np.zeros(stream.size, dtype='uint8') + 1
        isvalid = np.zeros(stream.size, dtype='uint8') + 1

        id_relevant = np.where(stream == 128)

        # overcome issue if 128 exists in padding (seems so that
        # either this does not happened before or padding was 0 in any case)
        try:
            idd = np.where(id_relevant < (flbuffer.size - padding))
            id_relevant = id_relevant[idd]
        except:
            pass

        for dummy, dummy2 in enumerate(id_relevant):
            for j, i in enumerate(dummy2):
                if mymap[i] != 0:
                    if stream[i + 1] != 0 or stream[i + 2] != 128:
                        mymap[i:i + 3] = 0
                        isvalid[i + 1:i + 3] = 0
                        delta = flbuffer[i + 1] + flbuffer[i + 2] * 256
                        if delta > 32768:
                            delta -= 65536
                        flbuffer[i] = delta
                    else:
                        mymap[i:i + 7] = 0
                        isvalid[i + 1:i + 7] = 0
                        # delta=sum(np.multiply(flbuffer[i+3:i+7],
                        #   np.array([1,256,65536,16777216],dtype='int64')))
                        delta = (
                            np.multiply(
                                flbuffer[i + 3:i + 7],
                                np.array([1, 256, 65536, 16777216],
                                         dtype='int64'))).sum()
                        if delta > 2147483648:
                            delta -= 4294967296
                        flbuffer[i] = delta

        try:
            id8sign = np.where((stream > 128) & (mymap != 0))
            flbuffer[id8sign] -= 256
            # print ("adjusting 8Bit vals")
            # for i, j in enumerate(stream):
            #     if j > 128 and mymap[i] !=0:
            #         flbuffer[i]=flbuffer[i]-256
            # print stream[0:11]
            # print flbuffer[0:11]

        except:
            pass

        try:
            # print sum(isvalid)    #should be 305548
            idd = np.where(isvalid != 0)
            flbuffer = flbuffer[idd]
        except:
            pass

        # print stream[0:11]
        # print flbuffer[0:11]

        res = np.cumsum(flbuffer, dtype='int32')
        # print max(res)

        if res.size - padding != n_out:
            return np.array([0])
        # by A.R., Apr 24, 2017
        # return res[0:n_out].reshape(xdim, ydim)
        return res[0:n_out].reshape(xdim, ydim, order='F')


class TIFLoader(object):

    """ TIF loader """

    @classmethod
    def load(cls, flbuffer):
        """ loads TIF file image data into numpy array

        :param flbuffer: numpy array with TIF file image data
        :type flbuffer: :class:`numpy.ndarray`
        :returns: image data
        :rtype: :class:`numpy.ndarray`
        """
        image = np.float(-1)
        # define unsigned default if undefined - i.e. like MAR165 data
        sample_format = 1
        flbuffer_endian = 'none'
        if sum(abs(flbuffer[0:2] - [73, 73])) == 0:
            flbuffer_endian = "<"  # little
        if sum(abs(flbuffer[0:2] - [77, 77])) == 0:
            flbuffer_endian = ">"  # big

        if flbuffer_endian == "none":
            return image     # or better to raise exception?

        numfortiff = np.uint16(
            struct.unpack_from(flbuffer_endian + "H", flbuffer[2:4])[0])
        if numfortiff != 42:
            return image  # or better to raise exception?

        ifd_off = np.uint32(
            struct.unpack_from(flbuffer_endian + "I", flbuffer[4:8])[0])
        #
        # jump to/eval image file directory (ifd)
        num_of_ifd = np.uint16(
            struct.unpack_from(
                flbuffer_endian + "H", flbuffer[ifd_off:ifd_off + 2])[0])

        for ifd_entry in range(num_of_ifd):
            field_tag = np.uint16(
                struct.unpack_from(
                    flbuffer_endian + "H",
                    flbuffer[ifd_off + 2 + ifd_entry * 12:ifd_off
                             + 4 + ifd_entry * 12])[0])
            field_type = np.uint16(
                struct.unpack_from(
                    flbuffer_endian + "H",
                    flbuffer[ifd_off + 4 + ifd_entry * 12:ifd_off
                             + 6 + ifd_entry * 12])[0])
            # num_vals = np.uint32(
            #    struct.unpack_from(
            #        flbuffer_endian + "I",
            #        flbuffer[ifd_off + 6 + ifd_entry * 12:ifd_off + 10
            #                 + ifd_entry * 12])[0])
            # given tiff 6.0 there are 12 type entries, currently not all of
            # them are accounted, A.R.
            val_or_off = 0
            if field_type == 1:  # check flbuffer addressing!
                val_or_off = np.uint8(
                    struct.unpack_from(
                        flbuffer_endian + "B",
                        flbuffer[ifd_off + 10 + ifd_entry * 12:ifd_off + 15
                                 + ifd_entry * 12])[0])
            if field_type == 3:
                val_or_off = np.uint16(
                    struct.unpack_from(
                        flbuffer_endian + "H",
                        flbuffer[ifd_off + 10 + ifd_entry * 12:ifd_off + 15
                                 + ifd_entry * 12])[0])
            if field_type == 4:
                val_or_off = np.uint32(
                    struct.unpack_from(
                        flbuffer_endian + "I",
                        flbuffer[ifd_off + 10 + ifd_entry * 12:ifd_off + 15
                                 + ifd_entry * 12])[0])
            if field_type == 8:
                val_or_off = np.int16(
                    struct.unpack_from(
                        flbuffer_endian + "h",
                        flbuffer[ifd_off + 10 + ifd_entry * 12:ifd_off
                                 + 15 + ifd_entry * 12])[0])
            if field_type == 9:
                val_or_off = np.int32(
                    struct.unpack_from(
                        flbuffer_endian + "i",
                        flbuffer[ifd_off + 10 + ifd_entry * 12:ifd_off + 15
                                 + ifd_entry * 12])[0])
            if field_type == 11:
                val_or_off = np.float32(
                    struct.unpack_from(
                        flbuffer_endian + "f",
                        flbuffer[ifd_off + 10 + ifd_entry * 12:ifd_off
                                 + 15 + ifd_entry * 12])[0])

            # eval (hopefully) tags needed to allow for getting an image
            if field_tag == 256:
                width = int(val_or_off)
            if field_tag == 257:
                length = int(val_or_off)
            if field_tag == 258:
                bit_per_sample = int(val_or_off)
            # compression scheme - return invalid if NOT none,
            # i.e. only uncompressed data is supported (forever!?)
            if field_tag == 259:
                if val_or_off != 1:
                    return image
            # photometric interpretation - 2 denotes RGB which is refused
            # otherwise don't mind/care ...
            if field_tag == 262:
                if val_or_off == 2:
                    return image
            if field_tag == 273:
                strip_offsets = val_or_off
            # likely equals image width
            # if field_tag == 278:
            #    rows_per_strip = val_or_off
            if field_tag == 279:
                strip_byte_counts = val_or_off
            if field_tag == 339:
                sample_format = val_or_off

        next_idf = np.uint32(
            struct.unpack_from(
                flbuffer_endian + "I",
                flbuffer[ifd_off + 2 + (ifd_entry + 1) * 12:
                         ifd_off + 6 + (ifd_entry + 1) * 12]
            )[0])
        if next_idf != 0:
            # print('another ifd exists ... NOT read')
            pass
        if width * length * bit_per_sample / 8 != strip_byte_counts:
            return image

        if sample_format == 1 and bit_per_sample == 8:
            image = np.uint8(
                struct.unpack_from(
                    flbuffer_endian + str(width * length) + "B",
                    flbuffer[strip_offsets:strip_offsets
                             + strip_byte_counts + 1]))
        if sample_format == 1 and bit_per_sample == 16:
            image = np.uint16(
                struct.unpack_from(
                    flbuffer_endian + str(width * length) + "H",
                    flbuffer[strip_offsets:strip_offsets
                             + strip_byte_counts + 1]))
        if sample_format == 1 and bit_per_sample == 32:
            image = np.uint32(
                struct.unpack_from(
                    flbuffer_endian + str(width * length) + "I",
                    flbuffer[strip_offsets:strip_offsets
                             + strip_byte_counts + 1]))
        # if sample_format == 2 and bit_per_sample == 8:
        #     image=np.int8(struct.unpack_from(
        #           flbuffer_endian+str(width*length)+"b",
        #     flbuffer[strip_offsets:strip_offsets
        #              +strip_byte_counts+1]))
        if sample_format == 2 and bit_per_sample == 16:
            image = np.int16(
                struct.unpack_from(
                    flbuffer_endian + str(width * length) + "h",
                    flbuffer[strip_offsets:strip_offsets
                             + strip_byte_counts + 1]))
        if sample_format == 2 and bit_per_sample == 32:
            image = np.int32(
                struct.unpack_from(
                    flbuffer_endian + str(width * length) + "i",
                    flbuffer[strip_offsets:strip_offsets
                             + strip_byte_counts + 1]))
        if sample_format == 3 and bit_per_sample == 32:
            image = np.float32(
                struct.unpack_from(
                    flbuffer_endian + str(width * length) + "f",
                    flbuffer[strip_offsets:strip_offsets
                             + strip_byte_counts + 1]))

        try:
            return np.transpose(image.reshape(width, length, order='F'))
        except:
            return np.transpose(image)


if __name__ == "__main__":

    # filename =
    # '/afs/desy.de/user/r/rothkirc/public/P03/lost_00001_00001.tif' # input
    # file name
    # input file name
    filename = '/afs/desy.de/user/r/rothkirc/public/20131129_eugen/' \
               + 'mar165_agbeh_00001.tif'

    tmp = np.fromfile(filename, dtype='uint8')  # read all content as unit 8
    resu = TIFLoader().load(tmp)
    print("Return value shape and dtype")
    print("%s %s" % (resu.shape, resu.dtype))
