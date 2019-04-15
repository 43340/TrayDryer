#!/usr/bin/python
# -*- coding: utf-8 -*-
# xzx
from flask import Flask, request, jsonify, make_response
from flask_sqlalchemy import SQLAlchemy
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash
from threading import Thread
from flask_socketio import SocketIO, emit
import threading
from flask_cors import CORS, cross_origin
import uuid
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

os.system('python /home/pi/dryer/lcdkp.py &')

pi = pigpio.pi()
sensor1 = si7021.si7021(1)
sensor2 = si7021.si7021(3)
pin = 26
fan = 6
pi.set_mode(pin, pigpio.OUTPUT)
pi.set_mode(fan, pigpio.OUTPUT)
global stop_run
global start_read
global read_counter
global timer
global time_left
time_left = ""
timer = 0
start_read = False
stop_run = True
read_counter = 0
pi.write(pin, 0)
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
    hum = db.Column(db.Integer)
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
        return jsonify({'message': 'Cannot perforn that function'})

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
        user_id=current_user.public_id).all()

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


# TODO: Change the specs cause this code smells
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
                     data['ctime'], data['rinte'], data['initw'], ts, uid)

    run_process(pid, data['stemp'], data['ctime'], data['rinte'])

    # run_process function. Do this on a different thread so it doesnt get clogged.
    # run_process(name, set_temp, cook_time, read_int, time_stamp, user_id)

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

    # run_process function. Do this on a different thread so it doesnt get clogged.
    # run_process(name, set_temp, cook_time, read_int, time_stamp, user_id)

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
        dht_data['hum'] = data.hum
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
def send_current(temp, hum, time_left, stop_run):
    socketio.emit('some event', {
        'temp': temp,
        'hum': hum,
        'timeleft': time_left,
        'stop_run': stop_run
    })


def get_temphumi_data(pid=""):

    temp = sensor1.Temperature()# + sensor2.Temperature()) / 2
    hum = sensor1.Humidity()# + sensor2.Humidity()) / 2

    if hum is not None and temp is not None:
        ts = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        return temp, hum, ts


# TODO: Function is getting too bloated. Try slimming ti down
def log_data(pid, set_temp, cook_time, read_interval, base_time):
    try:
        global read_counter
        global stop_run
        global time_left

        temp, hum, ts = get_temphumi_data(pid)
        timeleft = str(datetime.timedelta(seconds=cook_time))
        timer = datetime.datetime.now() # float(base_time) - float(datetime.timedelta(seconds=cook_time).total_seconds())
        print(timer)
        rtemp = round(temp, 2)
        rhum = round(hum, 2)
        print(temp)
        print(hum)
        lcd.lcd_display_string("Temp: {:0.2f}C".format(temp), 1)
        lcd.lcd_display_string("Hum: {:0.2f}%".format(hum), 2)
        lcd.lcd_display_string("ETA: " + timeleft, 3)

        send_current(str(rtemp), str(rhum), timeleft, stop_run)

        adjust_heater_power(set_temp, temp)
        adjust_fan_power()

        if read_counter >= read_interval:
            read_counter = 0
            dht_data = DHTData(temp=rtemp, hum=rhum, time_stamp=timer, process_id=pid)
            db.session.add(dht_data)
            db.session.commit()
        read_counter = read_counter + 1
        cook_time = cook_time - 1
    except Exception as error:
        print(error)
        dht_data = DHTData(temp=0, hum=0, time_stamp=0, process_id=pid)
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
        cook_time = cook_time - 1
        f(pid, set_temp, cook_time, read_interval, base_time)

        global stop_run
        if stop_run:
            global timer
            timer = 0
            break

        if cook_time < 0:
            set_stop_run()
            break


def log_process_data(pid, name, set_temp, cook_time, read_interval, ts, current_user):

    process_data = ProcessData(process_id=pid, name=name, set_temp=set_temp,
                               cook_time=cook_time, read_int=read_interval, initial_w=initial_weight, time_stamp=ts, user_id=current_user)

    db.session.add(process_data)
    db.session.commit()


def adjust_heater_power(set_temp, current_temp):
    if set_temp <= current_temp:
        pi.write(pin, 0)
    else:
        pi.write(pin, 1)


def adjust_fan_power():
    if stop_run:
        pi.set_PWM_dutycycle(fan, 64)
    else:
        pi.set_PWM_dutycycle(fan, 64)


# TODO: Change this use threading.time
def start_process(pid, set_temp, cook_time, read_interval):
    global stop_run
    print(stop_run)

    while not stop_run:

        current_temp, current_hum, cts = get_temphumi_data(pid)
        adjust_heater_power(set_temp, current_temp)
        log_data(pid, current_temp, current_hum, cts, cook_time)
        lcd.lcd_clear()
        # do_every(read_interval, log_data, pid, set_temp, cook_time, read_interval)
        do_every(1, log_data, pid, set_temp, cook_time, read_interval, cook_time)

        # time.sleep(read_interval)
        cook_time = cook_time - read_interval

        if cook_time <= 0:
            set_stop_run()
            break

    pi.write(pin, 0)
    pi.write(fan, 0)
    print("yay")
    set_stop_run
    return stop_run


@app.route('/data', methods=['GET'])
def get_th():
    global time_left
    global stop_run
    temp, hum, ts = get_temphumi_data()

    return jsonify({
            'temperature': temp,
            'humidity': hum,
            'timeleft': time_left,
            'stop': stop_run
        })


@app.route('/check', methods=['GET'])
def check_stop():

    global stop_run

    return jsonify({'stopped': stop_run})


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


@app.route('/process/report/<process_id>')
def pdf_template(process_id):
    process = ProcessData.query.filter_by(process_id=process_id).first()
    rendered = render_template('pdf_template.html', process_id=process_id, name=process.name, set_temp=process.set_temp, cook_time=str(datetime.timedelta(seconds=process.cook_time)), read_int=process.read_int, init_w=process.initial_w, time_stamp=process.time_stamp, username=process.user_id)
    pdf = pdfkit.from_string(rendered, False)

    response = make_response(pdf)
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = 'inline; filename={}.pdf'.format(process_id)

    return response


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
    stop_run = False
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
    socketio.run(app, host='0.0.0.0', port=8023)
