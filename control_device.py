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
import requests
import json

################################################################################
print("New ver 1.2")
################################################################################
last_time_stamp = datetime.now()
new_event_scan = False
tid = ""
################################################################################
# MODULE_CHECK_SIZE_CORE
# default_note ['Lenght','width','height','weight'] -> Unit: cm
# size_compare_note [XS<=1000, S<=4000, M<=8000,L<=15000,XL<=50000, XXL>50000] -> Unit: gram
# ID send to Monitoring [5-XS, 0-S, 1-M, 2-L, 3-XL, 4-XXL, 'e'-'---']
# recipe_note = (raw_lenght*raw_width*raw_height)/6 -> Scale to gram

default_small_parameter = [5.000, 3.500, 1.500, 50.000]
default_bulky_parameter = [30.000, 7.000, 5.000, 100.000]
size_compare = [1000, 4000, 8000, 15000, 50000]
################################################################################
time_update_status = int(datetime.now().strftime("%H")) + 1
update_status_init = ["lib", "main", "arduino", "zone_task", "", "", ""]


################################################################################
def read_single_data_func(data):
    try:
        filepath = "/home/admin1/Desktop/dws_record/" + data
        read_type = open(filepath, "r")
        type_sta = ["", ""]
        x = 0
        for line in read_type:
            type_sta[x] = line.replace("\n", "")
            x += 1
        read_type.close()
        return type_sta[0]
    except:
        return ""


##############################################################################################
def read_update_func(update_status):
    file_update = open("/home/admin1/Desktop/dws_record/update_status.txt", "r")
    x = 0
    for line in file_update:
        update_status[x] = line.replace("\n", "")
        x += 1
    file_update.close()
    return update_status


################################################################################

machine_tag = read_single_data_func("machine_type.txt")


################################################################################
def zone_display_status_func(machine_tag):
    try:
        zone_task_hub_status = read_update_func(update_status_init)[3].split(",")
        for x in zone_task_hub_status:
            if str(machine_tag).split("-")[1] in x:
                if "True" in x:
                    display_zone_status = True
                else:
                    display_zone_status = False
                break
    except:
        display_zone_status = False
    finally:
        return display_zone_status


display_zone_status = zone_display_status_func(machine_tag)


################################################################################
# MAINTAINX_CORE
# Global Parameter for payload
# Define the bearer token
bearer_token = read_single_data_func("bearer_token.txt")
################################################################################
# KEY HOOK
# Define the time interval (in seconds)
TIME_INTERVAL = 0.5
# Variable to store the last keypress time
last_keypress_time = None
################################################################################
# Make serial connection with Arduino
arduino_conn = True
try:
    if os.path.exists("/dev/ttyACM0"):
        serial_write_data = serial.Serial("/dev/ttyACM0", baudrate=57600, timeout=2)
    elif os.path.exists("/dev/ttyACM1"):
        serial_write_data = serial.Serial("/dev/ttyACM1", baudrate=57600, timeout=2)
    else:
        arduino_conn = False
except:
    arduino_conn = False
    print("No connect with Arduino")
    pass


################################################################################
def read_zone_task_func(zone_ops):
    file_zone = open("/home/admin1/Desktop/dws_record/zone_task.txt", "r")
    x = 0
    for line in file_zone:
        zone_ops[x] = line.replace("\n", "").split(",")
        x += 1
    file_zone.close()
    return zone_ops


##############################################################################################
def git_pull(repository_path):
    try:
        subprocess.run(["git", "init"])
        # Run 'git pull' command
        subprocess.run(["git", "pull", repository_path])
        print("Git pull successful.")
        subprocess.run(["rm", "-rf", ".git"])
        time.sleep(1)
    except:
        print("Please check Internet")


################################################################################
zone_ops = ["1-HCM", "2-HAN", "3-DNG", "4-KHH", "5-GIL", "6-DAK", "7-NGA"]
# And 'e' flag when error code HTTP 500 or update new TID on database
special_des_task = [
    "NGA-DienChau",
    "NGA-HoangMai",
    "NGA-NghiLoc",
    "BIT-TuyPhong",
    "BIT-BacBinh",
    "QUA-PhuocSon",
    "BID-TaySon",
]
zone = read_zone_task_func(zone_ops)


################################################################################
def get_last_time_stamp():
    p = subprocess.run(
        'sqlite3 -header -csv /var/tmp/nvdws/details.sqlite "select * from measurements ORDER BY timestamp DESC LIMIT 1;"',
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        shell=True,
    )
    data = p.stdout.decode("utf-8")
    if data == "":
        time_stamp = ""
        return time_stamp
    else:
        global_data = data.split("\n")[1].split(",")
        global_data[0] = datetime.strptime(
            global_data[0].replace("T", " ").replace("+07:00", ""), f"%Y-%m-%d %H:%M:%S"
        )
        return global_data


################################################################################
# Hookkey function
def on_press(key):
    global tid, last_keypress_time
    try:
        last_keypress_time = time.time()
        tid = tid + key.char
    except:
        pass


def check_last_keypress():
    global tid, new_event_scan, last_keypress_time
    while True:
        # Check if the last keypress occurred more than TIME_INTERVAL seconds ago
        if (
            last_keypress_time is not None
            and time.time() - last_keypress_time > TIME_INTERVAL
        ):
            try:
                if tid != "":
                    new_event_scan = False
                    size_check("", "err")
                    time.sleep(1.5)
                    new_event_scan = True
                    tid = ""
            except:
                pass
            last_keypress_time = None
        # Pause for a short duration before checking again
        time.sleep(0.1)


################################################################################
def size_check(dim_data, err):
    global arduino_conn, default_bulky_parameter, default_small_parameter, size_compare, zone, special_des_task, machine_tag, display_zone_status,zone
    GTC_tag = False
    if "DWS" in machine_tag:
        default = default_small_parameter
    else:
        default = default_bulky_parameter
    try:
        if arduino_conn == True:
            if err == "err":
                obj = "e"
                data = f"e-{obj}"
                serial_write_data.write(data.encode("utf-8"))
            else:
                for x in dim_data:
                    if "GTC" in str(x):
                        GTC_tag = True
                        break
                if dim_data[13] != "":
                    des_task_list = str(dim_data[13]).replace(' ', "").replace('"','').split('-')
                    des_id = des_task_list[0] + "-" + des_task_list[1]
                    if des_id not in special_des_task:
                        des_id = des_task_list[0]
                    obj = 0
                    for x in zone:
                        if des_id in x:
                            obj += 1
                            break
                    if obj == 0:
                        obj = "e"
                    obj = str(obj)
                else:
                    obj = "e"
                raw_lenght = float(dim_data[2]) / 10
                raw_width = float(dim_data[3]) / 10
                raw_height = float(dim_data[4]) / 10
                raw_weight = float(dim_data[5])
                if raw_lenght == 0:
                    raw_lenght = default[0]
                if raw_width == 0:
                    raw_width = default[1]
                if raw_height == 0:
                    raw_height = default[2]
                if raw_weight == 0:
                    raw_weight = default[3]
                recipe = (raw_lenght * raw_width * raw_height) / 6
                if recipe >= raw_weight:
                    weight_check = recipe
                else:
                    weight_check = raw_weight
                if weight_check <= size_compare[0]:
                    data = f"5-{obj}"
                elif weight_check <= size_compare[1]:
                    data = f"0-{obj}"
                elif weight_check <= size_compare[2]:
                    data = f"1-{obj}"
                elif weight_check <= size_compare[3]:
                    data = f"2-{obj}"
                elif weight_check <= size_compare[4]:
                    data = f"3-{obj}"
                else:
                    data = f"4-{obj}"
                if display_zone_status == False:
                    if GTC_tag == False:
                        data = f"e-{obj}"
                serial_write_data.write(data.encode("utf-8"))
    except:
        print("Check back connection between IPC and Arduino")
        pass


def get_size_data():
    global new_event_scan, last_time_stamp, arduino_conn
    while True:
        while new_event_scan:
            if arduino_conn == True:
                new_time_stamp = get_last_time_stamp()
                time.sleep(0.1)
                if new_time_stamp == "":
                    time.sleep(0.5)
                    continue
                elif new_time_stamp[0] > last_time_stamp:
                    size_check(new_time_stamp, "no")
                    last_time_stamp = new_time_stamp[0]
                    new_event_scan = False


################################################################################
# Record IPC status
def process_tempt_func():
    list_tempt = ["", "", "", ""]
    try:
        tempt_info = (
            subprocess.run(["sensors", "coretemp-isa-0000"], stdout=subprocess.PIPE)
            .stdout.decode("utf-8")
            .split("\n")
        )
        for x in range(0, 4):
            list_tempt[x] = (
                str(tempt_info[x + 3])
                .replace("  ", "")
                .replace("(high = +100.0°C, crit = +100.0°C)", "")
                .split(":")[1]
                .replace("°C", "")
                .replace("+", "")
            )
        list_tempt_convert = [float(x) for x in list_tempt]
    except:
        list_tempt_convert = "error_tempt"
    return list_tempt_convert


def check_system_status():
    # Return an object
    # Get CPU and memory usage and chip temperature
    try:
        cpu = psutil.cpu_percent(interval=1)
    except:
        cpu = "error_cpu"
    # Get RAM
    try:
        ram = float(
            str(psutil.virtual_memory())
            .replace(" ", "")
            .split(",")[2]
            .replace("percent=", "")
        )
    except:
        ram = "error_ram"
    # Get Temperature
    temperature_list_core = process_tempt_func()
    # Get Storegare
    try:
        disk_usage = (
            subprocess.run(["df", "/dev/sda3"], stdout=subprocess.PIPE)
            .stdout.decode(encoding="utf-8")
            .split("\n")[1]
            .split(" ")
        )
    except:
        try:
            disk_usage = (
                subprocess.run(["df", "/dev/sda2"], stdout=subprocess.PIPE)
                .stdout.decode(encoding="utf-8")
                .split("\n")[1]
                .split(" ")
            )
        except:
            disk_usage = "error_storegare"
    if disk_usage != "error_storegare":
        while True:
            try:
                disk_usage.remove("")
            except:
                break
        storegare = int(disk_usage[4].replace("%", ""))
    else:
        storegare = "error_storegare"
    # Return Data
    data = [cpu, ram, storegare, temperature_list_core]
    return data


def check_software_sta_func():
    # Check network status
    try:
        net_sta = (
            subprocess.run(["ifconfig"], stdout=subprocess.PIPE)
            .stdout.decode(encoding="utf-8")
            .split("\n")
        )
        net_check_LAN = net_sta[1]
        if ("inet" in net_check_LAN) and ("netmask" in net_check_LAN):
            net_check = "LAN"
        else:
            net_check = "Wifi"
    except:
        net_check = "error_net"
    # Get Software version
    try:
        directory = "/var/tmp/nvdws/updates"
        latest_folder = None
        latest_modification_time = 0
        for dir_name in os.listdir(directory):
            full_path = os.path.join(directory, dir_name)
            if os.path.isdir(full_path):
                modification_time = os.stat(full_path).st_mtime
                if modification_time > latest_modification_time:
                    latest_modification_time = modification_time
                    latest_folder = dir_name
    except:
        latest_folder = "error_ver"
    # Get Timezone monitoring
    try:
        with open("/etc/timezone", "r") as file:
            system_timezone = file.read().strip()
    except:
        system_timezone = "error_timezone"
    data = [net_check, latest_folder, system_timezone]
    return data


################################################################################
# API MaintainX working
def maintainX_API_post_create_workorder(bearer_token, machine_tag, issue_tag):
    # Define the API endpoint
    url = "https://api.getmaintainx.com/v1/workorders"
    machine_id_dict = {
        "VNDWS-HCM-21B-SR": 2691895,
        "VNDWS-HCM-22B-SR": 2691896,
        "VNDWS-HCM-23B-SR": 2691897,
        "VNDWS-HCM-24B-SR": 2691898,
        "VNDWS-HCM-25B-SR": 2691899,
        "VNDWS-HCM-26B-SR": 4902239,
        "VNDWS-HCM-27B-SR": 4908178,
        "VNDWS-HCM-28B-SR": 4908180,
        "VNDWS-HCM-01-SR": 1369940,
        "VNDWS-HCM-02-SR": 1920406,
        "VNDWS-HCM-03-SR": 1920407,
        "VNDWS-HCM-04-SR": 1920408,
        "VNDWS-HCM-05-SR": 1920409,
        "VNDWS-HCM-06-SR": 1920410,
        "VNDWS-HCM-07-SR": 1920411,
        "VNDWS-HCM-08-SR": 2524423,
        "VNDWS-HCM-09-SR": 2524424,
        "VNDWS-HCM-10-SR": 2524425,
        "VNDWS-HCM-11-SR": 2524426,
        "VNDWS-HCM-12-SR": 2524427,
        "VNDWS-HCM-13-SR": 2524428,
        "VNDWS-HCM-14-SR": 2524429,
        "VNDWS-HCM-15-SR": 2524430,
        "VNDWS-HCM-16-SR": 2524431,
        "VNDWS-HCM-17-SR": 2524432,
        "VNDWS-HCM-18-SR": 2524433,
        "VNDWS-HCM-19-SR": 4908181,
        "VNDWS-HCM-20-SR": 4908182,
        "VNDWS-HCM-29-SR": 4908183,
        "VNDWS-HCM-30-SR": 4908184,
        "VNDWS-HN-26B-SR": 2691900,
        "VNDWS-HN-27B-SR": 2691901,
        "VNDWS-HN-28B-SR": 2691902,
        "VNDWS-HN-29B-SR": 2691903,
        "VNDWS-HN-30B-SR": 2691904,
        "VNDWS-HN-31B-SR": 2691905,
        "VNDWS-HN-32B-SR": 2691906,
        "VNDWS-HN-33B-SR": 4908188,
        "VNDWS-HN-01-SR": 1920412,
        "VNDWS-HN-02-SR": 1920413,
        "VNDWS-HN-03-SR": 1920414,
        "VNDWS-HN-04-SR": 1920415,
        "VNDWS-HN-05-SR": 1920416,
        "VNDWS-HN-06-SR": 1920417,
        "VNDWS-HN-07-SR": 1920418,
        "VNDWS-HN-08-SR": 1920419,
        "VNDWS-HN-09-SR": 1920420,
        "VNDWS-HN-10-SR": 1920421,
        "VNDWS-HN-11-SR": 1920422,
        "VNDWS-HN-12-SR": 1920423,
        "VNDWS-HN-13-SR": 1920424,
        "VNDWS-HN-14-SR": 1920425,
        "VNDWS-HN-15-SR": 1920426,
        "VNDWS-HN-16-SR": 2524436,
        "VNDWS-HN-17-SR": 2524437,
        "VNDWS-HN-18-SR": 2524438,
        "VNDWS-HN-19-SR": 2524439,
        "VNDWS-HN-20-SR": 2524440,
        "VNDWS-HN-21-SR": 2524441,
        "VNDWS-HN-22-SR": 2524442,
        "VNDWS-HN-23-SR": 2524443,
        "VNDWS-HN-24-SR": 4908201,
        "VNDWS-HN-25-SR": 2524445,
        "VNDWS-HN-34-SR": 4908202,
        "VNDWS-HN-35-SR": 4908203,
        "VNDWS-HN-36-SR": 4908204,
        "VNDWS-HN-37-SR": 4908205,
        "VNDWS-HN-38-SR": 4908207,
        "VNDWS-HN-39-SR": 4908206,
        "VNDWS-NGA-01-SR": 5064114,
        "VNDWS-DAK-01-SR": 4908214,
        "VNDWS-DAK-02B-SR": 4908215,
        "VNDWS-DNG-01-SR": 2524435,
        "VNDWS-DNG-02-SR": 4908208,
        "VNDWS-DNG-03-SR": 4908209,
        "VNDWS-DNG-04B-SR": 4908210,
        "VNDWS-GIL-01-SR": 4908217,
        "VNDWS-GIL-02B-SR": 4908218,
        "VNDWS-KHH-01-SR": 2524434,
        "VNDWS-KHH-02-SR": 4908211,
        "VNDWS-KHH-04B-SR": 4908212,
    }
    location_id_dict = {
        "HN": 703519,
        "HCM": 548675,
        "DNG": 1097876,
        "KHH": 1097877,
        "DAK": 1868575,
        "GIL": 1868576,
        "NGA": 1868577,
    }
    assignees_id_dict = {"Auto_Manager": 406115, "Auto_Maintenance": 406114}
    vendor_id_dict = {
        "SR": 44279,
    }
    description_tag_dict = {
        "DWS": "Workorder was created from DWS - ",
        "Engineer": "Workorder was sent from Engineer laptop",
    }
    title_tag_dict = {
        "storegare": "Storgare over 90% - ",
        "cpu": f"Check %cpu over 70% - ",
        "ram": "Check %RAM over 70% - ",
        "tempt": "Check overheating IPC over 90% - ",
    }
    priority_dict = {
        "storegare": "HIGH",
        "cpu": "MEDIUM",
        "ram": "MEDIUM",
        "tempt": "MEDIUM",
    }
    categories_dict = {
        "storegare": "Preventive",
        "cpu": "Inspection",
        "ram": "Inspection",
        "tempt": "Inspection",
    }
    procedureTemplateId_dict = {
        "Corrective Maintenance": 1705541,
        "None": None,
    }
    # Fill data for payload region
    assignees_id_payload = assignees_id_dict["Auto_Manager"]
    requesterId_payload = assignees_id_dict["Auto_Manager"]
    vendorIds_payload = vendor_id_dict["SR"]
    # Data for payload
    estimatedTime_payload = 3600
    startDate_payload = (
        str(datetime.now()).split(" ")[0]
        + "T"
        + datetime.now().strftime("%X")
        + ".000Z"
    )
    asset_id_payload = machine_id_dict[machine_tag]
    location_id_payload = location_id_dict[str(machine_tag).split("-")[1]]
    # Logic
    categories_payload = categories_dict[issue_tag]
    description_payload = description_tag_dict["DWS"] + " " + machine_tag
    priority_payload = priority_dict[issue_tag]
    procedureTemplateId_payload = procedureTemplateId_dict["Corrective Maintenance"]
    title_payload = title_tag_dict[issue_tag] + " " + machine_tag
    # Define the JSON payload
    payload = {
        "assetId": asset_id_payload,
        "assignees": [{"type": "USER", "id": assignees_id_payload}],
        "estimatedTime": estimatedTime_payload,
        "requesterId": requesterId_payload,
        "categories": [categories_payload],
        "description": description_payload,
        "startDate": startDate_payload,
        "locationId": location_id_payload,
        "priority": priority_payload,
        "procedure": None,
        "procedureTemplateId": procedureTemplateId_payload,
        "title": title_payload,
        "vendorIds": [vendorIds_payload],
    }
    # Make the request with Bearer Token Authentication and JSON payload
    headers = {"Authorization": "Bearer " + bearer_token}
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=3)
        if "error" not in json.loads(response.text):
            response_id = json.loads(response.text)["id"]

            log_record = read_single_data_func("workorders_log_record.txt")
            log_record_dict = json.loads(log_record)
            log_record_dict[issue_tag] = response_id

            f = open("/home/admin1/Desktop/dws_record/workorders_log_record.txt", "w")
            f.write(json.dumps(log_record_dict))
            f.close()
    except:
        pass


def maintainX_API_post_conversation(
    bearer_token, teamchat_id, issue_tag, monitoring_time
):
    url = f"https://api.getmaintainx.com/v1/conversations/{teamchat_id}/messages"
    message_str = f"This error ({issue_tag}) has not been resolved yet - Please handle the problem immediately."
    payload = {"content": message_str}
    # Make the request with Bearer Token Authentication and JSON payload
    headers = {"Authorization": "Bearer " + bearer_token}
    if monitoring_time in [8, 15, 20]:
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=3)
        except:
            pass


def maintainX_API_get_workorders_status(
    bearer_token, machine_tag, monitoring_time, teamchat_id, workorders_id, issue_tag
):
    url = f"https://api.getmaintainx.com/v1/workorders/{workorders_id}"
    # Make the request with Bearer Token Authentication and JSON payload
    headers = {"Authorization": "Bearer " + bearer_token}
    try:
        response = json.loads(requests.get(url, headers=headers, timeout=3).text)
        if "error" not in response:
            response_status = response["workOrder"]["status"]
            if response_status != "DONE":
                maintainX_API_post_conversation(
                    bearer_token, teamchat_id, issue_tag, monitoring_time
                )
            else:
                maintainX_API_post_create_workorder(
                    bearer_token, machine_tag, issue_tag
                )
        else:
            maintainX_API_post_create_workorder(bearer_token, machine_tag, issue_tag)
    except:
        pass


################################################################################
def dws_operation_record_AWS():
    global machine_tag, time_update_status, bearer_token
    while True:
        # AWS instance public IP address and port
        aws_instance_port = 3000  # Replace with the port your server is listening on
        # Create a TCP socket
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # Set a timeout for the entire connection process (in seconds)
        client_socket.settimeout(10)
        monitoring_time = int(datetime.now().strftime("%H"))
        if monitoring_time == time_update_status:
            dws_ops = check_system_status()
            if monitoring_time == 23:
                time_update_status = 0
            else:
                time_update_status = monitoring_time + 1
            if monitoring_time == 6:
                subprocess.run(["shutdown", "now", "-r"])
                continue
            try:
                subprocess.run(["rm", "-f", "aws_ip_addr.txt"])
                time.sleep(1)
                repository_path_setup = (
                    "https://github.com/vannamlord/ninjavan_update_aws_ip.git"
                )
                git_pull(repository_path_setup)
            except:
                pass

            if not os.path.exists("/home/admin1/Desktop/dws_record/aws_ip_addr.txt"):
                repository_path_setup = (
                    "https://github.com/vannamlord/ninjavan_update_aws_ip.git"
                )
                git_pull(repository_path_setup)
            # AWS Monitoring
            try:
                aws_instance = read_single_data_func("aws_ip_addr.txt")
                aws_instance_sta = aws_instance.split(":")[1]
                aws_instance_ip = aws_instance.split(":")[0]
            except:
                aws_instance_sta = "Stopped"
                pass
            if aws_instance_sta == "Running":
                software_monitoring = check_software_sta_func()
                data_to_send = {
                    machine_tag: {
                        "time": str(datetime.now()),
                        "cpu": dws_ops[0],
                        "ram": dws_ops[1],
                        "storegare": dws_ops[2],
                        "tempt": dws_ops[3],
                        "net_sta": software_monitoring[0],
                        "latest_ver": software_monitoring[1],
                        "time_zone": software_monitoring[2],
                    }
                }
                try:
                    # Connect to the server
                    client_socket.connect((aws_instance_ip, aws_instance_port))
                    # Send data to the server
                    client_socket.sendall(json.dumps(data_to_send).encode("utf-8"))
                except:
                    pass
                finally:
                    # Close the socket
                    client_socket.close()
            # MaintainX Monitoring
            cpu = dws_ops[0]
            ram = dws_ops[1]
            storegare = dws_ops[2]
            tempt = dws_ops[3]
            # API parameter
            teamchat_id_VN = 286582
            try:
                workorders_id_log = json.loads(
                    read_single_data_func("workorders_log_record.txt")
                )
            except:
                pass
            try:
                if (cpu != "error_cpu") and (cpu >= 70):
                    maintainX_API_get_workorders_status(
                        bearer_token,
                        machine_tag,
                        monitoring_time,
                        teamchat_id_VN,
                        workorders_id_log["cpu"],
                        "cpu",
                    )
                if (ram != "error_ram") and (ram >= 70):
                    maintainX_API_get_workorders_status(
                        bearer_token,
                        machine_tag,
                        monitoring_time,
                        teamchat_id_VN,
                        workorders_id_log["ram"],
                        "ram",
                    )
                if (storegare != "error_storegare") and (storegare >= 90):
                    maintainX_API_get_workorders_status(
                        bearer_token,
                        machine_tag,
                        monitoring_time,
                        teamchat_id_VN,
                        workorders_id_log["storegare"],
                        "storegare",
                    )
                if tempt != "error_tempt":
                    for x in tempt:
                        if x >= 90:
                            maintainX_API_get_workorders_status(
                                bearer_token,
                                machine_tag,
                                monitoring_time,
                                teamchat_id_VN,
                                workorders_id_log["tempt"],
                                "tempt",
                            )
                            break
            except:
                pass


################################################################################
thread_get_size_data = threading.Thread(target=get_size_data)
thread_get_size_data.start()
thread_get_dws_data = threading.Thread(target=dws_operation_record_AWS)
thread_get_dws_data.start()
print("Tool is Running")
with keyboard.Listener(on_press=on_press) as listener:
    timer_thread = threading.Thread(target=check_last_keypress)
    timer_thread.start()
    # Keep the script running
    listener.join()
