# SPDX-FileCopyrightText: 2022 Liz Clark for Adafruit Industries
# SPDX-License-Identifier: MIT

import time
import ssl
import board
import pwmio
from analogio import AnalogIn
import adafruit_requests
import socketpool
import wifi
from adafruit_io.adafruit_io import IO_HTTP, AdafruitIO_RequestError
from simpleio import map_range
from adafruit_motor import servo
from digitalio import DigitalInOut, Direction, Pull

#  select which display is running the code
servo_one = True
servo_two = False

try:
    from secrets import secrets
except ImportError:
    print("WiFi secrets are kept in secrets.py, please add them there!")
    raise
#  connect to adafruitio
aio_username = secrets["aio_username"]
aio_key = secrets["aio_key"]

#print("Connecting to %s" % secrets["ssid"])
wifi.radio.connect(secrets["ssid"], secrets["password"])
#print("Connected to %s!" % secrets["ssid"])
print("Connected")

pool = socketpool.SocketPool(wifi.radio)
requests = adafruit_requests.Session(pool, ssl.create_default_context())
# Initialize an Adafruit IO HTTP API object
io = IO_HTTP(aio_username, aio_key, requests)

#  pylint: disable=undefined-variable
#  disabling undefined-variable for ease of comment/uncomment
#  servo_one or servo_two at top for user

#  setup for display 1
if servo_one:
    #  servo calibration values
    CALIB_MIN = 15708
    CALIB_MAX = 43968
    #  create feeds
    try:
        # get feed
        out_feed = io.get_feed("touch-1")
        in_feed = io.get_feed("touch-2")
    except AdafruitIO_RequestError:
        # if no feed exists, create one
        out_feed = io.create_new_feed("touch-1")
        in_feed = io.create_new_feed("touch-2")
#  setup for display 2
if servo_two:
    CALIB_MIN = 5947
    CALIB_MAX = 53003
    try:
        # get feed
        out_feed = io.get_feed("touch-2")
        in_feed = io.get_feed("touch-1")
    except AdafruitIO_RequestError:
        # if no feed exists, create one
        out_feed = io.create_new_feed("touch-2")
        in_feed = io.create_new_feed("touch-1")

received_data = io.receive_data(in_feed["key"])

SERVO_PIN = board.A1
FEEDBACK_PIN = board.A2
button = DigitalInOut(board.A3)
button.direction = Direction.INPUT
button.pull = Pull.DOWN

ANGLE_MIN = 0
ANGLE_MAX = 180

pwm = pwmio.PWMOut(SERVO_PIN, duty_cycle=2 ** 15, frequency=50)
servo = servo.Servo(pwm)
servo.angle = None
feedback = AnalogIn(FEEDBACK_PIN)

new_msg = None
last_msg = None
clock = 5
button_clock = 5
button_timer_status = False
ACTING_TIMER_THR = 5
button_state_last_loop = False


def get_position():
    return map_range(feedback.value, CALIB_MIN, CALIB_MAX, ANGLE_MIN, ANGLE_MAX)


while True:
    if (time.monotonic() - clock) > 5:
        received_data = io.receive_data(in_feed["key"])
        clock = time.monotonic()
    if not button.value and button_state_last_loop:
        button_timer_status = True
        button_clock = time.monotonic()
        servo.angle = None
        print("start timer")
    if button_timer_status:
        if (time.monotonic() - button_clock) > 5:
            pos = get_position()
            io.send_data(out_feed["key"], float(pos))
            print(f"New own servo position {float(pos)}")
            servo.angle = float(pos)
            print("reset timer und neuer Wert")
            button_timer_status = False
            time.sleep(1)

    if not button_timer_status and float(received_data["value"]) != last_msg:
        new_msg = float(received_data["value"])
        servo.angle = new_msg
        print(f"New servo received position {new_msg}")
        time.sleep(1)
        last_msg = new_msg
    button_state_last_loop = button.value
    time.sleep(0.1)
