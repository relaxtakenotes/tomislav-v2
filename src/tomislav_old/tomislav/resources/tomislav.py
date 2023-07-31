#!/usr/bin/env python3

# local
import valve.rcon
import a2s

# global
import discord
from discord.ext import tasks
import psutil
from ping3 import ping
import asyncio
from youtubesearchpython import VideosSearch
from steamid_converter import Converter
from mcstatus import JavaServer
import httpx
import ipaddress

import os
import shlex
import urllib
from random import randrange, choice, random
import re
import traceback
import json
import logging
from functools import wraps, partial
import subprocess
from time import sleep, time
import socket

usercfg = ""
fernet = None
logging.basicConfig(level=logging.INFO, filename=f"../logs/tomislav_{round(time())}.log", filemode="w")

def async_wrap(func):
    ''' Wrapper for sync functions to make them async '''
    @wraps(func)
    async def run(*args, loop=None, executor=None, **kwargs):
        if loop is None:
            loop = asyncio.get_event_loop()
        pfunc = partial(func, *args, **kwargs)
        return await loop.run_in_executor(executor, pfunc)
    return run

def clamp(n, smallest, largest):
    return max(smallest, min(n, largest))

class MyClient(discord.Client):
    def is_responding(self, processName):
        ''' Give the executable name and it'll return if it's responding '''
        for proc in psutil.process_iter():
            try:
                # Check if process name contains the given name string.
                if processName.lower() in proc.name().lower():
                    return True
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass
        return False

    async def vpn_ip_check(self, ip_list):
        if type(ip_list) == str:
            ip_list = ip_list.split(",")

        cache_to_append = {}
        for ip in ip_list:
            if self.cached_vpn_results.get(ip):
                cache_to_append.update({str(ip): self.cached_vpn_results.get(ip)})
                ip_list.remove(ip)

        ips_info = {}
        if ip_list:
            r = None
            async with httpx.AsyncClient() as client:
                r = await client.post(f'https://proxycheck.io/v2/?key{config["proxyapi_key"]}&vpn=1&risk=1', data={"ips": ",".join(ip_list)}) # wtf proxycheck?
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

    ''' pass on a list of ips separated by commas'''
    async def check_multiple_ips(self, ip_list):
        ip_list = ip_list.split(", ")
        clean_ips = []
        vpn_ips = []

        ips_info = await self.vpn_ip_check(ip_list)

        for key, value in ips_info.items():
            if value.get("proxy") or int(value.get("risk")) > 50:
                vpn_ips.append(key)
            else:
                clean_ips.append(key)

        return clean_ips, vpn_ips

    def get_common_steam_acc_info(self, sid):
        link = f"https://api.steampowered.com/ISteamUser/GetPlayerSummaries/v0002/?key={config['steamapi_key']}&steamids={sid}"
        response = httpx.get(link)
        json_response = json.loads(response.text)
        return json_response

    @async_wrap
    def async_get_common_steam_acc_info(self, sid):
        link = f"https://api.steampowered.com/ISteamUser/GetPlayerSummaries/v0002/?key={config['steamapi_key']}&steamids={sid}"
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
                                    "https://steamcdn-a.akamaihd.net/steamcommunity/public/images/avatars/fe/fef49e7fa7e1997310d705b2a6158ff8dc1cdfeb_full.jpg"]
                    if not (prof_info['avatarfull'] in default_pfps):
                        break
                return prof_info
            except IndexError:
                pass  # lol

    @async_wrap
    def get_random_nicknames_from_steam(self, amount):
        try:
            amount = int(amount)
            if amount > 10:
                return "No more than 10, please, dumbass."
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
        except Exception:
            logging.error(f"get random nicknames from steam: {traceback.format_exc()}")
            return f"{traceback.format_exc()}"

    def convert_steam_id(self, vanityurl):
        sid = None
        link = f"https://api.steampowered.com/ISteamUser/ResolveVanityURL/v0001/?key={config['steamapi_key']}&vanityurl={''.join(vanityurl).replace('https://steamcommunity.com/id/', '').replace('https://steamcommunity.com/profiles/', '').replace('/', '')}"
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
        try:
            sid = self.convert_steam_id(sid)
            sid_list["id3"] = Converter.to_steamID3(sid)
            sid_list["id64"] = Converter.to_steamID64(sid)
            sid_list["id"] = Converter.to_steamID(sid)

            return sid_list
        except Exception:
            return False

    async def find_address_steamid_internal(self, directory, find, sid=False, search_list=[]):
        # nope
        return output

    async def find_address_steamid(self, target, directory, find, sid=False, raw=False, pass_arrays=False, search_list=[]):
        array = await self.find_address_steamid_internal(directory, find, sid, search_list)
        temp_text = "\n".join(array)

        if raw and array:
            await self.send_wrapped_text(temp_text, target)
            return

        ip_list = re.findall(r'[0-9]+(?:\.[0-9]+){3}', temp_text)
        steamid_list = re.findall(r'(\[U:[10]:[0-9]+\])', temp_text)
        nickname_list = re.findall(r' \".*?<.*?>', temp_text)
        connection_times = re.findall(r'\d\d\/\d\d\/\d\d\d\d', temp_text)

        for i, name in enumerate(nickname_list):
            nickname_list[i] = name[2:].replace(re.search(r'<\d{1,}>', name).group(), "").replace("`", "").replace(",", "")
        nickname_list = list(set(nickname_list))

        ip_list = list(set(ip_list))
        steamid_list = list(set(steamid_list))
        nickname_list = list(set(nickname_list))

        if pass_arrays:
            tempholder = {}
            tempholder["ip_list"] = ip_list
            tempholder["steamid_list"] = steamid_list
            tempholder["nickname_list"] = nickname_list
            tempholder["connection_times"] = connection_times
            return tempholder

        # This assumes the weird american time format
        for i, timee in enumerate(connection_times):
            timee = timee.split("/")
            month = timee[0]
            day = timee[1]
            year = timee[2]
            connection_times[i] = f"{year}/{month}/{day}"
        connection_times.sort()

        if ip_list or steamid_list or nickname_list:
            stuff_lol = f"Looked up {' '.join(find)}!\n"
            stuff_lol += f"Number of connections: {len(connection_times)}\n"
            stuff_lol += f"Last connection: {connection_times[-1]}\n"
            stuff_lol += f"IP's: {', '.join(ip_list)}\n"
            stuff_lol += f"SteamID's: {', '.join(steamid_list)}\n"
            stuff_lol += f"Nicknames: {', '.join(nickname_list)}\n"
            await self.send_wrapped_text(stuff_lol, target)
            return

        await self.send_wrapped_text("No results!", target)

    async def find_geolocation(self, ip, return_array=False):
        try:
            async with httpx.AsyncClient() as client:
                headers = {
                    'accept': "application/json",
                    'content-type': "application/json"}
                response_raw = await client.get(f"http://ip-api.com/json/{ip}?fields=status,country,regionName,city,query", headers=headers)
            response = response_raw.json()
        except Exception as e:
            return f"Failed to get the geolocation... {e}"

        geolocation_array = [response.get("country", "Shithole"),
                            response.get("regionName", "Shithole"),
                            response.get("city", "Shithole")]

        if return_array:
            return geolocation_array

        return ", ".join(geolocation_array)

    async def find_geolocation_batch(self, ip_list):
        response = None
        async with httpx.AsyncClient() as client:
            headers = {
                'accept': "application/json",
                'content-type': "application/json"}
            response_raw = await client.post(f"http://ip-api.com/batch?fields=status,country,regionName,city,query", headers=headers, 
                                            data=json.dumps(ip_list))
            response = response_raw.json()

        locations = {}

        for result in response:
            query = result.get("query")
            if not query:
                continue
            geolocation_array = [result.get("country", "Shithole"),
                                result.get("regionName", "Shithole"),
                                result.get("city", "Shithole")]
            location = ", ".join(geolocation_array)
            locations.update({f"{query}": f"{location}"})

        return locations

    @async_wrap
    def query_the_server_minecraft_internal(self, address, port):
        return JavaServer(address, port).query()

    async def query_the_server_minecraft(self, address, port, add_time):
        try:
            query = await self.query_the_server_minecraft_internal(address, port)
            player_array = []
            motd = None
            version_mc = []
            for player in query.players.names:
                player_array.append(f"`{player}`")
            if not player_array:
                player_array = ["**No players.**"]
            if query.motd:
                motd = query.motd
            if query.software:
                version_mc = query.software.version
            geolocation = await self.find_geolocation(str(address))
            embedVar = discord.Embed(title="Server Information", description=geolocation, color=discord.Colour.green())
            embedVar.add_field(name="IP:", value=f"{address}:{port}", inline=False)
            embedVar.add_field(name="Game:", value="Minecraft", inline=False)
            embedVar.add_field(name="Version:", value=version_mc, inline=False)
            embedVar.add_field(name="MOTD:", value=motd, inline=False)
            embedVar.add_field(name="Player list:", value=", ".join(player_array), inline=False)
            if add_time:
                embedVar.add_field(name=f"Time of query:", value=f"Updated on: <t:{round(time())}:f> (<t:{round(time())}:R> for you)")
            return embedVar
        except Exception as e:
            embedVar = discord.Embed(title="Something went wrong.", description=e, color=discord.Colour.red())
            if add_time:
                embedVar.add_field(name=f"Time of query:", value=f"Updated on: <t:{round(time())}:f> (<t:{round(time())}:R> for you)")
            return embedVar

    async def query_the_server(self, ip, add_status=False, add_time=False):
        ''' Queries a source engine game server, puts it into a neat embed and returns it.
            add_status adds the game server status(high cpu usage, high traffic spikes, etc) to the embed, so you only should use it for your own server
            add_time just adds... time.
         '''

        if ip.startswith("169.254"):
            return discord.Embed(title="Server Information", description="Link-local IP. Source Datagram Relays output this IP to protect the servers from DDOS attacks. If you need to find a casual server IP, look up its name in google.", color=discord.Colour.red())

        ip_f, port_f = map(ip.replace(" ", "").split(":"), str)

        geolocation = await self.find_geolocation(ip_f)
        try:
            try:
                serverinfo = await a2s.ainfo((ip_f, port_f))
                players = await a2s.aplayers((ip_f, port_f))
                player_names_array = []
                for player in players:
                    if player.name:
                        player_name = player.name.replace("\r", "").replace("\n", "").replace("`", "")
                        player_names_array.append(f"`{player_name}` **({player.score} points)**")
                    else:
                        player_names_array.append("**(Player loading in...)**")

                if player_names_array:
                    player_names = ", ".join(player_names_array)
                else:
                    player_names = "**No players!**"

                embedVar = discord.Embed(title="Server Information", color=discord.Colour.green(), description=geolocation)
                embedVar.add_field(name="IP: ", value=ip.strip(), inline=False)
                embedVar.add_field(name="Server Name: ", value=serverinfo.server_name, inline=False)
                embedVar.add_field(name="Game: ", value=serverinfo.game, inline=False)
                embedVar.add_field(name="Tags: ", value=serverinfo.keywords.replace(",", ", "), inline=False)
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
                embedVar.add_field(name="IP: ", value=ip.strip(), inline=False)
                embedVar.add_field(name="Ping result: ", value=ping_result, inline=False)
                if (ip == config["server_ips"][0] and usercfg == "hvhusa") or (ip == config["server_ips"][1] and usercfg == "ns3072638"):  # usa.hvh.tf:27015
                    server_state = await self.ping_server(rcon_ip, config["rcon_pass"])
                    temp_string = ""
                    if server_state:
                        temp_string = "Server responds to echo. This could mean the query just failed or the server is under attack. Either way you can connect safely."
                    else:
                        temp_string = "Server doesn't respond to echo. Is dead."
                    embedVar.add_field(name="Server state: ", value=temp_string, inline=False)
            if add_time:
                embedVar.add_field(name=f"Time of query:", value=f"Updated on: <t:{round(time())}:f> (<t:{round(time())}:R> for you)")
            return embedVar
        except Exception as e:
            logging.error(f"query_the_server: {traceback.format_exc()}")
            await self.send_wrapped_text(target=self.grabbed_log_channel, text=traceback.format_exc(), pre_text="`Fail in query_the_server()!`")
            return discord.Embed(title=f"Error... {e}", description=geolocation, color=discord.Colour.red())

    async def send_embedded_image(self, link, target):
        ''' Simply embeds an image. changes the bar color to random and then sends it.
            link is the image that you want to embed
            target is the person/channel where you need to send the embedded image to
        '''
        embed = discord.Embed(color=discord.Colour.random())
        embed.set_image(url=link)
        try:
            await target.channel.send(embed=embed)
        except AttributeError:
            await target.send(embed=embed)

    async def send_file(self, directory, target):
        ''' Sends a file. That's it. I don't know why I made it.
            directory is quite literally the directory to the file
            target is the person/channel where you need to send the file to
        '''
        try:
            await target.channel.send(file=discord.File(directory))  # server
        except AttributeError:
            await target.send(file=discord.File(directory))  # dm

    def random_line(self, file):
        ''' Gets a random line from a specified file and returns it
            file accepts the directory to the... file
        '''
        with open(file, encoding='UTF-8') as f:
            links = f.read()
            return choice(links.rstrip().splitlines())

    async def native_capture(self):
        ''' Creates a detailed traffic capture through tcpdump
            you call and await for it, then use await send_file("detailed_capture.txt")
        '''
        if usercfg == "ns3072638":
            await self.shell_exec("sudo tcpdump -nnSXvv --no-promiscuous-mode -c 500 -i eno1 -w detailed_capture.pcap")
        else:
            await self.shell_exec("sudo tcpdump -nnSXvv --no-promiscuous-mode -c 500 -w detailed_capture.pcap")

    @async_wrap
    def nfo_capture(self, email, password, server_name):
        ''' Request a detailed traffic capture in the NFO control panel '''
        headers = {"Content-Type": "application/x-www-form-urlencoded",
                   "Cookie": "email=" + email + ";password=" + password + ";cookietoken=a"}

        data = urllib.parse.urlencode({"cookietoken": "a",
                                       "name": server_name,
                                       "typeofserver": "virtual",
                                       "traffic_detailed": True,
                                       "traffic_submit": True})
        data = data.encode('ascii')
        url = "https://www.nfoservers.com/control/firewall.pl"
        try:
            req = urllib.request.Request(url, data, headers)
            with urllib.request.urlopen(req) as response:
                the_page = response.read().decode("utf-8")
                if the_page.find("Traffic captured:"):
                    return True
        except Exception as e:
            return f"We ran into some problems: {e}"

    async def send_wrapped_text(self, text, target, pre_text=False):
        ''' Wraps the passed text under the 2000 character limit, sends everything and gives it neat formatting.
            text is the text that you need to wrap
            target is the person/channel where you need to send the wrapped text to
        '''
        if pre_text:
            pre_text = pre_text + "\n"
        else:
            pre_text = ""

        try:
            target = target.channel
        except AttributeError:
            pass

        wrapped_text = [(text[i:i + 1992 - len(pre_text)]) for i in range(0, len(text), 1992 - len(pre_text))]
        for i in range(len(wrapped_text)):
            if i > 0:
                pre_text = ""
            await target.send(f"{pre_text}```{wrapped_text[i]}```")

    async def warn_admins(self, text, send_capture=False):
        ''' DM's admins with specified text and sends traffic capture if told so
            text is the text that you need to send
            send_capture set to true will send the traffic capture, logically, false wont
        '''
        if self.mute_notifications:
            return

        if debug_mode:
            print(f"Attempted to send this: '{text}', skipped due to debug mode.")
            return

        text = f"<@&{config['notifications_role']}> {text}"

        if not send_capture:
            await self.notif_channel.send(f"{text}")
            return

        if config["traffic_capture_type"] == "nfo":
            result = await self.nfo_capture(config["nfo_email"], config["nfo_password"], config["nfo_server_name"])
            if result:
                await self.notif_channel.send(f"{text} (detailed capture has been made)")
            else:
                await self.notif_channel.send(f"{text} (error requsting a detailed capture: {result})")
        else:
            await self.native_capture()
            await self.notif_channel.send(f"{text}", file=discord.File("detailed_capture.pcap"))

    @async_wrap
    def video_search(self, query, result_limit):
        ''' Simply a wrapped sync videosearch function to make it async. Use it the same way but with await
            I made it because I didn't like the next() requirement in the original async library
        '''
        raw_result = VideosSearch(query, limit=result_limit)
        return raw_result.result()

    async def update_bot(self, message):
        try:
            message = message.channel
        except AttributeError:
            pass
        reset_output_cmd = await self.shell_exec("git reset --hard")
        update_output_cmd = await self.shell_exec("git pull")
        await self.send_wrapped_text(reset_output_cmd + "\n" + update_output_cmd, message)
        await message.send("The bot will now be restarted.")
        sleep(0.1)
        await client.close()
        exit()

    async def video_search_on_command(self, message, query, limit, random=False):
        ''' Search a video on youtube in on_message event
            message accepts the whole message that you get in the on_message event
            random decides if you will get 1 random video or a list of videos
        '''
        links = []
        try:
            message = message.channel
        except AttributeError:
            pass

        if random:
            results = await self.video_search(" ".join(query), 100)
            if results["result"]:
                await message.send(results["result"][randrange(len(results["result"]))]["link"])
            else:
                embedVar = discord.Embed(title="No video found!", color=discord.Colour.red())
                await message.send(embed=embedVar)
        else:
            results = await self.video_search(" ".join(query), int(limit))
            if results["result"]:
                for i in range(len(results["result"])):
                    links.append(results["result"][i]["link"])
                links_string = "\n".join(links)
                await message.send(links_string)
            else:
                embedVar = discord.Embed(title="No video found!", color=discord.Colour.red())
                await message.send(embed=embedVar)

    @async_wrap
    def server_rcon(self, ip, password, command):
        # Valve RCON made async by the bad and dumb means.
        with valve.rcon.RCON(ip, password, timeout=4) as rcon:
            rcon_result = rcon(command)
            if not rcon_result:
                return "Command was executed but no response was received.\n"
            return rcon_result

    async def ping_server(self, ip, password):
        # Ping a server through rcon and return true if anything was returned
        try:
            rcon_resp = await self.server_rcon(ip, password, "echo ping")
            if rcon_resp:
                return True
            else:
                return False
        except Exception:
            return False

    @async_wrap
    def shell_exec(self, command):
        p = subprocess.Popen(shlex.split(command), stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()
        return p[0].decode("utf-8", errors="ignore")

    async def restart_server(self, kill=False):
        await self.server_rcon(rcon_ip, config["rcon_pass"], "say [AUTO] Server is restarting. Return later.")
        await self.shell_exec("sudo systemctl restart tf2server")
        return True

    async def steamid_ban(self, steamid_list, reason, minutes):
        result = ""
        status_rcon = await self.server_rcon(rcon_ip, config["rcon_pass"], f"status")
        for sid in steamid_list:
            result += await self.server_rcon(rcon_ip, config["rcon_pass"], f"sm_addban {minutes} {sid} {reason}")
            userid = ""
            for line in status_rcon.split("\n"):
                if sid in line:
                    # remove multiple spaces, find userid pattern, turn the array into a string, remove spaces
                    userid = "".join(re.findall(r"# [0-9]+", " ".join(line.split()))).replace(" ", "")
            result += await self.server_rcon(rcon_ip, config["rcon_pass"], f"sm_kick {userid} {reason}")
        return result

    async def ip_ban(self, ip_list, reason, minutes):
        result = ""
        status_rcon = await self.server_rcon(rcon_ip, config["rcon_pass"], f"status")
        for ip in ip_list:
            userid = ""
            for line in status_rcon.split("\n"):
                if ip in line:
                    # remove multiple spaces, find userid pattern, turn the array into a string, remove spaces
                    userid = "".join(re.findall(r"# [0-9]+", " ".join(line.split()))).replace(" ", "")

            result += await self.server_rcon(rcon_ip, config["rcon_pass"], f"sm_kick {userid} {reason}")
            result += await self.server_rcon(rcon_ip, config["rcon_pass"], f"addip {minutes} {ip}")
        sleep(0.05)
        result += await self.server_rcon(rcon_ip, config["rcon_pass"], f"writeip")
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

    async def on_ready(self):
        self.network_recieved_old = 0
        self.network_packets_recieved_old = 0
        self.fully_ready = False
        self.cached_vpn_results = {}
        self.mute_notifications = False

        self.grab_and_start_tasks.start()

    @tasks.loop(seconds=60)
    async def funny_messages_routine(self):
        result = self.random_line("../cfg/status_messages.txt")
        await client.change_presence(activity=discord.Game(name=result))

    @tasks.loop(seconds=30)
    async def update_servers(self):
        try:
            if debug_mode:
                return
            for message in self.grabbed_update_messages:
                match message.id:
                    case 880453221418696714:
                        sinfo1 = await self.query_the_server(config["server_ips"][0], add_status=True, add_time=True)
                        await message.edit(embed=sinfo1)
                    case 887697061062000720:
                        sinfo2 = await self.query_the_server(config["server_ips"][1], add_status=True, add_time=True)
                        await message.edit(embed=sinfo2)
                    case _:
                        pass
        except Exception:
            logging.error(f"stupid stupid bug in update_servers: {traceback.format_exc()}")
            await self.send_wrapped_text(text=traceback.format_exc(), target=self.grabbed_log_channel, pre_text="stupid stupid bug in update_servers")

    @tasks.loop(seconds=5)
    async def traffic_check(self):
        if debug_mode:
            return
        self.difference = 0  # in the 5 second period
        self.difference_packets = 0  # in the 5 second period

        self.difference_mbps = 0  # actual per second value
        self.difference_pps = 0  # actual per second value

        cpu_usage = psutil.cpu_percent()
        network_recieved = int(psutil.net_io_counters().bytes_recv / 1e+6)
        network_packets_recieved = psutil.net_io_counters().packets_recv
        ''' We're calculating the traffic spike here '''
        self.difference = max(network_recieved - self.network_recieved_old, 0)
        if self.difference == network_recieved:
            self.difference = 0
        self.network_recieved_old = network_recieved

        self.difference_packets = max(network_packets_recieved - self.network_packets_recieved_old, 0)
        if self.difference_packets == network_packets_recieved:
            self.difference_packets = 0
        self.network_packets_recieved_old = network_packets_recieved

        self.difference_mbps = int(self.difference / 5)
        self.difference_pps = int(self.difference_packets / 5)

        if cpu_usage >= 90:
            await self.warn_admins(f"**The CPU usage is very high: {cpu_usage}%!**", send_capture=True)

        if self.difference_mbps >= 200 or self.difference_pps >= 80000:
            await self.warn_admins(f"**Possible DDOS attack! ({self.difference_mbps}mbps / {self.difference_pps}pps)**", send_capture=True)

    @tasks.loop(seconds=1, count=1)
    async def grab_and_start_tasks(self):
        await self.wait_until_ready()
        self.grabbed_update_messages = []
        logging.info("[LOAD] Grabbing channels...")
        try:
            self.grabbed_admin_channel = await client.fetch_channel(config["admin_text_channel"])
            self.grabbed_log_channel = await client.fetch_channel(config["logs_channel"])
            self.notif_channel = await client.fetch_channel(int(config["notifications_id"]))
            for channel_and_message in config["update_message"]:
                channel, message = channel_and_message.replace("c", "").replace("m", "").split(":")
                grabbed_channel = await client.fetch_channel(channel)
                grabbed_message = await grabbed_channel.fetch_message(message)
                self.grabbed_update_messages.append(grabbed_message)
        except (discord.errors.NotFound, discord.errors.Forbidden):
            logging.warning(f"[IMPORTANT] Not able to grab some channels! This will result in some functions not working. Please check the ID's in your config: {traceback.format_exc()}")

        logging.info(f"[LOAD] Success. Logged in as \"{self.user}\" ")

        self.traffic_check.start()
        self.update_servers.start()
        self.funny_messages_routine.start()

        self.fully_ready = True

    async def handle_admin_commands(self, message):
        if message.guild.id in config['whitelisted_server_ids'] and message.author.guild_permissions.administrator:
            match message.content.split():
                case [".toggle_notifs", *args]:
                    self.mute_notifications = not self.mute_notifications
                    await self.send_wrapped_text(f"{self.mute_notifications}", message)
                case [".updatebots", *args]:
                    await self.update_bot(message)
                case [".logs", *args]:
                    if not args[0:]:
                        await self.send_wrapped_text("Usage: .logs (Any keyword)", message)
                        return
                    await self.find_address_steamid(target=message, directory=config["logs_path"], find=args[0:], sid=False)
                case [".logs_sid", *args]:
                    if not args[0:]:
                        await self.send_wrapped_text("Usage: .logs_sid (SteamID of any type)", message)
                        return
                    await self.find_address_steamid(target=message, directory=config["logs_path"], find=args[0:], sid=True)
                case [".logs_mult", *args]:
                    if not args[0:]:
                        await self.send_wrapped_text("Usage: .logs_mult (multiple of, split by commas: ip, name or SteamID of type [U:1:69696969])", message)
                        return
                    search_args = " ".join(args[0:]).split(", ")
                    await self.find_address_steamid(target=message, directory=config["logs_path"], find=args[0:], sid=True, search_list=search_args)
                case [".rawlogs", *args]:
                    if not args[0:]:
                        await self.send_wrapped_text("Usage: .rawlogs (Any keyword)", message)
                        return
                    await self.find_address_steamid(target=message, directory=config["logs_path"], find=args[0:], sid=False, raw=True)
                case [".rawlogs_sid", *args]:
                    if not args[0:]:
                        await self.send_wrapped_text("Usage: .rawlogs_sid (SteamID of any type)", message)
                        return
                    await self.find_address_steamid(target=message, directory=config["logs_path"], find=args[0:], sid=True, raw=True)
                case [".ban", *args]:
                    if not args[0:]:
                        await self.send_wrapped_text("Usage: .ban (minutes) \"[U:1:LOL], (steamids of any type separated by spaces and commas.. in quotes!!)\" \"reason\"", message)
                        return

                    steamid_list = []
                    minutes = int(args[0])
                    reason = " ".join(args[2:])

                    regex_thing = re.findall(r"\"([^\"]*)\"", " ".join(args))
                    reason = regex_thing[1]
                    raw_sid_list = regex_thing[0].split(", ")

                    for sid in raw_sid_list:
                        steamid_conv = await self.convert_to_every_steamid(sid)
                        steamid_list.append(steamid_conv["id3"])

                    result = await self.steamid_ban(steamid_list=steamid_list, reason=reason, minutes=minutes)
                    await self.send_wrapped_text(result, message)

                    ban_logs_channel = await client.fetch_channel(config["ban_logs_id"])
                    if "[SM] Ban has been added." in result:
                        log_text = f"Admin {message.author.name} banned SteamID {str(steamid_list)} for {minutes} minutes with a reason: {reason}"
                        await self.send_wrapped_text(log_text, ban_logs_channel)
                case [".banip", *args]:
                    if not args[0:]:
                        await self.send_wrapped_text("Usage: .banip (minutes) \"69.69.69.69, 133.76.9.28 (ip's separated by spaces and commas.. in quotes!!)\" \"reason\"", message)
                        return

                    minutes = int(args[0])
                    ip = args[1]
                    regex_thing = re.findall(r"\"([^\"]*)\"", " ".join(args))
                    reason = regex_thing[1]
                    ip_list = regex_thing[0].split(", ")

                    result = await self.ip_ban(ip_list=ip_list, reason=reason, minutes=minutes)
                    await self.send_wrapped_text(result, message)

                    ban_logs_channel = await client.fetch_channel(config["ban_logs_id"])
                    if "Command was executed but no response was received." in result:
                        log_text = f"Admin {message.author.name} banned IP's {str(ip_list)} for {minutes} minutes with a reason: {reason}"
                        await self.send_wrapped_text(log_text, ban_logs_channel)
                case [".unban", *args]:
                    if not args[0:]:
                        await self.send_wrapped_text("Usage: .unban \"69.69.69.69, 133.76.9.28,\" \"reason\"", message)
                        return

                    regex_thing = re.findall(r"\"([^\"]*)\"", " ".join(args))
                    reason = regex_thing[1]
                    id_list = regex_thing[0].split(", ")
                    result = ""

                    remote_result = await t_recv()
                    for idd in id_list:
                        result += await self.server_rcon(rcon_ip, config["rcon_pass"], f"sm_unban {idd}")

                    await self.send_wrapped_text(result, message)

                    ban_logs_channel = await client.fetch_channel(config["ban_logs_id"])
                    if "filter removed for" in result:
                        log_text = f"Admin {message.author.name} unbanned SteamID's/IP's {str(id_list)} with a reason: {reason}"
                        await self.send_wrapped_text(log_text, ban_logs_channel)
                case [".donator", *args]:
                    if not args[0:]:
                        await self.send_wrapped_text("Usage: .donator (steamid of any type) | (tag) | (tag color in hex) | (player name)", message)
                        return
                    arguments = " ".join(args).split("|")
                    steamid, tag, color, name = arguments[0].strip(), arguments[1].strip(), arguments[2].strip(), arguments[3].strip()
                    formatted_steamid_list = await self.convert_to_every_steamid(steamid)
                    formatted_steamid = formatted_steamid_list["id"]
                    with open(config["admins_simple_path"], "a+") as f:
                        f.write(f'"{formatted_steamid}" "o" // {name}\n')
                    sleep(0.05)
                    result = f'Added: "{formatted_steamid}" "o" // {name}\n'
                    result += await self.server_rcon(rcon_ip, config["rcon_pass"], "sm_reloadadmins")
                    chatcolors_contents = ""
                    with open(config["ccc_path"], "r") as f:
                        for line in f.readlines():
                            if line != "}\n":
                                chatcolors_contents += line
                    with open(config["ccc_path"], "w") as f:
                        chatcolors_contents += f'    "{formatted_steamid}"\n'
                        chatcolors_contents += '    {\n'
                        chatcolors_contents += f'        "tag"               "{tag} "\n'
                        chatcolors_contents += f'        "tagcolor"          "{color}"\n'
                        chatcolors_contents += '    }\n'
                        chatcolors_contents += '}\n'
                        f.write(chatcolors_contents)
                    sleep(0.05)
                    result += "Written the tag stuff\n"
                    result += await self.server_rcobn(rcon_ip, config["rcon_pass"], "sm_reloadccc")
                    await self.send_wrapped_text(result, message)

            match message.content.split(" ")[1:]:
                case ["remove_duplicates", *args]:
                    if not args[0:]:
                        await self.send_wrapped_text("Usage: .remode_duplicates \"[U:1:211205495], [U:1:211205495], 19.19.19.19, 19.19.19.19\"", message)
                        return
                    regex_thing = re.findall(r"\"([^\"]*)\"", " ".join(args))
                    list_of_shit = regex_thing[0].split(", ")
                    list_of_shit = set(list_of_shit)
                    await self.send_wrapped_text(", ".join(list_of_shit), target=message)
                case ["guilds", *args]:
                    guilds_array = []
                    for guild in client.guilds:
                        guilds_array.append(guild.name + " (" + str(guild.id) + ")")
                    guilds_str = "\n".join(guilds_array)
                    await self.send_wrapped_text(f"Currently the bot is in these servers: {guilds_str}", message)
                case ["createinvite", *args]:
                    try:
                        guild = client.get_guild(int(args[0]))
                        invite = await guild.text_channels[1].create_invite()
                        await self.send_wrapped_text(f"Created an invite for {guild.name} ({guild.id}): {invite}", message)
                    except Exception as e:
                        await self.send_wrapped_text(f"Failed to leave the server. Probably already left or wasn't there in the first place. ({e})", message)
                case ["leaveserver", *args]:
                    if not args[0:]:
                        await self.send_wrapped_text("Usage: @bot leaveserver (Server ID, get it from the \"@bot guilds\" command)", message)
                        return
                    guild = client.get_guild(int(args[0]))
                    await guild.leave()
                    await self.send_wrapped_text(f"Left the server {guild.name} ({guild.id})", message)
                case ["detail", *args]:
                    cpu_frequency = psutil.cpu_freq()
                    cpu_usage = psutil.cpu_percent()
                    ram_usage = psutil.virtual_memory().percent
                    network_recieved = round(psutil.net_io_counters().bytes_recv / 1e+6)
                    network_sent = round(psutil.net_io_counters().bytes_sent / 1e+6)
                    network_recieved_packets = psutil.net_io_counters().packets_recv
                    server_state = await self.ping_server(rcon_ip, config["rcon_pass"])
                    embedVar = discord.Embed(title="Nicely done.", color=discord.Colour.blue())
                    embedVar.add_field(name="CPU Usage: ", value=f"{cpu_usage}% ({cpu_frequency.current/1000}ghz)", inline=False)
                    embedVar.add_field(name="RAM Usage: ", value=f"{ram_usage}%", inline=False)
                    embedVar.add_field(name="Network traffic received: ", value=f"{network_recieved}mb", inline=False)
                    embedVar.add_field(name="Network traffic received in packet amount: ", value=f"{network_recieved_packets}", inline=False)
                    embedVar.add_field(name="Network traffic sent: ", value=f"{network_sent}mb", inline=False)
                    embedVar.add_field(name="Network traffic received spike: ", value=f"{self.difference_mbps}mbps", inline=False)
                    embedVar.add_field(name="Packet count spike: ", value=f"{self.difference_pps}pps", inline=False)
                    embedVar.add_field(name="Server running (srcds_linux): ", value=server_state, inline=False)
                    await message.channel.send(embed=embedVar)
                case ["vpn", *args]:
                    if not args[0:]:
                        await self.send_wrapped_text("Usage: @bot vpn (IP)", message)
                        return

                    ips_info = await self.vpn_ip_check("".join(args[0]))
                    ips_info = ips_info.get("".join(args[0]))
                    embedVar = discord.Embed(title="IP Information", description="".join(args), color=discord.Colour.blue())
                    embedVar.add_field(name="VPN", value=str(ips_info.get("proxy")), inline=False)
                    embedVar.add_field(name="Location", value=ips_info.get("location"), inline=False)
                    embedVar.add_field(name="Risk", value=ips_info.get("risk"), inline=False)
                    await message.channel.send(embed=embedVar)
                case ["vpn_active", *args]:
                    status_output = await self.server_rcon(rcon_ip, config["rcon_pass"], "status")
                    status_output = self.format_status(status_output)

                    clean_entries = ""
                    vpn_entries = ""
                    fucking_string = ""

                    for player in status_output:
                        ips_info = await self.vpn_ip_check(player["ip"])
                        ips_info = ips_info.get(player["ip"])

                        add = f"\t- {player['username']} ({player['steamid']}, {player['ip']}): VPN: {ips_info.get('proxy')}. Geolocation: {ips_info.get('location')}. Risk: {ips_info.get('risk')}\n"
                        if ips_info.get("proxy") or int(ips_info.get("risk")) > 45:
                            vpn_entries += add
                        else:
                            clean_entries += add

                    fucking_string = f"Suspicious entries: \n{vpn_entries}\n"
                    fucking_string += f"Clean entries: \n{clean_entries}\n"
                    await self.send_wrapped_text(fucking_string, message)
                case ["vpn_mult", *args]:
                    if not args[0:]:
                        await self.send_wrapped_text("Usage: @bot vpn_mult (Multiple IP's, separated by commas)", message)
                        return
                    clean_list, vpn_list = await self.check_multiple_ips(" ".join(args[0:]))
                    embedVar = discord.Embed(title="IP Information", description=" ".join(args), color=discord.Colour.blue())
                    embedVar.add_field(name="VPN IP's", value=", ".join(vpn_list) + "...", inline=False)
                    embedVar.add_field(name="Clean IP's", value=", ".join(clean_list) + "...", inline=False)
                    await message.channel.send(embed=embedVar)
                case ["nativecapture", *args]:                            
                    await message.channel.send("Capture pending.")
                    await self.native_capture()
                    await self.send_file("detailed_capture.pcap", message)
                case ["restartserver", *args]:
                    if await self.restart_server():
                        await message.channel.send("Restarted the server.")
                case ["nfocapture", *args]:
                    embedVar = discord.Embed(title="NFO Traffic capture", description="Requesting the detailed capture...",
                                             color=discord.Colour.blue())
                    saved_message = await message.channel.send(embed=embedVar)
                    result = await self.nfo_capture(config["nfo_email"], config["nfo_password"], config["nfo_server_name"])
                    if result:
                        embedVar = discord.Embed(title="NFO Traffic capture", description="Success! Detailed traffic capture has been made.",
                                                 color=discord.Colour.green())
                        await saved_message.edit(embed=embedVar)
                    else:
                        embedVar = discord.Embed(title="NFO Traffic capture", description=f"Failure... ({result})", color=discord.Colour.red())
                        await saved_message.edit(embed=embedVar)
                case ["nuke", *args]:
                    new_channel = await message.channel.clone()
                    channel_position = message.channel.position
                    await message.channel.delete()
                    await new_channel.edit(position=channel_position, sync_permissions=True)
                    await new_channel.send("Nuked epic style!", delete_after=5)
                case ["update", *args]:
                    await self.update_bot(message)
                case ["shell", *args]:
                    if not (message.author.id in []):
                        await self.send_wrapped_text("You're not authorized to use this command.", message)
                        return
                    
                    if not args[0:]:
                        await self.send_wrapped_text("Usage: @bot shell (Any shell command)", message)
                        return
                    shell_output = None
                    try:
                        await self.send_wrapped_text("Executing...", message)
                        shell_output = await self.shell_exec(" ".join(args))
                    except Exception:
                        logging.error(f"shell: {traceback.format_exc()}")
                        await self.send_wrapped_text(traceback.format_exc(), message)
                    else:
                        await self.send_wrapped_text(shell_output, message)
                        await self.send_wrapped_text("Done!", message)
                case ["updategame", *args]:
                    try:
                        shell_return = None
                        await self.send_wrapped_text("Updating the game server... Will take some time, be patient!", message)
                        if usercfg == "hvhusa":
                            shell_return = await self.shell_exec("/home/steam/./steamcmd.sh +force_install_dir /home/steam/servers/tf2 +login anonymous +app_update 232250 validate +quit")
                        elif usercfg == "ns3072638":
                            shell_return = await self.shell_exec("/home/steam/steamcmd/./steamcmd.sh +force_install_dir /home/steam/servers/tf2 +login anonymous +app_update 232250 validate +quit")
                        await self.send_wrapped_text(shell_return, message, "Attempted to update the server. Restarting it now.")
                        if await self.restart_server():
                            await self.send_wrapped_text("Restarted the server.", message)
                    except Exception:
                        logging.error(f"updategame: {traceback.format_exc()}")
                        await self.send_wrapped_text(traceback.format_exc(), message)

    async def handle_user_commands(self, message):
        match message.content.split(" ")[1:]:
            case ["randomnickname", *args]:
                if not args[0:]:
                    await self.send_wrapped_text("Usage: @bot randomnickname (amount of nicknames, 10 max)", message)
                    return
                nicknames = await self.get_random_nicknames_from_steam(args[0])
                await self.send_wrapped_text(nicknames, message)
            case ["randomavatar", *args]:                        
                profileinfo = await self.get_random_avatar_from_steam()
                if isinstance(profileinfo, str):
                    embedVar = discord.Embed(color=discord.Colour.red(), title=f"Unexpected error: {profileinfo}")
                    await message.channel.send(embed=embedVar)
                    return
                embedVar = discord.Embed(color=discord.Colour.blue(), description=f"[Image Link]({profileinfo['avatarfull']})", title=f"`{profileinfo['personaname']}`")
                embedVar.set_image(url=profileinfo['avatarfull'])
                await message.channel.send(embed=embedVar)
            case ["mcinfo", *args]:
                if not args[0:]:
                    await self.send_wrapped_text("Usage: @bot mcinfo (IP:PORT)", message)
                    return
                try:
                    address, port = args[0].split(":")
                    embedVar = await self.query_the_server_minecraft(str(address), int(port), False)
                    await message.channel.send(embed=embedVar)
                except Exception as e:
                    embedVar = discord.Embed(title=f"Error. {e}", color=discord.Colour.red())
                    await message.channel.send(embed=embedVar)
            case ["sid", *args]:
                if not args[0:]:
                    await self.send_wrapped_text("Usage: @bot sid (SteamID of any type)", message)
                    return
                args = "".join(args)
                args = args.replace("https://steamcommunity.com/id/", "").replace("https://steamcommunity.com/profiles/", "").replace("/", "")
                result = await self.convert_to_every_steamid(args)
                try:
                    if result:
                        prof_info = await self.async_get_common_steam_acc_info(result["id64"])
                        prof_info = prof_info['response']['players'][0]
                        embedVar = discord.Embed(title=prof_info['personaname'], color=discord.Colour.blue())
                        embedVar.set_thumbnail(url=prof_info['avatarfull'])
                        embedVar.add_field(name="ID's", value=f"{result['id']}, {result['id3']}, {result['id64']}", inline=False)
                        embedVar.add_field(name="Permanent URL", value=f"https://steamcommunity.com/profiles/{result['id64']}", inline=False)
                        embedVar.add_field(name="Custom URL", value=prof_info['profileurl'], inline=False)
                        embedVar.add_field(name="Analysis", value=f"\
                            https://steamid.uk/profile/{result['id64']}\n\
                            https://steamid.io/lookup/{result['id64']}\n\
                            http://vacbanned.com/engine/check?qsearch={result['id64']}", inline=False)
                        await message.channel.send(embed=embedVar)
                    else:
                        embedVar = discord.Embed(title="Invalid SteamID", color=discord.Colour.red())
                        await message.channel.send(embed=embedVar)
                except Exception:
                    embedVar = discord.Embed(title="Invalid SteamID", color=discord.Colour.red())
                    logging.error(f"sid: {traceback.format_exc()}")
                    await message.channel.send(embed=embedVar)
                    await self.send_wrapped_text(traceback.format_exc(), self.grabbed_log_channel)
            case ["usainfo", *args]:
                s_info = await self.query_the_server(config["server_ips"][0], add_status=True)
                await message.channel.send(embed=s_info)
            case ["oldeuinfo", *args]:
                s_info = await self.query_the_server(config["server_ips"][1], add_status=True)
                await message.channel.send(embed=s_info)
            case ["custominfo", *args]:
                if not args[0:]:
                    await self.send_wrapped_text("Usage: @bot custominfo IP:PORT", message)
                    return
                s_info = await self.query_the_server(args[0])
                await message.channel.send(embed=s_info)
            case ["capybara", *args]:
                result = self.random_line("links/capy.txt")
                await self.send_embedded_image(result, message)
            case ["cat", *args]:
                result = self.random_line("links/cat.txt")
                await self.send_embedded_image(result, message)
            case ["dog", *args]:
                result = self.random_line("links/dog.txt")
                await self.send_embedded_image(result, message)
            case ["frog", *args]:
                result = self.random_line("links/frog.txt")
                await self.send_embedded_image(result, message)
            case ["videosearch", *args]:
                if not args[0:]:
                    await self.send_wrapped_text("Usage: @bot videosearch (amount) (query)", message)
                    return
                await self.video_search_on_command(message, args[1:], args[0], random=False)
            case ["randomvideosearch", *args]:
                if not args[0:]:
                    await self.send_wrapped_text("Usage: @bot randomvideosearch (query)", message)
                    return
                await self.video_search_on_command(message, args[0:], 0, random=True)
            case ["discordinfo", *args]:
                if not args[0:]:
                    await self.send_wrapped_text("Usage: @bot discordinfo (Discord ID)", message)
                    return
                user = await client.fetch_user(int(args[0]))
                embedVar = discord.Embed(title=f"{user} ({user.id})", color=discord.Colour.blue())
                embedVar.set_thumbnail(url=user.avatar_url)
                embedVar.add_field(name="Date of creation", value=user.created_at, inline=False)
                embedVar.add_field(name="System/Admin", value=user.system, inline=False)
                await message.channel.send(embed=embedVar)

    async def handle_rcon_channels(self, message):
        if message.channel.id == config["rcon_channel"] and not message.content.startswith("/"):
            async with message.channel.typing():
                try:
                    rcon_resp = await self.server_rcon(rcon_ip, config["rcon_pass"], message.content)
                    if rcon_resp:
                        await self.send_wrapped_text(rcon_resp, message)
                    else:
                        await message.channel.send("**Command was executed but there was no response.**")
                except Exception:
                    logging.error(traceback.format_exc())
                    await self.grabbed_log_channel.send(f"`[RCON-FAIL] Unexpected exception:`")
                    await self.send_wrapped_text(traceback.format_exc(), self.grabbed_log_channel)

    async def on_message(self, message):
        try:
            if not self.fully_ready:
                return

            if message.author.id == self.user.id:
                return

            if message.author.bot:
                return

            if (self.user.mentioned_in(message) and "@everyone" not in message.content) or (message.content and message.content.startswith("t.")):
                async with message.channel.typing():
                    await self.handle_admin_commands(message)
                    await self.handle_user_commands(message)

            await self.handle_rcon_channels(message)
        except Exception:
            logging.error(f"on message: {traceback.format_exc()}")
            await self.grabbed_log_channel.send(f"`[FAIL] on_message`")
            await self.send_wrapped_text(traceback.format_exc(), self.grabbed_log_channel)

if __name__ == "__main__":
    logging.info("[LOAD] Loading the config.")
    usercfg = socket.gethostname()
    logging.info(f"[LOAD] {usercfg}.json will be used.")
    with open(f"../cfg/{usercfg}.json") as config_file:
        config = json.load(config_file)

        debug_mode = False if config["debug_mode"].lower() == "false" else True
        start_server_automatically = False if config["start_server_automatically"].lower() == "false" else True
        ip_and_port_array = str(config["rcon_ip"]).split(":")
        rcon_ip = (str(ip_and_port_array[0]), int(ip_and_port_array[1]))

        valve.rcon.RCONMessage.ENCODING = "utf-8"

        intents = discord.Intents.default()
        intents.message_content = True
        client = MyClient(intents=intents)

        client.run(config["bot_token"])
