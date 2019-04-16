import lcddriver
import RPi.GPIO as GPIO
import time
import requests
import datetime

GPIO.setmode(GPIO.BCM)

lcd = lcddriver.lcd()
lcd.lcd_clear()
lcd.lcd_display_string("Tray Dryer", 1)
lcd.lcd_display_string("Control System", 2)

ip = 'http://10.3.141.1:8023'

MATRIX = [
    ['1', '4', '7', '*'],
    ['2', '5', '8', '0'],
    ['3', '6', '9', '#'],
    ['A', 'B', 'C', 'D']
]

ROW_PINS = [18, 23, 24, 25]
COL_PINS = [12, 16, 20, 21]

# Set GPIO Pins
for i in range(4):
    GPIO.setup(ROW_PINS[i], GPIO.IN, pull_up_down=GPIO.PUD_UP)

for j in range(4):
    GPIO.setup(COL_PINS[j], GPIO.OUT)
    GPIO.output(COL_PINS[j], 1)


def getKey(prompt="", prompt2=""):
    finput = ""

    if(prompt == "" and prompt2 == ""):
        pass
    else:
        lcd.lcd_clear()
        lcd.lcd_display_string(prompt, 1)
        lcd.lcd_display_string(prompt2, 2)
        lcd.lcd_display_string("(A)OK (B)BSp (C)Cncl", 4)

    try:
        GPIO.output(12, 1)
        GPIO.output(16, 1)
        GPIO.output(20, 1)
        GPIO.output(21, 1)

        while True:
            # test #
            for j in range(4):
                GPIO.output(COL_PINS[j], 0)
            # time.sleep(0.1)
                for i in range(4):
                    if GPIO.input(ROW_PINS[i]) == 0:
                        key = (MATRIX[i][j])

                        if (key == "A"):
                            time.sleep(0.8)
                            return finput
                        elif (key == "B"):
                            finput = finput[:-1]
                            lcd.lcd_clear()
                            lcd.lcd_display_string(prompt, 1)
                            lcd.lcd_display_string(prompt2, 2)
                            lcd.lcd_display_string(finput, 3)
                            lcd.lcd_display_string("(A)OK (B)BSp (C)Cncl", 4)
                            time.sleep(0.8)
                        elif (key == "C"):
                            finput = ""
                            lcd.lcd_clear()
                        elif (key == "D"):
                            main()
                        elif (key == "#"):
                            return key
                        elif (key == "*"):
                            return key
                        else:
                            finput = finput + key
                            lcd.lcd_display_string(finput, 3)
                            time.sleep(0.8)

                        # while(GPIO.input(ROW_PINS[i]) == 0):
                        #    pass
                GPIO.output(COL_PINS[j], 1)
            # time.sleep(0.2)
    except KeyboardInterrupt:
        GPIO.cleanup()


# get functions #


def get_set_temp():
    prompt = "Please enter the set"
    prompt2 = "temp for the process"
    set_temp = getKey(prompt, prompt2)
    return set_temp


def get_cook_time_hours():
    prompt = "Enter the desired"
    prompt2 = "cook time hours"
    cook_time = getKey(prompt, prompt2)

    if(cook_time == ''):
        return '0'

    return cook_time


def get_cook_time_mins():
    prompt = "Enter the desired"
    prompt2 = "cook time mins"
    cook_time = getKey(prompt, prompt2)

    if(cook_time == ''):
        return '0'

    return cook_time


def get_cook_time_secs():
    prompt = "Enter the desired"
    prompt2 = "cook time secs"
    cook_time = getKey(prompt, prompt2)

    if(cook_time == ''):
        return '0'

    return cook_time


def get_cook_time():
    h = int(get_cook_time_hours())
    m = int(get_cook_time_mins())
    s = int(get_cook_time_secs())

    return str((((h * 60) + m) * 60) + s)


def get_read_interval():
    prompt = "Enter the interval"
    prompt2 = "to read data"
    read_interval = getKey(prompt, prompt2)
    return read_interval


def get_initial_weight():
    prompt = "Enter initial"
    prompt2 = "weight"
    initial_weight = getKey(prompt, prompt2)
    return initial_weight


def getTempAndHum():
    r = requests.get(ip + '/data')
    data = r.json()
    ctemp = data['temperature']
    chum = data['humidity']
    lcd.lcd_clear()
    lcd.lcd_display_string("Data", 1)
    lcd.lcd_display_string("Temp: " + str(ctemp), 3)
    lcd.lcd_display_string("Hum: " + str(chum), 4)


def checkProcess():
    r = requests.get(ip + '/check')
    data = r.json()

    status = data['stopped']

    if not status:
        return False
    else:
        return True


def stopProcess():
    r = requests.get(ip + '/stop')
    data = r.json()

    status = data['stopped']

    print(status)


def sequence():
    lcd.lcd_clear()

    name = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
    set_temp = get_set_temp()
    cook_time = get_cook_time()
    read_interval = get_read_interval()
    initial_weight = get_initial_weight()

    lcd.lcd_clear()
    lcd.lcd_display_string("Press # to send", 1)
    """lcd.lcd_display_string(set_temp + " C", 2)
    lcd.lcd_display_string(cook_time + " sec", 3)
    lcd.lcd_display_string(read_interval + " sec", 4) """

    key = getKey()

    while(key != '#'):
        key = getKey()

    lcd.lcd_clear()
    lcd.lcd_display_string("Sending...", 1)
    time.sleep(1)
    lcd.lcd_clear()
    lcd.lcd_display_string("Sent", 1)
    time.sleep(1)

    lcd.lcd_clear()

    return name, set_temp, cook_time, read_interval, initial_weight


def login():
    url = ip + '/login'
    r = requests.get(url, auth=('admin', 'admin'))
    print(r.status_code)
    data = r.json()

    return data['token']


def set_variables():
    token = login()
    name, stemp, ctime, rinte, initw = sequence()
    url = ip + '/process'

    headers = {
        'x-access-token': token
    }

    datas = {
        "name": str(name),
        "stemp": int(stemp),
        "ctime": float(ctime),
        "rinte": float(rinte),
        "initw": float(initw)
    }

    r = requests.post(url, headers=headers, json=datas)

    print(r.status_code)


def main():
    time.sleep(2)
    try:
        while True:
            if checkProcess():
                set_variables()
            else:
                key = getKey()
                if(key == '*'):
                    stopProcess()
    except:
        lcd.lcd_clear()
        lcd.lcd_display_string("Make sure the server", 1)
        lcd.lcd_display_string("is online", 2)


main()
