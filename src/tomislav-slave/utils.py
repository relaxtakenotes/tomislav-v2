# custom
import psutil
import httpx
import urllib

# local/default
import shlex
import re
import subprocess
import json
from traceback import format_exc as traceback
import logging
from time import time
from socket import gethostname as get_host_name
import platform

logging.basicConfig(level=logging.INFO, filename=f"logs/tomislav_{round(time())}_utils.log", filemode="w")

config_file = open(f"configs/{get_host_name()}.json")
config = json.load(config_file)
config_file.close()

def shell_exec(command):
    p = subprocess.Popen(shlex.split(command), stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()
    return p[0].decode("utf-8", errors="ignore")

def create_traffic_dump():
    #shell_exec("sudo tcpdump -nnSXvv --no-promiscuous-mode -c 150 -i any -w detailed_capture.pcap")
    if config["nfo_capture"]:
        for server in config["nfo_servers"]:
            headers = {"Content-Type": "application/x-www-form-urlencoded",
                       "Cookie": "email=" + server.get('login') + ";password=" + server.get('password') + ";cookietoken=a"}

            data = urllib.parse.urlencode({"cookietoken": "a",
                                           "name": server.get('name'),
                                           "typeofserver": "virtual",
                                           "traffic_detailed": True,
                                           "traffic_submit": True})
            data = data.encode('ascii')
            url = "https://www.nfoservers.com/control/firewall.pl"
            try:
                req = urllib.request.Request(url, data, headers)
                with urllib.request.urlopen(req) as response:
                    the_page = response.read().decode("utf-8")
                    if not the_page.find("Traffic captured:"):
                        logging.info(f"{server.get('login')} {server.get('name')}: Failed detailed traffic capture: {str(the_page)}")
            except Exception as e:
                logging.error(f"create_traffic_dump: {traceback()} {e}")
    if platform.system() == "Linux":
        shell_exec("sudo tcpdump -nnSXvv --no-promiscuous-mode -c 150 -w detailed_capture.pcap")
        with open("detailed_capture.pcap", "rb") as f:
            return f.read()
    else:
        with open("detailed_capture.pcap", "w+") as f:
            f.write("Traffic couldn't be captured due to the OS not being Linux.")
        with open("detailed_capture.pcap", "r") as f:
            return f.read()

class tomislav_fernet():
    def __init__(self, fernet_instance):
        self.fernet = fernet_instance

    def enc(self, obj):
        try:
            string = json.dumps(obj)
            return (b"TOMISLAV_MESSAGE:::" + self.fernet.encrypt(string.encode())).decode()
        except Exception:
            print(f"t_enc: {traceback()}")
            return None

    def dec(self, packet):
        try:
            packet = packet.split(":::")
            if packet[0] and packet[0] == "TOMISLAV_MESSAGE":
                decrypted = self.fernet.decrypt(packet[1]).decode()
                return json.loads(decrypted)
            return None
        except Exception:
            print(f"t_dec: {traceback()}")
            return None

class stats():
    def __init__(self):
        self.network_recieved_old = 0
        self.network_packets_recieved_old = 0
        self.cpu_usage = 0
        self.difference_mbps = 0 
        self.difference_pps = 0
        self.delay = 5

    def update(self):
        self.difference = 0
        self.difference_packets = 0

        self.difference_mbps = 0
        self.difference_pps = 0

        self.cpu_usage = psutil.cpu_percent()
        network_recieved = int(psutil.net_io_counters().bytes_recv / 1e+6)
        network_packets_recieved = psutil.net_io_counters().packets_recv

        self.difference = max(network_recieved - self.network_recieved_old, 0)
        if self.difference == network_recieved:
            self.difference = 0
        self.network_recieved_old = network_recieved

        self.difference_packets = max(network_packets_recieved - self.network_packets_recieved_old, 0)
        if self.difference_packets == network_packets_recieved:
            self.difference_packets = 0
        self.network_packets_recieved_old = network_packets_recieved

        self.difference_mbps = int(self.difference / self.delay)
        self.difference_pps = int(self.difference_packets / self.delay)

        create_traffic_dump()

    def get_dict(self):
        return {"spike_mbps": self.difference_mbps, "spike_pps": self.difference_pps, "cpu_usage": self.cpu_usage}


class steam_logs():
    def find_address_steamid(self, directory, search_list, recursive=True, ignore_vpn=True):
        # nope
        return False
