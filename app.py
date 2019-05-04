#!/usr/bin/python
# -*- coding: utf-8 -*-
# xzx
from flask import Flask, request, jsonify, make_response, render_template, send_file
from flask_sqlalchemy import SQLAlchemy
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash
from threading import Thread
from flask_socketio import SocketIO, emit
import threading
from flask_cors import CORS, cross_origin
import flask_excel as excel
import xlsxwriter
import uuid
import math
import jwt
import pdfkit
import time
import datetime
import os
import si7021
import RPi.GPIO as GPIO
import pigpio
import lcddriver

app = Flask(__name__)
CORS(app)
app.config['SECRET_KEY'] = 'thisissecret'
socketio = SocketIO(app)
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + \
    os.path.join(basedir, 'dryer.db')

# os.system('python /home/pi/dryer/lcdkp.py &')

pi = pigpio.pi()
sensor1 = si7021.si7021(1)
sensor2 = si7021.si7021(4)
sensor3 = si7021.si7021(3)
pin = 26
fan = 6
pi.set_mode(pin, pigpio.OUTPUT)
pi.set_mode(fan, pigpio.OUTPUT)
global pause_run
global stop_run
global start_read
global read_counter
global timer
global time_left
global tempc
global tempc1
global tempc2
global tempc3
global humc
global humc1
global humc2
global humc3
global time_left
global fan_speed
fan_speed = 63
time_left = ""
tempc = ""
tempc1 = ""
tempc2 = ""
tempc3 = ""
humc = ""
humc1 = ""
humc2 = ""
humc3 = ""
timer = 0
start_read = False
stop_run = True
pause_run = False
read_counter = 0
pi.write(pin, 0)
pi.write(fan, 0)
lcd = lcddriver.lcd()
lcd.lcd_clear()
lcd.lcd_display_string("Tray Dryer", 1)
lcd.lcd_display_string("Control System", 2)

db = SQLAlchemy(app)


#  ███╗   ███╗ ██████╗ ██████╗ ███████╗██╗     ███████╗
#  ████╗ ████║██╔═══██╗██╔══██╗██╔════╝██║     ██╔════╝
#  ██╔████╔██║██║   ██║██║  ██║█████╗  ██║     ███████╗
#  ██║╚██╔╝██║██║   ██║██║  ██║██╔══╝  ██║     ╚════██║
#  ██║ ╚═╝ ██║╚██████╔╝██████╔╝███████╗███████╗███████║
#  ╚═╝     ╚═╝ ╚═════╝ ╚═════╝ ╚══════╝╚══════╝╚══════╝
#
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    public_id = db.Column(db.String(50), unique=True)
    name = db.Column(db.String(50))
    password = db.Column(db.String(80))
    admin = db.Column(db.Boolean)


class ProcessData(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    process_id = db.Column(db.String(50), unique=True)
    name = db.Column(db.String(50))
    set_temp = db.Column(db.Integer)
    cook_time = db.Column(db.Integer)
    read_int = db.Column(db.Integer)
    initial_w = db.Column(db.Integer)
    final_w = db.Column(db.Integer)
    time_stamp = db.Column(db.String(80))
    user_id = db.Column(db.Integer)  # now uses string but db still set as int


class DHTData(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    temp = db.Column(db.Integer)
    temp1 = db.Column(db.Integer)
    temp2 = db.Column(db.Integer)
    temp3 = db.Column(db.Integer)
    hum = db.Column(db.Integer)
    hum1 = db.Column(db.Integer)
    hum2 = db.Column(db.Integer)
    hum3 = db.Column(db.Integer)
    time_stamp = db.Column(db.String(80))
    process_id = db.Column(db.String(50))


#  ████████╗ ██████╗ ██╗  ██╗███████╗███╗   ██╗███████╗
#  ╚══██╔══╝██╔═══██╗██║ ██╔╝██╔════╝████╗  ██║██╔════╝
#     ██║   ██║   ██║█████╔╝ █████╗  ██╔██╗ ██║███████╗
#     ██║   ██║   ██║██╔═██╗ ██╔══╝  ██║╚██╗██║╚════██║
#     ██║   ╚██████╔╝██║  ██╗███████╗██║ ╚████║███████║
#     ╚═╝    ╚═════╝ ╚═╝  ╚═╝╚══════╝╚═╝  ╚═══╝╚══════╝
#
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None

        if 'x-access-token' in request.headers:
            token = request.headers['x-access-token']

        if not token:
            return jsonify({'message': 'Token is missing!'}), 401

        try:
            data = jwt.decode(token, app.config['SECRET_KEY'])
            current_user = User.query.filter_by(
                public_id=data['public_id']).first()
        except:
            return jsonify({'message': 'Token is invalid!'}), 401

        return f(current_user, *args, **kwargs)

    return decorated


#  ██╗   ██╗███████╗███████╗██████╗ ███████╗
#  ██║   ██║██╔════╝██╔════╝██╔══██╗██╔════╝
#  ██║   ██║███████╗█████╗  ██████╔╝███████╗
#  ██║   ██║╚════██║██╔══╝  ██╔══██╗╚════██║
#  ╚██████╔╝███████║███████╗██║  ██║███████║
#   ╚═════╝ ╚══════╝╚══════╝╚═╝  ╚═╝╚══════╝
#
@app.route('/user', methods=['GET'])
@token_required
def get_all_users(current_user):

    if not current_user.admin:
        return jsonify({'message': 'Cannot perforn that function'})

    users = User.query.all()

    output = []

    for user in users:
        user_data = {}
        user_data['public_id'] = user.public_id
        user_data['name'] = user.name
        user_data['password'] = user.password
        user_data['admin'] = user.admin
        output.append(user_data)

    return jsonify(output)


@app.route('/user/<public_id>', methods=['GET'])
@token_required
def get_one_user(current_user, public_id):

    if not current_user.admin:
        return jsonify({'message': 'Cannot perforn that function'})

    user = User.query.filter_by(public_id=public_id).first()

    if not user:
        return jsonify({'message': 'No user found!'})

    user_data = {}
    user_data['public_id'] = user.public_id
    user_data['name'] = user.name
    user_data['password'] = user.password
    user_data['admin'] = user.admin

    return jsonify({'user': user_data})


@app.route('/user', methods=['POST'])
@token_required
def create_user(current_user):

    if not current_user.admin:
        return jsonify({'message': 'Cannot perform that function'})

    data = request.get_json()

    hashed_password = generate_password_hash(data['password'], method='sha256')

    new_user = User(public_id=str(uuid.uuid4()),
                    name=data['name'], password=hashed_password, admin=False)
    db.session.add(new_user)
    db.session.commit()

    return jsonify({'message': 'New user created'})


@app.route('/user/<public_id>', methods=['PUT'])
@token_required
def promote_user(current_user, public_id):

    if not current_user.admin:
        return jsonify({'message': 'Cannot perforn that function'})

    user = User.query.filter_by(public_id=public_id).first()

    if not user:
        return jsonify({'message': 'No user found!'})

    user.admin = True
    db.session.commit()

    return jsonify({'message': 'The user has been promoted!'})


@app.route('/user/<public_id>', methods=['DELETE'])
@token_required
def delete_user(current_user, public_id):

    if not current_user.admin:
        return jsonify({'message': 'Cannot perforn that function'})

    user = User.query.filter_by(public_id=public_id).first()

    if not user:
        return jsonify({'message': 'No user found!'})

    db.session.delete(user)
    db.session.commit()

    return jsonify({'message': 'The user has been deleted!'})


#  ██╗      ██████╗  ██████╗ ██╗███╗   ██╗
#  ██║     ██╔═══██╗██╔════╝ ██║████╗  ██║
#  ██║     ██║   ██║██║  ███╗██║██╔██╗ ██║
#  ██║     ██║   ██║██║   ██║██║██║╚██╗██║
#  ███████╗╚██████╔╝╚██████╔╝██║██║ ╚████║
#  ╚══════╝ ╚═════╝  ╚═════╝ ╚═╝╚═╝  ╚═══╝
#
@app.route('/login', methods=['GET', 'POST'])
def login():

    auth = request.authorization
    print(auth)

    if not auth or not auth.username or not auth.password:
        return make_response('Could not verify', 401, {'WWW-Authenticate': 'Basic realm="Login required"'})

    user = User.query.filter_by(name=auth.username).first()

    if not user:
        return make_response('Could not verify', 401, {'WWW-Authenticate': 'Basic realm="Login required"'})

    if check_password_hash(user.password, auth.password):
        token = jwt.encode({'public_id': user.public_id, 'exp': datetime.datetime.utcnow(
        ) + datetime.timedelta(days=1)}, app.config['SECRET_KEY'])

        return jsonify({
            'token': token.decode('UTF-8'),
            'user': user.name,
            'admin': user.admin
        })

    return make_response('Could not verify', 401, {'WWW-Authenticate': 'Basic realm="Login required"'})


#  ██████╗ ██████╗  ██████╗  ██████╗███████╗███████╗███████╗
#  ██╔══██╗██╔══██╗██╔═══██╗██╔════╝██╔════╝██╔════╝██╔════╝
#  ██████╔╝██████╔╝██║   ██║██║     █████╗  ███████╗███████╗
#  ██╔═══╝ ██╔══██╗██║   ██║██║     ██╔══╝  ╚════██║╚════██║
#  ██║     ██║  ██║╚██████╔╝╚██████╗███████╗███████║███████║
#  ╚═╝     ╚═╝  ╚═╝ ╚═════╝  ╚═════╝╚══════╝╚══════╝╚══════╝
#

# get all the registered users
@app.route('/process/admin', methods=['GET'])
@token_required
def get_all_processes(current_user):

    # check if the account is an admin
    if not current_user.admin:
        return jsonify({
            'message': 'Cannot perform that operation'
        }), 401

    # get all the processes in the database
    processes = ProcessData.query.all()

    output = []

    for process in processes:
        process_data = {}
        process_data['process_id'] = process.process_id
        process_data['name'] = process.name
        process_data['set_temp'] = process.set_temp
        process_data['cook_time'] = process.cook_time
        process_data['read_int'] = process.read_int
        process_data['initial_w'] = process.initial_w
        process_data['final_w'] = process.final_w
        process_data['time_stamp'] = process.time_stamp
        process_data['user_id'] = process.user_id
        output.append(process_data)

    return jsonify(output)

# get all processes by the user
@app.route('/process', methods=['GET'])
@token_required
def get_all_processes_by_user(current_user):  # only the users processes

    # get all the processes by the user
    processes = ProcessData.query.filter_by(
        user_id=current_user.name).all()

    output = []

    for process in processes:
        process_data = {}
        process_data['process_id'] = process.process_id
        process_data['name'] = process.name
        process_data['set_temp'] = process.set_temp
        process_data['cook_time'] = process.cook_time
        process_data['read_int'] = process.read_int
        process_data['initial_w'] = process.initial_w
        process_data['final_w'] = process.final_w
        process_data['time_stamp'] = process.time_stamp
        process_data['user_id'] = process.user_id
        output.append(process_data)

    return jsonify(output)


@app.route('/process', methods=['POST'])
@token_required
def new_process(current_user):
    global stop_run

    if not stop_run:
        return jsonify({'message': 'Process ongoing'}), 403
    data = request.get_json()

    pid = str(uuid.uuid4())
    ts = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    uid = current_user.name

    log_process_data(pid, data['name'], data['stemp'],
                     data['ctime'], data['rinte'], 0, ts, uid)

    run_process(pid, data['stemp'], data['ctime'], data['rinte'])

    return jsonify({'message': 'Process started!'})


@app.route('/process/reset')
@token_required
def reset_process(current_user):
    global stop_run

    process = ProcessData.query.order_by(ProcessData.id.desc()).first()

    if not stop_run:
        return jsonify({'message': 'Process ongoing'}), 403

    pid = str(uuid.uuid4())
    ts = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    uid = current_user.name

    log_process_data(pid, process.name, process.set_temp,
                     process.cook_time, process.read_int, process.initial_w, ts, uid)

    run_process(pid, process.set_temp, process.cook_time, process.read_int)

    return jsonify({'message': 'Process started!'})


@app.route('/process/<process_id>', methods=['DELETE'])
@token_required
def delete_process(current_user, process_id):

    process = ProcessData.query.filter_by(process_id=process_id).first()

    if not process:
        return jsonify({'message': 'Entry not found'})

    db.session.delete(process)
    db.session.commit()

    return jsonify({'message': 'The entry has been deleted!'})


#  ██████╗  █████╗ ████████╗ █████╗
#  ██╔══██╗██╔══██╗╚══██╔══╝██╔══██╗
#  ██║  ██║███████║   ██║   ███████║
#  ██║  ██║██╔══██║   ██║   ██╔══██║
#  ██████╔╝██║  ██║   ██║   ██║  ██║
#  ╚═════╝ ╚═╝  ╚═╝   ╚═╝   ╚═╝  ╚═╝
#
@app.route('/data/<process_id>', methods=['GET'])
@token_required
def get_process_by_id(current_user, process_id):
    print(current_user.id)

    # get the data per process
    dhtdata = DHTData.query.filter_by(process_id=process_id).all()

    output = []

    for data in dhtdata:
        dht_data = {}
        dht_data['temp'] = data.temp
        dht_data['temp1'] = data.temp1
        dht_data['temp2'] = data.temp2
        dht_data['temp3'] = data.temp3
        dht_data['hum'] = data.hum
        dht_data['hum1'] = data.hum1
        dht_data['hum2'] = data.hum2
        dht_data['hum3'] = data.hum3
        dht_data['time_stamp'] = data.time_stamp
        dht_data['process_id'] = data.process_id
        output.append(dht_data)

    return jsonify(output)


#  ███████╗██╗   ██╗███╗   ██╗ ██████╗████████╗██╗ ██████╗ ███╗   ██╗███████╗
#  ██╔════╝██║   ██║████╗  ██║██╔════╝╚══██╔══╝██║██╔═══██╗████╗  ██║██╔════╝
#  █████╗  ██║   ██║██╔██╗ ██║██║        ██║   ██║██║   ██║██╔██╗ ██║███████╗
#  ██╔══╝  ██║   ██║██║╚██╗██║██║        ██║   ██║██║   ██║██║╚██╗██║╚════██║
#  ██║     ╚██████╔╝██║ ╚████║╚██████╗   ██║   ██║╚██████╔╝██║ ╚████║███████║
#  ╚═╝      ╚═════╝ ╚═╝  ╚═══╝ ╚═════╝   ╚═╝   ╚═╝ ╚═════╝ ╚═╝  ╚═══╝╚══════╝
#
def send_current(temp, temp1, temp2, temp3, hum, hum1, hum2, hum3, time_left, stop_run):
    socketio.emit('some event', {
        'temp': temp,
        'temp1': temp1,
        'temp2': temp2,
        'temp3': temp3,
        'hum': hum,
        'hum1': hum1,
        'hum2': hum2,
        'hum3': hum3,
        'timeleft': time_left,
        'stop_run': stop_run
    })


def get_temphumi_data(pid=""):

    temp = (sensor1.Temperature() + sensor2.Temperature() + sensor3.Temperature()) / 3
    hum = (sensor1.Humidity() + sensor2.Humidity() + sensor3.Humidity()) / 3

    temp1 = sensor1.Temperature()
    temp2 = sensor2.Temperature()
    temp3 = sensor3.Temperature()
    temp = (temp1 + temp2 + temp3) / 3
    hum1 = sensor1.Humidity()
    hum2 = sensor2.Humidity()
    hum3 = sensor3.Humidity()
    hum = (hum1 + hum2 + hum3) / 3

    if hum is not None and temp is not None:
        ts = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        return temp, temp1, temp2, temp3, hum, hum1, hum2, hum3, ts


def log_data(pid, set_temp, cook_time, read_interval, base_time):
    try:
        global read_counter
        global stop_run
        global time_left
        global tempc
        global tempc1
        global tempc2
        global tempc3
        global humc
        global humc1
        global humc2
        global humc3

        temp, temp1, temp2, temp3, hum, hum1, hum2, hum3, ts = get_temphumi_data(pid)   
        timeleft = str(datetime.timedelta(seconds=cook_time))
        time_left = timeleft
        tempc = temp
        tempc1 = temp1
        tempc2 = temp2
        tempc3 = temp3
        humc = hum
        humc1 = hum1
        humc2 = hum2
        humc3 = hum3
        rtemp = round(temp, 2)
        rtemp1 = round(temp1, 2)
        rtemp2 = round(temp2, 2)
        rtemp3 = round(temp3, 2)
        rhum = round(hum, 2)
        rhum1 = round(hum1, 2)
        rhum2 = round(hum2, 2)
        rhum3 = round(hum3, 2)
        timer = str(datetime.datetime.now())  # float(base_time) - float(datetime.timedelta(seconds=cook_time).total_seconds())
        lcd.lcd_display_string("    |Ave|C1 |C2 |C3 ", 1)
        lcd.lcd_display_string("Temp|{}C|{}C|{}C|{}C".format(int(rtemp), int(rtemp1), int(rtemp2), int(rtemp3)), 2)
        lcd.lcd_display_string("Hum |{}%|{}%|{}%|{}%".format(int(rhum), int(rhum1), int(rhum2), int(rhum3)), 3)
        lcd.lcd_display_string("ETA: " + timeleft + "(*)Stop", 4)
        # lcd.lcd_display_string("(*)Stop", 4)

        send_current(str(rtemp), str(rtemp1), str(rtemp2), str(rtemp3), str(rhum), str(rhum1), str(rhum2), str(rhum3), timeleft, stop_run)

        adjust_heater_power(set_temp, temp)
        adjust_fan_power(set_temp, temp)

        if read_counter >= read_interval:
            read_counter = 0
            dht_data = DHTData(temp=rtemp, temp1=rtemp1, temp2=rtemp2,
                               temp3=rtemp3, hum=rhum, hum1=rhum1, hum2=rhum2,
                               hum3=rhum3, time_stamp=timer, process_id=pid)
            db.session.add(dht_data)
            db.session.commit()
        
        global pause_run
        if not pause_run:
            read_counter = read_counter + 2
            cook_time = cook_time - 2
        else:
            pi.write(pin, 0)
            pi.write(fan, 0)
    except Exception as error:
        print(error)
        dht_data = DHTData(temp=0, temp1=0, temp2=0,
                           temp3=0, hum=0, hum1=0, hum2=0,
                           hum3=0, time_stamp=str(datetime.datetime.now()), process_id=pid)
        db.session.add(dht_data)
        db.session.commit()
        pi.write(pin, 0)
        pi.write(fan, 0)


def do_every(period, f, pid, set_temp, cook_time, read_interval, base_time):
    def g_tick():
        t = time.time()
        count = 0
        while True:
            count += 1
            yield max(t + count*period - time.time(), 0)
    g = g_tick()
    while True:
        time.sleep(next(g))
        global pause_run
        if not pause_run:
            cook_time = cook_time - 2

        f(pid, set_temp, cook_time, read_interval, base_time)
        
        global stop_run
        if stop_run:
            global timer
            timer = 0
            pi.write(pin, 0)
            pi.write(fan, 0)
            break

        if cook_time <= 0:
            set_stop_run()
            break


def log_process_data(pid, name, set_temp, cook_time, read_interval, initial_weight, ts, current_user):

    process_data = ProcessData(process_id=pid, name=name, set_temp=set_temp,
                               cook_time=cook_time, read_int=read_interval, initial_w=initial_weight, time_stamp=ts, user_id=current_user)

    db.session.add(process_data)
    db.session.commit()


def adjust_heater_power(set_temp, current_temp):
    if set_temp <= current_temp:
        pi.write(pin, 0)
    else:
        pi.write(pin, 1)


def adjust_fan_power(set_temp, current_temp):
    global stop_run
    global fan_speed
    if stop_run:
        pi.write(fan, 0)
    else:
        pi.set_PWM_dutycycle(fan, fan_speed)


def start_process(pid, set_temp, cook_time, read_interval):
    global stop_run
    print(stop_run)

    while not stop_run:

        temp, temp1, temp2, temp3, hum, hum1, hum2, hum3, ts = get_temphumi_data(pid)
        adjust_heater_power(set_temp, temp)
        log_data(pid, temp, hum, ts, cook_time)
        lcd.lcd_clear()
        # do_every(read_interval, log_data, pid, set_temp, cook_time, read_interval)
        do_every(2, log_data, pid, set_temp, cook_time, read_interval, cook_time)

        # time.sleep(read_interval)
        cook_time = cook_time - read_interval

        if cook_time <= 0:
            set_stop_run()
            break

    pi.write(pin, 0)
    # pi.write(fan, 0)
    print("yay")
    set_stop_run
    return stop_run


@app.route('/data', methods=['GET'])
def get_th():
    global time_left
    global tempc
    global tempc1
    global tempc2
    global tempc3
    global humc
    global humc1
    global humc2
    global humc3
    global stop_run

    return jsonify({
        'temperature': "{}".format(tempc),
        'temperature1': "{}".format(tempc1),
        'temperature2': "{}".format(tempc2),
        'temperature3': "{}".format(tempc3),
        'humidity': "{}".format(humc),
        'humidity1': "{}".format(humc1),
        'humidity2': "{}".format(humc2),
        'humidity3': "{}".format(humc3),
        'timeleft': time_left,
        'stop': stop_run
    })


@app.route('/fan/inc', methods=['GET'])
def inc_fan():
    global fan_speed
    fan_speed = math.floor(fan_speed + 12.75)
    if(fan_speed > 255):
        fan_speed = 255
    print(fan_speed)

    return jsonify({'message': 'The fan speed has been increased!'})


@app.route('/fan/dec', methods=['GET'])
def dec_fan():
    global fan_speed
    fan_speed = math.floor(fan_speed - 12.75)
    if(fan_speed < 64):
        fan_speed = 64
    print(fan_speed)

    return jsonify({'message': 'The fan speed has been decreased!'})


@app.route('/check', methods=['GET'])
def check_stop():

    global stop_run

    return jsonify({'stopped': stop_run})


@app.route('/pause', methods=['GET'])
def set_pause():
    global pause_run

    pause_run = not pause_run

    return jsonify({'paused': pause_run})


@app.route('/stop', methods=['GET'])
def stop():

    set_stop_run()

    return jsonify({'stopped': stop_run})


@app.route('/process/<process_id>/<final_w>', methods=['PUT'])
@token_required
def set_final_weight(current_user, process_id, final_w):

    process = ProcessData.query.filter_by(process_id=process_id).first()

    if not process:
        return jsonify({'message': 'Process not found'})

    process.final_w = final_w
    db.session.commit()

    return jsonify({'message': 'The final weight has been set'})


@app.route("/process/report/<process_id>")
def dl_file(process_id):
    query_sets = DHTData.query.filter_by(process_id=process_id).all()
    column_names = ['time_stamp', 'temp', 'temp1', 'temp2', 'temp3', 'hum', 'hum1', 'hum2', 'hum3']
    return excel.make_response_from_query_sets(query_sets, column_names, "xls", file_name="{}".format(process_id))


@app.route("/download/report/<process_id>")
def download_file(process_id):
    print("Generating .xlsx file...")

    process = ProcessData.query.filter_by(process_id=process_id).first()
    dhtdata = DHTData.query.filter_by(process_id=process_id).all()

    output = []

    for data in dhtdata:
        dht_data = {}
        dht_data['temp'] = data.temp
        dht_data['temp1'] = data.temp1
        dht_data['temp2'] = data.temp1
        dht_data['temp3'] = data.temp3
        dht_data['hum'] = data.hum
        dht_data['hum1'] = data.hum1
        dht_data['hum2'] = data.hum2
        dht_data['hum3'] = data.hum3
        dht_data['time_stamp'] = data.time_stamp.split('.', 1)[0]
        dht_data['process_id'] = data.process_id
        output.append(dht_data)

    workbook = xlsxwriter.Workbook('{}.xlsx'.format(process_id))
    worksheet = workbook.add_worksheet()

    merge_format = workbook.add_format({
        'align':    'center',
        'valign':   'vcenter',
    })

    merge_format_title = workbook.add_format({
        'align':    'center',
        'valign':   'vcenter',
        'font_size': 20
    })

    merge_format_date = workbook.add_format({
        'align':    'right',
        'valign':   'vcenter',
    })

    merge_format_underline = workbook.add_format({
        'align':    'center',
        'valign':   'vcenter',
        'underline': True
    })

    border_format = workbook.add_format({
                            'border': 1,
                        })

    header = '&L&G&C\nMariano Marcos State University\nCollege of Engineering&R&G'
    footer = '&CSystem created by: Alfredo Costes Jr., Justin Moises Sebastian, Janeth Tolentino, Kathleen Mae Villanueva, Arvin John Yadao\nAdvisers: Engr. Samuel Franco, Engr. Vladimir Ibanez'

    worksheet.set_column(0, 0, 17.5)
    worksheet.set_column(1, 8, 12)

    worksheet.set_margins(top=1.5)
    worksheet.merge_range('A1:I1', process.name, merge_format_title)
    worksheet.merge_range('B2:C2', 'Set Temperature: {}'.format(process.set_temp), merge_format)
    worksheet.merge_range('D2:E2', 'Drying Time: {}'.format(str(datetime.timedelta(seconds=process.cook_time))), merge_format)
    worksheet.merge_range('F2:G2', 'Read Interval: {} minutes'.format((process.read_int / 60)), merge_format)
    worksheet.merge_range('A3:I3', '{}'.format(process.time_stamp), merge_format_date)
    worksheet.merge_range('B4:E4', 'Temperature', merge_format)
    worksheet.merge_range('F4:I4', 'Humidity', merge_format)
    worksheet.write('A5', 'Date/Time', border_format)
    worksheet.write('B5', 'Sensor 1', border_format)
    worksheet.write('C5', 'Sensor 2', border_format)
    worksheet.write('D5', 'Sensor 3', border_format)
    worksheet.write('E5', 'Average', border_format)
    worksheet.write('F5', 'Sensor 1', border_format)
    worksheet.write('G5', 'Sensor 2', border_format)
    worksheet.write('H5', 'Sensor 3', border_format)
    worksheet.write('I5', 'Average', border_format)
    worksheet.set_landscape()
    worksheet.set_header(header, {'image_left': 'mmsu-logo.png', 'image_right': 'coe-logo.png'})
    worksheet.set_footer(footer)

    ordered_list=["time_stamp", "temp", "temp1", "temp2", "temp3", "hum", "hum1", "hum2", "hum3", "process_id"]

    row = 5
    for data in output:
        for _key,_value in data.items():
            col=ordered_list.index(_key)
            worksheet.write(row, col, _value, border_format)
        row += 1
    
    row_name_sign = len(output) + 9
    worksheet.merge_range('G{}:I{}'.format(row_name_sign, row_name_sign), '___{}___'.format(process.user_id), merge_format_underline)
    worksheet.merge_range('G{}:I{}'.format(row_name_sign + 1, row_name_sign + 1), "Researcher", merge_format)

    worksheet.set_column('J:J', 20, merge_format, {'hidden': 1})

    workbook.close()

    response = make_response(send_file('{}.xlsx'.format(process_id)))
    response.headers['Content-Type'] = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    response.headers['Content-Disposition'] = 'attachment; filename={}.xlsx'.format(
        process_id)

    return response


""" @app.route('/process/report/<process_id>')
def pdf_template(process_id):
    process = ProcessData.query.filter_by(process_id=process_id).first()
    rendered = render_template('pdf_template.html', process_id=process_id, name=process.name, set_temp=process.set_temp, cook_time=str(datetime.timedelta(seconds=process.cook_time)), read_int=process.read_int, init_w=process.initial_w, time_stamp=process.time_stamp, username=process.user_id)
    pdf = pdfkit.from_string(rendered, False)

    response = make_response(pdf)
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = 'inline; filename={}.pdf'.format(process_id)

    return response """


#  ████████╗██╗  ██╗██████╗ ███████╗ █████╗ ██████╗ ███████╗
#  ╚══██╔══╝██║  ██║██╔══██╗██╔════╝██╔══██╗██╔══██╗██╔════╝
#     ██║   ███████║██████╔╝█████╗  ███████║██║  ██║███████╗
#     ██║   ██╔══██║██╔══██╗██╔══╝  ██╔══██║██║  ██║╚════██║
#     ██║   ██║  ██║██║  ██║███████╗██║  ██║██████╔╝███████║
#     ╚═╝   ╚═╝  ╚═╝╚═╝  ╚═╝╚══════╝╚═╝  ╚═╝╚═════╝ ╚══════╝
#                                                           
def manual_run(pid, set_temp, cook_time, read_interval):
    t = Thread(target=start_process, args=(pid, set_temp, cook_time, read_interval))
    t.start()


def run_process(pid, set_temp, cook_time, read_interval):
    global stop_run
    global pause_run
    stop_run = False
    pause_run = False
    manual_run(pid, set_temp, cook_time, read_interval)


def set_stop_run():
    global stop_run
    pi.write(pin, 0)
    pi.write(fan, 0)
    stop_run = True
    time.sleep(1)
    lcd.lcd_clear()
    lcd.lcd_display_string("Tray Dryer", 1)
    lcd.lcd_display_string("Control System", 2)


if __name__ == '__main__':
    # app.run(host='0.0.0.0', port=8023, debug="True")
    excel.init_excel(app)
    socketio.run(app, host='0.0.0.0', port=8023)
