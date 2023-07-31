# tomislav-v2
 Discord bot for source engine server management

This project has been something that I've worked on for quite a few years now. I've improved a lot in different aspects since its start. It's time this finally goes into the wild. V1 and V2 are both included.

To be clear, this repository is not meant for people that don't already know programming at least a bit, as some stuff might need changing for your specific needs.

What does this do, exactly?:<br>
 This provides a bunch of tools that you can use over discord to control your source engine servers. It's been actively used by me and my friends when we all hosted multi-region TF2 game servers. With this, you can ban/unban, send stuff over rcon, create embeds that have up-to-date information about your server and a bunch of other things that I might have forgotten. To be sure, check out the source code.

How to setup this bot:
 - Check every .sh script, set the paths within them to be correct for your own usage.
 - Check out every config file. They are not commented, but if you keep the main and the slave configs both in mind, you'll be able to figure out what goes where pretty easily. You don't have to fill out the slave servers, this bot is operational without them. (one thing to note though is that you need an encryption key for fernet. google how to generate one if you don't know how to)
 - Install the requirements from requirements.txt
 - Make a service to execute the needed run scripts on system startup.
 - Start the bot and pray to god you configured it right.

Notes:
 - This uses symmetric encryption to talk between the main and the slave servers. Depending on your python server, you can enabled communications under HTTPS, which will make it way more secure.
 - User information query is cut out of this version due to being broken and generally not having any use for me. It's not hard to recreate it though. Make sure your server outputs logs and then go off from that.

Credits:
 - serverstf (https://github.com/serverstf/python-valve) - for the valve modules that are directly included in this project due to the need of modifiying it.
 - AlexHodgson (https://github.com/AlexHodgson/steamid-converter) - for the steamid conversion modules that are also directly included in this project due to the need of modifying it.
 - Naleksuh - nfoservers related networking stuff. I didn't forget you yet, buddy.