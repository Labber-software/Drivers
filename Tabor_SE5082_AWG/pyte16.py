#!/usr/bin/env python
# -*- coding: utf-8 -*-
# =========================================================================
# Copyright (C) 2016  Tabor-Electronics Ltd <http://www.taborelec.com/>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
# =========================================================================

'''
pyte16 -- control Tabor-Electronics instruments using `pyvisa` 1.6 or above.

@author:     Nadav
@date:       2016-11-23
@license:    GPL
@copyright:  2016 Tabor-Electronics Ltd.
@contact:    <http://www.taborelec.com/>
'''
from __future__ import print_function
from builtins import input
import sys
import socket
import ctypes
import struct
import math
import warnings
import numpy as np
import visa
import pyvisa.constants as vc
#from pyvisa.errors import (VisaIOError, VisaIOWarning)

__version__    = '1.0.1'
__revision__   = '$Rev: 3947 $'
__docformat__  = 'reStructuredText'

__all__ = [
    'open_session',
    'send_cmd',
    'download_binary_data',
    'download_binary_file',
    'download_binary_file',
    'download_arbcon_wav_file',
    'download_segment_lengths',
    'download_sequencer_table',
    'download_adv_seq_table',
    'download_fast_pattern_table',
    'download_linear_pattern_table',
    'build_sine_wave',
    'build_triangle_wave',
    'build_square_wave',
    'add_markers',
    'make_combined_wave'    ]

def _list_udp_awg_instruments():
    '''
    Using UDP list all AWG-Instruments with LAN Interface

    :returns: two lists: 1. VISA-Resource-Names 2. Instrument-IDN-Strings
    '''
    BROADCAST = '255.255.255.255'
    UDPSRVPORT = 7501
    UPFRMPORT = 7502
    FRMHEADERLEN = 22
    FRMDATALEN = 1024
    FLASHLINELEN = 32
    #FLASHOPCODELEN  = 1

    vi_tcpip_resource_names = []
    vi_tcpip_resource_descs = []

    query_msg = bytearray([0xff] * FRMHEADERLEN)
    query_msg[0] = 'T'
    query_msg[1] = 'E'
    query_msg[2] = 'I'
    query_msg[3] = 'D'

    try:
        udp_server_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_IP)
        udp_server_sock.bind(("0.0.0.0", UDPSRVPORT)) # any IP-Address
        udp_server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, FRMHEADERLEN + FRMDATALEN)
        udp_server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, True)

        # Send the query-message (to all)
        udp_server_sock.sendto(query_msg, (BROADCAST, UPFRMPORT))

        # Receive responses
        udp_server_sock.settimeout(2)
        while True:
            try:
                data, addr = udp_server_sock.recvfrom(FRMHEADERLEN + FRMDATALEN)
                vi_tcpip_resource_names.append("TCPIP::{0}::5025::SOCKET".format(addr[0]))

                ii = FRMHEADERLEN
                manuf_name = ''
                model_name = ''
                serial_nb = ''
                fw_ver = ''
                while ii + FLASHLINELEN <= len(data):
                    opcode = data[ii]
                    attr = data[ii + 1 : ii + FLASHLINELEN - 1]
                    attr.rstrip()
                    if opcode == 'D':
                        manuf_name = attr
                    elif opcode == 'I':
                        model_name = attr
                    elif opcode == 'S':
                        serial_nb = attr
                    elif opcode == 'F':
                        fw_ver = attr

                    idn = '{0:s},{1:s},{2:s},{3:s}'.format(manuf_name,model_name,serial_nb,fw_ver)
                    vi_tcpip_resource_descs.append(idn)
                    ii = ii + FLASHLINELEN
            except socket.timeout:
                break
    except:
        pass

    return vi_tcpip_resource_names, vi_tcpip_resource_descs

def _select_visa_rsc_name(rsc_manager=None, title=None, interface_name=None):
    """Select VISA Resource name.

    The suportted interfaces names are: 'TCPIP', 'USB', 'GPIB', 'VXI', 'ASRL'

    :param rsc_manager: (optional) visa resource-manager.
    :param title: (optional) string displayed as title.
    :param interface_name: (optional) visa interface name.
    :returns: the selected resource name (string).
    """

    if rsc_manager is None:
        rsc_manager = visa.ResourceManager()

    selected_rsc_name = None

    rsc_names = []
    rsc_descs = []
    num_rscs = 0

    intf_nb = 0
    if interface_name is not None:
        intf_map = { 'TCPIP' : 1, 'USB' : 2, 'GPIB' : 3, 'VXI' : 4, 'ASRL' : 5 }
        intf_nb = intf_map.get(interface_name, 0)

    while True:
        #uit_flag = True
        rsc_names = []
        rsc_descs = []
        num_rscs = 0

        if intf_nb in (1,2,3,4,5):
            choice = intf_nb
        else:
            if title is not None:
                print()
                print(title)
                print('=' * len(title))
            print()
            print("Select VISA Interface type:")
            print(" 1. TCPIP")
            print(" 2. USB")
            print(" 3. GPIB")
            print(" 4. VXI")
            print(" 5. ASRL")
            print(" 6. LXI")
            print(" 7. Enter VISA Resource-Name")
            print(" 8. Quit")
            choice = prompt_msg("Please enter your choice [1:7]: ", "123467")
            try:
                choice = int(choice)
            except:
                choice = -1
            print()

        if choice == 1:
            print()
            ip_str = prompt_msg("Enter IP-Address, or press[Enter] to search:  ",)
            print()
            if len(ip_str) == 0:
                print('Searching AWG-Instruments ... ')
                rsc_names, rsc_descs = _list_udp_awg_instruments()
                print()
            else:
                try:
                    packed_ip = socket.inet_aton(ip_str)
                    ip_str = socket.inet_ntoa(packed_ip)
                    selected_rsc_name = "TCPIP::{0}::5025::SOCKET".format(ip_str)
                    break
                except:
                    print()
                    print("Invalid IP-Address")
                    print()
                    continue
        elif choice == 2:
            rsc_names = rsc_manager.list_resources(query="?*USB?*INSTR")
        elif choice == 3:
            rsc_names = rsc_manager.list_resources(query="?*GPIB?*INSTR")
        elif choice == 4:
            rsc_names = rsc_manager.list_resources(query="?*VXI?*INSTR")
        elif choice == 5:
            rsc_names = rsc_manager.list_resources(query="?*ASRL?*INSTR")
        elif choice == 6:
            host_name = prompt_msg('Please enter Host-Name: ')
            if len(host_name) > 0:
                selected_rsc_name = "TCPIP::{0}::INSTR".format(host_name)
                break
        elif choice == 7:
            resource_name = prompt_msg('Please enter VISA Resurce-Name: ')
            print()
            if len(resource_name) > 0:
                selected_rsc_name = resource_name
                break
        elif choice == 8:
            break
        else:
            print()
            print("Invalid choice")
            print()
            continue

        num_rscs = len(rsc_names)
        if  num_rscs == 0:
            print()
            print('No VISA Resource was found!')
            yes_no = prompt_msg("Do you want to retry [y/n]: ", "yYnN")
            if yes_no in "yY":
                continue
            else:
                break
        elif num_rscs == 1 and choice != 1:
            selected_rsc_name = rsc_names[0]
            break
        elif num_rscs > 1 or (num_rscs == 1 and choice == 1):
            if len(rsc_descs) != num_rscs:
                rsc_descs = ["" for n in range(num_rscs)]
                # get resources descriptions:
                for n, name in zip(range(num_rscs), rsc_names):
                    vi = None
                    try:
                        vi =rsc_manager.open_resource(name)
                        vi.read_termination = '\n'
                        vi.write_termination = '\n'
                        ans_str = vi.ask('*IDN?')
                        rsc_descs[n] = ans_str
                    except:
                        pass
                    if vi is not None:
                        try:
                            vi.close()
                            vi = None
                        except:
                            pass

            print("Please choose one of the available devices:")
            for n, name, desc in zip(range(num_rscs), rsc_names, rsc_descs):
                print(" {0:d}. {1} ({2})".format(n+1, desc, name))
            print(" {0:d}. Back to main menu".format(num_rscs+1))
            msg = "Please enter your choice [{0:d}:{1:d}]: ".format(1, num_rscs+1)
            valid_answers = [str(i+1) for i in range(num_rscs+1)]
            choice = prompt_msg(msg, valid_answers)

            try:
                choice = int(choice)
            except:
                choice = num_rscs+1

            if choice == num_rscs+1:
                continue
            else:
                selected_rsc_name = rsc_names[choice - 1]
                break

    return selected_rsc_name

def _init_vi_inst(vi, timeout_msec=30000, read_buff_size_bytes=4096, write_buff_size_bytes=4096):
    '''Initialize the given Instrument VISA Session

    :param vi: `pyvisa` instrument.
    :param timeout_msec: VISA-Timeout (in milliseconds)
    :param read_buff_size_bytes: VISA Read-Buffer Size (in bytes)
    :param write_buff_size_bytes: VISA Write-Buffer Size (in bytes)
    '''

    if vi is not None:
        vi.timeout = int(timeout_msec)
        vi.visalib.set_buffer(vi.session, vc.VI_READ_BUF, int(read_buff_size_bytes))
        vi.__dict__['read_buff_size'] = read_buff_size_bytes
        vi.visalib.set_buffer(vi.session, vc.VI_WRITE_BUF, int(write_buff_size_bytes))
        vi.__dict__['write_buff_size'] = write_buff_size_bytes
        vi.read_termination = '\n'
        vi.write_termination = '\n'
        intf_type = vi.get_visa_attribute(vc.VI_ATTR_INTF_TYPE)
        if intf_type in (vc.VI_INTF_USB, vc.VI_INTF_GPIB, vc.VI_INTF_TCPIP):
            vi.set_visa_attribute(vc.VI_ATTR_WR_BUF_OPER_MODE, vc.VI_FLUSH_ON_ACCESS)
            vi.set_visa_attribute(vc.VI_ATTR_RD_BUF_OPER_MODE, vc.VI_FLUSH_ON_ACCESS)
            if intf_type == vc.VI_INTF_TCPIP:
                vi.set_visa_attribute(vc.VI_ATTR_TERMCHAR_EN, vc.VI_TRUE)   # vc.VI_FALSE
        vi.clear()

def open_session(resource_name = None, title_msg = None, vi_rsc_mgr = None, extra_init=True):
    '''Open VISA Session (optionally prompt for resource name).

    The `resource_name` can be either:
        1. Full VISA Resource-Name (e.g. 'TCPIP::192.168.0.170::5025::SOCKET')
        2. IP-Address (e.g. '192.168.0.170')
        3. Interface-Name (either 'TCPIP', 'USB', 'GPIB', 'VXI' or 'ASRL')
        4. None

    :param resource_name: the Resource-Name
    :param title_msg: title-message (for the interactive-menu)
    :param vi_rsc_mgr: VISA Resource-Manager
    :param extra_init: should perform extra initialization
    :returns: `pyvisa` instrument.

    Example:

        >>> import pyte
        >>>
        >>> # Connect to Arbitrary-Wave-Generator Instrument through TCPIP
        >>> # (the user will be asked to enter the instrument's IP-Address):
        >>> vi = pyte.open_session(resource_name='TCPIP', title_msg='Connect to AWG Instrument')
        >>>
        >>> # Connect to Digital-Multimeter through USB:
        >>> dmm = pyte.open_session(resource_name='USB', extra_init=False)
        >>>
        >>> print vi.ask('*IDN?')
        >>> print dmm.ask('*IDN?')
        >>>
        >>> # Do some work ..
        >>>
        >>> vi.close()
        >>> dmm.close()

    '''

    vi = None
    try:

        if vi_rsc_mgr is None:
            vi_rsc_mgr = visa.ResourceManager()

        if resource_name is None:
            resource_name = _select_visa_rsc_name(vi_rsc_mgr, title_msg)
        elif resource_name.upper() in ('TCPIP', 'USB', 'GPIB', 'VXI', 'ASRL'):
            resource_name = _select_visa_rsc_name(vi_rsc_mgr, title_msg, resource_name.upper())
        else:
            try:
                packed_ip = socket.inet_aton(resource_name)
                ip_str = socket.inet_ntoa(packed_ip)
                if resource_name == ip_str:
                    resource_name = "TCPIP::{0}::5025::SOCKET".format(ip_str)
            except:
                pass

        if resource_name is None:
            return None

        vi = vi_rsc_mgr.open_resource(resource_name)
        if extra_init and vi is not None:
            _init_vi_inst(vi)
    except:
        print('Failed to open "{0}"\n{1}'.format(resource_name, sys.exc_info()))

    return vi

def prompt_msg(msg, valid_answers = None):
    """Prompt message and return user's answer."""
    ans = input(msg)
    if valid_answers is not None:
        count = 0
        while ans not in valid_answers:
            count += 1
            ans = input(msg)
            if count == 5:
                break;
    return ans

def make_bin_dat_header(bin_dat_size, header_prefix=None):
    '''Make Binary-Data Header

    :param bin_dat_size: the binary-data total size in bytes.
    :param header_prefix: header-prefix (e.g. ":TRACe:DATA")
    :returns: binary-data header (string)
    '''
    bin_dat_size = int(bin_dat_size)
    dat_sz_str = "{0:d}".format(bin_dat_size)

    if header_prefix is None:
        header_prefix = ''

    bin_dat_header = '{0:s}#{1:d}{2:s}'.format(header_prefix, len(dat_sz_str), dat_sz_str)
    return bin_dat_header

def get_visa_err_desc(err_code):
    '''Get description of the given visa error code.'''
    desc = None
    try:
        from pyvisa.errors import completion_and_error_messages
        desc = completion_and_error_messages.get(err_code)
    except:
        pass
    if desc is None:
        desc = 'VISA-Error {0:x}'.format(int(err_code))

    return desc

def write_raw_string(vi, wr_str):
    '''Write raw string to device (no termination character is added)

    :param vi: `pyvisa` instrument.
    :param wr_str:  the string to write.
    :returns: written-bytes count.
    '''

    ret_count = 0
    count = 0

    write_termination = vi.write_termination
    vi.write_termination = ''
    try:
        #ret_count = len(wr_str)
        #p_dat = ctypes.cast(wr_str, ctypes.POINTER(ctypes.c_byte))
        #ul_sz = ctypes.c_ulong(ret_count)
        #p_ret = ctypes.cast(count, ctypes.POINTER(ctypes.c_ulong))
        #err_code = vi.visalib.viWrite(vi.session, p_dat, ul_sz, p_ret)
        count, err_code = vi.write(wr_str)
        if err_code < 0:
            err_desc = get_visa_err_desc(err_code)
            wrn_msg = 'write_raw_string(wr_str="{0}")={1} ({2})'.format(wr_str, err_code, err_desc)
            warnings.warn(wrn_msg)
        elif count < 0:
            ret_count = count
    except:
        ret_count = min(count, -1)
        wrn_msg = 'write_raw_string(wr_str="{0}") failed\n{1}'.format(wr_str,sys.exc_info())
        warnings.warn(wrn_msg)

    vi.write_termination = write_termination

    return ret_count

def write_raw_bin_dat(vi, bin_dat, dat_size, max_chunk_size = 1024):
    """Write raw binary data to device.

    The binary data is sent in chunks of up to `max_chunk_size` bytes

    :param vi: `pyvisa` instrument.
    :param bin_dat: the binary data buffer.
    :param dat_size: the data-size in bytes.
    :param max_chunk_size: maximal chunk-size (in bytes).
    :returns: written-bytes count.
    """

    ret_count = 0
    err_code = 0
    wr_offs = 0
    count = 0

    write_termination = vi.write_termination
    vi.write_termination = ''
    try:
        if isinstance(bin_dat, np.ndarray):
            p_dat = bin_dat.ctypes.data_as(ctypes.POINTER(ctypes.c_byte))
        else:
            p_dat = ctypes.cast(bin_dat, ctypes.POINTER(ctypes.c_byte))

        p_cnt = ctypes.cast(count, ctypes.POINTER(ctypes.c_ulong))

        if dat_size <= max_chunk_size:
            ul_sz = ctypes.c_ulong(dat_size)
            err_code = vi.visalib.viWrite(vi.session, p_dat, ul_sz, p_cnt)
            ret_count = dat_size
        else:
            while wr_offs < dat_size:
                chunk_sz = min(max_chunk_size, dat_size - wr_offs)
                ul_sz = ctypes.c_ulong(chunk_sz)
                ptr = ctypes.cast(ctypes.addressof(p_dat.contents) + wr_offs, ctypes.POINTER(ctypes.c_byte))
                err_code = vi.visalib.viWrite(vi.session, ptr, ul_sz, p_cnt)
                if count < 0 or err_code < 0:
                    ret_count = min(count, -1)
                    break
                ret_count = ret_count + chunk_sz
                wr_offs = wr_offs + chunk_sz

        if count < 0 or err_code < 0:
            err_desc = get_visa_err_desc(err_code)
            wrn_msg = 'write_raw_bin_dat(dat_size={0})={1}, wr_offs={2}, err_code={3} ({4})'.format(dat_size, count, err_code, err_desc)
    except:
        ret_count = min(ret_count, -1)
        wrn_msg = 'write_raw_bin_dat(dat_size={0}) failed\n{1}'.format(dat_size, sys.exc_info())
        warnings.warn(wrn_msg)

    vi.write_termination = write_termination
    return ret_count

def send_cmd(vi, cmd_str, paranoia_level=1):
    '''Send (SCPI) Command to Instrument

    :param vi: `pyvisa` instrument.
    :param cmd_str: the command string.
    :param paranoia_level: paranoia-level (0:low, 1:normal, 2:high)
    '''
    if paranoia_level == 1:
        ask_str = cmd_str.rstrip()
        if len(ask_str) > 0:
            ask_str += '; *OPC?'
        else:
            ask_str = '*OPC?'
        _ = vi.ask(ask_str)
    elif paranoia_level >= 2:
        ask_str = cmd_str.rstrip()
        if len(ask_str) > 0:
            ask_str += '; :SYST:ERR?'
        else:
            ask_str = ':SYST:ERR?'
        syst_err = vi.ask(ask_str)
        if not syst_err.startswith('0'):
            syst_err = syst_err.rstrip()
            wrn_msg = 'ERR: "{0}" after CMD: "{1}"'.format(syst_err, cmd_str)
            _ = vi.ask('*CLS; *OPC?') # clear the error-list
            if paranoia_level >= 3:
                raise NameError(wrn_msg)
            else:
                warnings.warn(wrn_msg)

    else:
        vi.write(cmd_str)

def _pre_download_binary_data(vi, bin_dat_size=None):
    '''Pre-Download Binary-Data

    :param vi: `pyvisa` instrument.
    :param bin_dat_size: the binary-data-size in bytes (can be omitted)
    :returns: the max write-chunk size (in bytes) and the original time-out (in msec)
    '''
    orig_timeout = vi.timeout
    max_chunk_size = 4096

    try:
        max_chunk_size = vi.__dict__.get('write_buff_size', default=max_chunk_size)
        intf_type = vi.get_visa_attribute(vc.VI_ATTR_INTF_TYPE)
        if intf_type == vc.VI_INTF_GPIB:
            _ = vi.write("*OPC?")
            for _ in range(2000):
                status_byte = vi.stb
                if (status_byte & 0x10) == 0x10:
                    break
            _ = vi.read()
            max_chunk_size = min(max_chunk_size, 30000)
            if bin_dat_size is not None and orig_timeout < bin_dat_size / 20:
                vi.timeout = int(bin_dat_size / 20)
        else:
            max_chunk_size = min(max_chunk_size, 256000)
    except:
        pass

    return orig_timeout, max_chunk_size

def _post_download_binary_data(vi, orig_timeout):
    '''Post-Download Binary-Data

    :param vi: `pyvisa` instrument.
    :param orig_timeout: the original time-out (in msec)
    '''

    if orig_timeout is not None and vi.timeout != orig_timeout:
        vi.timeout = orig_timeout

def download_binary_data(vi, pref, bin_dat, dat_size, paranoia_level=1):
    """Download binary data to instrument.

    Notes:
      1. The caller needs not add the binary-data header (#<data-length>)
      2. The header-prefix, `pref`, can be empty string or `None`

    :param vi: `pyvisa` instrument.
    :param pref: the header prefix (e.g. ':TRACe:DATA').
    :param bin_dat: the binary data buffer.
    :param dat_size: the data-size in bytes.
    :param paranoia_level: paranoia-level (0:low, 1:normal, 2:high)
    :returns: written-bytes count.

    Example:
        >>> import pyte
        >>>
        >>> vi = pyte.open_session('192.168.0.170')
        >>> _ = vi.ask('*RST; *CLS; *OPC?') # reset the instrument
        >>> _ = vi.ask(':FUNC:MODE USER; *OPC?') # select arbirary-wave mode
        >>> _ = vi.ask(':FREQ::RAST 2GHz; *OPC?') # Set sampling-rate = 2GHz
        >>>
        >>> # build sine-wave (single cycle) of 1024-points:
        >>> sin_wav = pyte.build_sine_wave(cycle_len=1024)
        >>>
        >>> # download it to the active segment of the active channel:
        >>> pyte.download_binary_data(vi, 'TRAC:DATA', sin_wav, 1024 * 2)
        >>>
        >>> _ = vi.ask(':OUTP ON; *OPC?') # turn on the active channel
        >>> print vi.ask(':SYST:ERR?')
        >>> vi.close()
    """
    ret_count = 0

    try:
        orig_timeout, max_chunk_size = _pre_download_binary_data(vi, dat_size)

        try:
            dat_header = make_bin_dat_header(dat_size, pref)
            if paranoia_level >= 1:
                # Add *OPC? to the beginning of the binary-data header:
                dat_header = '*OPC? ;' + dat_header

            ret_count = write_raw_string(vi, dat_header)

            if ret_count < 0:
                wrn_msg = "Failed to write binary-data header"
                warnings.warn(wrn_msg)
            else:
                count = write_raw_bin_dat(vi, bin_dat, dat_size, max_chunk_size)
                if count < 0:
                    ret_count = count
                    wrn_msg = "Failed to write binary-data"
                    warnings.warn(wrn_msg)
                else:
                    ret_count = ret_count + count

            if paranoia_level >= 1:
                # Read the response to the *OPC? query that was sent with the binary-data header
                _ = vi.read()
        finally:
            _post_download_binary_data(vi, orig_timeout)

        if paranoia_level >= 2:
            syst_err = vi.ask(':SYST:ERR?')
            if not syst_err.startswith('0'):
                syst_err = syst_err.rstrip()
                wrn_msg = 'ERR: "{0}" after sending binary data (pref="{1}", dat_size={2})'.format(syst_err, pref, dat_size)
                _ = vi.ask('*CLS; *OPC?') # clear the error-list
                if paranoia_level >= 3:
                    raise NameError(wrn_msg)
                else:
                    warnings.warn(wrn_msg)

    except:
        if ret_count >= 0:
            ret_count = -1
        wrn_msg = 'Error in download_binary_data(pref="{0}", dat_size={1}): \n{2}'.format(pref, dat_size, sys.exc_info())
        if paranoia_level >= 3:
            raise NameError(wrn_msg)
        else:
            warnings.warn(wrn_msg)

    return ret_count

def download_binary_file(vi, pref, file_path, offset=0, data_size=None, paranoia_level=1):
    """Download binary data from file to instrument.

    Notes:
      1. The caller needs not add the binary-data header (#<data-length>)
      2. The header-prefix, `pref`, can be empty string or `None`

    :param vi: `pyvisa` instrument.
    :param pref: the header prefix (e.g. ':TRACe:DATA').
    :param file_path: the file path.
    :param offset: starting-offset in the file (in bytes).
    :param data_size: data-size in bytes (`None` means all)
    :param paranoia_level: paranoia-level (0:low, 1:normal, 2:high)
    :returns: written-bytes count.

    Example:
        >>> import pyte
        >>> import os
        >>> file_path = os.path.expanduser('~')
        >>> file_path = os.path.join(file_path, 'Documents')
        >>> file_path = os.path.join(file_path, 'sin.wav')
        >>>
        >>> # build sine-wave (single cycle) of 1024-points:
        >>> sin_wav = pyte.build_sine_wave(cycle_len=1024)
        >>> # write it to binary file:
        >>> sin_wav.tofile(file_path)
        >>>
        >>> # Later on ..
        >>>
        >>> vi = pyte.open_session('192.168.0.170')
        >>> _ = vi.ask('*RST; *CLS; *OPC?') # reset the instrument
        >>> _ = vi.ask(':FUNC:MODE USER; *OPC?') # select arbirary-wave mode
        >>> _ = vi.ask(':FREQ::RAST 2GHz; *OPC?') # Set sampling-rate = 2GHz
        >>>
        >>> # write wave-data from file to the active segment of the active channel:
        >>> pyte.download_binary_file(vi, file_path, 'TRAC:DATA')
        >>>
        >>> _ = vi.ask(':OUTP ON; *OPC?') # turn on the active channel
        >>> print vi.ask(':SYST:ERR?')
        >>> vi.close()
    """
    ret_count = 0

    with open(file_path, mode='rb') as infile:
        try:
            infile.seek(0,2) # move the cursor to the end of the file
            file_size = infile.tell()

            if data_size is None:
                data_size = file_size

            if offset + data_size > file_size:
                data_size = max(0, file_size - offset)

            if data_size > 0:
                #print
                #print 'Download {0:d} bytes from file \"{1:s\" ... '.format(data_size, file_path)
                orig_timeout, max_chunk_size = _pre_download_binary_data(vi, data_size)

                try:
                    dat_header = make_bin_dat_header(data_size, pref)
                    if paranoia_level >= 1:
                        # Add *OPC? to the beginning of the binary-data header:
                        dat_header = '*OPC? ;' + dat_header

                    ret_count = write_raw_string(vi, dat_header)

                    if ret_count < 0:
                        wrn_msg = "Failed to write binary-data header"
                        warnings.warn(wrn_msg)
                    else:
                        infile.seek(offset) # move the cursor to the specified offset

                        offset = 0
                        while offset < data_size and ret_count >= 0:
                            chunk_size = min(data_size - offset, 4096)
                            chunk = np.fromfile(infile, dtype=np.uint8, count=chunk_size)
                            count = write_raw_bin_dat(vi, chunk, chunk_size, max_chunk_size)
                            if count < 0:
                                ret_count = count
                                wrn_msg = "Failed to write binary-data "
                                warnings.warn(wrn_msg)
                            else:
                                offset = offset + chunk_size
                                ret_count = ret_count + chunk_size

                        if paranoia_level >= 1:
                            # Read the response to the *OPC? query that was sent with the binary-data header
                            _ = vi.read()
                finally:
                    _post_download_binary_data(vi, orig_timeout)

                if paranoia_level >= 2:
                    syst_err = vi.ask(':SYST:ERR?')
                    if not syst_err.startswith('0'):
                        syst_err = syst_err.rstrip()
                        wrn_msg = 'ERR: "{0}" after sending binary data (pref="{1}", dat_size={2})'.format(syst_err, pref, data_size)
                        warnings.warn(wrn_msg)
                        _ = vi.ask('*CLS; *OPC?') # clear the error-list
        except:
            if ret_count >= 0:
                ret_count = -1
            wrn_msg = 'Error in download_binary_data(pref="{0}", data_size={1}): \n{2}'.format(pref, data_size, sys.exc_info()[0])
            warnings.warn(wrn_msg)

    return ret_count

def download_arbcon_wav_file(vi, file_path, pref=':TRAC:DATA', bits_per_point=14, paranoia_level=1):
    """Download wave data from binary wav file created by the ArbConnection to instrument.

    :param vi: `pyvisa` instrument.
    :param file_path: the file path.
    :param pref: the header prefix (e.g. ':TRACe:DATA').
    :param bits_per_point: number of bits per wave-point.
    :param paranoia_level: paranoia-level (0:low, 1:normal, 2:high)
    :returns: written-bytes count.
    """
    ret_count = 0

    with open(file_path, mode='rb') as infile:
        try:
            infile.seek(0,2) # move the cursor to the end of the file
            file_size = infile.tell()

            wav_len = file_size // 2

            if wav_len > 0:
                data_size = wav_len * 2
                orig_timeout, max_chunk_size = _pre_download_binary_data(vi, wav_len * 2)

                try:

                    dat_header = make_bin_dat_header(data_size, pref)
                    if paranoia_level >= 1:
                        # Add *OPC? to the beginning of the binary-data header:
                        dat_header = '*OPC? ;' + dat_header

                    ret_count = write_raw_string(vi, dat_header)

                    if ret_count < 0:
                        wrn_msg = "Failed to write binary-data header"
                        warnings.warn(wrn_msg)
                    else:
                        infile.seek(0) # move the cursor to the file beginnig

                        offset = 0
                        while offset < wav_len and ret_count >= 0:
                            chunk_size = min(wav_len - offset, max_chunk_size // 2)
                            chunk = np.fromfile(infile, dtype=np.uint16, count=chunk_size) + 2**(bits_per_point-1)
                            chunk = np.clip(chunk, 0, 2**bits_per_point-1)
                            count = write_raw_bin_dat(vi, chunk, chunk.nbytes, chunk.nbytes)
                            if count < 0:
                                ret_count = count
                                wrn_msg = "Failed to write binary-data "
                                warnings.warn(wrn_msg)
                            else:
                                offset = offset + chunk_size
                                ret_count = ret_count + count

                        if paranoia_level >= 1:
                            # Read the response to the *OPC? query that was sent with the binary-data header
                            _ = vi.read()
                finally:
                    _post_download_binary_data(vi, orig_timeout)

                if paranoia_level >= 2:
                    syst_err = vi.ask(':SYST:ERR?')
                    if not syst_err.startswith('0'):
                        syst_err = syst_err.rstrip()
                        wrn_msg = 'ERR: "{0}" after sending binary data (pref="{1}", dat_size={2})'.format(syst_err, pref, data_size)
                        warnings.warn(wrn_msg)
                        _ = vi.ask('*CLS; *OPC?') # clear the error-list
        except:
            if ret_count >= 0:
                ret_count = -1
            wrn_msg = 'Error in download_binary_data(pref="{0}", data_size={1}): \n{2}'.format(pref, data_size, sys.exc_info()[0])
            warnings.warn(wrn_msg)

    return ret_count

def download_segment_lengths(vi, seg_len_list, pref=':SEGM:DATA', paranoia_level=1):
    '''Download Segments-Lengths Table to Instrument

    :param vi: `pyvisa` instrument.
    :param seg_len_list: the list of segments-lengths.
    :param pref: the binary-data-header prefix.
    :param paranoia_level: paranoia-level (0:low, 1:normal, 2:high)
    :returns: written-bytes count.

    Example:
        The fastest way to download multiple segments to the instrument
        is to download the wave-data of all the segments, including the
        segment-prefixes (idle-points) of all segments except the 1st,
        into segment 1 (pseudo segment), and afterward download the
        appropriate segment-lengths.

        >>> # Select segment 1:
        >>> _ = vi.ask(':TRACe:SELect 1; *OPC?')
        >>>
        >>> # Download the wave-data of all segments:
        >>> pyte.download_binary_data(vi, ':TRACe:DATA', wave_data, total_size)
        >>>
        >>> # Download the appropriate segment-lengths list:
        >>> seg_lengths = [ 1024, 1024, 384, 4096, 8192 ]
        >>> pyte.download_segment_lengths(vi, seg_lengths)
    '''
    if isinstance(seg_len_list, np.ndarray):
        if seg_len_list.ndim != 1:
            seg_len_list = seg_len_list.flatten()
        if seg_len_list.dtype != np.uint32:
            seg_len_list = np.asarray(seg_len_list, dtype=np.uint32)
    else:
        seg_len_list = np.asarray(seg_len_list, dtype=np.uint32)
        if seg_len_list.ndim != 1:
            seg_len_list = seg_len_list.flatten()

    return download_binary_data(vi, pref, seg_len_list, seg_len_list.nbytes, paranoia_level=paranoia_level)

def download_sequencer_table(vi, seq_table, pref=':SEQ:DATA', paranoia_level=1):
    '''Download Sequencer-Table to Instrument

    The sequencer-table, `seq_table`, is a list of 3-tuples
    of the form: (<repeats>, <segment no.>, <jump-flag>)

    :param vi: `pyvisa` instrument.
    :param seq_table: the sequencer-table (list of 3-tuples)
    :param pref: the binary-data-header prefix.
    :param paranoia_level: paranoia-level (0:low, 1:normal, 2:high)
    :returns: written-bytes count.

    Example:
        >>> # Create Sequencer-Table:
        >>> repeats = [ 1, 1, 100, 4, 1 ]
        >>> seg_nb = [ 2, 3, 5, 1, 4 ]
        >>> jump = [ 0, 0, 1, 0, 0 ]
        >>> sequencer_table = zip(repeats, seg_nb, jump)
        >>>
        >>> # Select sequence no. 1:
        >>>  _ = vi.ask(':SEQ:SELect 1; *OPC?')
        >>>
        >>> # Download the sequencer-table:
        >>> pyte.download_sequencer_table(vi, sequencer_table)

    '''
    try:
        tbl_len = len(seq_table)
    except:
        seq_table = list(seq_table)
        tbl_len = len(seq_table)
    s = struct.Struct('< L H B x')
    s_size = s.size
    m = np.empty(s_size * tbl_len, dtype='uint8')
    for n in range(tbl_len):
        repeats, seg_nb, jump_flag = seq_table[n]
        s.pack_into(m, n * s_size, np.uint32(repeats), np.uint16(seg_nb), np.uint8(jump_flag))

    return download_binary_data(vi, pref, m, m.nbytes, paranoia_level=paranoia_level)

def download_adv_seq_table(vi, adv_seq_table, pref=':ASEQ:DATA', paranoia_level=1):
    '''Download Advanced-Sequencer-Table to Instrument

    The advanced-sequencer-table, `adv_seq_table`, is a list of 3-tuples
    of the form: (<repeats>, <sequence no.>, <jump-flag>)

    :param vi: `pyvisa` instrument.
    :param seq_table: the sequencer-table (list of 3-tuples)
    :param pref: the binary-data-header prefix.
    :param paranoia_level: paranoia-level (0:low, 1:normal, 2:high)
    :returns: vwritten-bytes count.

    Example:
        >>> # Create advanced-sequencer table:
        >>> repeats = [ 1, 1, 100, 4, 1 ]
        >>> seq_nb = [ 2, 3, 5, 1, 4 ]
        >>> jump = [ 0, 0, 1, 0, 0 ]
        >>> adv_sequencer_table = zip(repeats, seq_nb, jump)
        >>>
        >>> # Download it to instrument
        >>> pyte.download_adv_seq_table(vi, adv_sequencer_table)
    '''
    try:
        tbl_len = len(adv_seq_table)
    except:
        adv_seq_table = list(adv_seq_table)
        tbl_len = len(adv_seq_table)
    s = struct.Struct('< L H B x')
    s_size = s.size
    m = np.empty(s_size * tbl_len, dtype='uint8')
    for n in range(tbl_len):
        repeats, seq_nb, jump_flag = adv_seq_table[n]
        s.pack_into(m, n * s_size, np.uint32(repeats), np.uint16(seq_nb), np.uint8(jump_flag))

    return download_binary_data(vi, pref, m, m.nbytes, paranoia_level=paranoia_level)

def download_fast_pattern_table(vi, patt_table, pref=':PATT:COMP:FAST:DATA', paranoia_level=1):
    '''Download Fast (Piecewise-flat) Pulse-Pattern Table  to Instrument

    The pattern-table, `patt_table`, is a list of 2-tuples
    of the form: (<voltage-level (volt)>, <dwell-time (sec)>)

    :param vi: `pyvisa` instrument.
    :param patt_table: the pattern-table (list of 2-tuples)
    :param pref: the binary-data-header prefix.
    :param paranoia_level: paranoia-level (0:low, 1:normal, 2:high)
    :returns: written-bytes count.

    Note:
        In order to avoid Settings-Conflict make sure you can find
        a valid sampling-rate, `sclk`, such that the length in points
        of each dwell-time, `dwell-time*sclk` is integral number, and
        the total length in points is divisible by the segment-quantum
        (either 16 or 32 depending on the instrument model).
        Optionally set the point-time-resolution manually to `1/sclk`.

    Example:
        >>> import pyte
        >>> vi = pyte.open_session('192.168.0.170')
        >>>
        >>> # Create fast-pulse pattern table:
        >>> volt_levels = [0.0 , 0.1 , 0.5 , 0.1 , -0.1, -0.5, -0.1, -0.05]
        >>> dwel_times =  [1e-9, 1e-6, 1e-9, 1e-6, 1e-6, 1e-9, 1e-6, 5e-9 ]
        >>> pattern_table = zip(volt_levels, dwel_times)
        >>>
        >>> # Set Function-Mode=Pattern, Pattern-Mode=Composer, Pattern-Type=Fast:
        >>> _ = vi.ask(':FUNC:MODE PATT; :PATT:MODE COMP; :PATT:COMP:TRAN:TYPE FAST; *OPC?')
        >>>
        >>> # Optionally set User-Defined (rather than Auto) point sampling time:
        >>> _ = vi.ask(':PATT:COMP:RES:TYPE USER; :PATT:COMP:RES 0.5e-9; *OPC?')
        >>>
        >>> # Download the pattern-table to instrument:
        >>> pyte.download_fast_pattern_table(vi, pattern_table)
        >>>
        >>> vi.close()
    '''
    try:
        tbl_len = len(patt_table)
    except:
        patt_table = list(patt_table)
        tbl_len = len(patt_table)
    s = struct.Struct('< f d')
    s_size = s.size
    m = np.empty(s_size * tbl_len, dtype='uint8')
    for n in range(tbl_len):
        volt_level, dwel_time = patt_table[n]
        volt_level = float(volt_level)
        dwel_time = float(dwel_time)
        s.pack_into(m, n * s_size, volt_level, dwel_time)

    return download_binary_data(vi, pref, m, m.nbytes, paranoia_level=paranoia_level)

def download_linear_pattern_table(vi, patt_table, start_level, pref=':PATT:COMP:LIN:DATA', paranoia_level=1):
    '''Download Piecewise-Linear Pulse-Pattern to Instrument

    The pattern-table, `patt_table`, is a list of 2-tuples
    of the form: (<voltage-level (volt)>, <dwell-time (sec)>).

    Here the `vlotage-level` is the section's end-level.
    The section's start-lavel is the previous-section's end-level.
    The argument `start_level` is the first-section's start-level.

    :param vi: `pyvisa` instrument.
    :param patt_table: the pattern-table (list of 2-tuples)
    :param start_level: the (first-section's) start voltage level.
    :param pref: the binary-data-header prefix.
    :param paranoia_level: paranoia-level (0:low, 1:normal, 2:high)
    :returns: written-bytes count.

    Note:
        In order to avoid Settings-Conflict make sure you can find
        a valid sampling-rate, `sclk`, such that the length in points
        of each dwell-time, `dwell-time` * `sclk` is integral number, and
        the total length in points is divisible by the segment-quantum
        (either 16 or 32 depending on the instrument model).
        Optionally set the point-time-resolution manually to `1/sclk`.

    Example:
        >>> import pyte
        >>> vi = pyte.open_session('192.168.0.170')
        >>>
        >>> # Create fast-pulse pattern table:
        >>> start_level = 0.0
        >>> volt_levels = [0.1 , 0.1 , 0.5 , 0.1 , -0.1, -0.1, -0.5, -0.1, 0.0  ]
        >>> dwel_times  = [1e-9, 1e-6, 1e-9, 1e-6, 4e-9, 1e-6, 1e-9, 1e-6, 1e-9 ]
        >>> pattern_table = zip(volt_levels, dwel_times)
        >>>
        >>> # Set Function-Mode=Pattern, Pattern-Mode=Composer, Pattern-Type=Linear:
        >>> _ = vi.ask(':FUNC:MODE PATT; :PATT:MODE COMP; :PATT:COMP:TRAN:TYPE LIN; *OPC?')
        >>>
        >>> # Optionally set User-Defined (rather than Auto) point sampling time:
        >>> _ = vi.ask(':PATT:COMP:RES:TYPE USER; :PATT:COMP:RES 0.5e-9; *OPC?')
        >>>
        >>> # Download the pattern-table to instrument:
        >>> pyte.download_linear_pattern_table(vi, pattern_table, start_level)
        >>>
        >>> vi.close()
    '''
    try:
        tbl_len = len(patt_table)
    except:
        patt_table = list(patt_table)
        tbl_len = len(patt_table)
    s = struct.Struct('< f d')
    s_size = s.size
    m = np.empty(s_size * tbl_len, dtype='uint8')
    for n in range(tbl_len):
        volt_level, dwel_time = patt_table[n]
        volt_level = float(volt_level)
        dwel_time = float(dwel_time)
        s.pack_into(m, n * s_size, volt_level, dwel_time)

    if start_level is not None:
        start_level = float(start_level)
        _ = vi.ask(':PATT:COMP:LIN:STARt {0:f}; *OPC?'.format(start_level))

    return download_binary_data(vi, pref, m, m.nbytes, paranoia_level=paranoia_level)

def build_sine_wave(cycle_len, num_cycles=1, phase_degree=0, low_level=0, high_level=2**14-1, dac_min=0, dac_max=2**14-1):
    '''Build Sine Wave

    :param cycle_len: cycle length (in points).
    :param num_cycles: number of cycles.
    :param phase_degree: starting-phase (in degrees)
    :param low_level: the sine low level.
    :param high_level: the sine high level.
    :param dac_min: DAC minimal value.
    :param dac_max: DAC maximal value.
    :returns: `numpy.array` with the wave data (DAC values)

    '''

    cycle_len = int(cycle_len)
    num_cycles = int(num_cycles)

    if cycle_len <= 0 or num_cycles <= 0:
        return None

    wav_len = cycle_len * num_cycles

    phase = float(phase_degree) * math.pi / 180.0
    x = np.linspace(start=phase, stop=phase+2*math.pi, num=cycle_len, endpoint=False)

    zero_val = (low_level + high_level) / 2.0
    amplitude = (high_level - low_level) / 2.0
    y = np.sin(x) * amplitude + zero_val
    y = np.round(y)
    y = np.clip(y, dac_min, dac_max)

    y = y.astype(np.uint16)

    wav = np.empty(wav_len, dtype=np.uint16)
    for n in range(num_cycles):
        wav[n * cycle_len : (n + 1) * cycle_len] = y

    return wav

def build_triangle_wave(cycle_len, num_cycles=1, phase_degree=0, low_level=0, high_level=2**14-1, dac_min=0, dac_max=2**14-1):
    '''Build Triangle Wave

    :param cycle_len: cycle length (in points).
    :param num_cycles: number of cycles.
    :param phase_degree: starting-phase (in degrees)
    :param low_level: the triangle low level.
    :param high_level: the triangle high level.
    :param dac_min: DAC minimal value.
    :param dac_max: DAC maximal value.
    :returns: `numpy.array` with the wave data (DAC values)

    '''

    cycle_len = int(cycle_len)
    num_cycles = int(num_cycles)

    if cycle_len <= 0 or num_cycles <= 0:
        return None

    wav_len = cycle_len * num_cycles

    phase = float(phase_degree) * math.pi / 180.0
    x = np.linspace(start=phase, stop=phase+2*math.pi, num=cycle_len, endpoint=False)

    zero_val = (low_level + high_level) / 2.0
    amplitude = (high_level - low_level) / 2.0
    y = np.sin(x)
    y = np.arcsin(y) * 2 * amplitude / math.pi + zero_val
    y = np.round(y)
    y = np.clip(y, dac_min, dac_max)

    y = y.astype(np.uint16)

    wav = np.empty(wav_len, dtype=np.uint16)
    for n in range(num_cycles):
        wav[n * cycle_len : (n + 1) * cycle_len] = y

    return wav

def build_square_wave(cycle_len, num_cycles=1, duty_cycle=50.0, phase_degree=0, low_level=0, high_level=2**14-1, dac_min=0, dac_max=2**14-1):
    '''Build Square Wave

    :param cycle_len: cycle length (in points).
    :param num_cycles: number of cycles.
    :param duty_cycle: duty-cycle (between 0% and 100%)
    :param phase_degree: starting-phase (in degrees)
    :param low_level: the triangle low level.
    :param high_level: the triangle high level.
    :param dac_min: DAC minimal value.
    :param dac_max: DAC maximal value.
    :returns: `numpy.array` with the wave data (DAC values)

    '''

    cycle_len = int(cycle_len)
    num_cycles = int(num_cycles)

    if cycle_len <= 0 or num_cycles <= 0:
        return None

    wav_len = cycle_len * num_cycles

    duty_cycle = np.clip(duty_cycle, 0.0, 100.0)
    low_level = np.clip(low_level, dac_min, dac_max)
    high_level = np.clip(high_level, dac_min, dac_max)

    phase = float(phase_degree) * math.pi / 180.0
    x = np.linspace(start=phase, stop=phase+2*math.pi, num=cycle_len, endpoint=False)
    x = x <= 2 * math.pi * duty_cycle / 100.0
    y = np.full(x.shape, low_level)
    y[x] = high_level

    y = y.astype(np.uint16)

    wav = np.empty(wav_len, dtype=np.uint16)
    for n in range(num_cycles):
        wav[n * cycle_len : (n + 1) * cycle_len] = y

    return wav

def add_markers(dat_buff, marker_pos, marker_width, marker_bit1, marker_bit2, dat_offs=0, dat_len=None):
    """Add markers bits to the wave-data in the given buffer.

    Note that in case of 4-channels devices, the markers bits
    are both added to the 1st channel of each channels-pair.

    IMPORTANT: This function currently fits only 4-channels devices (WX2184 / WX1284).

    :param dat_buff: `numpy` array containing the wave-data (data-type='uint16')
    :param marker_pos: the marker start-position within the wave-data (in wave-points)
    :param marker_width: the marker width (in wave-points).
    :param marker_bit1: the value of 1st marker's bit (zero or one)
    :param marker_bit2: the value of 2nd marker's bit (zero or one)
    :param dat_offs: the offset of the wave-data within the data-buffer (default: 0).
    :param dat_len: the length of the actual wave-data (default: the length of `dat_buff`).
    """

    shift_pts = 12

    if dat_len is None:
        dat_len = len(dat_buff) - dat_offs

    if len(dat_buff) > 0 and dat_len > 0 and marker_width > 0:

        marker_bits = 0
        if marker_bit1:
            marker_bits |= 0x4000
        if marker_bit2:
            marker_bits |= 0x8000

        assert(marker_pos % 2 == 0)
        assert(marker_width % 2 == 0)
        assert(dat_len % 16 == 0 and dat_len >= 16)

        seg_pos = (marker_pos + shift_pts) % dat_len
        seg_pos = (seg_pos//16)*16 + 8 + (seg_pos%16)//2

        while marker_width > 0:
            if seg_pos >= dat_len:
                seg_pos = 8

            buf_index = (dat_offs + seg_pos) % len(dat_buff)
            dat_buff[buf_index] &= 0x3fff
            dat_buff[buf_index] |= marker_bits

            marker_width -= 2
            seg_pos += 1
            if seg_pos % 16 == 0:
                seg_pos += 8

def make_combined_wave(wav1, wav2, dest_array, dest_array_offset=0, add_idle_pts=False, quantum=16):
    '''Make 2-channels combined wave from the 2 given waves

    The destination-array, `dest_array`, is either a `numpy.array` with `dtype=uint16`, or `None`.
    If it is `None` then only the next destination-array's write-offset offset is calculated.

    Each of the given waves, `wav1` and `wav2`, is either a `numpy.array` with `dtype=uint16`, or `None`.
    If it is `None`, then the corresponding entries of `dest_array` are not changed.

    :param wav1: the DAC values of wave 1 (either `numpy.array` with `dtype=uint16`, or `None`).
    :param wav2: the DAC values of wave 2 (either `numpy.array` with `dtype=uint16`, or `None`).
    :param dest_array: the destination-array (either `numpy.array` with `dtype=uint16`, or `None`).
    :param dest_array_offset: the destination-array's write-offset.
    :param add_idle_pts: should add idle-points (segment-prefix)?
    :param quantum: the combined-wave quantum (usually 16 points)
    :returns: the next destination-array's write-offset offset.
    '''
    len1, len2 = 0,0
    if wav1 is not None:
        len1 = len(wav1)

    if wav2 is not None:
        len2 = len(wav2)

    wav_len = max(len1, len2)
    if 0 == wav_len:
        return dest_array_offset

    if wav_len % quantum != 0:
        wav_len = wav_len + (quantum - wav_len % quantum)

    tot_len = 2 * wav_len
    if add_idle_pts:
        tot_len = tot_len + 2 * quantum

    if dest_array is None:
        return dest_array_offset + tot_len

    dest_len = len(dest_array)

    if min(quantum, len2) > 0:
        rd_offs = 0
        wr_offs = dest_array_offset
        if add_idle_pts:
            wr_offs = wr_offs + 2 * quantum

        while rd_offs < len2 and wr_offs < dest_len:
            chunk_len = min((quantum, len2 - rd_offs, dest_len - wr_offs))
            dest_array[wr_offs : wr_offs + chunk_len] = wav2[rd_offs : rd_offs + chunk_len]
            rd_offs = rd_offs + chunk_len
            wr_offs = wr_offs + chunk_len + quantum

        if add_idle_pts:
            rd_offs = 0
            wr_offs = dest_array_offset
            chunk_len = min(quantum, dest_len - wr_offs)
            if chunk_len > 0:
                dest_array[wr_offs : wr_offs + chunk_len] = wav2[0]

    if min(quantum, len1) > 0:
        rd_offs = 0
        wr_offs = dest_array_offset + quantum
        if add_idle_pts:
            wr_offs = wr_offs + 2 * quantum

        while rd_offs < len1 and wr_offs < dest_len:
            chunk_len = min((quantum, len1 - rd_offs, dest_len - wr_offs))
            dest_array[wr_offs : wr_offs + chunk_len] = wav1[rd_offs : rd_offs + chunk_len]
            rd_offs = rd_offs + chunk_len
            wr_offs = wr_offs + chunk_len + quantum

        if add_idle_pts:
            rd_offs = 0
            wr_offs = dest_array_offset + quantum
            chunk_len = min(quantum, dest_len - wr_offs)
            if chunk_len > 0:
                dest_array[wr_offs : wr_offs + chunk_len] = wav1[0]

    return dest_array_offset + tot_len





