# custom
import discord
from discord.ext import tasks
import httpx
from cryptography.fernet import Fernet

# local/default
import json
import os
import logging
from random import choice
from traceback import format_exc as traceback
from socket import gethostname as get_host_name
from functools import wraps, partial
from utils import src_interface, u_ip, textwrap, servers, steam, read_traffic_dump, async_wrap, format_log_output
from time import time
import re
import asyncio
import argparse
import shlex
import sys

def include(filename):
    with open(filename, 'r') as f:
        exec(f.read(), sys._getframe(1).f_globals, sys._getframe(1).f_locals)

logging.basicConfig(level=logging.INFO, filename=f"logs/tomislav_{round(time())}.log", filemode="w")

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)
client.admin_commands = {}
client.user_commands = {}

config_file = open(f"configs/{get_host_name()}.json")
config = json.load(config_file)
config_file.close()

steam_utils = steam(config["steamapi_key"])
ip_utils = u_ip(config["proxycheck_key"])
server_utils = src_interface(ip_utils)
fernet = Fernet(config["encryption_key"])

include("config_system.py")
include("commands.py")
include("misc.py")

@tasks.loop(seconds=5)
async def check_slave_servers():
    s_responses = await client.slave_servers.get_status()
    for key, response in s_responses.items():
        if response.get("ddos"):
            file = await read_traffic_dump(response.get("traffic_dump"))
            await send_notifications(f"{key}: DDOS Activity detected!", file)       
        if response.get("high_cpu_usage"):
            file = await read_traffic_dump(response.get("traffic_dump"))
            await send_notifications(f"{key}: Suspicious CPU usage detected!", file)

@tasks.loop(seconds=60)
async def funny_messages_routine():
    with open("configs/status_messages.txt") as f:
        content = f.readlines()
        await client.change_presence(activity=discord.Game(name=choice(content)))

@tasks.loop(seconds=32)
async def update_src_query_messages():
    for item in client.src_query_messages:
        s_info = await server_utils.get_query_embed(address=item.get("address"), add_time=True)
        try:
            await item.get("message").edit(embed=s_info)
        except (discord.errors.NotFound, discord.errors.Forbidden):
            option = await get_guild_option(item.get("guild_id"), "src_query_message")
            for server in option:
                if item.get("address") in server and item.get("time_set") in server:
                    await remove_from_guild_option(item.get("guild_id"), "src_query_message", server)
                    continue

@tasks.loop(seconds=32)
async def update_mc_query_messages():
    for item in client.mc_query_messages:
        s_info = await server_utils.get_mc_query_embed(address=item.get("address"), add_time=True)
        try:
            await item.get("message").edit(embed=s_info)
        except (discord.errors.NotFound, discord.errors.Forbidden):
            option = await get_guild_option(item.get("guild_id"), "mc_query_message")
            for server in option:
                if item.get("address") in server and item.get("time_set") in server:
                    await remove_from_guild_option(item.get("guild_id"), "mc_query_message", server)
                    continue

@client.event
async def on_ready():
    client.slave_servers = servers(config["servers"], fernet)

    await update_guild_configs()

    update_src_query_messages.start()
    update_mc_query_messages.start()
    funny_messages_routine.start()
    check_slave_servers.start()

    logging.info(f"Logged in as {client.user} (ID: {client.user.id})")         

@client.event
async def on_message(message):
    if message.author == client.user:
        return

    if client.user.mentioned_in(message) and "@everyone" not in message.content:
        await handle_admin_commands(message)
        await handle_user_commands(message)
    else:
        for rcon_instance in client.rcon_channels:
            if message.channel.id == rcon_instance.get("channel").id and message.guild.id == rcon_instance.get("guild_id"):
                output = await server_utils.rcon(address=rcon_instance.get("address"), rcon_pass=rcon_instance.get("rcon_pass"), command=message.content)
                wrapped_output = textwrap(output)
                for msg_block in wrapped_output:
                    await message.reply(msg_block)

@client.event
async def on_error(event, *args, **kwargs):
    error_formatted = f"Event: {event}\nArgs: {args}\nKwargs: {kwargs}\nTraceback: {traceback()}"
    print(error_formatted)
    logging.error(error_formatted)

if __name__ == "__main__":
	client.run(config["token"])