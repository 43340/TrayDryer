#!/usr/bin/python

# -*- coding: utf-8 -*-

""" Custom SI7021 module
Minimal SI7021 module to interface with the SI7021 sensor.
Class uses the PiGPIO library to access the GPIO. This module
only include methods to get the Temperature and Relative Humidity 
and do not include any other features. This is created for my use
case as I am using a software i2c channel as well as something to
use to learn how to create python modules. This is pretty much a 
stripped down version of saper_2's code so if you want a fully
featured module please look into his module @
http://github.com/saper-2/python-si7021

Credits:
        Me - 43340
        saper_2 - I used his code as a basis for this module
        PiGPIO - http://abyz.me.uk/rpi/gpio
License:
        MIT
"""

import time
import pigpio

class si7021:
    def __init__(self, _piBus, _address=0x40, _readMode=0):
        """Initialize SI7021 interface class.

        Args:
                _piBus: Raspberry Pi I2C bus number
                _address: SI7021 I2C address
                _readmode: Measurement RH/Temp exec & readmode
        Returns:
                none
        """
        self.piBus = int(_piBus)
        self.address = int(_address)
        self.pio = pigpio.pi()
        self.readMode = int(_readMode)
    

    def __del__(self):
        self.pio.stop()

    
    # SI7021_DEF_ADDR=Ox40
    SI7021_CMD_MEAS_HUMI_NO_HOLD_MASTER=0xF5
    SI7021_CMD_MEAS_TEMP_NO_HOLD_MASTER=0xF3
    SI7021_CMD_RESET=0xFE
    SI7021_CMD_READ_EID2=0xFC


    def Reset(self):
        dev = self.pio.i2c_open(self.piBus, self.address)
        self.pio.i2c_write_byte(dev, self.SI7021_CMD_RESET);
        self.pio.i2c_close(dev)
        time.sleep(0.1)
        return
    

    def Humidity(self):
        """
        Perform humidity measurement.
        Uses NO HOLD MASTER mode.
        The conversion result after issuing commandis read back after a delay of 30ms.
        Minimum safe time is about 12ms according to datasheet.

        Args:
            none
        Returns:
            RH value (int)
        """
        dev = self.pio.i2c_open(self.piBus, self.address)
        self.pio.i2c_write_byte(dev, self.SI7021_CMD_MEAS_HUMI_NO_HOLD_MASTER)
        time.sleep(0.03) # 30 ms. Minimum of 12ms
        (count, data) = self.pio.i2c_read_device(dev, 2)
        self.pio.i2c_close(dev)
        lsb = data[1] & self.SI7021_CMD_READ_EID2
        msb = data[0]
        measurement = int(msb << 8 | lsb)
        humidity = (125.0 * measurement / 65536) - 6
        return humidity


    def Temperature(self):
        """
        Perform temperature measurement
        Uses NO HOLD MASTER mode
        The conversion result after issuing commandis read back after a delay of 20ms.
        Minimum safe time is about 11ms according to datasheet.

        Args:
            none
        Return:
            Temp value (int)
        """
        dev = self.pio.i2c_open(self.piBus, self.address)
        self.pio.i2c_write_byte(dev, self.SI7021_CMD_MEAS_TEMP_NO_HOLD_MASTER)
        time.sleep(0.2) # 20ms. Minimum of 11ms
        (count, data) = self.pio.i2c_read_device(dev, 2)
        self.pio.i2c_close(dev)
        lsb = data[1] & 0xFC
        msb = data[0]
        measurement = int(msb << 8 | lsb)
        temperature = (175.72 * measurement / 65536) - 46.85
        return temperature
    

    def GetTempHumi(self):
        temp = self.Temperature()
        humi = self.Humidity()
        return temp, humi
