"""
file: 
author: 
last updated:
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
from PyQt5.QtCore import Qt, QTime, QTimer, QLocale
from PyQt5.QtGui import QDoubleValidator, QFont, QPalette, QColor

class OutOfBandMeasurementAutomation(QWidget):
    def __init__(self):
        super().__init__()

        self.fsv = fsv.FSV(tags.fsv_addr)
        self.sps = sps.SPS(tags.sps_addr)
        self.fsv.initialize()
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
        erp_label = QLabel('Maximum e.r.p as measured (SAC):')
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
        self.start_button = QPushButton('Start Automated Measurement')
        self.start_button.clicked.connect(self.execute_oob_measurement)

        exec_layout.addWidget(self.checkbox_obw)
        exec_layout.addWidget(self.checkbox_oob)
        exec_layout.addWidget(self.checkbox_temp)
        exec_layout.addWidget(self.checkbox_volt)
        exec_layout.addWidget(self.start_button)

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

        always_required_inputs = (
            self.proj_input.text() and
            self.op_freq_input.input_field.text() and
            self.nom_volt_input.text() and
            self.op_channel_width_input.input_field.text() and
            self.selected_path_label.text()
        )

        total_input = always_required_inputs

        if self.checkbox_temp.isChecked():
            further_inputs = (
                self.min_temp_input.text() and
                self.max_temp_input.text()
            )
            total_input = further_inputs and always_required_inputs

        if self.checkbox_volt.isChecked():
            further_inputs = (
                self.min_volt_input.text() and
                self.max_volt_input.text()
            )
            total_input = further_inputs and always_required_inputs

        return total_input

    # convert frequency of specific unit multiple to Hz for further consistent processing
    def convert_freq(self, freq, unit):
        if unit == 'kHz':
            return int(freq * 1000)
        if unit == 'MHz':
            return int(freq * 1000000)
        if unit == 'GHz':
            return int(freq * 1000000000)

    def execute_oob_measurement(self):

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

            # Extract path
            path = self.selected_path_label.text()

            # Set screenshot filenames
            filename_obw = f"{datetime.datetime.now().strftime('%Y-%m-%d_')}" + project_nr + "_" + "OccupiedBandwidth.jpg"
            filename_oob_oc = f"{datetime.datetime.now().strftime('%Y-%m-%d_')}" + project_nr + "_" + "OOB-OC.jpg"
            filename_oob_ofb = f"{datetime.datetime.now().strftime('%Y-%m-%d_')}" + project_nr + "_" + "OOB-OFB-center.jpg"

            # Centre frequency
            freq_unit = self.op_freq_input.unit_selector.currentText()
            centre_freq_raw = self.op_freq_input.input_field.text()
            centre_freq = self.convert_freq(float(centre_freq_raw), freq_unit)

            # Span
            freq_unit = self.op_channel_width_input.unit_selector.currentText()
            ocw_raw = self.op_channel_width_input.input_field.text()
            ocw = self.convert_freq(float(ocw_raw), freq_unit)

            # ERP adjustment
            if self.erp_input.text():
                self.fsv.adjust_erp(self.erp_input.text(), centre_freq, ocw, 100000)

            ## Parameters change from here on out, depending on tests performed
            if self.checkbox_obw.isChecked() and self.checkbox_obw.isChecked():

                # First: OBW measurement
                self.status_bar.showMessage('Measuring occupied bandwidth...')
                tags.log('main', 'Starting OBW measurement.')
                QApplication.processEvents()

                obw_parameters = self.standard.calc_obw_parameters(ocw)

                measured_bandwidth = self.fsv.measure_obw(filename_obw, path, centre_freq, obw_parameters)

                # Second: OOB measurement
                self.status_bar.showMessage('Measuring out-of-band emissions for the operating channel...')
                tags.log('main', 'Starting OOB operating channel measurement.')
                QApplication.processEvents()

                oob_parameters = self.standard.calc_oob_parameters(ocw)
                self.fsv.prep_oob_parameters(oob_parameters)

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

                # Stop timer and display results
                self.timer.stop()
                elapsed_time = self.start_time.secsTo(QTime.currentTime())
                self.status_bar.showMessage(f'Measurement complete. Total time: {elapsed_time} seconds')
                self.display_results(measured_bandwidth, oc_pass, ofb_pass)
                tags.log('main', f'Automated measurement complete. Time elapsed: {elapsed_time}')

        else:
            QMessageBox.warning(self, 'Input Error', 'Please fill out all fields and select a path before starting the measurement.')
    

    # display results in bottom of GUI
    def display_results(self, obw, oc_pass, ofb_pass):
        self.obw_result_label.setText(f'Measured Occupied Bandwidth: <b>{self.fsv.format_freq(str.strip(obw))}</b>')
        oc_status = "OOB Operating Channel Test: <b><font color='green'>PASS</font></b>" if oc_pass else "Operating Channel: <b><font color='red'>FAIL</font></b>"
        self.op_channel_result_label.setText(oc_status)
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
