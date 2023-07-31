def register_cmd(func, func_name, typee, description="No description."):
    if typee == "admin":
        client.admin_commands[func_name] = [func, description]
    elif typee == "user":
        client.user_commands[func_name] = [func, description]

async def handle_admin_commands(message):
    if not is_allowed(message):
        return

    _split = message.content.split()[1:]
    args = _split[1:]
    cmd = _split[0]

    if client.admin_commands.get(cmd):
        async with message.channel.typing():
            await client.admin_commands[cmd][0](message, args)

async def handle_user_commands(message):
    _split =  message.content.split()[1:]
    args = _split[1:]
    cmd = _split[0]

    if client.user_commands.get(cmd):
        async with message.channel.typing():
            await client.user_commands[cmd][0](message, args)

async def cmd_status(message, args):
    output = "Server Status\n-------------"
    responses = await client.slave_servers.get_raw_status()
    for key, response in responses.items():
        output += f"\n{key}:\n\tTraffic Spike (mbps): {response.get('spike_mbps')}\n\t"
        output += f"Traffic Spike (pps): {response.get('spike_pps')}\n\t"
        output += f"Cpu Usage: {response.get('cpu_usage')}%\n"
    for block in textwrap(output):
        await message.reply(block)

async def cmd_toggle_notifs(message, args):
    if message.channel.id not in await get_guild_option(guild_id=message.guild.id, option_name="notif_channel"):
        await append_to_guild_option(guild_id=message.guild.id, option_name="notif_channel", option_value=message.channel.id)
        await message.reply(f"Important notifications will be sent here.")
    else:
        await remove_from_guild_option(guild_id=message.guild.id, option_name="notif_channel", option_value=message.channel.id)
        await message.reply(f"No notifications will be sent here anymore.")

async def cmd_toggle_ban_logs(message, args):
    if message.channel.id not in await get_guild_option(guild_id=message.guild.id, option_name="ban_logs_channels"):
        await append_to_guild_option(guild_id=message.guild.id, option_name="ban_logs_channels", option_value=message.channel.id)
        await message.reply(f"Ban events will now be logged in this channel!")
    else:
        await remove_from_guild_option(guild_id=message.guild.id, option_name="ban_logs_channels", option_value=message.channel.id)
        await message.reply(f"Ban events **WON'T** be logged in this channel now!")

async def cmd_toggle_whitelist(message, args):
    target_id = int(args[0])
    if target_id not in await get_guild_option(guild_id=message.guild.id, option_name="whitelisted_clients"):
        await append_to_guild_option(guild_id=message.guild.id, option_name="whitelisted_clients", option_value=target_id)
        await message.reply(f"<@{target_id}> now can use admin commands regardless of their roles.")
    else:
        await remove_from_guild_option(guild_id=message.guild.id, option_name="whitelisted_clients", option_value=target_id)
        await message.reply(f"<@{target_id}> now can't use admin commands. (Can be bypassed by administrator permissions!)")

async def cmd_create_mc_query(message, args):
    s_info = await server_utils.get_mc_query_embed(address=args[0], add_time=True)
    message_sent = await message.channel.send(embed=s_info)
    await append_to_guild_option(guild_id=message.guild.id, option_name="mc_query_message", option_value=f"{message.channel.id}|{message_sent.id}|{args[0]}|{round(time())}")

async def cmd_create_query(message, args):
    s_info = await server_utils.get_query_embed(address=args[0], add_time=True)
    message_sent = await message.channel.send(embed=s_info)
    await append_to_guild_option(guild_id=message.guild.id, option_name="src_query_message", option_value=f"{message.channel.id}|{message_sent.id}|{args[0]}|{round(time())}")

async def cmd_toggle_rcon_relay(message, args):
    address = str(args[0])
    password = str(args[1])
    if address == "del" and password == "del":
        for rcon_instance in client.rcon_channels:
            if message.guild.id == rcon_instance.get("channel").id:
                option = await get_guild_option(rcon_instance.get("guild_id"), "src_rcon_channel")
                for server in option:
                    if str(rcon_instance.get("channel").id) in server and rcon_instance.get("time_set") in server:
                        await remove_from_guild_option(rcon_instance.get("guild_id"), "src_rcon_channel", server)
                        continue
                await message.reply(f"Removed this channel from being an RCON relay.")
        return

    await append_to_guild_option(guild_id=message.guild.id, option_name="src_rcon_channel", option_value=f"{message.channel.id}|{address}|{password}|{round(time())}")
    await message.reply(f"Made this channel as an RCON relay for address {address}")

async def cmd_vpn(message, args):
    addresses = " ".join(args)
    result = await ip_utils.check_multiple_ips_str(addresses.split(", "))
    for msg_block in textwrap(result):
        await message.reply(msg_block)

async def cmd_restartgames(message, args):
    result = await client.slave_servers.restart_game_servers()
    output = ""

    for server_name, response in result.items():
        output += f"{server_name}:\n\t"
        for cmd_name, cmd_output in response.items():
            output += f"\"{cmd_name}\":\n\t\t{cmd_output}\n\n"

    for block in textwrap(str(output)):
        await message.reply(block)

async def cmd_updategames(message, args):
    result = await client.slave_servers.update_game_servers()
    output = ""

    for server_name, response in result.items():
        output += f"{server_name}:\n\t"
        for cmd_name, cmd_output in response.items():
            output += f"\"{cmd_name}\":\n\t\t{cmd_output}\n\n"

    for block in textwrap(str(output)):
        await message.reply(block)

async def cmd_logs(message, args):
    if len(" ".join(args)) < 2:
        return
        
    query = re.findall('"([^"]*)"', " ".join(args))[0].split(", ")
    recursive = False
    ignorevpn = False
    if " --recursivevpn" in " ".join(args):
        recursive = True
    if " --ignorevpn" in " ".join(args):
        ignorevpn = True

    #print(" ".join(args), query, recursive, ignorevpn)

    output = None
    if len(query) <= 1:
        output = await client.slave_servers.send_logs_request(" ".join(query), recursive=recursive, ignore_vpn=ignorevpn)
    else:
        output = await client.slave_servers.send_logs_request(query, recursive=recursive, ignore_vpn=ignorevpn)

    for msg_block in textwrap(format_log_output(output)):
        await message.reply(msg_block)

async def cmd_ban(message, args):
    query = re.findall('"([^"]*)"', " ".join(args))
    minutes = int(query[0])
    ban_list = query[1].split(", ")
    reason = query[2]

    #print(query, minutes, ban_list, reason)

    #await message.channel.send(f"{cmd_args.ban_list=}\n{cmd_args.reason=}\n{cmd_args.minutes}\n{spaced_args=}\n{shlex_args=}")

    sid_list = []
    ip_list = []

    for item in ban_list:
        if re.match(r'[0-9]+(?:\.[0-9]+){3}', item):
            ip_list.append(item)
        if re.match(r'(?:https?\:\/\/steamcommunity.com\/id\/[A-Za-z_0-9]+)|(?:\/id\/[A-Za-z_0-9]+)|(?:https?\:\/\/steamcommunity.com\/profiles\/[0-9]+)|(?:STEAM_[10]:[10]:[0-9]+)|(?:\[U:[10]:[0-9]+\])|(?:[^\/][0-9]{8,})', item):
            steamid_conv = await steam_utils.convert_to_every_steamid(item)
            sid_list.append(steamid_conv["id3"])

    result_id = {}
    result_ip = {}
    if sid_list:
        result_id = await server_utils.steamid_ban(steamid_list=sid_list, reason=reason, minutes=minutes, servers=config["rcon_servers"])
    if ip_list:
        result_ip = await server_utils.ip_ban(ip_list=ip_list, reason=reason, minutes=minutes, servers=config["rcon_servers"])

    reply_content = f"Banned {', '.join(ban_list)}!\n"
    for server_id, output_id in result_id.items():
        reply_content += f"\t(SID) {server_id}: {output_id}\n"
    for server_ip, output_ip in result_ip.items():
        reply_content += f"\t(IP) {server_ip}: {output_ip}\n"

    wrapped_reply = textwrap(reply_content)
    for block in wrapped_reply:
        await message.reply(block)

    await send_ban_manage_event(f"{message.author} ({message.author.id})", ", ".join(ban_list), reason, minutes, "banned")

async def cmd_unban(message, args):
    if not args[0:]:
        await message.reply("Usage: .unban \"69.69.69.69, 133.76.9.28, [U:0:73721]\" \"reason\"")
        return

    query = re.findall('"([^"]*)"', " ".join(args))
    unban_list = query[0].split(", ")
    reason = query[1]

    #print(query, unban_list, reason)

    result = await server_utils.unban(id_list=unban_list, reason=reason, servers=config["rcon_servers"])

    reply_content = f"Unbanned {', '.join(unban_list)}!\n"
    for server, output in result.items():
        reply_content += f"\t{server}: {output}\n"
    wrapped_reply = textwrap(reply_content)
    for block in wrapped_reply:
        await message.reply(block)

    await send_ban_manage_event(f"{message.author} ({message.author.id})", ", ".join(unban_list), reason, "infinite", "unbanned")

async def cmd_sid(message, args):
    steamid_list = []
    if ", " in " ".join(args):
        steamid_list = " ".join(args).split(", ")
    else:
        steamid_list.append(args[0])

    output = ""
    for steamid in steamid_list:
        steamid = steamid.replace("https://steamcommunity.com/id/", "").replace("https://steamcommunity.com/profiles/", "").replace("/", "")
        result = await steam_utils.convert_to_every_steamid(steamid)
        try:
            prof_info = await steam_utils.async_get_common_steam_acc_info(result["id64"]) # todo: you can optimize this
            prof_info = prof_info['response']['players'][0]

            output += f"{prof_info['personaname']}:\n"
            output += f"\tAvatar URL: {prof_info['avatarfull']}\n"
            output += f"\tID's: {result['id']}, {result['id3']}, {result['id64']}\n"
            output += f"\tPermanent URL: https://steamcommunity.com/profiles/{result['id64']}\n"
            output += f"\tCustom URL: {prof_info['profileurl']}\n"
            output += f"\tAnalysis: \n"
            output += f"\t\thttps://steamid.uk/profile/{result['id64']}\n"
            output += f"\t\thttps://steamid.io/lookup/{result['id64']}\n"
            output += f"\t\thttps://vacbanned.com/engine/check?qsearch={result['id64']}\n"
            output += f"\t\thttps://steamrep.com/profiles/{result['id64']}\n"
            output += f"\t\thttps://rep.tf/{result['id64']}\n"
        except Exception:
            embedVar = discord.Embed(title="Invalid SteamID", color=discord.Colour.red())
            await message.channel.send(embed=embedVar)

    wrapped_reply = textwrap(output)
    for msg_block in wrapped_reply:
        await message.reply(msg_block)

async def cmd_custominfo(message, args):
    s_info = await server_utils.get_query_embed(address=args[0])
    await message.channel.send(embed=s_info)

async def cmd_mc_custominfo(message, args):
    s_info = await server_utils.get_mc_query_embed(address=args[0])
    await message.channel.send(embed=s_info)

async def cmd_randomnickname(message, args):
    if not args[0:]:
        await message.reply("Usage: @bot randomnickname (amount of nicknames, 10 max)")
        return
    nicknames = await steam_utils.get_random_nicknames_from_steam(args[0])
    await message.reply(nicknames)

async def cmd_randomavatar(message, args):
    profileinfo = await steam_utils.get_random_avatar_from_steam()
    if isinstance(profileinfo, str):
        embedVar = discord.Embed(color=discord.Colour.red(), title=f"Unexpected error: {profileinfo}")
        await message.reply(embed=embedVar)
        return
    embedVar = discord.Embed(color=discord.Colour.blue(), description=f"[Image Link]({profileinfo['avatarfull']})", title=f"`{profileinfo['personaname']}`")
    embedVar.set_image(url=profileinfo['avatarfull'])
    await message.reply(embed=embedVar)

async def cmd_help(message, args):
    response = "Ping the bot before using these commands.\n\nAdmin commands:\n"
    for name, data in client.admin_commands.items():
        response += f"\t{name} - {data[1]}\n"
    response += "\nUser commands:\n"
    for name, data in client.user_commands.items():
        response += f"\t{name} - {data[1]}\n"
    for block in textwrap(response):
        await message.channel.send(block)

register_cmd(cmd_status, "status", "admin", "Prints out the status of slave servers.") 
register_cmd(cmd_toggle_notifs, "toggle_notifs", "admin", "Toggles system notifications in a given channel.") 
register_cmd(cmd_toggle_ban_logs, "toggle_ban_logs", "admin", "Toggles ban logs in a given channel.") 
register_cmd(cmd_toggle_whitelist, "toggle_whitelist", "admin", "Toggles admin command access on a specified user, given a user id.") 
register_cmd(cmd_create_mc_query, "create_mc_query", "admin", "Creates an updating query embed for a minecraft server, given an ip and a port.") 
register_cmd(cmd_create_query, "create_query", "admin", "Creates an updating query embed for a source engine server, given an ip and a port.") 
register_cmd(cmd_toggle_rcon_relay, "toggle_rcon_relay", "admin", "Creates an rcon relay in a given channel. (@tomislav toggle_rcon_relay address:port password)") 
register_cmd(cmd_vpn, "vpn", "admin", "Given however many IP's will print out their geolocation, risk percentage and a bool if it's an IP from a VPN.") 
register_cmd(cmd_restartgames, "restartgames", "admin", "Restarts all slave servers.") 
register_cmd(cmd_updategames, "updategames", "admin", "Updates all slave servers.") 
#register_cmd(cmd_logs, "logs", "admin", "Finds logged information from a given steamid, ip or name list. Currently broken.") 
register_cmd(cmd_ban, "ban", "admin", "Ban a player from all slave servers given a steamid or an ip (can be a list)") 
register_cmd(cmd_unban, "unban", "admin", "Unban a player from all slave servers given a steamid or an ip (can be a list)")

register_cmd(cmd_sid, "sid", "user", "Lists out helpful information about a steamid.") 
register_cmd(cmd_custominfo, "custominfo", "user", "Returns information about a source engine server given an ip and a port") 
register_cmd(cmd_mc_custominfo, "mc_custominfo", "user", "Returns information about a minecraft server given an ip and a port") 
register_cmd(cmd_randomnickname, "randomnickname", "user", "Returns random nicknames acquired from steam. Maximum 10 at a time.") 
register_cmd(cmd_randomavatar, "randomavatar", "user", "Returns a random profile picture acquired from steam.")
register_cmd(cmd_help, "help", "user", "Lets you see commands that you can use with this bot.")