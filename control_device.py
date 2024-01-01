#!/usr/bin/env python
import subprocess
import threading
import time
import serial
import os
import psutil
import socket
from datetime import datetime
from pynput import keyboard
################################################################################
print("New ver 1.1")
################################################################################
last_time_stamp = datetime.now()
new_event_scan = False
tid=''
################################################################################
# default_note ['Lenght','width','height','weight'] -> Unit: cm
# size_compare_note [XS<=1000, S<=4000, M<=8000,L<=15000,XL<=50000, XXL>50000] -> Unit: gram
# ID send to Monitoring [5-XS, 0-S, 1-M, 2-L, 3-XL, 4-XXL, 'e'-'---']
# recipe_note = (raw_lenght*raw_width*raw_height)/6 -> Scale to gram

default_small_parameter = [5.000,3.500,1.500,50.000]
default_bulky_parameter = [30.000,7.000,5.000,100.000]
size_compare = [1000,4000,8000,15000,50000]

################################################################################
#Key Hook
# Define the time interval (in seconds)
TIME_INTERVAL = 0.5
# Variable to store the last keypress time
last_keypress_time = None
################################################################################
# Make serial connection with Arduino
arduino_conn = True
try:
    if(os.path.exists('/dev/ttyACM0')):
        serial_write_data = serial.Serial(
            '/dev/ttyACM0', baudrate=57600, timeout=2)
    elif (os.path.exists('/dev/ttyACM1')):
        serial_write_data = serial.Serial(
            '/dev/ttyACM1', baudrate=57600, timeout=2)
    else:
        arduino_conn =False
except:
    arduino_conn =False
    print('No connect with Arduino')
    pass
################################################################################
# AWS instance public IP address and port
aws_instance_port = 3000  # Replace with the port your server is listening on

# Create a TCP socket
client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
# Set a timeout for the entire connection process (in seconds)
timeout_seconds = 10
client_socket.settimeout(timeout_seconds)

time_update_status = int(datetime.now().strftime("%H")) + 1
################################################################################
def read_single_data_func(data):
    try:
        filepath = "/home/admin1/Desktop/dws_record/"+data
        read_type = open(filepath, "r")
        type_sta = ['','']
        x = 0
        for line in read_type:
            type_sta[x] = line.replace('\n','')
            x += 1
        read_type.close()
        return type_sta[0]
    except:
        return ''
machine_id = read_single_data_func("machine_type.txt")
################################################################################
def read_zone_task_func(zone_ops):
    file_zone = open("/home/admin1/Desktop/dws_record/zone_task.txt", "r")
    x = 0
    for line in file_zone:
        zone_ops[x] = line.replace('\n','').split(',')
        x += 1
    file_zone.close()
    return zone_ops
##############################################################################################
def git_pull(repository_path):
    try:
        # Run 'git pull' command
        subprocess.run(['git', 'pull',repository_path])
        print("Git pull successful.")
    except:
        print("Please check Internet")
################################################################################
zone_ops = ['1-HCM','2-HAN','3-DNG','4-KHH','5-GIL','6-DAK','7-NGA'] 
# And 'e' flag when error code HTTP 500 or update new TID on database
special_des_task =['NGA-DienChau','NGA-HoangMai','NGA-NghiLoc','BIT-TuyPhong','BIT-BacBinh','QUA-PhuocSon','BID-TaySon'] 
zone = read_zone_task_func(zone_ops)
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
    global arduino_conn,default_bulky_parameter,default_small_parameter,\
        size_compare,zone,special_des_task,machine_id
    GTC_tag = False
    if('DWS' in machine_id):
        default = default_small_parameter
    else:
        default = default_bulky_parameter
    try:
        if(arduino_conn == True):
            if(err == "err"):
                obj = 'e'
                data = f'e-{obj}'
                serial_write_data.write(data.encode('utf-8'))
            else:
                for x in dim_data:
                    if ("GTC" in x):
                        GTC_tag = True
                        break
                if(dim_data[13]!= ''):
                    des_task_list = str(dim_data[13]).replace(' ','').split('-')
                    des_id = des_task_list[0]+'-'+des_task_list[1]
                    if(des_id not in special_des_task):
                        des_id = des_task_list[0]
                    obj = 0
                    for x in zone:
                        if(des_id in x):
                            obj += 1
                            break
                    if obj == 0:
                        obj = 'e'
                    obj = str(obj)
                else:
                    obj = 'e'
                raw_lenght = float(dim_data[2])/10
                raw_width = float(dim_data[3])/10
                raw_height = float(dim_data[4])/10
                raw_weight = float(dim_data[5])
                if(raw_lenght == 0):
                    raw_lenght = default[0]
                if(raw_width == 0):
                    raw_width = default[1]
                if(raw_height == 0):
                    raw_height = default[2]
                if(raw_weight == 0):
                    raw_weight = default[3]
                recipe = (raw_lenght*raw_width*raw_height)/6
                if(recipe >= raw_weight):
                    weight_check = recipe
                else:
                    weight_check = raw_weight
                if(weight_check <= size_compare[0]):
                    data = f'5-{obj}'
                elif(weight_check <= size_compare[1]):
                    data = f'0-{obj}'
                elif(weight_check <= size_compare[2]):
                    data = f'1-{obj}'
                elif(weight_check <= size_compare[3]):
                    data = f'2-{obj}'
                elif(weight_check <= size_compare[4]):
                    data = f'3-{obj}'
                else:
                    data = f'4-{obj}'
                if(GTC_tag == False):
                    data = f'e-{obj}'
                serial_write_data.write(data.encode('utf-8'))
    except:
        print("Check back connection between IPC and Arduino")
        pass

def get_size_data():
    global new_event_scan,last_time_stamp,arduino_conn
    while True:
        while new_event_scan:
            if(arduino_conn == True):
                new_time_stamp = get_last_time_stamp()
                time.sleep(0.1)
                if(new_time_stamp == ''):
                    time.sleep(0.5)
                    continue
                elif(new_time_stamp[0]>last_time_stamp):
                    size_check(new_time_stamp,"no")
                    last_time_stamp = new_time_stamp[0]
                    new_event_scan = False
################################################################################
def process_tempt_func(data):
    list_tempt = ['','','','']
    for x in range(0,4):
        list_tempt[x] = str(data[x+3]).replace(' ','').\
            replace('(high = +100.0°C, crit = +100.0°C)','').\
                split(':')[1].replace('°C','').replace('+','')
    return list_tempt
def check_system_status():
    # Return an object
    # Get CPU and memory usage and chip temperature
    cpu_percent = 'CPU_Utilization_%:' + str(psutil.cpu_percent(interval=1))
    memory_info = 'RAM_%:'+ str(psutil.virtual_memory()).replace(' ','').split(',')[2].replace('percent=','')
    disk_usage = subprocess.run(['df','/dev/sda3'],stdout=subprocess.PIPE).\
        stdout.decode(encoding='utf-8').split('\n')[1].split(' ')
    while True:
        try:
            disk_usage.remove('')
        except:
            break
    disk_usage_vol = 'Free_disk_usage_GB:' + str(int((int(disk_usage[3]))/1000000)) + '-Used_%:' + disk_usage[4].replace('%','')
    try:
        tempt_info = subprocess.run(['sensors', 'coretemp-isa-0000'],stdout=subprocess.PIPE).stdout.decode('utf-8').split('\n')
        temperature_list_core = process_tempt_func(tempt_info)
    except:
        temperature_list_core = ['','','','']
    data = [cpu_percent,memory_info,disk_usage_vol,temperature_list_core]
    return data
################################################################################
def dws_operation_record():
    global machine_id,time_update_status,aws_instance_port
    while True:
        monitoring_time = int(datetime.now().strftime("%H"))
        if(monitoring_time == time_update_status):
            if(monitoring_time == 23):
                time_update_status = 0
            else:
                time_update_status = monitoring_time + 1
            try:
                subprocess.run(['rm', '-f','aws_ip_addr.txt'])
                time.sleep(0.1)
                subprocess.run(['git','init'])
            except:
                pass
            repository_path_setup = 'https://github.com/vannamlord/ninjavan_update_aws_ip.git'
            git_pull(repository_path_setup)
            subprocess.run(['rm', '-rf','.git'])
            time.sleep(1)
            aws_instance = read_single_data_func("aws_ip_addr.txt")
            aws_instance_sta = aws_instance.split(':')[1]
            aws_instance_ip = aws_instance.split(':')[0]
            if(aws_instance_sta == 'Running'):
                dws_ops = check_system_status()
                data_to_send = str(datetime.now()) + '=' + machine_id + '=' + str(dws_ops[0]) + '='  + str(dws_ops[1])\
                    + '=' + str(dws_ops[2])+ '=' + str(dws_ops[3])
                try:
                    # Connect to the server
                    client_socket.connect((aws_instance_ip, aws_instance_port))
                    # Send data to the server
                    client_socket.sendall(data_to_send.encode('utf-8'))
                except:
                    pass
                finally:
                    # Close the socket
                    client_socket.close()
################################################################################
thread_get_size_data = threading.Thread(target=get_size_data)
thread_get_size_data.start()
thread_get_dws_data = threading.Thread(target=dws_operation_record)
thread_get_dws_data.start()
print("Tool is Running")
with keyboard.Listener(on_press=on_press) as listener:
    timer_thread = threading.Thread(target=check_last_keypress)
    timer_thread.start()
    # Keep the script running
    listener.join()