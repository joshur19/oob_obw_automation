"""
file: main file for OBW and OOB measurement automation in the context of EN 300 220-1
author: rueck.joshua@gmail.com
last updated: 10/07/2024
"""

import sys
import fsv
import sps
import csv
import tags
import EN_300_220_1
import datetime
from time import sleep
from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel, QLineEdit, QComboBox, QPushButton, QFileDialog, QStatusBar, QMessageBox, QCheckBox, QRadioButton)
from PyQt5.QtCore import Qt, QTime, QTimer, QLocale, QThread, pyqtSignal
from PyQt5.QtGui import QDoubleValidator, QFont

class MeasurementThread(QThread):
    measurement_complete = pyqtSignal(dict)

    def __init__(self, parent, fsv, sps, standard, inputs):
        super().__init__()
        self.parent = parent
        self.fsv = fsv
        self.sps = sps
        self.standard = standard
        self.inputs = inputs

    def run(self):
        try:
            results = {}

            path = self.inputs['path']
            filename_obw = self.inputs['filename_obw']
            filename_oob_oc = self.inputs['filename_oob_oc']
            filename_oob_ofb = self.inputs['filename_oob_ofb']
            centre_freq = self.inputs['centre_freq']
            ocw = self.inputs['ocw']
            voltage = self.inputs['voltage']
            measure_obw = self.inputs['measure_obw']
            measure_oob = self.inputs['measure_oob']
            
            self.parent.apply_nom_voltage(voltage)

            if measure_obw and measure_oob:
                measured_bandwidth = self.parent.execute_obw_measurement(ocw, centre_freq, path, filename_obw)
                oc_pass, ofb_pass = self.parent.execute_oob_measurement(ocw, centre_freq, path, filename_oob_oc, filename_oob_ofb)
                results = {
                    'obw': measured_bandwidth,
                    'oc_pass': oc_pass,
                    'ofb_pass': ofb_pass,
                    'obw_measured': True,
                    'oob_measured': True
                }
            elif measure_obw:
                measured_bandwidth = self.parent.execute_obw_measurement(ocw, centre_freq, path, filename_obw)
                results = {
                    'obw': measured_bandwidth,
                    'obw_measured': True,
                    'oob_measured': False
                }
            elif measure_oob:
                oc_pass, ofb_pass = self.parent.execute_oob_measurement(ocw, centre_freq, path, filename_oob_oc, filename_oob_ofb)
                results = {
                    'oc_pass': oc_pass,
                    'ofb_pass': ofb_pass,
                    'obw_measured': False,
                    'oob_measured': True
                }
            
            self.sps.set_amp_off()

            self.measurement_complete.emit(results)

        except Exception as e:
            print(e)

class OutOfBandMeasurementAutomation(QWidget):
    def __init__(self):
        super().__init__()

        self.fsv = fsv.FSV(tags.fsv_addr)
        self.sps = sps.SPS(tags.sps_addr)
        self.fsv.initialize("FSV")
        self.sps.initialize()
        self.standard = EN_300_220_1.EN_300_220_1()

        self.initUI()
    
    # initialize GUI
    def initUI(self):
        self.setWindowTitle('EN 300 220-1 Test Automation')
        QApplication.setStyle('Fusion')
        
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
        self.nom_volt_input = QLineEdit()
        self.nom_volt_input.setValidator(self.volt_validator)
        self.nom_volt_input.setFixedWidth(tags.inputfield_width)
        volt_label = QLabel('V')

        nom_volt_layout.addWidget(nom_volt_label)
        nom_volt_layout.addStretch()
        nom_volt_layout.addWidget(self.nom_volt_input)
        nom_volt_layout.addWidget(volt_label)

        # Input for entering AC Frequency if necessary
        self.acfreq_validator = QDoubleValidator(0.0, 1000, 2, notation=QDoubleValidator.StandardNotation)
        self.acfreq_validator.setLocale(QLocale(QLocale.English))

        ac_freq_layout = QHBoxLayout()
        self.ac_radio = QRadioButton('AC', self)
        self.dc_radio = QRadioButton('DC', self)
        self.dc_radio.setChecked(True)
        self.frequency_label = QLabel('Set AC Frequency (Hz):')
        self.frequency_input = QLineEdit(self)
        self.frequency_input.setValidator(self.acfreq_validator)
        self.frequency_input.setFixedWidth(tags.inputfield_width)
        self.frequency_label.setEnabled(False)
        self.frequency_input.setEnabled(False)

        ac_freq_layout.addWidget(self.ac_radio)
        ac_freq_layout.addWidget(self.dc_radio)
        ac_freq_layout.addWidget(self.frequency_label)
        ac_freq_layout.addWidget(self.frequency_input)

        self.ac_radio.toggled.connect(self.toggle_frequency_input)

        # EUT-specific boot time
        self.eut_boot_validator = QDoubleValidator(0.0, 3600, 1, notation=QDoubleValidator.StandardNotation)
        self.eut_boot_validator.setLocale(QLocale(QLocale.English))

        eut_boot_layout = QHBoxLayout()
        eut_boot_label = QLabel('(Optional) EUT boot time to intended operation mode:')
        self.eut_boot_input = QLineEdit()
        self.eut_boot_input.setValidator(self.eut_boot_validator)
        self.eut_boot_input.setFixedWidth(tags.inputfield_width)
        sec_label = QLabel('s')

        eut_boot_layout.addWidget(eut_boot_label)
        eut_boot_layout.addStretch()
        eut_boot_layout.addWidget(self.eut_boot_input)
        eut_boot_layout.addWidget(sec_label)

        # Finish up manufacturer info group
        man_info_layout.addWidget(self.op_freq_input)
        man_info_layout.addWidget(self.op_channel_width_input)
        man_info_layout.addLayout(nom_volt_layout)
        man_info_layout.addLayout(ac_freq_layout)
        man_info_layout.addLayout(eut_boot_layout)

        man_info_group.setLayout(man_info_layout)

        
        ### Test parameters group
        parameters_group = QGroupBox('Test Parameters')
        parameters_layout = QVBoxLayout()
        
        # ERP adjustment
        self.dbm_validator = QDoubleValidator(-50, 50, 2, notation=QDoubleValidator.StandardNotation)
        self.dbm_validator.setLocale(QLocale(QLocale.English))

        erp_layout = QHBoxLayout()
        erp_label = QLabel('(Optional) Maximum e.r.p as measured (SAC):')
        self.erp_input = QLineEdit()
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
        self.min_temp_input = QLineEdit()
        self.min_temp_input.setValidator(self.temp_validator)
        self.min_temp_input.setPlaceholderText("Min Temp.")
        self.min_temp_input.setFixedWidth(tags.inputfield_width)
        self.max_temp_input = QLineEdit()
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
        self.min_volt_input = QLineEdit()
        self.min_volt_input.setValidator(self.volt_validator)
        self.min_volt_input.setPlaceholderText("Min Voltage")
        self.min_volt_input.setFixedWidth(tags.inputfield_width)
        self.max_volt_input = QLineEdit()
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
        self.checkbox_temp = QCheckBox('Include extreme temperature testing')
        self.checkbox_volt = QCheckBox('Include extreme voltage testing')
        self.checkbox_dm2 = QCheckBox('EUT generates test signal of type D-M2')
        
        # Start measurement button
        bold_font = QFont()
        bold_font.setBold(True)
        self.start_button = QPushButton('Start Automated Measurement')
        self.start_button.setFont(bold_font)
        self.start_button.clicked.connect(self.execute_measurement)

        # Stop measurement button
        self.stop_button = QPushButton('Interrupt Automated Measurement')
        self.stop_button.setEnabled(False)

        exec_layout.addWidget(self.checkbox_obw)
        exec_layout.addWidget(self.checkbox_oob)
        exec_layout.addWidget(self.checkbox_temp)
        exec_layout.addWidget(self.checkbox_volt)
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
        input_field = QLineEdit()
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

        if not self.proj_input.text():
            QMessageBox.warning(self, 'Input Error', 'Please enter the project number.')
            return False
        if not self.op_freq_input.input_field.text():
            QMessageBox.warning(self, 'Input Error', 'Please enter the operating frequency.')
            return False
        if not self.nom_volt_input.text():
            QMessageBox.warning(self, 'Input Error', 'Please enter the nominal operating voltage.')
            return False
        if not self.op_channel_width_input.input_field.text():
            QMessageBox.warning(self, 'Input Error', 'Please enter the operating channel width.')
            return False
        if not self.selected_path_label.text():
            QMessageBox.warning(self, 'Input Error', 'Please select a path for saving screenshots.')
            return False

        if self.checkbox_temp.isChecked():
            if not self.min_temp_input.text() or not self.max_temp_input.text():
                QMessageBox.warning(self, 'Input Error', 'Please enter the extreme temperature range.')
                return False

        if self.checkbox_volt.isChecked():
            if not self.min_volt_input.text() or not self.max_volt_input.text():
                QMessageBox.warning(self, 'Input Error', 'Please enter the extreme voltage range.')
                return False

        return True

    # convert frequency of specific unit multiple to Hz for further consistent processing
    def convert_freq(self, freq, unit):
        if unit == 'kHz':
            return int(freq * 1000)
        if unit == 'MHz':
            return int(freq * 1000000)
        if unit == 'GHz':
            return int(freq * 1000000000)

    def execute_measurement(self):

        if self.validate_inputs():
            
            ## Preparation and extraction of relevant input from GUI
            self.status_bar.showMessage('Measurement started...')
            QApplication.processEvents()
            
            # Start timer to measure time elapsed
            self.timer = QTimer()
            self.start_time = QTime.currentTime()
            self.timer.start(1000)  # Update every second

            # Extract project number
            project_nr = self.proj_input.text().replace(" ", "-").replace("/", "-")

            # Centre frequency
            freq_unit = self.op_freq_input.unit_selector.currentText()
            centre_freq_raw = self.op_freq_input.input_field.text()
            centre_freq = self.convert_freq(float(centre_freq_raw), freq_unit)

            # Span
            freq_unit = self.op_channel_width_input.unit_selector.currentText()
            ocw_raw = self.op_channel_width_input.input_field.text()
            ocw = self.convert_freq(float(ocw_raw), freq_unit)

            ## Prepare inputs and execute measurements in asynchronous thread
            inputs = {
                'path': self.selected_path_label.text(),
                'filename_obw': f"{datetime.datetime.now().strftime('%Y-%m-%d_')}" + project_nr + "_" + "OccupiedBandwidth.jpg",
                'filename_oob_oc': f"{datetime.datetime.now().strftime('%Y-%m-%d_')}" + project_nr + "_" + "OOB-OC.jpg",
                'filename_oob_ofb': f"{datetime.datetime.now().strftime('%Y-%m-%d_')}" + project_nr + "_" + "OOB-OFB-center.jpg",
                'centre_freq': centre_freq,
                'ocw': ocw,
                'voltage': self.nom_volt_input.text(),
                'measure_obw': self.checkbox_obw.isChecked(),
                'measure_oob': self.checkbox_oob.isChecked()
            }

            self.measurement_thread = MeasurementThread(self, self.fsv, self.sps, self.standard, inputs)
            self.measurement_thread.measurement_complete.connect(self.display_results)
            self.measurement_thread.start()
            self.start_button.setEnabled(False)
            self.stop_button.setEnabled(True)
    
    # function containing all GUI and instrument logic for occupied bandwidth measurement
    def execute_obw_measurement(self, ocw, centre_freq, path, filename_obw):
        self.status_bar.showMessage('Measuring occupied bandwidth...')
        tags.log('main', 'Starting OBW measurement.')
        QApplication.processEvents()

        obw_parameters = self.standard.calc_obw_parameters(ocw)

        return self.fsv.measure_obw(filename_obw, path, centre_freq, obw_parameters)

    # function containing all GUI and instrurment logic for out-of-band emissions measurement
    def execute_oob_measurement(self, ocw, centre_freq, path, filename_oob_oc, filename_oob_ofb):
        self.status_bar.showMessage('Measuring out-of-band emissions for the operating channel...')
        tags.log('main', 'Starting OOB operating channel measurement.')
        QApplication.processEvents()

        oob_parameters = self.standard.calc_oob_parameters(ocw)
        self.fsv.prep_oob_parameters(centre_freq, oob_parameters)

        limit_points_oc = self.standard.calc_limit_oc(centre_freq, ocw)
        oc_pass = self.fsv.measure_oob_oc(limit_points_oc, filename_oob_oc, path)
    
        self.status_bar.showMessage('Measuring out-of-band emissions for the operational frequency band...')
        tags.log('main', 'Starting OOB operational frequency band measurement.')
        QApplication.processEvents()

        f_low, f_high = self.determine_freq_range(centre_freq, fhss=False)  # TODO: FHSS true/false in der GUI abfragen

        limit_points_ofb = self.standard.calc_limit_ofb(f_low, f_high)
        ofb_pass = self.fsv.measure_oob_ofb(limit_points_ofb, filename_oob_ofb, path)

        # cleanup display
        self.fsv.set_center_freq(centre_freq)
        self.fsv.set_span(6*ocw)

        return oc_pass, ofb_pass
    
    # function containing logic for applying nominal voltage with GUI input
    def apply_nom_voltage(self, voltage):
        voltage = float(voltage)

        if voltage > 270.0 or voltage <= 0.0:
            QMessageBox.warning(self, 'Input Error', 'Please enter a valid voltage.')
            return
        
        if self.dc_radio.isChecked():
            self.sps.set_voltage_dc(voltage)
        else:
            ac_freq = self.frequency_input.text()
            if not ac_freq or int(ac_freq) > 100:
                ac_freq = 50
                self.frequency_input.setText('50')

            self.sps.set_voltage_ac(voltage, ac_freq)

        ## TODO: check if voltage was succesfully applied 
        delay = 10
        if self.eut_boot_input.text():
            delay = float(self.eut_boot_input.text())

        sleep(delay)       # allow for EUT to boot and reach normal operating mode

    # display results in bottom of GUI
    def display_results(self, results):

        self.timer.stop()
        elapsed_time = self.start_time.secsTo(QTime.currentTime())
        self.status_bar.showMessage(f'Measurement complete. Total time: {elapsed_time} seconds')
        tags.log('main', f'Automated measurement complete. Time elapsed: {elapsed_time}s')
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)

        obw_measured = results.get('obw_measured', False)
        oob_measured = results.get('oob_measured', False)
        
        if obw_measured:
            obw = results['obw']
            self.obw_result_label.setText(f'Measured Occupied Bandwidth: <b>{self.fsv.format_freq(str.strip(obw))}</b>')
        
        if oob_measured:
            oc_pass = results['oc_pass']
            oc_status = "OOB Operating Channel Test: <b><font color='green'>PASS</font></b>" if oc_pass else "Operating Channel: <b><font color='red'>FAIL</font></b>"
            self.op_channel_result_label.setText(oc_status)
            
            ofb_pass = results['ofb_pass']
            ofb_status = "OOB Operational Frequency Band Test: <b><font color='green'>PASS</font></b>" if ofb_pass else "Operational Frequency Band: <b><font color='red'>FAIL</font></b>"
            self.op_band_result_label.setText(ofb_status)

        self.screenshots_path_label.setText(f'Screenshots saved at: <a href="{self.selected_path_label.text()}">{self.selected_path_label.text()}</a>')

    # determine frequency range with given operating frequency. returns lower and upper limits
    def determine_freq_range(self, freq, fhss: bool, filename="ERC-data/bands_03-2024.csv"):

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
    app = QApplication(sys.argv)
    window = OutOfBandMeasurementAutomation()
    window.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
