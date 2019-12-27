#!/usr/bin/env python
from BaseDriver import LabberDriver, Error
import zhinst
import zhinst.utils

import numpy as np
import textwrap
import time

# define API version
ZI_API = 6


class Driver(LabberDriver):
    """ This class implements a Labber driver"""

    def performOpen(self, options={}):
        """Perform the operation of opening the instrument connection"""

        # connect, either through name or by autodetecting
        if self.comCfg.address == '<autodetect>':
            self.daq = zhinst.utils.autoConnect(api_level=ZI_API)
            self.device = zhinst.utils.autoDetect(self.daq)
        else:
            (self.daq, self.device, _) = zhinst.utils.create_api_session(
                self.comCfg.address, ZI_API, required_devtype='HDAWG',
                required_err_msg='This driver requires a HDAWG')
        # keep track of node datatypes
        self._node_datatypes = dict()
        self.n_ch = 8
        self.waveform_updated = [False] * self.n_ch
        self.buffer_sizes = [0] * 4
        self.log('Connected', self.device)

    def performClose(self, bError=False, options={}):
        """Perform the close instrument connection operation"""
        # do not check for error if close was called with an error
        try:
            base = '/%s/awgs/0/' % self.device
            self.daq.setInt(base + 'enable', 0)
        except Exception:
            # never return error here
            pass


    def initSetConfig(self):
        """This function is run before setting values in Set Config"""
        # clear waveforms
        for n in range(self.n_ch):
            self.setValue('AWG%d - Waveform' % (n + 1), [])


    def performSetValue(self, quant, value, sweepRate=0.0, options={}):
        """Perform the Set Value instrument operation. This function should
        return the actual value set by the instrument"""
        # keep track of updated waveforms
        if self.isFirstCall(options):
            self.waveform_updated = [False] * self.n_ch
            self.update_sequencer = False
        # update value, necessary since we later use getValue to get config
        quant.setValue(value)

        if quant.get_cmd != '':
            # set node parameters
            value = self._set_node_value(quant, value)
        elif quant.name.endswith(' - Waveform'):
            # mark waveform as updated
            awg = int(quant.name[3]) - 1
            self.waveform_updated[awg] = True

        # check if sequencer need to be re-compiled
        if (quant.name == 'Channel grouping' or
                quant.name.find('Enable AWG') >= 0 or
                quant.name.startswith('Run mode') or
                quant.name.startswith('Trig period') or
                quant.name.startswith('Buffer length')):
            self.update_sequencer = True

        # if final call, make sure instrument is synced before returning
        if self.isFinalCall(options):
            if self.update_sequencer:
                self._configure_sequencer()
                # after configuring sequencer, all waveforms must be uploaded
                self.waveform_updated = [True] * self.n_ch

            if np.any(self.waveform_updated):
                self._upload_waveforms(self.waveform_updated)
            self.daq.sync()
        return value


    def performGetValue(self, quant, options={}):
        """Perform the Set Value instrument operation. This function should
        return the actual value set by the instrument"""
        if quant.get_cmd != '':
            value = self._get_node_value(quant)
        else:
            # for all others, return local value
            value = quant.getValue()
        return value


    def _map_awg_to_channel(self):
        """Create map between AWGs in use and corresponding output channels"""
        self.awg_in_use = [False] * self.n_ch
        self.awg_to_ch = [[] for n in range(self.n_ch)]
        for ch in range(self.n_ch):
            (d, r) = divmod(ch, 2)
            for m in range(2):
                awg = d * 2 + m
                on = self.getValue('Ch%d - Enable AWG %d' % (ch + 1, awg + 1))
                if on:
                    self.awg_in_use[awg] = True
                    self.awg_to_ch[awg].append(ch)


    def _configure_sequencer(self, group=1, buffer_size=None):
        """Configure sequencer and upload program for given group"""
        # currently only supports one AWG group
        if self.getValue('Channel grouping') != '1 x 8':
            raise Error('Driver currently only support 1x8 channel group mode')

        self._map_awg_to_channel()
        # create waveforms, one per channel
        awg_program = ''.join(
            ['wave w%d = zeros(_n_);\n' % (n + 1) for n in range(self.n_ch)])

        # create list of link between AWGs and channel outputs
        x = []
        for awg, in_use in enumerate(self.awg_in_use):
            if in_use:
                # awg in use, create string for playing wave
                y = ','.join([('%d' % (ch + 1)) for ch in self.awg_to_ch[awg]])
                y += ', w%d' % (awg + 1)
                x.append(y)
            else:
                # not in use, still add to corresponding channel, will be empty
                x.append('%d, w%d' % (awg + 1, awg + 1))
        channels = ', '.join(x)
        self.log(channels)

        # check version of API
        new_style = hasattr(self.daq, 'setVector')
        # proceed depending on run mode
        run_mode = self.getValue('Run mode, group %d' % group)
        # in internal trigger mode, make buffer as long as trig interval
        if run_mode == 'Internal trigger':
            trig_period = self.getValue('Trig period, group %d' % group)
            sampling_rate = 2.4E9 / (
                2 ** self.getValueIndex('Sampling rate, group %d' % group))
            # timing changed for new API version
            if new_style:
                # new style - large delays
                buffer_size = int(round((trig_period - 30E-9 - 3.9E-6) * sampling_rate))
                # wait time is in units of 10/3 ns
                wait_time = int(round(3 * (30E-9 / 10E-9)))
                # remove a few clock cycles to account for while/wait time
                wait_time -= 7
                awg_program += textwrap.dedent("""\
                    setUserReg(0, 0);
                    while(true){
                        while(getUserReg(0) == 0){
                            playWave(%s);
                            waitWave();
                            wait(%d);
                        }
                    }""") % (channels, wait_time)
            else:
                buffer_size = int(round(trig_period * sampling_rate))
                # wait time is in units of 10/3 ns
                wait_time = int(round(3 * (trig_period / 10E-9)))
                # remove a few clock cycles to account for while/wait time
                wait_time -= 7
                awg_program += textwrap.dedent("""\
                    setUserReg(0, 0);
                    while(true){
                        while(getUserReg(0) == 0){
                            playWave(%s);
                            wait(%d);
                        }
                    }""") % (channels, wait_time)

            # limit to max memory of unit
            buffer_size = min(buffer_size, 64E6)
            awg_program = awg_program.replace('_n_', ('%d' % buffer_size))

        elif run_mode == 'External trigger':
            buffer_length = self.getValue('Buffer length, group %d' % group)
            sampling_rate = 2.4E9 / (
                2 ** self.getValueIndex('Sampling rate, group %d' % group))
            buffer_size = int(round(buffer_length * sampling_rate))
            # limit to max memory of unit
            buffer_size = min(buffer_size, 64E6)

            awg_program += textwrap.dedent("""\
                setUserReg(0, 0);
                while(true){
                    waitDigTrigger(1);
                    playWave(%s);
                }""") % (channels)
            # the code below trigs faster, but only works for <400 ns waveforms
            # setUserReg(0, 0);
            # while(true){
            #     playWaveDigTrigger(1, %s);

            awg_program = awg_program.replace('_n_', ('%d' % buffer_size))

        # keep track of buffer size
        self.buffer_sizes[group - 1] = buffer_size
        # stop current AWG
        base = '/%s/awgs/0/' % self.device
        self.daq.setInt(base + 'enable', 0)
        # compile and upload
        self._upload_awg_program(awg_program)

        # set to single-shot mode and enable
        self.daq.setInt(base + 'single', 1)
        self.daq.setInt(base + 'enable', 1)

        # # proceed depending on channel grouping
        # if self.getValue('Channel grouping') in ('1 x 8', 'MDS'):
        #     pass
        # elif self.getValue('Channel grouping') == '4 x 2':
        #     pass
        # elif self.getValue('Channel grouping') == '2 x 4':
        #     pass


    def _upload_waveforms(self, awg_updated=None):
        """Upload all waveforms to device"""
        # check version of API
        new_style = hasattr(self.daq, 'setVector')
        # get updated channels
        if awg_updated is None:
            awg_updated = [True] * self.n_ch

        # upload waveforms pairwise
        for ch in range(0, self.n_ch, 2):
            # upload if one or both waveforms are updated
            if awg_updated[ch] or awg_updated[ch + 1]:
                # get waveform data
                if self.awg_in_use[ch]:
                    x1 = self.getValueArray('AWG%d - Waveform' % (ch + 1))
                else:
                    # upload a small empty waveform
                    x1 = np.zeros(100)
                if self.awg_in_use[ch + 1]:
                    x2 = self.getValueArray('AWG%d - Waveform' % (ch + 2))
                else:
                    # upload a small empty waveform
                    x2 = np.zeros(100)

                # upload interleaved data
                (core, ch_core) = divmod(ch, 2)
                if new_style:
                    # in the new style, waveform must match buffer size
                    n = self.buffer_sizes[0]
                else:
                    n = max(len(x1), len(x2))
                data = np.zeros((n, 2))
                data[:len(x1), 0] = x1
                data[:len(x2), 1] = x2
                base = '/%s/awgs/%d/' % (self.device, core)

                # check old or new-style uploads
                if new_style:
                    # new-style call
                    data_zh = zhinst.utils.convert_awg_waveform(data.flatten())
                    self.daq.setVector(
                        base + 'waveform/waves/0', data_zh)
                else:
                    # old-style call
                    self.daq.setInt(base + 'waveform/index', 0)
                    self.daq.sync()
                    self.daq.vectorWrite(
                        base + 'waveform/data', data.flatten())

                # set enabled
                self.daq.setInt(base + 'enable', 1)


    def _upload_awg_program(self, awg_program, core=0):
        # Transfer the AWG sequence program. Compilation starts automatically.
        # Create an instance of the AWG Module
        awgModule = self.daq.awgModule()
        awgModule.set('awgModule/device', self.device)
        awgModule.set('awgModule/index', int(core))
        awgModule.execute()
        awgModule.set('awgModule/compiler/sourcestring', awg_program)
        while awgModule.getInt('awgModule/compiler/status') == -1:
            time.sleep(0.1)
            if self.isStopped():
                return

        if awgModule.getInt('awgModule/compiler/status') == 1:
            # compilation failed, raise an exception
            raise Error(
                'Upload failed:\n' +
                awgModule.getString('awgModule/compiler/statusstring'))

        if awgModule.getInt('awgModule/compiler/status') == 2:
            self.log(
                "Compiler warning: ",
                awgModule.getString('awgModule/compiler/statusstring'))

        # Wait for the waveform upload to finish
        time.sleep(0.1)
        while ((awgModule.getDouble('awgModule/progress') < 1.0) and
                (awgModule.getInt('awgModule/elf/status') != 1)):
            time.sleep(0.1)
            if self.isStopped():
                return

        if awgModule.getInt('awgModule/elf/status') == 1:
            raise Error("Uploading the AWG program failed.")


    def _get_node_value(self, quant):
        """Get instrument value using ZI node hierarchy"""
        # get node definition
        node = self._get_node(quant)
        dtype = self._get_node_datatype(node)
        # read data from ZI
        d = self.daq.get(node, True)
        if len(d) == 0:
            raise Error('No value defined at node %s.' % node)
        # extract and return data
        data = next(iter(d.values()))
        # if returning dict, strip timing information (API level 6)
        if isinstance(data, dict) and 'value' in data:
            data = data['value']
        value = dtype(data[0])

        # convert to index for combo datatypes
        if quant.datatype == quant.COMBO:
            # if no command options are given, use index
            if len(quant.cmd_def) == 0:
                cmd_options = list(range(len(quant.combo_defs)))
            else:
                # convert option list to correct datatype
                cmd_options = [dtype(x) for x in quant.cmd_def]

            # look for correct option
            try:
                index = cmd_options.index(value)
                value = quant.combo_defs[index]
            except Exception:
                raise Error(
                    'Invalid value %s for quantity %s, should be one of %s.' %
                    (str(value), quant.name, str(cmd_options)))

        self.log('Get value', quant.name, node, data, value)
        return value


    def _set_node_value(self, quant, value):
        """Set value of quantity using ZI node hierarchy"""
        # get node definition and datatype
        node = self._get_node(quant)
        dtype = self._get_node_datatype(node)

        # special case for combo box items
        if quant.datatype == quant.COMBO:
            index = quant.getValueIndex(value)
            # if no command items are given, send index
            if len(quant.cmd_def) == 0:
                self._set_parameter(node, index)
            # if command options are given, check data type
            else:
                str_value = quant.cmd_def[index]
                self._set_parameter(node, dtype(str_value))

        # standard datatype, just send to instruments
        else:
            self._set_parameter(node, dtype(value))

        # read actual value set by the instrument
        # value = self._get_node_value(quant)
        return value


    def _set_parameter(self, node, value):
        """Set value for given node"""
        if isinstance(value, float):
            # self.daq.setDouble(node, value)
            self.daq.asyncSetDouble(node, value)
        elif isinstance(value, int):
            # self.daq.setInt(node, value)
            self.daq.asyncSetInt(node, value)
        elif isinstance(value, str):
            # self.daq.setString(node, value)
            self.daq.asyncSetString(node, value)
        elif isinstance(value, complex):
            self.daq.setComplex(node, value)


    def _get_node(self, quant):
        """Get node string for quantity"""
        return '/' + self.device + quant.get_cmd


    def _get_node_datatype(self, node):
        """Get datatype for object at node"""
        # used cached value, if available
        if node in self._node_datatypes:
            return self._node_datatypes[node]
        # find datatype from returned data
        d = self.daq.get(node, True)
        if len(d) == 0:
            raise Error('No value defined at node %s.' % node)

        data = next(iter(d.values()))
        # if returning dict, strip timing information (API level 6)
        if isinstance(data, dict) and 'value' in data:
            data = data['value']
        # get first item, if python list assume string
        if isinstance(data, list):
            dtype = str
        # not string, should be np array, check dtype
        elif data.dtype in (int, np.int_, np.int64, np.int32, np.int16):
            dtype = int
        elif data.dtype in (float, np.float_, np.float64, np.float32):
            dtype = float
        elif data.dtype in (complex, np.complex_, np.complex64, np.complex128):
            dtype = complex
        else:
            raise Error('Undefined datatype for node %s.' % node)

        # keep track of datatype for future use
        self._node_datatypes[node] = dtype
        self.log('Datatype:', node, dtype)
        return dtype

if __name__ == '__main__':
    pass
