"""
file: class for interfacing with R&S FSV signal analyzer
author: rueck.joshua@gmail.com
last updated: 10/07/2024
"""

import instrument
import tags
from time import sleep
from PIL import Image
import io
import os

class FSV(instrument.BaseInstrument):

    def __init__(self, visa_address):
        super().__init__(visa_address)
        self.stop_flag = False
        if self.connect('FSV'):
            self.instrument.write('SYST:DISP:UPD ON')
            self.disconnect()

    # set stop flag for interruption
    def stop_operation(self):
        self.stop_flag = True

    # check if stop flag has been set
    def check_stop(self):
        if self.stop_flag:
            raise InterruptedError('Measurement was stopped.')
        
    # reset
    def reset(self):
        if self.connect():
            self.instrument.write('*RST')
            sleep(1)
            self.disconnect()

    ### GENERAL PARAMETERS
    # set center frequency within limits specified by manual (up to 30 GHz)
    def set_center_freq(self, freq):
        if (freq > 0 and freq < 30000000000):
            if self.connect():
                self.instrument.write(f'SENS:FREQ:CENT {freq}')
                self.disconnect()
                tags.log('FSV', f'Center frequency set to {self.format_freq(freq)}')
        else:
            tags.log('FSV', 'Invalid frequency, not in range of FSV.')

    def set_center_freq_connected(self, freq):
        if (freq > 0 and freq < 30000000000):
            self.instrument.write(f'SENS:FREQ:CENT {freq}')
            tags.log('FSV', f'Center frequency set to {self.format_freq(freq)}')
        else:
            tags.log('FSV', 'Invalid frequency, not in range of FSV.')

    # set span (also up to 30 GHz)
    def set_span(self, freq):
        if (freq > 0 and freq < 30000000000):
            if self.connect():
                self.instrument.write(f'SENS:FREQ:SPAN {freq}')
                self.disconnect()
                tags.log('FSV', f'Span set to {self.format_freq(freq)}')
        else:
            tags.log('FSV', 'Invalid frequency, not in range of FSV.')

    def set_span_connected(self, freq):
        if (freq > 0 and freq < 30000000000):
            self.instrument.write(f'SENS:FREQ:SPAN {freq}')
            tags.log('FSV', f'Span set to {self.format_freq(freq)}')
        else:
            tags.log('FSV', 'Invalid frequency, not in range of FSV.')

    # adjust offset to reflect reference max e.r.p. as measured in SAC
    def adjust_erp(self, ref_value, centre_frequency, ocw, rbw):
        offset = 0

        ref_value = float(ref_value)

        try:

            if self.connect():
                self.set_center_freq_connected(centre_frequency)
                sleep(0.5)
                self.set_span_connected(6*ocw)
                sleep(0.5)
                self.set_rbw_connected(rbw)
                sleep(0.5)

                self.check_stop()

                self.instrument.write('CALC:MARK1:STAT ON')
                self.instrument.write('DISP:TRAC:MODE MAXH')
                sleep(3)
                self.instrument.write('CALC:MARK:MAX')
                level = float(self.instrument.query('CALC:MARK:Y?'))

                self.check_stop()

                if level < ref_value:
                    while level <= ref_value:
                        offset = offset+0.5
                        self.instrument.write(f'DISP:TRAC:Y:RLEV:OFFS {offset}')
                        sleep(3)
                        self.check_stop()
                        self.instrument.write('CALC:MARK:MAX')
                        level = float(self.instrument.query('CALC:MARK:Y?'))

                else:
                    while level >= ref_value:
                        offset = offset-0.5
                        self.instrument.write(f'DISP:TRAC:Y:RLEV:OFFS {offset}')
                        sleep(3)
                        self.check_stop()
                        self.instrument.write('CALC:MARK:MAX')
                        level = float(self.instrument.query('CALC:MARK:Y?'))
            
            tags.log('FSV', f"Reference level offset set to {offset} dB, current peak: {level}")

        except InterruptedError:
            self.disconnect()
            tags.log('FSV', 'Measurement interrupted.')
            return None
    
    # set FSV resolution bandwidth
    def set_rbw(self, rbw):
        if self.connect():
            self.instrument.write(f'SENS:BAND:RES {rbw}')
            self.disconnect()
            tags.log('FSV', f'RBW set to {self.format_freq(rbw)}.')

    def set_rbw_connected(self, rbw):
        self.instrument.write(f'SENS:BAND:RES {rbw}')
        tags.log('FSV', f'RBW set to {self.format_freq(rbw)}.')

    # set FSV video bandwidth
    def set_vbw_ratio(self, ratio):
        if self.connect():
            self.instrument.write(f'SENS:BAND:VID:RAT {ratio}')
            self.disconnect()
            tags.log('FSV', f'VBW set to {ratio}x RBW.')

    def set_vbw_ratio_connected(self, ratio):
        self.instrument.write(f'SENS:BAND:VID:RAT {ratio}')
        tags.log('FSV', f'VBW set to {ratio}x RBW.')

    # set trace mode of specific trace
    def set_trace_mode(self, trace_nr, trace_mode):
        valid_modes = ['write', 'view', 'average', 'maxhold', 'minhold', 'blank']
        if trace_mode not in valid_modes:
            raise ValueError(f'Invalid value for trace_mode. Expected one of {valid_modes}, got {trace_mode}')

        ### TODO: also check if trace number is valid
        if self.connect():
            self.instrument.write(f'DISP:TRAC{trace_nr}:MODE {trace_mode}')
            self.disconnect()
            tags.log('FSV', f'TRACE {trace_nr} set to mode {trace_mode}.')

    def set_trace_mode_connected(self, trace_nr, trace_mode):
        valid_modes = ['write', 'view', 'average', 'maxhold', 'minhold', 'blank']
        if trace_mode not in valid_modes:
            raise ValueError(f'Invalid value for trace_mode. Expected one of {valid_modes}, got {trace_mode}')

        ### TODO: also check if trace number is valid
        self.instrument.write(f'DISP:TRAC{trace_nr}:MODE {trace_mode}')
        tags.log('FSV', f'TRACE {trace_nr} set to mode {trace_mode}.')

    # set detector mode to specific values
    def set_det_mode(self, det_mode):
        valid_modes = ['apeak', 'negative', 'positive', 'sample', 'rms', 'average', 'qpeak']
        if det_mode not in valid_modes:
            raise ValueError(f'Invalid value for det_mode. Expected one of {valid_modes}, got {det_mode}')
        
        if self.connect():
            self.instrument.write(f'SENS:WIND:DET {det_mode}')
            self.disconnect()
            tags.log('FSV', f'Detector mode set to {det_mode}.')

    def set_det_mode_connected(self, det_mode):
        valid_modes = ['apeak', 'negative', 'positive', 'sample', 'rms', 'average', 'qpeak']
        if det_mode not in valid_modes:
            raise ValueError(f'Invalid value for det_mode. Expected one of {valid_modes}, got {det_mode}')
        
        self.instrument.write(f'SENS:WIND:DET {det_mode}')
        tags.log('FSV', f'Detector mode set to {det_mode}.')

    # show marker table true/false
    def show_mtable(self, visible):
        if self.connect():
            if visible:
                self.instrument.write("DISP:MTAB ON")
                tags.log('FSV', "Marker table turned on.")
            else:
                self.instrument.write("DISP:MTAB OFF")
                tags.log('FSV', "Marker table turned off.")
            self.disconnect()

    # take a screenshot and save it at a specified path
    def take_screenshot(self, filename, path):
        fsv_path = 'C:\\Documents and Settings\\instrument\\My Documents\\My Pictures\\screenshot.jpg'

        if self.connect():
            self.instrument.write('HCOP:DEV:LANG JPG')
            self.instrument.write('HCOP:DEST "MMEM"')
            self.instrument.write(f'MMEM:NAME "{fsv_path}"')
            self.instrument.write('HCOP')

            sleep(5)

            out = self.instrument.query_binary_values(f"MMEM:DATA? '{fsv_path}'", datatype='B')
            outData = bytearray(out)
            image = Image.open(io.BytesIO(outData))
            image.save(os.path.join(path.replace('/', '\\'), filename.replace(':', '-')))
            image.close()

            formatted_path = path.replace('/', '\\')
            tags.log('FSV', f"Screenshot saved under {os.path.join(formatted_path, filename.replace(':', '-'))}")

            self.disconnect()

    # take a screenshot in a process when connection already active
    def take_screenshot_connected(self, filename, path):
        fsv_path = 'C:\\Documents and Settings\\instrument\\My Documents\\My Pictures\\screenshot.jpg'

        self.instrument.write('HCOP:DEV:LANG JPG')
        self.instrument.write('HCOP:DEST "MMEM"')
        self.instrument.write(f'MMEM:NAME "{fsv_path}"')
        self.instrument.write('HCOP')

        sleep(5)

        out = self.instrument.query_binary_values(f"MMEM:DATA? '{fsv_path}'", datatype='B')
        outData = bytearray(out)
        image = Image.open(io.BytesIO(outData))
        image.save(os.path.join(path.replace('/', '\\'), filename.replace(':', '-')))
        image.close()

        formatted_path = path.replace('/', '\\')
        tags.log('FSV', f"Screenshot saved under {os.path.join(formatted_path, filename.replace(':', '-'))}")


    ### AUTOMATED TEST PROCEDURES
    # measure occupied bandwidth with FSV built-in functions
    def measure_obw(self, filename, path, center_frequency, obw_parameters):
        try:
            if self.connect():
                # prepare parameters
                self.set_center_freq_connected(center_frequency)
                sleep(0.5)
                self.set_span_connected(obw_parameters['span'])
                sleep(0.5)
                self.set_rbw_connected(obw_parameters['rbw'])
                sleep(0.5)

                self.check_stop()

                self.set_vbw_ratio_connected(obw_parameters['vbw_ratio'])
                sleep(0.5)
                self.set_trace_mode_connected(1, 'maxhold')
                sleep(1)
                self.set_trace_mode_connected(2, 'write')
                sleep(1)
                self.set_det_mode_connected(obw_parameters['det_mode'])      # BUG: for some reason trace 2 isn't affected by the detector mode change
                sleep(0.5)

                self.check_stop()

                # perform automated measurement
                self.instrument.write('CALC:MARK:FUNC:POW:SEL OBW')
                sleep(4)
                self.check_stop()
                obw = self.instrument.query('CALC:MARK:FUNC:POW:RES? OBW')
                tags.log('FSV', f'OBW measurement executed: {self.format_freq(str.strip(obw))}')
                self.take_screenshot_connected(filename, path)
                sleep(5)
                self.disconnect()
                return obw
            else:
                return None
            
        except InterruptedError:
            self.disconnect()
            tags.log('FSV', 'Measurement interrupted.')
            return None
        
    # setup instrument for OOB measurement
    def prep_oob_parameters(self, centre_freq, oob_parameters):
        try:
            if self.connect():
                # prepare parameters
                self.set_center_freq_connected(centre_freq)
                sleep(0.5)
                self.set_span_connected(oob_parameters['span'])
                sleep(0.5)
                self.set_rbw_connected(oob_parameters['rbw'])
                sleep(0.5)
                self.check_stop()
                self.set_trace_mode_connected(1, 'maxhold')
                sleep(0.5)
                self.set_trace_mode_connected(2, 'write')
                sleep(0.5)
                self.set_det_mode_connected(oob_parameters['det_mode'])

                self.disconnect()
        except InterruptedError:
            self.disconnect()
            tags.log('FSV', 'Measurement interrupted.')
            return None
    
        
    # measure out-of-band emissions for operating channel
    def measure_oob_oc(self, limit_points, filename, path):
        try:
            if self.connect():
                # clear lines and then define a new limit line
                self.instrument.write('CALC:LIM1:DEL')
                self.instrument.write('CALC:MARK:AOFF')
                self.instrument.write('CALC:LIM1:NAME "LIMIT"')
                self.instrument.write('CALC:LIM1:COMM "Upper Limit OOB"')
                self.instrument.write('CALC:LIM1:TRAC 1')
                self.instrument.write('CALC:LIM1:UNIT DBM')

                self.check_stop()
                sleep(1)

                # create the SCPI commands for populating the limit line with datapoints with the given list of points
                freq_cmd, dbm_cmd = self.create_limit_scpi_commands(limit_points)
                self.instrument.write(freq_cmd)
                self.instrument.write(dbm_cmd)

                self.check_stop()
                sleep(1)

                # adjust the offset in order to display limit line correctly and turn on the limit line
                self.instrument.write('DISP:TRAC:Y:RLEV 20dBm')
                self.instrument.write('CALC:LIM1:UPP:STAT ON')
                self.instrument.write('CALC:LIM1:STAT ON')

                tags.log('FSV', 'Limit line for operating channel added.')

                self.check_stop()
                sleep(3)

                # deploy markers to peaks surrounding operating channel, three to either side of operating channel
                left_oc_border = limit_points[1][0]
                right_oc_border = limit_points[4][0]

                for nr in range(1, 4):
                    self.instrument.write(f'CALC:MARK{nr} ON')
                    sleep(0.5)
                    self.instrument.write(f'CALC:MARK{nr}:X {left_oc_border if nr == 1 else self.instrument.query(f"CALC:MARK{nr-1}:X?")}')
                    sleep(0.5)
                    self.instrument.write(f'CALC:MARK{nr}:MAX:LEFT')
                    sleep(0.5)
                    self.check_stop()

                for nr in range (4, 7):
                    self.instrument.write(f'CALC:MARK{nr} ON')
                    sleep(0.5)
                    self.instrument.write(f'CALC:MARK{nr}:X {right_oc_border if nr == 4 else self.instrument.query(f"CALC:MARK{nr-1}:X?")}')
                    sleep(0.5)
                    self.instrument.write(f'CALC:MARK{nr}:MAX:RIGHT')
                    sleep(0.5)
                    self.check_stop()

                self.instrument.write('DISP:MTAB ON')

                tags.log('FSV', 'Markers added to out-of-band domain in operating channel measurement.')

                sleep(2)
                self.check_stop()

                # query limit check and then take a screenshot
                oc_fail = self.instrument.query('CALC:LIM1:FAIL?')
                self.take_screenshot_connected(filename, path)

                sleep(5)

                # disconnect from device
                self.disconnect()

                tags.log('FSV', f'Operating Channel OOB Test: {"PASS" if "0" in oc_fail else "FAIL"}')

                return '0' in oc_fail
            
        except InterruptedError:
            self.disconnect()
            tags.log('FSV', 'Measurement interrupted.')
            return None
        
    # measure out-of-band emissions for operational frequency band
    def measure_oob_ofb(self, limit_points, filename, path):
        try:
            if self.connect():

                # cleanup and then define a new limit line
                self.instrument.write('CALC:LIM1:DEL')
                self.instrument.write('CALC:MARK:AOFF')
                self.instrument.write('CALC:LIM1:NAME "LIMIT"')
                self.instrument.write('CALC:LIM1:COMM "Upper Limit OOB"')
                self.instrument.write('CALC:LIM1:TRAC 1')
                self.instrument.write('CALC:LIM1:UNIT DBM')

                self.check_stop()
                sleep(1)

                # create the SCPI commands for populating the limit line with datapoints with the given list of points
                freq_cmd, dbm_cmd = self.create_limit_scpi_commands(limit_points)
                self.instrument.write(freq_cmd)
                self.instrument.write(dbm_cmd)

                self.check_stop()
                sleep(1)

                # adjust the offset in order to display limit line correctly and turn on the limit line
                self.instrument.write('DISP:TRAC:Y:RLEV 20dBm')
                self.instrument.write('CALC:LIM1:UPP:STAT ON')  # turns on limit line
                self.instrument.write('CALC:LIM1:STAT ON')  # turns on limit check

                tags.log('FSV', 'Limit line for operational frequency band added.')

                self.check_stop()
                sleep(3)

                # deploy markers to peaks surrounding operational frequency band, three to either side of frequency band
                left_ofb_border = limit_points[2][0]
                right_ofb_border = limit_points[4][0]

                for nr in range(1, 4):
                    self.instrument.write(f'CALC:MARK{nr} ON')
                    sleep(0.5)
                    self.instrument.write(f'CALC:MARK{nr}:X {left_ofb_border if nr == 1 else self.instrument.query(f"CALC:MARK{nr-1}:X?")}')
                    sleep(0.5)
                    self.instrument.write(f'CALC:MARK:MAX{nr}:LEFT')
                    sleep(0.5)
                    self.check_stop()

                for nr in range (4, 7):
                    self.instrument.write(f'CALC:MARK{nr} ON')
                    sleep(0.5)
                    self.instrument.write(f'CALC:MARK{nr}:X {right_ofb_border if nr == 4 else self.instrument.query(f"CALC:MARK{nr-1}:X?")}')
                    sleep(0.5)
                    self.instrument.write(f'CALC:MARK:MAX{nr}:RIGHT')
                    sleep(0.5)
                    self.check_stop()

                self.instrument.write('DISP:MTAB ON')

                tags.log('FSV', 'Markers added to out-of-band domain in operational frequency band measurement.')

                ofb_fail = self.instrument.query('CALC:LIM1:FAIL?')

                self.check_stop()
                sleep(2)

                self.take_screenshot_connected(filename, path)

                self.check_stop()
                sleep(5)

                # execute measurements for lower and upper edge cases with different RBW
                # clear limit lines, set RBW and add threshold line according to standard
                self.instrument.write('CALC:LIM1:DEL')
                self.instrument.write('SENS:BAND:RES 10000')
                self.instrument.write('CALC:MARK:AOFF')

                self.instrument.write('CALC:LIM1:NAME "LIMIT: -36dB"')
                self.instrument.write('CALC:LIM1:COMM "Upper Limit OOB"')
                self.instrument.write('CALC:LIM1:TRAC 1')
                self.instrument.write('CALC:LIM1:UNIT DBM')

                self.check_stop()

                freq_cmd, dbm_cmd = self.create_limit_scpi_commands([(left_ofb_border-4000000, -36), (right_ofb_border+4000000, -36)])
                self.instrument.write(freq_cmd)
                self.instrument.write(dbm_cmd)

                self.instrument.write('CALC:LIM1:UPP:STAT ON')  # turns on limit line
                self.instrument.write('CALC:LIM1:STAT ON')  # turns on limit check

                ### TODO: Centre frequency und span nach Standard anpassen (Table 17)

                # move displayed spectrum to lower edge case and take a screenshot
                self.instrument.write(f'SENS:FREQ:STAR {left_ofb_border-4000000}')  # 4 MHz down from left border
                self.instrument.write(f'SENS:FREQ:STOP {left_ofb_border}')

                for nr in range(1, 4):
                    self.instrument.write(f'CALC:MARK{nr} ON')
                    sleep(0.5)
                    self.instrument.write(f'CALC:MARK{nr}:MAX:NEXT')
                    sleep(0.5)
                    self.check_stop()

                tags.log('FSV', 'Measurement for lower spurious domain concluded.')

                sleep(2)
                self.check_stop()
                self.take_screenshot_connected(filename.replace('center', 'left'), path)
                sleep(5)

                # move displayed spectrum to upper edge case and take a screenshot
                self.instrument.write(f'SENS:FREQ:STAR {right_ofb_border}')  # 4 MHz up from right border
                self.instrument.write(f'SENS:FREQ:STOP {right_ofb_border+4000000}')

                self.instrument.write('CALC:MARK:AOFF')

                for nr in range(1, 4):
                    self.instrument.write(f'CALC:MARK{nr} ON')
                    sleep(0.5)
                    self.instrument.write(f'CALC:MARK{nr}:MAX:NEXT')
                    sleep(0.5)
                    self.check_stop()

                tags.log('FSV', 'Measurement for upper spurious domain concluded.')

                sleep(2)
                self.check_stop()
                self.take_screenshot_connected(filename.replace('center', 'right'), path)
                sleep(5)

                # cleanup
                self.instrument.write('CALC:LIM1:DEL')
                self.instrument.write('CALC:MARK:AOFF')
                self.instrument.write('DISP:MTAB OFF')

                # query limit check from device and then disconnect
                self.disconnect()

                tags.log('FSV', f"Operational Frequency Band OOB Test: {'PASS' if '0' in ofb_fail else 'FAIL'}")

                return '0' in ofb_fail
            
        except InterruptedError:
            self.disconnect()
            tags.log('FSV', 'Measurement interrupted.')
            return None


    ### HELPER FUNCTIONS
    # format frequency, takes a frequency number and returns a string with appropriate unit (kHz, MHz, GHz)
    def format_freq(self, freq):
        try:
            freq = float(freq)
        except ValueError:
            raise ValueError(f"Invalid frequency value: {freq}")

        if float(freq) / 10**9 > 1.0:
            return str(round(float(freq)/10**9, 3)) + ' GHz'
        elif float(freq) / 10**6 > 1.0:
            return str(round(float(freq/10**6), 3)) + ' MHz'
        elif float(freq) / 10**3 > 1.0:
            return str(round(float(freq/10**3),3)) + ' kHz'
        else:
            return f'{freq} Hz'

    # create SCPI commands for populating limit line data points
    def create_limit_scpi_commands(self, points):
        freq_points = ",".join(f"{freq} Hz" for freq, _ in points)
        scpi_freq_command = f"CALC:LIM1:CONT {freq_points}"
        
        dbm_values = ",".join(f"{dbm}" for _, dbm in points)
        scpi_dbm_command = f"CALC:LIM1:UPP {dbm_values}"
        
        return scpi_freq_command, scpi_dbm_command