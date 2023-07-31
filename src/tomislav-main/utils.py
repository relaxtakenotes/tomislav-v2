# custom
import discord
import httpx
from ping3 import ping
from mcstatus import JavaServer

# local/default
import valve.rcon
import a2s
from steamid_converter import Converter
from functools import wraps, partial
from time import time
import os
import json
import asyncio
from traceback import format_exc as traceback
from base64 import b64encode, b64decode
from random import randrange
import re
import shlex
import logging

valve.rcon.RCONMessage.ENCODING = "utf-8"

logging.basicConfig(level=logging.INFO, filename=f"logs/tomislav_{round(time())}_utils.log", filemode="w")

def async_wrap(func):
    ''' Wrapper for sync functions to make them async '''
    @wraps(func)
    async def run(*args, loop=None, executor=None, **kwargs):
        if loop is None:
            loop = asyncio.get_event_loop()
        pfunc = partial(func, *args, **kwargs)
        return await loop.run_in_executor(executor, pfunc)
    return run

def textwrap(text):
    return ["```" + (text[i:i + 1990]) + "```" for i in range(0, len(text), 1990)]

def format_log_output(output):
    nickname_string = ', '.join(list(set(output['nickname_list'])))
    steamid_string = ', '.join(list(set(output['steamid_list'])))
    ip_string = ', '.join(list(set(output['ip_list'])))
    num_conn = int(output['connection_times'])

    reply_content = f"Number of connections: {num_conn}\n"
    reply_content += f"IP's: {ip_string}\n"
    reply_content += f"SteamID's: {steamid_string}\n"
    reply_content += f"Nicknames: {nickname_string}\n"

    return reply_content

@async_wrap
def read_traffic_dump(data):
    if data:
        with open("detailed_capture.pcap", "wb+") as f:
            f.write(b64decode(data))
        return "detailed_capture.pcap"
    return None

class servers():
    def __init__(self, servers, fernet_instance):
        self.servers = servers
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

    def send_to_server(self, server, address, params, return_data=False, timeout=30):
        r = httpx.get(address, params={"data": self.enc(params)}, timeout=timeout)
        if return_data:
            return self.dec(r.json().get("data"))
        return {server.split("|")[0]: self.dec(r.json().get("data"))}

    @async_wrap
    def get_status(self):
        responses = {}
        for server in self.servers:
            try:
                address, password = server.split("|")
                address = "http://" + address + "/status"

                params = {'password': password}
                
                responses.update(self.send_to_server(server, address, params))
            except (httpx.ConnectTimeout, json.decoder.JSONDecodeError, httpx.ReadTimeout):
                # it's ok
                pass
        return responses

    @async_wrap
    def get_raw_status(self):
        responses = {}
        for server in self.servers:
            try:
                address, password = server.split("|")
                address = "http://" + address + "/status_raw"

                params = {'password': password}
                
                responses.update(self.send_to_server(server, address, params))
            except (httpx.ConnectTimeout, json.decoder.JSONDecodeError, httpx.ReadTimeout):
                # it's ok
                pass
        return responses

    @async_wrap
    def send_logs_request(self, query, recursive=False, ignore_vpn=False):
        result = {}
        result["ip_list"] = [] 
        result["steamid_list"] = [] 
        result["nickname_list"] = [] 
        result["connection_times"] = 0

        for server in self.servers:
            try:   
                address, password = server.split("|")
                address = "http://" + address + "/find_logs"

                params = {'find': query, 'password': password, 'recursive': recursive, 'ignore_vpn': ignore_vpn}

                response = self.send_to_server(server, address, params, return_data=True)

                result["ip_list"] += response.get("ip_list") 
                result["steamid_list"] += response.get("steamid_list") 
                result["nickname_list"] += response.get("nickname_list") 
                result["connection_times"] += response.get("connection_times")
            except (httpx.ConnectTimeout, json.decoder.JSONDecodeError, httpx.ReadTimeout):
                # it's ok
                pass
        return result

    @async_wrap
    def update_game_servers(self):
        responses = {}
        for server in self.servers:
            try:     
                address, password = server.split("|")
                address = "http://" + address + "/update_game_servers"
                params = {'password': password}
                responses.update(self.send_to_server(server, address, params, timeout=None))
            except (httpx.ConnectTimeout, json.decoder.JSONDecodeError, httpx.ReadTimeout):
                # it's ok
                pass
        return responses        

    @async_wrap
    def restart_game_servers(self):
        responses = {}
        for server in self.servers:
            try:     
                address, password = server.split("|")
                address = "http://" + address + "/restart_servers"
                params = {'password': password}
                responses.update(self.send_to_server(server, address, params))
            except (httpx.ConnectTimeout, json.decoder.JSONDecodeError, httpx.ReadTimeout):
                # it's ok
                pass
        return responses

class steam():
    def __init__(self, key):
        self.key = key

    def get_common_steam_acc_info(self, sid):
        link = f"https://api.steampowered.com/ISteamUser/GetPlayerSummaries/v0002/?key={self.key}&steamids={sid}"
        response = httpx.get(link)
        json_response = json.loads(response.text)
        return json_response

    @async_wrap
    def async_get_common_steam_acc_info(self, sid):
        link = f"https://api.steampowered.com/ISteamUser/GetPlayerSummaries/v0002/?key={self.key}&steamids={sid}"
        response_raw = httpx.get(link)
        response = response_raw.json()
        return response

    @async_wrap
    def get_random_avatar_from_steam(self):
        while True:
            try:
                prof_info = None
                while True:
                    prof_info = self.get_common_steam_acc_info(Converter.to_steamID64(f"[U:1:{randrange(1000000000)}]"))
                    prof_info = prof_info['response']['players'][0]
                    default_pfps = ["https://avatars.akamai.steamstatic.com/fef49e7fa7e1997310d705b2a6158ff8dc1cdfeb_full.jpg",
                                    "https://steamcdn-a.akamaihd.net/steamcommunity/public/images/avatars/fe/fef49e7fa7e1997310d705b2a6158ff8dc1cdfeb_full.jpg",
                                    "https://avatars.steamstatic.com/fef49e7fa7e1997310d705b2a6158ff8dc1cdfeb_full.jpg"]
                    if prof_info['avatarfull'] not in default_pfps:
                        break
                return prof_info
            except IndexError:
                pass  # lol

    @async_wrap
    def get_random_nicknames_from_steam(self, amount):
        amount = int(amount)
        if amount > 10:
            return "No more than 10, please."
        random_nicknames = []
        for i in range(amount):
            prof_info = None
            while True:
                prof_info = self.get_common_steam_acc_info(Converter.to_steamID64(f"[U:1:{randrange(1000000000)}]"))
                try:
                    prof_info = prof_info['response']['players'][0]
                    if prof_info['personaname']:
                        break
                except IndexError:
                    pass
            name = prof_info['personaname']
            random_nicknames.append(name)
        return ", ".join(random_nicknames)

    def convert_steam_id(self, vanityurl):
        sid = None
        link = f"https://api.steampowered.com/ISteamUser/ResolveVanityURL/v0001/?key={self.key}&vanityurl={''.join(vanityurl).replace('https://steamcommunity.com/id/', '').replace('https://steamcommunity.com/profiles/', '').replace('/', '')}"
        response = httpx.get(link).json().get("response")
        try:
            if response['steamid']:
                sid = str(Converter.to_steamID3(response['steamid']))
        except KeyError:
            try:
                sid = str(Converter.to_steamID3("".join(vanityurl)))
            except Exception:
                sid = "".join(vanityurl)
        return sid

    @async_wrap
    def convert_to_every_steamid(self, sid):
        sid_list = {}

        sid = self.convert_steam_id(sid)
        sid_list["id3"] = Converter.to_steamID3(sid)
        sid_list["id64"] = Converter.to_steamID64(sid)
        sid_list["id"] = Converter.to_steamID(sid)

        return sid_list

class u_ip():
    def __init__(self, key):
        self.key = key
        self.cached_vpn_results = {}

    async def vpn_ip_check(self, ip_list):
        cache_to_append = {}
        for ip in ip_list:
            if self.cached_vpn_results.get(ip):
                cache_to_append.update({str(ip): self.cached_vpn_results.get(ip)})
                ip_list.remove(ip)

        ips_info = {}
        if ip_list:
            r = None
            async with httpx.AsyncClient() as client:
                r = await client.post(f'https://proxycheck.io/v2/?key{self.key}&vpn=1&risk=1', data={"ips": ",".join(ip_list)})
                r = r.json()
            countries = await self.find_geolocation_batch(ip_list)
            del r["status"]
            for key, value in r.items():
                proxy = True if value.get("proxy") == "yes" else False
                risk = value.get("risk")
                result = {"proxy": proxy, "risk": risk, "location": countries[key]}
                ips_info[key] = result
                self.cached_vpn_results[key] = result

        ips_info.update(cache_to_append)
        return ips_info

    async def check_multiple_ips_str(self, ip_list):
        output = ""
        ips_info = await self.vpn_ip_check(ip_list)
        for key, value in ips_info.items():
            output += f"{key} - Proxy: {value.get('proxy')} | Risk: {value.get('risk')} | Location: {value.get('location')}\n"

        return output     

    async def check_multiple_ips(self, ip_list):
        clean_ips = []
        vpn_ips = []

        ips_info = await self.vpn_ip_check(ip_list)

        for key, value in ips_info.items():
            if value.get("proxy") or int(value.get("risk")) > 50:
                vpn_ips.append(key)
            else:
                clean_ips.append(key)

        return clean_ips, vpn_ips

    async def find_geolocation_batch(self, ip_list):
        response = None
        async with httpx.AsyncClient() as client:
            headers = {
                'accept': "application/json",
                'content-type': "application/json"}
            response_raw = await client.post(f"http://ip-api.com/batch?fields=status,country,regionName,city,query", headers=headers, data=json.dumps(ip_list))
            response = response_raw.json()

        locations = {}

        for result in response:
            query = result.get("query")
            if not query:
                continue
            geolocation_array = [result.get("country", "Unknown"),
                                result.get("regionName", "Unknown"),
                                result.get("city", "Unknown")]
            location = ", ".join(geolocation_array)
            locations.update({f"{query}": f"{location}"})

        return locations

    async def find_geolocation(self, ip, return_array=False):
        try:
            async with httpx.AsyncClient() as client:
                headers = {'accept': "application/json", 'content-type': "application/json"}
                response_raw = await client.get(f"http://ip-api.com/json/{ip}?fields=status,country,regionName,city,query", headers=headers)
            response = response_raw.json()
        except Exception as e:
            return f"Failed to get the geolocation... {e}"

        geolocation_array = [response.get("country", "Unknown"),
                            response.get("regionName", "Unknown"),
                            response.get("city", "Unknown")]

        if return_array:
            return geolocation_array

        return ", ".join(geolocation_array)

class src_interface():
    def __init__(self, ip_forensics=None):
        self.cached_shortened_url = {}
        self.ip_forensics = ip_forensics

    # here because of the ip_forensics class
    async def get_mc_query_embed(self, address, add_time=False):
        if address.startswith("169.254"):
            return discord.Embed(title="Server Information", description="Link-local IP. Wtf?", color=discord.Colour.red())
        if not ":" in address:
            return discord.Embed(title="Server Information", description="Include the port as well!", color=discord.Colour.red())

        ip_f, port_f = address.replace(" ", "").split(":")

        ip_f = str(ip_f)
        port_f = str(port_f)

        geolocation = "..."
        if self.ip_forensics:
            geolocation = await self.ip_forensics.find_geolocation(ip_f)
        try:
            server = JavaServer.lookup(address)
            status = server.status()
            query = server.query()

            player_names = "**No players!**"
            player_names_array = []
            for name in query.players.names:
                player_names_array.append(F"`{name}`")
            if player_names_array:
                player_names = ", ".join(player_names_array)

            embedVar = discord.Embed(title=f"Query Information", color=discord.Colour.green(), description=geolocation)
            embedVar.add_field(name="IP: ", value=address.strip(), inline=False)
            embedVar.add_field(name="MOTD: ", value=query.motd, inline=False)
            embedVar.add_field(name="Game: ", value="Minecraft", inline=False)
            embedVar.add_field(name="Player Count: ", value=status.players.online, inline=False)
            embedVar.add_field(name="Player List: ", value=player_names, inline=False)
        except Exception as e:
            ping_thing = ping(ip_f)
            if ping_thing is None:
                ping_result = "Timed out. (Server most likely down)"
            elif not ping_thing:
                ping_result = "Host unknown. (Invalid IP/Address)"
            else:
                ping_result = f"Ping took {round(ping_thing*1000)}ms (The IP is responsive and the server is most likely alive)"
            embedVar = discord.Embed(title=f"Error... {e}", description=geolocation, color=discord.Colour.red())
            embedVar.add_field(name="IP: ", value=address, inline=False)
            embedVar.add_field(name="Ping result: ", value=ping_result, inline=False)
        if add_time:
            embedVar.add_field(name=f"Time of query:", value=f"Updated on: <t:{round(time())}:f> (<t:{round(time())}:R> for you)")
        return embedVar

    async def get_query_embed(self, address, add_time=False):
        if address.startswith("169.254"):
            return discord.Embed(title="Server Information", description="Link-local IP. Source Datagram Relays output this IP to protect the servers from DDOS attacks. If you need to find a casual server IP, look up its name in google.", color=discord.Colour.red())

        ip_f, port_f = address.replace(" ", "").split(":")

        ip_f = str(ip_f)
        port_f = str(port_f)

        geolocation = "..."
        if self.ip_forensics:
            geolocation = await self.ip_forensics.find_geolocation(ip_f)

        try:
            serverinfo = await a2s.ainfo((ip_f, port_f))
            players = await a2s.aplayers((ip_f, port_f))
            player_names_array = []
            for player in players:
                if player.name:
                    player_name = player.name.replace("\r", "").replace("\n", "").replace("`", "")
                    player_names_array.append(f"`{player_name}`")
                else:
                    player_names_array.append("**(Player loading in...)**")

            if player_names_array:
                player_names = ", ".join(player_names_array)
            else:
                player_names = "**No players!**"

            #shortened_url = self.cached_shortened_url.get(address)
            #if not shortened_url:
            #    async with httpx.AsyncClient() as client:
            #        r = await client.post("https://is.gd/create.php", params={"format": "simple", "url": address})
            #        shortened_url = r.text
            #        self.cached_shortened_url.update({address: shortened_url})

            embedVar = discord.Embed(title=f"Query Information", color=discord.Colour.green(), description=geolocation)
            embedVar.add_field(name="IP: ", value=address.strip(), inline=False)
            embedVar.add_field(name="Server Name: ", value=serverinfo.server_name, inline=False)
            embedVar.add_field(name="Game: ", value=serverinfo.game, inline=False)
            embedVar.add_field(name="Player Count: ", value=f"{serverinfo.player_count}/{serverinfo.max_players}", inline=False)
            embedVar.add_field(name="Map: ", value=serverinfo.map_name, inline=False)
            embedVar.add_field(name="Player List: ", value=player_names, inline=False)
        except Exception as e:
            ping_thing = ping(ip_f)
            if ping_thing is None:
                ping_result = "Timed out. (Server most likely down)"
            elif not ping_thing:
                ping_result = "Host unknown. (Invalid IP/Address)"
            else:
                ping_result = f"Ping took {round(ping_thing*1000)}ms (The IP is responsive and the server is most likely alive)"
            embedVar = discord.Embed(title=f"Error... {e}", description=geolocation, color=discord.Colour.red())
            embedVar.add_field(name="IP: ", value=address, inline=False)
            embedVar.add_field(name="Ping result: ", value=ping_result, inline=False)
        if add_time:
            embedVar.add_field(name=f"Time of query:", value=f"Updated on: <t:{round(time())}:f> (<t:{round(time())}:R> for you)")
        return embedVar

    @async_wrap
    def rcon(self, address, rcon_pass, command):
        ip, port = address.split(":")
        ip = str(ip)
        port = int(port)
        with valve.rcon.RCON((ip, port), rcon_pass, timeout=4) as rcon:
            rcon_result = rcon(command)
            if not rcon_result:
                return "Command was executed but no response was received.\n"
            return rcon_result

    async def steamid_ban(self, steamid_list, reason, minutes, servers):
        result = {}
        for server in servers:
            rcon_ip, rcon_pass = server.split("|")
            status_rcon = await self.rcon(rcon_ip, rcon_pass, f"status")
            command = ""
            for sid in steamid_list:
                userid = ""
                for line in status_rcon.split("\n"):
                    if sid in line:
                        # remove multiple spaces, find userid pattern, turn the array into a string, remove spaces
                        userid = "".join(re.findall(r"# [0-9]+", " ".join(line.split()))).replace(" ", "")
                command += f"sm_kick {userid} {reason}; sm_addban {minutes} {sid} {reason};"
            output = await self.rcon(rcon_ip, rcon_pass, command)
            if "[SM] Ban has been added." in output:
                result.update({rcon_ip: "Success"})
            else:
                result.update({rcon_ip: "Fail: " + output})
        return result

    async def ip_ban(self, ip_list, reason, minutes, servers):
        result = {}
        for server in servers:
            rcon_ip, rcon_pass = server.split("|")
            status_rcon = await self.rcon(rcon_ip, rcon_pass, f"status")
            command = ""
            for ip in ip_list:
                userid = ""
                for line in status_rcon.split("\n"):
                    if ip in line:
                        # remove multiple spaces, find userid pattern, turn the array into a string, remove spaces
                        userid = "".join(re.findall(r"# [0-9]+", " ".join(line.split()))).replace(" ", "")
                command += f"sm_kick {userid} {reason}; addip {minutes} {ip};"
            output = await self.rcon(rcon_ip, rcon_pass, f"{command} writeip")
            result.update({rcon_ip: "Unknown (addip doesn't return anything so we can't know if it worked!)"})
            #if "Command was executed but no response was received." in output:
            #    result.update({rcon_ip: "Success"})
            #else:
            #    result.update({rcon_ip: "Fail: " + output})
        return result

    async def unban(self, id_list, reason, servers):
        result = {}
        for server in servers:
            rcon_ip, rcon_pass = server.split("|")
            status_rcon = await self.rcon(rcon_ip, rcon_pass, f"status")
            output = ""
            for idd in id_list:
                output += await self.rcon(rcon_ip, rcon_pass, f"sm_unban {idd}")
            if "filter removed for" in output:
                result.update({rcon_ip: "Success"})
            else:
                result.update({rcon_ip: "Fail"})
        return result

    def format_status(self, status):
        status = status.split("\n")
        players = []
        for idx, line in enumerate(status):
            if idx < 10:  # get rid of that server info garbage
                continue
            if len(status) - idx == 1:  # get rid of the phantom newline i cant get rid of otherwise
                continue
            line = " ".join(line.split())
            user = {
                "userid": "".join(re.findall(r"# [0-9]+", " ".join(line.split()))).replace(" ", ""),
                "username": re.findall(r"\"([^\"]*)\"", line)[0],
                "steamid": re.findall(r'(\[U:[10]:[0-9]+\])', line)[0],
                "ip": re.findall(r'[0-9]+(?:\.[0-9]+){3}', line)[0]                
            }
            players.append(user)
        return players
