# custom
from flask import Flask as flask
from flask import request, make_response, jsonify
from cryptography.fernet import Fernet

# local/default
from threading import Thread
from time import sleep
from utils import stats, steam_logs, tomislav_fernet, create_traffic_dump, shell_exec
import json
from base64 import b64encode, b64decode
from socket import gethostname as get_host_name
import re
import logging
from time import time

logging.basicConfig(level=logging.INFO, filename=f"logs/tomislav_{round(time())}_app.log", filemode="w")

config_file = open(f"configs/{get_host_name()}.json")
config = json.load(config_file)
config_file.close()

app = flask(__name__)
statistics_obj = stats()
server_logs = steam_logs()
t_fernet = tomislav_fernet(Fernet(config["encryption_key"]))

def network_statistics():
    while True:
        statistics_obj.update()
        sleep(statistics_obj.delay)

def start_background_tasks():
    thread = Thread(target=network_statistics)
    thread.daemon = True
    thread.start()

def err_response(object_thing):
    response = make_response(jsonify({"data": t_fernet.enc(object_thing)}), 404)
    response.headers["Content-Type"] = "application/json"
    return response

def success_response(object_thing):
    response = make_response(jsonify({"data": t_fernet.enc(object_thing)}), 200)
    response.headers["Content-Type"] = "application/json"
    return response

def get_args():
    return t_fernet.dec(request.args.get("data"))

@app.route('/status', methods=['GET'])
def status():
    args = get_args()

    if args.get("password") != config["password"]:
        return err_response({"error! write to the dev": "lol"})

    stats = statistics_obj.get_dict()
    under_ddos = (stats.get("spike_mbps") > 200 or stats.get("spike_pps") > 80000)
    suspicious_cpu_usage = (stats.get("cpu_usage") > 75)

    response = {"high_cpu_usage": suspicious_cpu_usage, "ddos": under_ddos, "traffic_dump": None}

    if under_ddos or suspicious_cpu_usage:
        response["traffic_dump"] = b64encode(create_traffic_dump()).decode("ascii")

    return success_response(response)

@app.route('/status_raw', methods=['GET'])
def status_raw():
    args = get_args()

    if args.get("password") != config["password"]:
        return err_response({"error! write to the dev": "lol"})

    stats = statistics_obj.get_dict()
    response = {"spike_mbps": stats.get("spike_mbps"), "spike_pps": stats.get("spike_pps"), "cpu_usage": stats.get("cpu_usage")}

    return success_response(response)

@app.route('/find_logs', methods=['GET'])
def logs():
    args = get_args()

    if args.get("password") != config["password"]:
        return err_response({"error! write to the dev": "lol"}) 

    tempholder = {}
    tempholder["ip_list"] = []
    tempholder["steamid_list"] = []
    tempholder["nickname_list"] = []
    tempholder["connection_times"] = 0

    for dirr in config["logs_dir"]:
        query = None
        if type(args.get("find")) == str:
            query = [args.get("find")]
        else:
            query = args.get("find")
        result = server_logs.find_address_steamid(dirr, search_list=query, recursive=args.get("recursive"), ignore_vpn=args.get("ignore_vpn"))
        tempholder["ip_list"] += result["ip_list"] 
        tempholder["steamid_list"] += result["steamid_list"] 
        tempholder["nickname_list"] += result["nickname_list"] 
        tempholder["connection_times"] += result["connection_times"]

    return success_response(tempholder)

@app.route('/update_game_servers', methods=['GET'])
def update_game_servers():
    # todo: pass server names/aliases to restart/update specifically

    args = get_args()

    if args.get("password") != config["password"]:
        return err_response({"error! write to the dev": "lol"}) 

    result = {}

    for dictt in config["update_scripts"]:
        result.update({dictt.get("update_script"): shell_exec(dictt.get("update_script"))})
        shell_exec(dictt.get("server_restart_cmd"))

    return success_response(result)

@app.route('/restart_servers', methods=['GET'])
def restart_servers():
    # todo: pass server names/aliases to restart/update specifically
    args = get_args()

    if args.get("password") != config["password"]:
        return err_response({"error! write to the dev": "lol"}) 

    result = {}

    for dictt in config["update_scripts"]:
        result.update({dictt.get("server_restart_cmd"): "Success"})
        shell_exec(dictt.get("server_restart_cmd"))

    return success_response(result)

if __name__ == 'app':
    start_background_tasks()