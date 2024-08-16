"""
file: implementation of class for climatic test chamber based on work by Matias Senger on GitHub
author: rueck.joshua@gmail.com
last updated: 02/08/2024
"""

import socket
from threading import RLock
import tags
from time import sleep

# relevant commands in communicating with climatic test chamber as per S!MPAC simserv protocol
cmd_getinfo_type = b'99997\xb61\xb61\r'
cmd_getinfo_year = b'99997\xb61\xb62\r'
cmd_getinfo_serial = b'99997\xb61\xb63\r'
cmd_settmp = b'11001\xb61\xb61\xb6'
cmd_gettemp = b'11004\xb61\xb61\r'
cmd_start = b'14001\xb61\xb61\xb61\r'
cmd_stop = b'14001\xb61\xb61\xb60\r'
cmd_getrunning = b'14003\xb61\xb61\r'

class WKL:

    # initialize instance and communication with device via direct socket connection
    def __init__(self, ip: str, timeout=1):
        self.communication_lock = RLock()
        self.temperature_min = -40
        self.temperature_max = 180
        with self.communication_lock:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((ip, 2049))
            self.socket.settimeout(timeout)

    # helper function for low level communication with climate chamber
    def _send_and_receive(self, command):
        with self.communication_lock:
            self.socket.send(command)
            response_raw = self.socket.recv(512)
        response = response_raw.decode('utf-8', errors='backslashreplace').replace('\\xb6', '¶').replace('\r\n', '')
        return response.split('¶')[1:]

    # string attribute of WKL providing identifying information of device
    @property
    def idn(self):
        type = self._send_and_receive(cmd_getinfo_type)[0]
        year = self._send_and_receive(cmd_getinfo_year)[0]
        serial = self._send_and_receive(cmd_getinfo_serial)[0]
        return f'Climate Chamber Weiss Technik {type}, {year}, {serial}'
    
    # float attribute of WKL containing the current temperature measured by internal thermometer of WKL
    @property
    def current_temp(self):
        temp_raw = self._send_and_receive(cmd_gettemp)
        temp = temp_raw[0]
        return float(temp)

    # boolean attribute of WKL defining if climate chamber is running or not
    @property
    def is_running(self):
        status_raw = self._send_and_receive(cmd_getrunning)
        status = status_raw[0]
        if status == '1':
            return True
        elif status == '0':
            return False
        else:
            raise RuntimeError(f'Unexpected response for running status: {status}')

    # set temperature of climate chamber
    def set_temp(self, temp):
        if self.temperature_min <= temp <= self.temperature_max:
            cmd = cmd_settmp + f'{temp}'.encode('ascii') + b'\r'
            with self.communication_lock:
                self.socket.send(cmd)
            tags.log('WKL', f'Temperature set to {temp} °C.')
            return True
        else:
            raise ValueError("Temperature must be between -40 and 180 degrees Celsius.")

    # start operation of climate chamber
    def start(self):
        with self.communication_lock:
            self.socket.send(cmd_start)
            response_raw = self.socket.recv(512)    # two socket reads to clear buffer, turned out to be necessary during testing
            response_raw = self.socket.recv(512)
            tags.log('WKL', 'Climate chamber turned on.')
            sleep(1)

    # stop operationg of climate chamber
    def stop(self):
        with self.communication_lock:
            self.socket.send(cmd_stop)
            response_raw = self.socket.recv(512)    # socket read to clear buffer
            tags.log('WKL', 'Climate chamber turned off.')
            sleep(1)