#!/usr/bin/env python
import subprocess
import threading
import time
import serial
from datetime import datetime
from pynput import keyboard
################################################################################
print("New ver 1.1")
################################################################################
last_time_stamp = datetime.now()
new_event_scan = False
tid=''
# Define the time interval (in seconds)
TIME_INTERVAL = 0.5
# Variable to store the last keypress time
last_keypress_time = None
################################################################################
# Make serial connection
try:
    serial_write_data = serial.Serial(
        '/dev/ttyACM0', baudrate=57600, timeout=2)
except:
    try:
        serial_write_data = serial.Serial(
        '/dev/ttyACM1', baudrate=57600, timeout=2)
    except:
        pass
################################################################################
def get_last_time_stamp():
    p = subprocess.run("sqlite3 -header -csv /var/tmp/nvdws/details.sqlite \"select * from measurements ORDER BY timestamp DESC LIMIT 1;\"",
                                                            stdout=subprocess.PIPE, stderr=subprocess.PIPE,shell=True)
    data = p.stdout.decode('utf-8')
    if(data == ''):
        time_stamp =''
        return time_stamp
    else:
        global_data = data.split('\n')[1].split(',')
        global_data[0] = datetime.strptime(global_data[0].replace('T',' ').replace("+07:00",''),'%Y-%m-%d %H:%M:%S')
        return global_data
################################################################################
def on_press(key):
    global tid,last_keypress_time
    try:
        last_keypress_time = time.time()
        tid = tid + key.char
    except:
        pass
def check_last_keypress():
    global tid,new_event_scan,last_keypress_time
    while True:
        # Check if the last keypress occurred more than TIME_INTERVAL seconds ago
        if last_keypress_time is not None and time.time() - last_keypress_time > TIME_INTERVAL:
            try:
                if(tid !=''):
                    new_event_scan = False
                    size_check('',"err")
                    time.sleep(1.5)
                    new_event_scan = True
                    tid = ''
            except:
                pass
            last_keypress_time = None
            

        # Pause for a short duration before checking again
        time.sleep(0.1)

################################################################################
def size_check(dim_data,err):
    try:
        if(err=="err"):
            serial_write_data.write(b'6')
        else:
            raw_lenght = float(dim_data[2])/10
            raw_width = float(dim_data[3])/10
            raw_height = float(dim_data[4])/10
            raw_weight = float(dim_data[5])
            if(raw_lenght == 0):
                raw_lenght = 5.000
            if(raw_width ==0):
                raw_width = 3.500
            if(raw_height == 0):
                raw_height = 1.500
            if(raw_weight ==0):
                raw_weight = 50.000
            weight_scale = (raw_lenght*raw_width*raw_height)/6
            if(weight_scale >= raw_weight):
                weight_check = weight_scale
            else:
                weight_check = raw_weight
            if(weight_check <=1000):
                serial_write_data.write(b'5')
            elif(weight_check <= 4000):
                serial_write_data.write(b'0')
            elif(weight_check <= 8000):
                serial_write_data.write(b'1')
            elif(weight_check <= 15000):
                serial_write_data.write(b'2')
            elif(weight_check <= 50000):
                serial_write_data.write(b'3')
            else:
                serial_write_data.write(b'4')
    except:
        print("Check back connection between IPC and Arduino")
################################################################################
def get_size_data():
    global new_event_scan,last_time_stamp
    while True:
        while new_event_scan:
            new_time_stamp = get_last_time_stamp()
            time.sleep(0.1)
            if(new_time_stamp == ''):
                time.sleep(0.5)
                continue
            elif(new_time_stamp[0]>last_time_stamp):
                print("Data: "+ str(new_time_stamp[0])+' '+ new_time_stamp[1])
                for x in new_time_stamp:
                    try:
                        if ("GTC" in x):
                            size_check(new_time_stamp,"no")
                            break
                    except:
                        pass
                last_time_stamp = new_time_stamp[0]
                new_event_scan = False
thread_get_size_data = threading.Thread(target=get_size_data)
thread_get_size_data.start()
print("Tool is Running")
with keyboard.Listener(on_press=on_press) as listener:
    timer_thread = threading.Thread(target=check_last_keypress)
    timer_thread.start()
    # Keep the script running
    listener.join()

