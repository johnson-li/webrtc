# packet.py - recognize GPS packet types
# This code is generated by scons.  Do not hand-hack it!
#
# This file is Copyright 2019 by the GPSD project
# SPDX-License-Identifier: BSD-2-Clause
#
# This code runs compatibly under Python 2 and 3.x for x >= 2.
# Preserve this property!
#
# -*- coding: utf-8 -*-
"""Python binding of the libgpsd module for recognizing GPS packets.

The new() function returns a new packet-lexer instance.  Lexer instances
have two methods:
    get() takes a file descriptor argument and returns a tuple consisting of
the integer packet type and string packet value.  On end of file it returns
(-1, '').
    reset() resets the packet-lexer to its initial state.
    The module also has a register_report() function that accepts a callback
for debug message reporting.  The callback will get two arguments, the error
level of the message and the message itself.
"""
from __future__ import absolute_import, print_function
import ctypes
import ctypes.util
import os
import os.path
import sys

import gps  # For gps.__path__
import gps.misc


# Packet types and  Logging levels extracted from gpsd.h
MAX_PACKET_LENGTH = 9216
COMMENT_PACKET = 0
NMEA_PACKET = 1
AIVDM_PACKET = 2
GARMINTXT_PACKET = 3
SIRF_PACKET = 4
ZODIAC_PACKET = 5
TSIP_PACKET = 6
EVERMORE_PACKET = 7
ITALK_PACKET = 8
GARMIN_PACKET = 9
NAVCOM_PACKET = 10
UBX_PACKET = 11
SUPERSTAR2_PACKET = 12
ONCORE_PACKET = 13
GEOSTAR_PACKET = 14
NMEA2000_PACKET = 15
GREIS_PACKET = 16
MAX_GPSPACKET_TYPE = 16
RTCM2_PACKET = 17
RTCM3_PACKET = 18
JSON_PACKET = 19
PACKET_TYPES = 20
SKY_PACKET = 21
LOG_SHOUT = 0
LOG_WARN = 1
LOG_CLIENT = 2
LOG_INF = 3
LOG_PROG = 4
LOG_IO = 5
LOG_DATA = 6
LOG_SPIN = 7
LOG_RAW = 8
LOG_RAW1 = 9
LOG_RAW2 = 10
ISGPS_ERRLEVEL_BASE = LOG_RAW



class PacketLibraryNotFoundError(Exception):
    """Error loading packet library."""
    pass


def importado():
    """
Load the packet library or throw a PacketLibraryNotFoundError trying.
See below for search order.
find_library() looks in: LD_LIBRARY_PATH, DYLD_LIBRARY_PATH,
$home/lib, /.usr/local/lib, /usr/lib, /lib
Returns the library handle."""

    packet_name = 'libgpsdpacket.so.28.0.0'
    packet_dirs = []         # places to look
    lib_dir = '/usr/local/lib'

    # First look in the directory containing this 'gps' package, possibly
    # following a symlink in the process.
    # This is the normal location within the build tree.  It is expected
    # to fail when running the installed version.
    packet_dirs.append(os.path.dirname(os.path.realpath(gps.__path__[0])))

    # Next look in the library install directory.
    # This is the expected location when running the installed version.
    packet_dirs.append(os.path.realpath(lib_dir))

    # Form full paths to candidates so far
    packet_paths = [os.path.join(os.path.abspath(x), packet_name)
                    for x in packet_dirs]

    # Finally try find_library().

    # find_library() looks for bare library name, using dlopen()
    # May, or may not, return a full path.  Either way use as is.
    #
    # linux dlopen() looks in:
    #  LD_LIBRARY_PATH,
    #  paths in /etc/ld.so.cache,
    #  /lib(64) and /usr/lib(64)
    #
    # macOS dlopen() looks in:
    #  LD_LIBRARY_PATH,
    #  DYLD_LIBRARY_PATH,
    #  current working directory,
    #  DYLD_FALLBACK_LIBRARY_PATH (default: $HOME/lib:/usr/local/lib:/usr/lib)
    # Note that some recent macOS versions have stopped honoring *_LIBRARY_PATH,
    # for security reasons.
    #
    # Linux:
    #   find_library() does not usually return a full path.
    #   LoadLibrary() can use a full path, or whatever find_library() returned.
    #
    # macOS:
    #   find_library() returns a full path unless lib in current directory
    #   find_library() returns no full path if lib in current directory
    #   But LoadLibrary() always needs a full path
    #
    packet_path = ctypes.util.find_library('gpsdpacket')
    if packet_path:
        packet_paths.append(packet_path)

    for packet_path in packet_paths:
        try:
            if sys.flags.verbose:
                print('try_packet_lib: %s' % packet_path, file=sys.stderr)
            lib = ctypes.cdll.LoadLibrary(packet_path)
            # get the library version from the library
            gpsd_version = ctypes.c_char_p.in_dll(lib, "gpsd_version").value
            gpsd_version = gps.polystr(gpsd_version)
            if '3.22.1~dev' != gpsd_version:
                sys.stderr.write("WARNING: got library version %s, "
                                 "expected %s\n" %
                                 (gpsd_version, '3.22.1~dev'))
            return lib
        except OSError:
            pass

    raise PacketLibraryNotFoundError("Can't find packet library")


_loaded = None
_packet = importado()

_lexer_size = ctypes.c_size_t.in_dll(_packet, "fvi_size_lexer")
LEXER_SIZE = _lexer_size.value
_buffer_size = ctypes.c_size_t.in_dll(_packet, "fvi_size_buffer").value

REPORTER = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_char_p)


class GpsdErrOutT(ctypes.Structure):
    '''Used in gps.packet:register_report() to set logging callback.'''
    # pylint: disable-msg=R0903
    _fields_ = [('debug', ctypes.c_int),
                ('report', REPORTER),
                ('label', ctypes.c_char_p)]


class lexer_t(ctypes.Structure):
    '''Used in gps.packet:lexer.get() to pass in data and pull
    out length, packet type, packet, and another datum.'''
    # pylint: disable-msg=R0903
    _fields_ = [
        ('packet_type', ctypes.c_int),
        ('state', ctypes.c_uint),
        ('length', ctypes.c_size_t),
        ('inbuffer', ctypes.c_ubyte * _buffer_size),
        ('inbuflen', ctypes.c_size_t),
        ('inbufptr', ctypes.c_char_p),
        ('outbuffer', ctypes.c_ubyte * _buffer_size),
        ('outbuflen', ctypes.c_size_t),
        ('char_counter', ctypes.c_ulong),
        ('retry_counter', ctypes.c_ulong),
        ('counter', ctypes.c_uint),
        ('errout', GpsdErrOutT),
    ]


def new():
    """new() -> new packet-self object"""
    return Lexer()


def register_report(reporter):
    """register_report(callback)

    callback must be a callable object expecting a string as parameter."""
    global _loaded
    if callable(reporter):
        _loaded.errout.report = REPORTER(reporter)


class Lexer():
    """GPS packet lexer object

Fetch a single packet from file descriptor
"""
    pointer = None

    def __init__(self):
        global _loaded
        _packet.ffi_Lexer_init.restype = ctypes.POINTER(lexer_t)
        self.pointer = _packet.ffi_Lexer_init()
        _loaded = self.pointer.contents

    def get(self, file_handle):
        """Get a packet from a file descriptor."""
        global _loaded
        _packet.packet_get.restype = ctypes.c_int
        _packet.packet_get.argtypes = [ctypes.c_int, ctypes.POINTER(lexer_t)]
        length = _packet.packet_get(file_handle, self.pointer)
        _loaded = self.pointer.contents
        packet = ''
        for octet in range(_loaded.outbuflen):
            packet += chr(_loaded.outbuffer[octet])
        return [length,
                _loaded.packet_type,
                gps.misc.polybytes(packet),
                _loaded.char_counter]

    def reset(self):
        """Reset the packet self to ground state."""
        _packet.ffi_Lexer_init.restype = None
        _packet.ffi_Lexer_init.argtypes = [ctypes.POINTER(lexer_t)]
        _packet.ffi_Lexer_init(self.pointer)

# vim: set expandtab shiftwidth=4
