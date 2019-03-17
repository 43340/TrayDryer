#!/usr/bin/python

# -*- coding: utf-8 -*-

import time
import RPi.GPIO as GPIO
import lcddriver

GPIO.setmode(GPIO.BCM)

lcd = lcddriver.lcd()
lcd.lcd_clear()

MATRIX = [
    ['1','2','3','A'],
    ['4','5','6','B'],
    ['7','8','9','C'],
    ['*','0','#','D']
]

ROW_PINS = [18, 23, 24, 25]
COL_PINS = [12, 16, 20, 21]

# Set GPIO Pins
for i in range(4):
    GPIO.setup(ROW_PINS[i], GPIO.IN, pull_up_down = GPIO.PUD_UP)

for j in range(4):
    GPIO.setup(COL_PINS[j], GPIO.OUT)
    GPIO.output(COL_PINS[j], 1)

class Keypad:
    def __init__(self, ):
        """Initialize Keypad interface class"""