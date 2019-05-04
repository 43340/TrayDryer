#!/usr/bin/env python3
from gpiozero import Button
from signal import pause
import time
import os, sys
import lcddriver

offGPIO = int(sys.argv[1]) if len(sys.argv) >=2 else 22
holdTime = int(sys.argv[2]) if len(sys.argv) >= 3 else 6
lcd = lcddriver.lcd()

def shutdown():
	lcd.lcd_clear()
	print("Shutdown")
	time.sleep(1)
	os.system("sudo poweroff")

btn = Button(offGPIO, hold_time=holdTime)
btn.when_held = shutdown
pause()
