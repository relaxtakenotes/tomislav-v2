async def send_notifications(text, file=None):
    for channel in client.notif_channels:
        if file:
            await channel.send(text, file=discord.File(file))
        else:
            await channel.send(text)

async def send_ban_manage_event(initiator, banned_people, reason, minutes, event_type):
    if os.path.isdir("/var/www/private/"):
        ban_list = []
        if os.path.isfile("/var/www/private/ban_list.json"):
            with open("/var/www/private/ban_list.json", "r") as f:
                ban_list = json.load(f)

        with open("/var/www/private/ban_list.json", "w+") as f:
            if event_type == "banned":
                for identificator in banned_people.split(", "):
                    ban_list.append({"id": identificator, "reason": reason, "minutes": minutes})
            elif event_type == "unbanned":
                for i, user in enumerate(ban_list):
                    for identificator in banned_people.split(", "):
                        if user["id"] == identificator:
                            ban_list.remove(user)
            f.write(json.dumps(ban_list))

    for channel in client.ban_logs_channels:
        wrapped_text = textwrap(f"Administrator {initiator} {event_type} \"{banned_people}\" for {minutes} minutes with a reason \"{reason}\"")
        for block in wrapped_text:
            await channel.send(block)

def is_allowed(message):
    try:
        if (message.author.guild_permissions.administrator or message.author.id in client.whitelisted_clients or message.author.id in config["admins"]) and message.guild.id in config["whitelisted_guilds"]:
            return True
    except Exception as e: # not much errors can happen here and they wouldn't be serious anyway
        print(e)
        pass
    return False