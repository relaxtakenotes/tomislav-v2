def create_dir(dirr):
    if not os.path.exists(dirr):
        os.mkdir(dirr)

def file_exists(dirr):
    if os.path.isfile(dirr):
        return True
    return False

def get_config(dirr):
    cfg = {}
    if file_exists(dirr):
        with open(f"{dirr}", "r") as f:
            cfg = json.load(f)
    return cfg

async def get_guild_option(guild_id, option_name):
    dirr = f"internal/{guild_id}.json"
    guild_config = get_config(dirr)
    return guild_config.get(option_name, [])

async def set_guild_option(guild_id, option_name, option_value):
    dirr = f"internal/{guild_id}.json"
    guild_config = get_config(dirr)
    guild_config[option_name] = option_value
    logging.warning(str(guild_config))
    with open(f"{dirr}", "w+") as f:
        json.dump(guild_config, f)
    await update_guild_configs()

async def remove_guild_option(guild_id, option_name):
    dirr = f"internal/{guild_id}.json"
    guild_config = get_config(dirr)
    if not guild_config.get(option_name):
        return
    del guild_config[option_name]
    with open(f"{dirr}", "w+") as f:
        json.dump(guild_config, f)
    await update_guild_configs()

async def append_to_guild_option(guild_id, option_name, option_value):
    option = await get_guild_option(guild_id, option_name)
    logging.warning(str(option))
    if option_value in option:
        logging.warning(str(f"{option_value} in {option}"))
        return
    option.append(option_value)
    await set_guild_option(guild_id, option_name, option)

async def remove_from_guild_option(guild_id, option_name, option_value):
    option = await get_guild_option(guild_id, option_name)
    if option_value not in option:
        return
    option.remove(option_value)
    await set_guild_option(guild_id, option_name, option)

async def update_guild_configs():
    client.notif_channels = []
    client.src_query_messages = []
    client.mc_query_messages = []
    client.rcon_channels = []
    client.whitelisted_clients = []
    client.ban_logs_channels = []

    internal_configs = [f for f in os.listdir("internal/") if os.path.isfile(os.path.join("internal/", f))]
    for cfg_name in internal_configs:
        guild_id = int(cfg_name.replace(".json", ""))
        cfg = {}

        with open("internal/" + cfg_name) as f:
            cfg = json.load(f)

        if cfg.get("notif_channel"):
            for channel in cfg.get("notif_channel"):
                try:
                    fetched_channel = await client.fetch_channel(int(channel))
                    client.notif_channels.append(fetched_channel)
                except (discord.errors.NotFound, discord.errors.Forbidden):
                    pass

        if cfg.get("ban_logs_channels"):
            for channel in cfg.get("ban_logs_channels"):
                try:
                    fetched_channel = await client.fetch_channel(int(channel))
                    client.ban_logs_channels.append(fetched_channel)
                except (discord.errors.NotFound, discord.errors.Forbidden):
                    pass

        if cfg.get("whitelisted_clients"):
            client.whitelisted_clients = cfg.get("whitelisted_clients")

        if cfg.get("src_query_message"):
            for server in cfg.get("src_query_message"):
                chan_id, msg_id, address, time_set = server.split("|")

                try:
                    fetched_channel = await client.fetch_channel(int(chan_id))
                    fetched_message = await fetched_channel.fetch_message(int(msg_id))
                except (discord.errors.NotFound, discord.errors.Forbidden):
                    await remove_from_guild_option(guild_id, "src_query_message", server)
                    continue

                client.src_query_messages.append({"message": fetched_message, "address": address, "guild_id": guild_id, "time_set": time_set})

        if cfg.get("mc_query_message"):
            for server in cfg.get("mc_query_message"):
                chan_id, msg_id, address, time_set = server.split("|")

                try:
                    fetched_channel = await client.fetch_channel(int(chan_id))
                    fetched_message = await fetched_channel.fetch_message(int(msg_id))
                except (discord.errors.NotFound, discord.errors.Forbidden):
                    await remove_from_guild_option(guild_id, "mc_query_message", server)
                    continue

                client.mc_query_messages.append({"message": fetched_message, "address": address, "guild_id": guild_id, "time_set": time_set})

        if cfg.get("src_rcon_channel"):
            for server in cfg.get("src_rcon_channel"):
                chan_id, address, rcon_pass, time_set = server.split("|")

                try:
                    fetched_channel = await client.fetch_channel(int(chan_id))
                except (discord.errors.NotFound, discord.errors.Forbidden):
                    logging.warning(f"we removed {guild_id} src_rcon_channel {server}")
                    await remove_from_guild_option(guild_id, "src_rcon_channel", server)
                    continue

                client.rcon_channels.append({"channel": fetched_channel, "address": address, "rcon_pass": rcon_pass, "guild_id": guild_id, "time_set": time_set})

    # deduplicate elements. sometimes corruption can appear or shit can get duplicated and i want to get rid of that.
    # preferably fix this properly and not do this jank
    client.notif_channels = list(set(client.notif_channels))
    client.whitelisted_clients = list(set(client.whitelisted_clients))
    client.ban_logs_channels = list(set(client.ban_logs_channels))

    client.src_query_messages = [dict(tupleized) for tupleized in set(tuple(item.items()) for item in client.src_query_messages)]
    client.rcon_channels = [dict(tupleized) for tupleized in set(tuple(item.items()) for item in client.rcon_channels)]