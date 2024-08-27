"""
file: main file for OBW and OOB measurement automation in the context of EN 300 220-1
author: rueck.joshua@gmail.com
last updated: 27/08/2024
"""

import sys
import csv
import datetime
from time import sleep
import fsv
import sps
import wkl
import tags
import EN_300_220_1
from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel, QLineEdit, QComboBox, QPushButton, QFileDialog, QStatusBar, QMessageBox, QCheckBox, QRadioButton)
from PyQt5.QtCore import Qt, QTime, QTimer, QLocale, QThread, pyqtSignal
from PyQt5.QtGui import QDoubleValidator, QFont, QIcon
import ctypes

WKL_TIME_TO_SET = 30 # in Minuten

# Class handling the measurement operation in a background thread once the measurement button is clicked
class MeasurementThread(QThread):

    measurement_complete = pyqtSignal(dict)

    def __init__(self, parent, fsv, sps, chamber, standard, inputs):
        super().__init__()
        self.parent = parent
        self.fsv = fsv
        self.sps = sps
        self.chamber = chamber
        self.standard = standard
        self.inputs = inputs            

    # main function of MeasurementThread class containing the general logical structure of measurement
    def run(self):
        try:
            results = {}

            # prepare all parameters that were transmitted from main thread
            path = self.inputs['path']
            filename_obw = self.inputs['filename_obw']
            filename_oob_oc = self.inputs['filename_oob_oc']
            filename_oob_ofb = self.inputs['filename_oob_ofb']
            centre_freq = self.inputs['centre_freq']
            ocw = self.inputs['ocw']
            voltage = self.inputs['voltage']
            temp_min = self.inputs['temp_min']
            temp_max = self.inputs['temp_max']
            volt_min = self.inputs['volt_min']
            volt_max = self.inputs['volt_max']
            measure_obw = self.inputs['measure_obw']
            measure_oob = self.inputs['measure_oob']
            measure_ex = self.inputs['measure_ex']
            adjust_erp = self.inputs['adjust_erp']
            dm2 = False
            self.stop_flag = False

            if self.parent.checkbox_dm2.isChecked():
                dm2 = True

            # ERP adjustment
            if adjust_erp:
                self.fsv.adjust_erp(adjust_erp, centre_freq, ocw, 100000)   # 100 kHz RBW weil das wohl standardmäßig so eingestellt wird bei dieser Messung

            if self.stop_flag:
                self.cleanup()
                return

            ### IF BOTH TESTS (OBW + OOB) should be performed
            if measure_obw and measure_oob:

                # IF EXTREME CONDITIONS should be performed for both tests
                if measure_ex:

                    # prepare structures for results
                    bandwidths = []
                    oc_passes = []
                    ofb_passes = []

                    ## 1) EXECUTE TESTS UNDER NORMAL CONDITIONS
                    measured_bandwidth = self.parent.execute_obw_measurement(ocw, centre_freq, path, filename_obw)
                    oc_pass, ofb_pass = self.parent.execute_oob_measurement(ocw, centre_freq, path, filename_oob_oc, filename_oob_ofb, dm2)

                    bandwidths.append(float(measured_bandwidth))
                    oc_passes.append(oc_pass)
                    ofb_passes.append(ofb_pass)

                    if self.stop_flag:
                        self.cleanup()
                        return

                    ## 2) EXECUTE TESTS UNDER EXTREME VOLTAGE AT MAXIMUM TEMP
                    if not self.set_temperature_and_wait(temp_max):
                        return

                    # set voltage to min volt
                    if not self.set_ex_voltage(volt_min):
                        return

                    # execute both tests with appropriate filenames
                    filename = filename_obw[:-4] + "_maxtemp_minvolt" + ".jpg"
                    measured_bandwidth = self.parent.execute_obw_measurement(ocw, centre_freq, path, filename)

                    filename_oc = filename_oob_oc[:-4] + "_maxtemp_minvolt" + ".jpg"
                    filename_ofb = filename_oob_ofb[:-4] + "_maxtemp_minvolt" + ".jpg"
                    oc_pass, ofb_pass = self.parent.execute_oob_measurement(ocw, centre_freq, path, filename_oc, filename_ofb, dm2)

                    bandwidths.append(float(measured_bandwidth))
                    oc_passes.append(oc_pass)
                    ofb_passes.append(ofb_pass)

                    if self.stop_flag:
                        self.cleanup()
                        return

                    # set voltage to max volt
                    if not self.set_ex_voltage(volt_max):
                        return
                    
                    # execute both tests with appropriate filenames
                    filename = filename_obw[:-4] + "_maxtemp_maxvolt" + ".jpg"
                    measured_bandwidth = self.parent.execute_obw_measurement(ocw, centre_freq, path, filename)

                    filename_oc = filename_oob_oc[:-4] + "_maxtemp_maxvolt" + ".jpg"
                    filename_ofb = filename_oob_ofb[:-4] + "_maxtemp_maxvolt" + ".jpg"
                    oc_pass, ofb_pass = self.parent.execute_oob_measurement(ocw, centre_freq, path, filename_oc, filename_ofb, dm2)

                    bandwidths.append(float(measured_bandwidth))
                    oc_passes.append(oc_pass)
                    ofb_passes.append(ofb_pass)

                    if self.stop_flag:
                        self.cleanup()
                        return
                    
                    self.chamber.stop()
                    sleep(2)

                    self.set_ex_voltage(voltage)

                    ## 3) EXECUTE TESTS UNDER EXTREME VOLTAGE AT MINIMUM TEMP
                    if not self.set_temperature_and_wait(temp_min):
                        return

                    # set voltage to min volt
                    if not self.set_ex_voltage(volt_min):
                        return

                    # execute both tests with appropriate filenames
                    filename = filename_obw[:-4] + "_mintemp_minvolt" + ".jpg"
                    measured_bandwidth = self.parent.execute_obw_measurement(ocw, centre_freq, path, filename)

                    filename_oc = filename_oob_oc[:-4] + "_mintemp_minvolt" + ".jpg"
                    filename_ofb = filename_oob_ofb[:-4] + "_mintemp_minvolt" + ".jpg"
                    oc_pass, ofb_pass = self.parent.execute_oob_measurement(ocw, centre_freq, path, filename_oc, filename_ofb, dm2)

                    bandwidths.append(float(measured_bandwidth))
                    oc_passes.append(oc_pass)
                    ofb_passes.append(ofb_pass)

                    if self.stop_flag:
                        self.cleanup()
                        return

                    # set voltage to max volt
                    if not self.set_ex_voltage(volt_max):
                        return
                    
                    # execute both tests with appropriate filenames
                    filename = filename_obw[:-4] + "_mintemp_maxvolt" + ".jpg"
                    measured_bandwidth = self.parent.execute_obw_measurement(ocw, centre_freq, path, filename)

                    filename_oc = filename_oob_oc[:-4] + "_mintemp_maxvolt" + ".jpg"
                    filename_ofb = filename_oob_ofb[:-4] + "_mintemp_maxvolt" + ".jpg"
                    oc_pass, ofb_pass = self.parent.execute_oob_measurement(ocw, centre_freq, path, filename_oc, filename_ofb, dm2)

                    bandwidths.append(float(measured_bandwidth))
                    oc_passes.append(oc_pass)
                    ofb_passes.append(ofb_pass)

                    ## prepare results
                    results = {
                        'measure_ex': True,
                        'obw': bandwidths,
                        'oc_passes': oc_passes,
                        'ofb_passes': ofb_passes,
                        'obw_measured': True,
                        'oob_measured': True
                    }

                # IF ONLY NORMAL CONDITIONS for BOTH tests
                else:
                    measured_bandwidth = self.parent.execute_obw_measurement(ocw, centre_freq, path, filename_obw)
                    if self.stop_flag:
                        self.cleanup()
                        return
                    oc_pass, ofb_pass = self.parent.execute_oob_measurement(ocw, centre_freq, path, filename_oob_oc, filename_oob_ofb, dm2)
                    if self.stop_flag:
                        self.cleanup()
                        return
                    
                    results = {
                        'measure_ex': False,
                        'obw': measured_bandwidth,
                        'oc_pass': oc_pass,
                        'ofb_pass': ofb_pass,
                        'obw_measured': True,
                        'oob_measured': True
                    }

            ### IF ONLY OBW TEST should be performed
            elif measure_obw:

                # IF EXTREME CONDITIONS for obw test
                if measure_ex:

                    # prepare structures for results
                    bandwidths = []

                    ## 1) EXECUTE OBW TEST UNDER NORMAL CONDITIONS
                    measured_bandwidth = self.parent.execute_obw_measurement(ocw, centre_freq, path, filename_obw)
                    bandwidths.append(float(measured_bandwidth))

                    if self.stop_flag:
                        self.cleanup()
                        return

                    ## 2) EXECUTE OBW TEST UNDER EXTREME VOLTAGE AT MAXIMUM TEMP
                    if not self.set_temperature_and_wait(temp_max):
                        return

                    # set voltage to min volt
                    if not self.set_ex_voltage(volt_min):
                        return

                    # execute test with appropriate filename
                    filename = filename_obw[:-4] + "_maxtemp_minvolt" + ".jpg"
                    measured_bandwidth = self.parent.execute_obw_measurement(ocw, centre_freq, path, filename)

                    bandwidths.append(float(measured_bandwidth))

                    if self.stop_flag:
                        self.cleanup()
                        return

                    # set voltage to max volt
                    if not self.set_ex_voltage(volt_max):
                        return
                    
                    # execute test with appropriate filename
                    filename = filename_obw[:-4] + "_maxtemp_maxvolt" + ".jpg"
                    measured_bandwidth = self.parent.execute_obw_measurement(ocw, centre_freq, path, filename)

                    bandwidths.append(float(measured_bandwidth))

                    if self.stop_flag:
                        self.cleanup()
                        return
                    
                    self.chamber.stop()
                    sleep(2)

                    self.set_ex_voltage(voltage)

                    ## 3) EXECUTE OBW TEST UNDER EXTREME VOLTAGE AT MINIMUM TEMP
                    if not self.set_temperature_and_wait(temp_min):
                        return

                    # set voltage to min volt
                    if not self.set_ex_voltage(volt_min):
                        return

                    # execute test with appropriate filename
                    filename = filename_obw[:-4] + "_mintemp_minvolt" + ".jpg"
                    measured_bandwidth = self.parent.execute_obw_measurement(ocw, centre_freq, path, filename)

                    bandwidths.append(float(measured_bandwidth))

                    if self.stop_flag:
                        self.cleanup()
                        return

                    # set voltage to max volt
                    if not self.set_ex_voltage(volt_max):
                        return

                    # execute test with appropriate filename
                    filename = filename_obw[:-4] + "_mintemp_maxvolt" + ".jpg"
                    measured_bandwidth = self.parent.execute_obw_measurement(ocw, centre_freq, path, filename)

                    bandwidths.append(float(measured_bandwidth))

                    ## prepare results
                    results = {
                        'measure_ex': True,
                        'obw': bandwidths,
                        'obw_measured': True,
                        'oob_measured': False
                    }

                # IF ONLY NORMAL CONDITIONS for obw test
                else:
                    measured_bandwidth = self.parent.execute_obw_measurement(ocw, centre_freq, path, filename_obw)
                    if self.stop_flag:
                        self.cleanup()
                        return
                    results = {
                        'measure_ex': False,
                        'obw': measured_bandwidth,
                        'obw_measured': True,
                        'oob_measured': False
                    }

            ### IF ONLY OOB TEST should be performed
            elif measure_oob:

                # IF EXTREME CONDITIONS for oob test
                if measure_ex:

                    # prepare structures for results
                    oc_passes = []
                    ofb_passes = []

                    ## 1) EXECUTE TEST UNDER NORMAL CONDITIONS
                    oc_pass, ofb_pass = self.parent.execute_oob_measurement(ocw, centre_freq, path, filename_oob_oc, filename_oob_ofb, dm2)

                    oc_passes.append(oc_pass)
                    ofb_passes.append(ofb_pass)

                    if self.stop_flag:
                        self.cleanup()
                        return

                    ## 2) EXECUTE TEST UNDER EXTREME VOLTAGE AT MAXIMUM TEMP
                    if not self.set_temperature_and_wait(temp_max):
                        return

                    # set voltage to min volt
                    if not self.set_ex_voltage(volt_min):
                        return

                    # execute test with appropriate filenames
                    filename_oc = filename_oob_oc[:-4] + "_maxtemp_minvolt" + ".jpg"
                    filename_ofb = filename_oob_ofb[:-4] + "_maxtemp_minvolt" + ".jpg"
                    oc_pass, ofb_pass = self.parent.execute_oob_measurement(ocw, centre_freq, path, filename_oc, filename_ofb), dm2

                    oc_passes.append(oc_pass)
                    ofb_passes.append(ofb_pass)

                    if self.stop_flag:
                        self.cleanup()
                        return

                    # set voltage to max volt
                    if not self.set_ex_voltage(volt_max):
                        return
                    
                    # execute test with appropriate filenames
                    filename_oc = filename_oob_oc[:-4] + "_maxtemp_maxvolt" + ".jpg"
                    filename_ofb = filename_oob_ofb[:-4] + "_maxtemp_maxvolt" + ".jpg"
                    oc_pass, ofb_pass = self.parent.execute_oob_measurement(ocw, centre_freq, path, filename_oc, filename_ofb, dm2)

                    oc_passes.append(oc_pass)
                    ofb_passes.append(ofb_pass)

                    if self.stop_flag:
                        self.cleanup()
                        return
                    
                    self.chamber.stop()
                    sleep(2)

                    self.set_ex_voltage(voltage)

                    ## 3) EXECUTE TEST UNDER EXTREME VOLTAGE AT MINIMUM TEMP
                    if not self.set_temperature_and_wait(temp_min):
                        return

                    # set voltage to min volt
                    if not self.set_ex_voltage(volt_min):
                        return

                    # execute test with appropriate filenames
                    filename_oc = filename_oob_oc[:-4] + "_mintemp_minvolt" + ".jpg"
                    filename_ofb = filename_oob_ofb[:-4] + "_mintemp_minvolt" + ".jpg"
                    oc_pass, ofb_pass = self.parent.execute_oob_measurement(ocw, centre_freq, path, filename_oc, filename_ofb, dm2)

                    oc_passes.append(oc_pass)
                    ofb_passes.append(ofb_pass)

                    if self.stop_flag:
                        self.cleanup()
                        return

                    # set voltage to max volt
                    if not self.set_ex_voltage(volt_max):
                        return

                    # execute test with appropriate filenames
                    filename_oc = filename_oob_oc[:-4] + "_mintemp_maxvolt" + ".jpg"
                    filename_ofb = filename_oob_ofb[:-4] + "_mintemp_maxvolt" + ".jpg"
                    oc_pass, ofb_pass = self.parent.execute_oob_measurement(ocw, centre_freq, path, filename_oc, filename_ofb, dm2)

                    oc_passes.append(oc_pass)
                    ofb_passes.append(ofb_pass)

                    ## prepare results
                    results = {
                        'measure_ex': True,
                        'oc_passes': oc_passes,
                        'ofb_passes': ofb_passes,
                        'obw_measured': False,
                        'oob_measured': True
                    }

                # IF ONLY NORMAL CONDITIONS for oob test
                else:
                    oc_pass, ofb_pass = self.parent.execute_oob_measurement(ocw, centre_freq, path, filename_oob_oc, filename_oob_ofb, dm2)
                    if self.stop_flag:
                        self.cleanup()
                        return
                    results = {
                        'measure_ex': False,
                        'oc_pass': oc_pass,
                        'ofb_pass': ofb_pass,
                        'obw_measured': False,
                        'oob_measured': True
                    }
            
            tags.log('Background Thread', 'Measurement complete. Turning all instruments off. Await the results in the GUI.')

            # turn off equipment after test is complete
            self.cleanup()
            
            if not self.stop_flag:
                self.measurement_complete.emit(results)

        except Exception as e:
            tags.log('Background Thread', f'Exception {e}')
            self.stop()
            self.parent.show_warning('Error in background thread', 'Undefined error in background thread during measurement, check logs.')

    # set the chamber to a certain temperature and wait for a specific amount of time defined by global variable. check if temperature is reached, if not wait 5 mins longer
    def set_temperature_and_wait(self, temperature):
        if not self.chamber.set_temp(float(temperature)):
            tags.log('Background Thread WKL', 'Error setting temperature.')
            self.cleanup()
            return False
        
        self.chamber.start()
        self.parent.status_bar.showMessage(f'Chamber set to {temperature} °C and started.')
        
        i = 0
        for _ in range(WKL_TIME_TO_SET):  # 1 iteration = 1 minute
            i = i+1
            sleep(60)
            tags.log('Background Thread WKL', f'Chamber currently at {float(self.chamber.current_temp):.2f} °C. {i} out of {WKL_TIME_TO_SET} minutes elapsed.')
            self.parent.status_bar.showMessage(f'Chamber running, {float(self.chamber.current_temp):.2f} / {temperature} °C, {i} / {WKL_TIME_TO_SET} mins elapsed')
            if self.stop_flag:
                self.cleanup()
                return False
            
        # if temperature has been reached within 1 °C
        if float(temperature)-1 < self.chamber.current_temp < float(temperature)+1:
            tags.log('Background Thread WKL', 'Temperature reached, starting with measurements.')
            self.parent.status_bar.showMessage(f'Temperature reached, starting with measurements at {temperature} °C')
            return True
        # if temperature has not been reached yet
        else:
            tags.log('Background Thread WKL', 'Temperature not yet reached. Waiting another 5 minutes.')
            for _ in range(5):  # 5 iterations for 5 minutes
                sleep(60)
                tags.log('Background Thread WKL', f'Chamber currently at {self.chamber.current_temp:.2f} °C')
                if self.stop_flag:
                    self.cleanup()
                    return False
            if float(temperature)-1 < self.chamber.current_temp < float(temperature)+1:
                return True
            else:
                tags.log('Background Thread WKL', 'Temperature not reached. Error in setting temperature. Process being terminated.')
                self.cleanup()
                return False
    
    def set_ex_voltage(self, voltage):
        if not self.parent.apply_ex_voltage(voltage):
            self.parent.show_warning('Error applying voltage', 'Check connection to power supply.')
            tags.log('Background Thread SPS', 'Error applying voltage.')
            self.cleanup()
            return False
        return True

    def stop(self):
        self.stop_flag = True
        self.sps.stop_operation()
        self.fsv.stop_operation()

    def cleanup(self):
        self.sps.set_amp_off()
        self.fsv.reset()
        self.sps.reset()
        if self.chamber.is_running:
            self.chamber.stop()
        tags.log('Background Thread', 'Instruments turned off and/or reset to defaults.')



class NoCommaLineEdit(QLineEdit):
    def __init__(self, *args, **kwargs):
        super(NoCommaLineEdit, self).__init__(*args, **kwargs)
    
    def keyPressEvent(self, event):
        if event.text() == ',':
            # Ignore the comma key press
            event.ignore()
        else:
            # Process other key presses normally
            super(NoCommaLineEdit, self).keyPressEvent(event)


# Class for main application with GUI definition and all relevant abstracted functions for interacting with equipment
class OutOfBandMeasurementAutomation(QWidget):

    def __init__(self):
        super().__init__()

        self.fsv = fsv.FSV(tags.fsv_addr)
        self.sps = sps.SPS(tags.sps_addr)
        self.fsv.initialize("FSV")
        self.sps.initialize()
        self.standard = EN_300_220_1.EN_300_220_1()

        try:
            self.chamber = wkl.WKL(tags.wkl_ip)
            tags.log('main', f'Succesfully connected to instrument {self.chamber.idn}')
        except:
            tags.log('main', 'Error initializing climate chamber.')         

        self.initUI()
    
    # initialize GUI
    def initUI(self):
        self.setWindowTitle('EN 300 220-1 Test Automation')
        QApplication.setStyle('Fusion')
        self.setWindowIcon(QIcon('robot.ico'))
        self.setMinimumSize(500, 730)
        
        # Main layout
        main_layout = QVBoxLayout()
        
        ### Project number input
        project_layout = QHBoxLayout()
        project_label = QLabel('Project number:')
        self.proj_input = QLineEdit()
        project_hint = QLabel('Format: ABC XX/XXX')

        italic_font = QFont()
        italic_font.setItalic(True)
        project_hint.setFont(italic_font)

        project_layout.addWidget(project_label)
        project_layout.addWidget(self.proj_input)
        project_layout.addWidget(project_hint)

        ### Manufacturer info group
        man_info_group = QGroupBox('Manufacturer Info')
        man_info_layout = QVBoxLayout()

        # Frequency inputs for Operating Frequency and Operating Channel Width
        self.op_freq_input = self.create_frequency_input('Operating Frequency')
        self.op_channel_width_input = self.create_frequency_input('Operating Channel Width')

        # Input for entering nominal operating voltage
        self.volt_validator = QDoubleValidator(0.0, 270, 2, notation=QDoubleValidator.StandardNotation)
        self.volt_validator.setLocale(QLocale(QLocale.English))

        nom_volt_layout = QHBoxLayout()
        nom_volt_label = QLabel('Nominal Operating Voltage:')
        self.nom_volt_input = NoCommaLineEdit()
        self.nom_volt_input.setValidator(self.volt_validator)
        self.nom_volt_input.setFixedWidth(tags.inputfield_width)
        volt_label = QLabel('V')

        nom_volt_layout.addWidget(nom_volt_label)
        nom_volt_layout.addStretch()
        nom_volt_layout.addWidget(self.nom_volt_input)
        nom_volt_layout.addWidget(volt_label)

        # Input for entering AC Frequency if necessary
        self.acfreq_validator = QDoubleValidator(0.0, 100, 2, notation=QDoubleValidator.StandardNotation)
        self.acfreq_validator.setLocale(QLocale(QLocale.English))

        ac_freq_layout = QHBoxLayout()
        self.ac_radio = QRadioButton('AC', self)
        self.dc_radio = QRadioButton('DC', self)
        self.dc_radio.setChecked(True)
        self.frequency_label = QLabel('Set AC Frequency (Hz):')
        self.frequency_input = NoCommaLineEdit(self)
        self.frequency_input.setValidator(self.acfreq_validator)
        self.frequency_input.setFixedWidth(tags.inputfield_width)
        self.frequency_label.setEnabled(False)
        self.frequency_input.setEnabled(False)

        ac_freq_layout.addWidget(self.ac_radio)
        ac_freq_layout.addWidget(self.dc_radio)
        ac_freq_layout.addStretch()
        ac_freq_layout.addWidget(self.frequency_label)
        ac_freq_layout.addWidget(self.frequency_input)

        self.ac_radio.toggled.connect(self.toggle_frequency_input)

        # EUT-specific boot time
        self.eut_boot_validator = QDoubleValidator(0.0, 100, 1, notation=QDoubleValidator.StandardNotation)
        self.eut_boot_validator.setLocale(QLocale(QLocale.English))

        # Finish up manufacturer info group
        man_info_layout.addWidget(self.op_freq_input)
        man_info_layout.addWidget(self.op_channel_width_input)
        man_info_layout.addLayout(nom_volt_layout)
        man_info_layout.addLayout(ac_freq_layout)

        man_info_group.setLayout(man_info_layout)

        ### Test parameters group
        parameters_group = QGroupBox('Test Parameters')
        parameters_layout = QVBoxLayout()
        
        # ERP adjustment
        self.dbm_validator = QDoubleValidator(-50, 50, 2, notation=QDoubleValidator.StandardNotation)
        self.dbm_validator.setLocale(QLocale(QLocale.English))

        erp_layout = QHBoxLayout()
        erp_label = QLabel('(Optional) Maximum e.r.p as measured (SAC):')
        self.erp_input = NoCommaLineEdit()
        self.erp_input.setValidator(self.dbm_validator)
        self.erp_input.setFixedWidth(tags.inputfield_width)
        erp_hint = QLabel('dBm')
        erp_layout.addWidget(erp_label)
        erp_layout.addStretch()
        erp_layout.addWidget(self.erp_input)
        erp_layout.addWidget(erp_hint)

        # Temperature range
        self.temp_validator = QDoubleValidator(-40, 180, 2, notation=QDoubleValidator.StandardNotation)
        self.temp_validator.setLocale(QLocale(QLocale.English))

        temp_layout = QHBoxLayout()
        temp_label = QLabel('Extreme Temperature Range:')
        self.min_temp_input = NoCommaLineEdit()
        self.min_temp_input.setValidator(self.temp_validator)
        self.min_temp_input.setPlaceholderText("Min Temp.")
        self.min_temp_input.setFixedWidth(tags.inputfield_width)
        self.max_temp_input = NoCommaLineEdit()
        self.max_temp_input.setValidator(self.temp_validator)
        self.max_temp_input.setPlaceholderText("Max Temp.")
        self.max_temp_input.setFixedWidth(tags.inputfield_width)
        celsius_label = QLabel('°C')

        temp_layout.addWidget(temp_label)
        temp_layout.addStretch()
        temp_layout.addWidget(self.min_temp_input)
        temp_layout.addWidget(self.max_temp_input)
        temp_layout.addWidget(celsius_label)

        # Voltage range
        ex_volt_layout = QHBoxLayout()
        ex_volt_label = QLabel('Extreme Voltage Range:')
        self.min_volt_input = NoCommaLineEdit()
        self.min_volt_input.setValidator(self.volt_validator)
        self.min_volt_input.setPlaceholderText("Min Voltage")
        self.min_volt_input.setFixedWidth(tags.inputfield_width)
        self.max_volt_input = NoCommaLineEdit()
        self.max_volt_input.setValidator(self.volt_validator)
        self.max_volt_input.setPlaceholderText("Min Voltage")
        self.max_volt_input.setFixedWidth(tags.inputfield_width)
        volt_label2 = QLabel('  V')

        ex_volt_layout.addWidget(ex_volt_label)
        ex_volt_layout.addStretch()
        ex_volt_layout.addWidget(self.min_volt_input)
        ex_volt_layout.addWidget(self.max_volt_input)
        ex_volt_layout.addWidget(volt_label2)

        # Screenshot path selection
        select_path_layout = QHBoxLayout()
        self.select_path_button = QPushButton('Select path for saving screenshots')
        self.select_path_button.clicked.connect(self.select_path)
        self.selected_path_label = QLabel('')
        self.selected_path_label.setWordWrap(True)
        select_path_layout.addWidget(self.select_path_button)
        select_path_layout.addWidget(self.selected_path_label)
        
        # Combine input group sections
        parameters_layout.addLayout(erp_layout)
        parameters_layout.addLayout(temp_layout)
        parameters_layout.addLayout(ex_volt_layout)
        parameters_layout.addLayout(select_path_layout)
        parameters_group.setLayout(parameters_layout)

        ### Execute Measurement group
        exec_group = QGroupBox('Execute Measurement')
        exec_layout = QVBoxLayout()    

        # OBW measurement button
        self.checkbox_obw = QCheckBox('Execute Occupied Bandwidth Measurement')
        self.checkbox_oob = QCheckBox('Execute Out-Of-Band Emissions Measurement')
        self.checkbox_ex = QCheckBox('Test under extreme conditions')
        self.checkbox_dm2 = QCheckBox('EUT generates test signal of type D-M2')
        self.checkbox_fhss = QCheckBox('Device operates with FHSS')
        
        # Start measurement button
        bold_font = QFont()
        bold_font.setBold(True)
        self.start_button = QPushButton('Start Automated Measurement')
        self.start_button.setFont(bold_font)
        self.start_button.clicked.connect(self.execute_measurement)

        # Stop measurement button
        self.stop_button = QPushButton('Interrupt Automated Measurement')
        self.stop_button.clicked.connect(self.stop_measurement)
        self.stop_button.setEnabled(False)

        exec_layout.addWidget(self.checkbox_obw)
        exec_layout.addWidget(self.checkbox_oob)
        exec_layout.addWidget(self.checkbox_ex)
        exec_layout.addWidget(self.checkbox_dm2)
        exec_layout.addWidget(self.checkbox_fhss)
        exec_layout.addWidget(self.start_button)
        exec_layout.addWidget(self.stop_button)

        exec_group.setLayout(exec_layout)

        # Status bar
        self.status_bar = QStatusBar()
        
        # Results section
        results_group = QGroupBox('Results')
        results_layout = QVBoxLayout()
        
        self.obw_result_label = QLabel()
        self.op_channel_result_label = QLabel()
        self.op_band_result_label = QLabel()
        self.screenshots_path_label = QLabel()
        self.screenshots_path_label.setOpenExternalLinks(True)
        
        results_layout.addWidget(self.obw_result_label)
        results_layout.addWidget(self.op_channel_result_label)
        results_layout.addWidget(self.op_band_result_label)
        results_layout.addWidget(self.screenshots_path_label)
        
        results_group.setLayout(results_layout)

        # Add widgets to main layout
        main_layout.addLayout(project_layout)
        main_layout.addWidget(man_info_group)
        main_layout.addWidget(parameters_group)
        main_layout.addWidget(exec_group)
        main_layout.addWidget(self.status_bar)
        main_layout.addWidget(results_group)

        self.setLayout(main_layout)

    # template for creation of frequency input incl. unit kHz/MHz/GHz
    def create_frequency_input(self, label_text):
        widget = QWidget()
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        
        label = QLabel(label_text)
        input_field = NoCommaLineEdit()
        input_field.setFixedWidth(tags.inputfield_width)  # Fixed width for input fields
        unit_selector = QComboBox()
        unit_selector.addItems(['kHz', 'MHz', 'GHz'])
        unit_selector.setCurrentIndex(1)
        unit_selector.setFixedWidth(60)  # Fixed width for unit selector

        # Double Validator for correct format of voltage input
        self.freq_validator = QDoubleValidator(0.0, 1000, 3, notation=QDoubleValidator.StandardNotation)
        self.freq_validator.setLocale(QLocale(QLocale.English))
        input_field.setValidator(self.freq_validator)
        
        # Ensure the label, input field, and unit selector are aligned correctly
        layout.addWidget(label)
        layout.addWidget(input_field, alignment=Qt.AlignRight)
        layout.addWidget(unit_selector)
        
        widget.setLayout(layout)
        
        widget.input_field = input_field
        widget.unit_selector = unit_selector
        
        return widget
    
    # UI helper function for AC/DC input change
    def toggle_frequency_input(self):
        if self.ac_radio.isChecked():
            self.frequency_label.setEnabled(True)
            self.frequency_input.setEnabled(True)
        else:
            self.frequency_label.setEnabled(False)
            self.frequency_input.setEnabled(False)
    
    # function called by button to select path on computer for saving screenshots & more
    def select_path(self):
        path = QFileDialog.getExistingDirectory(self, 'Select Directory')
        if path:
            self.selected_path_label.setText(path)
    
    # check inputs before starting measurement
    def validate_inputs(self):

        # check if project number was input
        if not self.proj_input.text():
            self.show_warning('Input Error', 'Please enter the project number.')
            return False
        
        # check if operating frequency was input and if it is valid (<30 GHz)
        if self.op_freq_input.input_field.text():
            if self.op_freq_input.unit_selector.currentIndex() == 2:    # if unit selected is GHz
                if float(self.op_freq_input.input_field.text()) > 30.0:
                    self.show_warning('Input Error', 'Please enter a valid operating frequency. Maximum: 30 GHz')
                    return False
        else:
            self.show_warning('Input Error', 'Please enter the operating frequency.')
            return False
        
        # check if operating channel width was input and if it is valid (<30 GHz)
        if self.op_channel_width_input.input_field.text():
            if self.op_channel_width_input.unit_selector.currentIndex() == 2:    # if unit selected is GHz
                if float(self.op_channel_width_input.input_field.text()) > 30.0:
                    self.show_warning('Input Error', 'Please enter a valid operating channel width. Maximum: 30 GHz')
                    return False
        else:
            self.show_warning('Input Error', 'Please enter the operating channel width.')
            return False
        
        # check if nominal voltage was input and if it is valid (<230 V)
        if self.nom_volt_input.text():
            if float(self.nom_volt_input.text()) > 230.0:
                self.show_warning('Input Error', 'Please enter a valid nominal operating voltage. Maximum: 230 V')
                return False
        else:
            self.show_warning('Input Error', 'Please enter the nominal operating voltage.')
            return False

        # check if e.r.p reference value was input and if it is valid (-35 dBm < e.r.p reference < 14 dBm)
        if self.erp_input.text():
            if not -35 < float(self.erp_input.text()) < 14:
                self.show_warning('Input Error', 'Please enter a valid e.r.p reference value between -20 and 14 dBm.')

        # if testing under extreme conditions check temp and voltage inputs as well
        if self.checkbox_ex.isChecked():
            if not self.min_temp_input.text() or not self.max_temp_input.text() or not self.min_volt_input.text() or not self.max_volt_input.text():
                self.show_warning('Input Error', 'Please enter the ranges for extreme conditions.')
                return False
            else:
                if float(self.min_temp_input.text()) < self.chamber.temperature_min or float(self.max_temp_input.text()) > self.chamber.temperature_max:
                    self.show_warning('Input Error', f'Temperature must be between {self.chamber.temperature_min} and {self.chamber.temperature_max} °C')
                    return False

        # check if path for screenshots has been selected
        if not self.selected_path_label.text():
            self.show_warning('Input Error', 'Please select a path for saving screenshots.')
            return False

        # make sure that at least one measurement is supposed to be executed (OBW/OOB)
        if self.checkbox_obw.isChecked() or self.checkbox_oob.isChecked():
            return True
        else:
            self.show_warning('Input Error', 'Please select at least one of both OBW/OOB measurements to be executed.')
            return False
    
    # display a message box warning
    def show_warning(self, title, msg):
        QMessageBox.warning(self, title, msg)

    # convert frequency of specific unit multiple to Hz for further consistent processing
    def convert_freq(self, freq, unit):
        if unit == 'kHz':
            return int(freq * 1000)
        if unit == 'MHz':
            return int(freq * 1000000)
        if unit == 'GHz':
            return int(freq * 1000000000)

    # execute selected measurements (connected to 'Start Automated Measurement' button)
    def execute_measurement(self):

        if self.validate_inputs():
            
            ## Preparation and extraction of relevant input from GUI
            self.status_bar.showMessage('Setting EUT supply voltage. Please wait a moment.')
            QApplication.processEvents()

            self.start_button.setEnabled(False)
            self.stop_button.setEnabled(True)

            # Apply nominal voltage to EUT with SPS power supply
            tags.log('main', 'Setting nominal voltage at EUT.')
            self.apply_nom_voltage(self.nom_volt_input.text())

            # Display window and pause execution to give user time to set up the EUT, re-commence operation of program once user clicks "continue"
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle("Setup EUT")
            msg_box.setText("Once the EUT is ready for testing please press 'Ok' to proceed.")
            msg_box.setIcon(QMessageBox.Information)
            msg_box.addButton(QMessageBox.Ok)
            msg_box.exec_()

            self.status_bar.showMessage('Measurement started...')
            QApplication.processEvents()
            
            # Start timer to measure time elapsed
            self.timer = QTimer()
            self.start_time = QTime.currentTime()
            self.timer.start(1000)  # Update every second

            # Extract project number
            project_nr = self.proj_input.text().replace(" ", "-").replace("/", "-")

            # Extract centre frequency
            freq_unit = self.op_freq_input.unit_selector.currentText()
            centre_freq_raw = self.op_freq_input.input_field.text()
            centre_freq = self.convert_freq(float(centre_freq_raw), freq_unit)

            # Extract span
            freq_unit = self.op_channel_width_input.unit_selector.currentText()
            ocw_raw = self.op_channel_width_input.input_field.text()
            ocw = self.convert_freq(float(ocw_raw), freq_unit)

            ## Prepare inputs to execute measurements in asynchronous thread
            inputs = {
                'path': self.selected_path_label.text(),
                'filename_obw': f"{datetime.datetime.now().strftime('%Y-%m-%d_')}" + project_nr + "_" + "OccupiedBandwidth.jpg",
                'filename_oob_oc': f"{datetime.datetime.now().strftime('%Y-%m-%d_')}" + project_nr + "_" + "OOB-OC.jpg",
                'filename_oob_ofb': f"{datetime.datetime.now().strftime('%Y-%m-%d_')}" + project_nr + "_" + "OOB-OFB-center.jpg",
                'centre_freq': centre_freq,
                'ocw': ocw,
                'voltage': self.nom_volt_input.text(),
                'temp_min': self.min_temp_input.text(),
                'temp_max': self.max_temp_input.text(),
                'volt_min': self.min_volt_input.text(),
                'volt_max': self.max_volt_input.text(),
                'measure_obw': self.checkbox_obw.isChecked(),
                'measure_oob': self.checkbox_oob.isChecked(),
                'measure_ex': self.checkbox_ex.isChecked(),
                'adjust_erp': self.erp_input.text()
            }

            # Initialize new thread and start the measurement logic on that thread
            self.measurement_thread = MeasurementThread(self, self.fsv, self.sps, self.chamber, self.standard, inputs)
            self.measurement_thread.measurement_complete.connect(self.display_results)
            self.measurement_thread.start()
            tags.log('main', 'Asynchronous thread initialized and measurement started.')

    # stops currently ongoing measurement (connected to 'Interrupt Automated Measurement' button)
    def stop_measurement(self):
        if hasattr(self, 'measurement_thread'):
            tags.log('main', 'Stop measurement button clicked. Please wait a moment while everything shuts down.')
            self.measurement_thread.stop()
            self.measurement_thread.wait()
            self.timer.stop()
            sleep(2)
            self.status_bar.showMessage('Measurement interrupted. Please restart program.')
            self.start_button.setEnabled(True)
            self.stop_button.setEnabled(False)
            self.show_warning('Measurement interrupted', 'Testing has been stopped and equipment turned off. Please restart program in order to properly continue any testing.')
    
    # function containing all GUI and instrument logic for occupied bandwidth measurement
    def execute_obw_measurement(self, ocw, centre_freq, path, filename_obw):
        self.status_bar.showMessage('Measuring occupied bandwidth...')
        tags.log('main', 'Starting OBW measurement.')
        QApplication.processEvents()

        obw_parameters = self.standard.calc_obw_parameters(ocw)

        return self.fsv.measure_obw(filename_obw, path, centre_freq, obw_parameters)

    # function containing all GUI and instrurment logic for out-of-band emissions measurement
    def execute_oob_measurement(self, ocw, centre_freq, path, filename_oob_oc, filename_oob_ofb, dm2):

        # get test parameters as per definition in standard and then set them on spectrum analyzer
        oob_parameters = self.standard.calc_oob_parameters(ocw)
        self.fsv.prep_oob_parameters(centre_freq, oob_parameters, dm2)

        # 1) OOB testing for operating channel
        self.status_bar.showMessage('Measuring out-of-band emissions for the operating channel...')
        tags.log('main', 'Starting OOB operating channel measurement.')
        QApplication.processEvents()

        limit_points_oc = self.standard.calc_limit_oc(centre_freq, ocw)
        oc_pass = self.fsv.measure_oob_oc(limit_points_oc, filename_oob_oc, path)

        # 2) OOB testing for operational frequency band    
        self.status_bar.showMessage('Measuring out-of-band emissions for the operational frequency band...')
        tags.log('main', 'Starting OOB operational frequency band measurement.')
        QApplication.processEvents()

        f_low, f_high = self.determine_freq_range(centre_freq, self.checkbox_fhss.isChecked())

        limit_points_ofb = self.standard.calc_limit_ofb(f_low, f_high)
        ofb_pass = self.fsv.measure_oob_ofb(limit_points_ofb, filename_oob_ofb, path)
        self.fsv.prep_oob_parameters(centre_freq, oob_parameters, dm2)

        return oc_pass, ofb_pass
    
    # function containing logic for applying nominal voltage with GUI input
    def apply_nom_voltage(self, voltage):
        voltage = float(voltage)

        if voltage > 270.0 or voltage <= 0.0:
            QMessageBox.warning(self, 'Input Error', 'Please enter a valid voltage.')
            return
        
        if self.dc_radio.isChecked():
            result = self.sps.set_voltage_dc(voltage)
        else:
            ac_freq = self.frequency_input.text()
            if not ac_freq or int(ac_freq) > 100:
                ac_freq = 50
                self.frequency_input.setText('50')

            result = self.sps.set_voltage_ac(voltage, ac_freq)

        # check if stop flag was set
        if not result:
            return

    # function for setting voltage in cases of min/max voltage extreme conditions
    def apply_ex_voltage(self, voltage):
        voltage = float(voltage)
        
        if self.dc_radio.isChecked():
            result = self.sps.change_voltage_dc(voltage)
        else:
            result = self.sps.change_voltage_ac(voltage)

        # check if stop flag was set
        if not result:
            return False

        sleep(10)

        return True

    # display results in bottom of GUI
    def display_results(self, results):

        # stop timer and adjust GUI to reflect end of measurement
        self.timer.stop()
        elapsed_time = self.start_time.secsTo(QTime.currentTime())
        self.status_bar.showMessage(f'Measurement complete. Total time: {elapsed_time // 3600}h{(elapsed_time % 3600) // 60}m{elapsed_time % 60}s')
        tags.log('main', f'Automated measurement complete. Time elapsed: {elapsed_time // 3600}h{(elapsed_time % 3600) // 60}m{elapsed_time % 60}s ({elapsed_time} seconds)')
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)

        # get results values from background thread
        obw_measured = results.get('obw_measured', False)
        oob_measured = results.get('oob_measured', False)
        ex_measured = results.get('measure_ex', False)
        
        if obw_measured:

            if ex_measured:
                obw_min = min(results['obw'])
                obw_max = max(results['obw'])
                self.obw_result_label.setText(f'Measured Occupied Bandwidth (extreme conditions): min: <b>{self.fsv.format_freq(obw_min)}</b> max: <b>{self.fsv.format_freq(obw_max)}</b>')
            else:
                obw = results['obw']
                self.obw_result_label.setText(f'Measured Occupied Bandwidth: <b>{self.fsv.format_freq(str.strip(obw))}</b>')
        
        if oob_measured:

            if ex_measured:
                oc_pass = all(results['oc_passes'])
                ofb_pass = all(results['ofb_passes'])

                oc_status = "OOB Operating Channel Test (throughout extreme conditions): <b><font color='green'>PASS</font></b>" if oc_pass else "Operating Channel: <b><font color='red'>FAIL</font></b>"
                self.op_channel_result_label.setText(oc_status)

                ofb_status = "OOB Operational Frequency Band Test (throughout extreme conditions): <b><font color='green'>PASS</font></b>" if ofb_pass else "Operational Frequency Band: <b><font color='red'>FAIL</font></b>"
                self.op_band_result_label.setText(ofb_status)

            else:
                oc_pass = results['oc_pass']
                oc_status = "OOB Operating Channel Test: <b><font color='green'>PASS</font></b>" if oc_pass else "Operating Channel: <b><font color='red'>FAIL</font></b>"
                self.op_channel_result_label.setText(oc_status)
                
                ofb_pass = results['ofb_pass']
                ofb_status = "OOB Operational Frequency Band Test: <b><font color='green'>PASS</font></b>" if ofb_pass else "Operational Frequency Band: <b><font color='red'>FAIL</font></b>"
                self.op_band_result_label.setText(ofb_status)

        self.screenshots_path_label.setText(f'Screenshots saved at: <a href="{self.selected_path_label.text()}">{self.selected_path_label.text()}</a>')

    # determine frequency range with given operating frequency. returns lower and upper limits
    def determine_freq_range(self, freq, fhss: bool = False, filename="ERC-data/bands_03-2024.csv"):

        if fhss:
            filename="ERC-data/bands_03-2024_FHSS.csv"

        with open(filename, 'r') as csvfile:
            reader = csv.reader(csvfile)
            # Skip the header row (assuming the first row contains column names)
            next(reader)

            for row in reader:
                # Get band name, lower frequency, and upper frequency
                band, lower_freq, upper_freq = row

                # Convert frequencies to integers (assuming integer values in Hz)
                lower_freq = int(lower_freq)
                upper_freq = int(upper_freq)

                # Check if the given frequency falls within the current band
                if lower_freq <= freq <= upper_freq:
                    return lower_freq, upper_freq

        # Frequency not found in any band
        return None

def main():
    myappid = 'tuevnord.srdautomation'
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
    app = QApplication(sys.argv)
    window = OutOfBandMeasurementAutomation()
    window.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
