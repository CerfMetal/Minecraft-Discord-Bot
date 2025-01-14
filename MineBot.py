# MineBot V2.0
# Made by Tom Croux
# Date : Sun 11 Jul 2021
# License : GNU General Public License v3.0 (see LICENSE)

# Initalise imports
import os
import discord
import subprocess
import asyncio
from mcstatus import MinecraftServer
import time
from spontit import SpontitResource
import yaml
import threading
import queue

# -------------------------------------------------------------------------------------------------- #
# ----------------------------------------- Variables ---------------------------------------------- #
# -------------------------------------------------------------------------------------------------- #
BotName = ""

# Load the configuration from the config.yaml file"
config = []
try :
    with open(r'config.yaml') as file:
        # The FullLoader parameter handles the conversion from YAML
        # scalar values to Python the dictionary format
        documents = yaml.load(file, Loader=yaml.FullLoader)
        for item, doc in documents.items():
            config.append(doc)
except :
    print("ERROR : Can't find the config.yaml file")
    print("Downloading the config file...")
    try :
        os.system("wget https://github.com/CerfMetal/MineBot/raw/main/config.yaml")
        print("Config file downloaded successfully")
    except :
        print("ERROR : Download failed")
    exit()

# Server Settings
ScreenPrefix, StartMinecraftServer, StartTunnel, LocalIP, Whitelist, MinecraftChat = config[0], config[1], config[2], config[3], config[4], config[5]
# Discord Settings
DiscordToken, Prefix, ServerIP, EventChannelId, Administrator = config[6], config[7].lower(), config[8], config[9], config[10]
# Additional Settings
SpontitToken, SpontitUserName, ChannelName = config[11], config[12], config[13]

# Discord setup
try :
    client = discord.Client()
except :
    print("ERROR : Discord Token error")
    exit()

# Spontit setup
try :
    resource = SpontitResource(SpontitUserName, SpontitToken)
except :
    print("Error : Failed to initalise the Spontit Ressource (check username and token)")

# Emoji
Success = "👍"
Error = "🚫"
Sent = "✅"
Gaming = "🎮"
Sad = "😔"
Nice = "🤏"

# -------------------------------------------------------------------------------------------------- #
# ------------------------------------------ Help -------------------------------------------------- #
# -------------------------------------------------------------------------------------------------- #
# Help on commands
commandsAdmin = []
commands = []

if ScreenPrefix == None :
    print('Set ScreenPrefix to "minecraft"')
    ScreenPrefix = "minecraft"

if StartMinecraftServer != None :
    commandsAdmin.append("start - Start the minecraft server")
    commandsAdmin.append("stop - Stop the minecraft server")
    commandsAdmin.append("send - Send a command to the minecraft server")
    commandsAdmin.append("say - Broadcast a message to the minecraft server")

commandsAdmin.append("term - Send a command to the server")

if ServerIP != None :
    commandsAdmin.append("ip - Get the ip of the minecraft server")
    commands.append("ip - Get the ip of the minecraft server")

if LocalIP != None :
    commandsAdmin.append("list - Get online players")
    commands.append("list - Get online players")

if Whitelist :
    commandsAdmin.append("add - Whitelist a player using its ign")
    commands.append("add - Whitelist a player using its ign")

commandsAdmin.append("report - Report a bug")
commands.append("report - Report a bug")

if ChannelName != None : commandsAdmin.append("event - Create an event")

if isinstance(MinecraftChat, int) == False :
    MinecraftChat = 0


# -------------------------------------------------------------------------------------------------- #
# -------------------------------------------------------------------------------------------------- #


# -------------------------------------------------------------------------------------------------- #
# ------------------------------------------ Discord ----------------------------------------------- #
# -------------------------------------------------------------------------------------------------- #
# Run when the program is connected to the discord server
@client.event
async def on_ready():
    print("We have logged in as {0.user}".format(client))
    Loop()
    BotInfo()
    if MinecraftChat != 0 :
        LoopChat()


# Update the current activity of the bot - Run every 20 seconds 
@client.event
async def ServerPresence():
    while True :
        # If the server is running
        if ServerStatus() == True :
            onlinePlayers = OnlinePlayers()
            if onlinePlayers == None or onlinePlayers == 0 :
            	try : 
            		await client.change_presence(status=discord.Status.online, activity=discord.Game(name="Minecraft"))
            	except : 
            		pass
            else :
            	try :
                    server = MinecraftServer.lookup(LocalIP)
                    query = server.query()
                    await client.change_presence(status=discord.Status.online, activity=discord.Game(name="Minecraft (" + str(onlinePlayers) + ") : " + "\n" + "{0}".format(", ".join(query.players.names))))
            	except :
            		pass

        # If the server is closed
        elif ServerStatus() == False :
            try : 
            	await client.change_presence(status=discord.Status.idle, activity=discord.Activity(type=discord.ActivityType.watching, name="TV | " + Prefix + " help"))
            except : 
            	pass

        await asyncio.sleep(20)

@client.event
async def MinecraftChatLink():
    cmd_queue = queue.Queue()
    dj = threading.Thread(target=console, args=(cmd_queue,))
    dj.start()
    while 1:
        cmd = cmd_queue.get()
        if cmd.startswith("msg") :
            cmd = cmd.replace("msg ", "", 1)
            sender = str(cmd.split(" ")[0])
            msg = f"**{sender}** : {cmd.replace(sender, '', 1)}"
            await client.get_channel(MinecraftChat).send(msg)
        if cmd == 'quit':
            break

# Run on new message
@client.event
async def on_message(message) :
	# Ignore messages coming from the bot
    if message.author == client.user :
        return

    # -------------------------------------------------------- #
    # ----------------------- mn start ----------------------- #
    # -------------------------------------------------------- #
	# Start the server
    elif message.content.lower().startswith(Prefix + " start") and StartMinecraftServer != None and (message.author.guild_permissions.administrator or Administrator.contains(message.author.name)) :
		# If the server is not running -> start it
    	if ServerStatus() == False:
    		await message.channel.send("Opening server...")
    		Start(message.author.name)

    		# If the server started
    		if ServerStatus() == True and IPStatus() == True:
    			await message.channel.send("The server started! It should be up and running soon") and await message.add_reaction(Success)

    		# If the server didn't start
    		else :
    			# Warn the sender
    			await message.channel.send("ERROR : can't open the server!") and await message.add_reaction(Error)

    	# If the server is already running -> pass
    	else :
    		await message.channel.send("The server is already runnning!") and await message.add_reaction(Error)

    # -------------------------------------------------------- #
    # ------------------------ mn stop ----------------------- #
    # -------------------------------------------------------- #
    # Stop the server
    elif message.content.lower().startswith(Prefix + " stop") and message.author.guild_permissions.administrator and StartMinecraftServer != None :
    	# If the server is running
    	if ServerStatus() == True:
    		await message.channel.send("Stopping the server") and await message.add_reaction(Success)
    		Stop(message.author.name)

    	# If the server isn't running -> pass
    	else:
    		# Warn the sender
    		await message.channel.send("The server is not running") and await message.add_reaction(Error)

    # -------------------------------------------------------- #
    # ------------------------ mn send ----------------------- #
    # -------------------------------------------------------- #
    # Monitor the minecraft server
    elif message.content.lower().startswith(Prefix + " send") and message.author.guild_permissions.administrator:
        # If the server is running
        if ServerStatus() == True:
            await message.channel.send("Command sent!") and await message.add_reaction(Sent)

            cmd = message.content.split(" ")
            del cmd[0]
            del cmd[0]

            #cmd = message.content.replace(Prefix + " send ", "")
            MinecraftServerCommand(' '.join(cmd), message.author.name)

        # If the server isn't running -> pass
        else:
            # Warn the sender
            await message.channel.send("The server is not running... Start the server to send a command!") and await message.add_reaction(Error)

    # -------------------------------------------------------- #
    # ----------------------- mn term ------------------------ #
    # -------------------------------------------------------- #
    # Monitor the server
    elif message.content.lower().startswith(Prefix + " term") and message.author.guild_permissions.administrator :
        termCmd = message.content.split(" ")
        del termCmd[0]
        del termCmd[0]
        MinecraftTerminalCommand(' '.join(termCmd), message.author.name)
        await message.channel.send("Command sent!") and await message.add_reaction(Sent)

    # -------------------------------------------------------- #
    # ------------------------ mn ip ------------------------- #
    # -------------------------------------------------------- #
    # Send the ip
    elif message.content.lower().startswith(Prefix + " ip") and ServerIP != None:
        embedVar = discord.Embed(title=BotName + "Minecraft IP", description="", color=0x2B2B2B)
        if "\\n" in ServerIP :
            ServerIPList = ServerIP.split("\\n")
            for i in range (len(ServerIPList)):
                embedVar.add_field(name=ServerIPList[i].split("- ")[0], value=ServerIPList[i].split("- ")[1], inline=False)
        else :
            embedVar.add_field(name=ServerIP.split("- ")[0], value=ServerIP.split("- ")[1], inline=False)

        await message.channel.send(embed=embedVar) and await message.add_reaction(Gaming)

    # -------------------------------------------------------- #
    # ----------------------- mn help ------------------------ #
    # -------------------------------------------------------- #
    # Help with commands
    elif message.content.lower().startswith(Prefix + " help") :
        # If the sender is admin
        if message.author.guild_permissions.administrator :
            helps = commandsAdmin
            embedVar = discord.Embed(title=BotName + " Help (Administrator)", description="", color=0x2B2B2B)

    	# If the sender isn't admin
        else :
            helps = commands
            embedVar = discord.Embed(title=BotName + " Help", description="", color=0x2B2B2B)


        # Send available commmands
        for i in range (len(helps)):
            embedVar.add_field(name=Prefix + " " + helps[i].split("- ")[0], value=helps[i].split("- ")[1], inline=True)

        await message.channel.send(embed=embedVar)

    # -------------------------------------------------------- #
    # ------------------------ mn add ------------------------ #
    # -------------------------------------------------------- #
    # Whitelist player
    elif message.content.lower().startswith(Prefix + " add") and Whitelist :
        # If the server is running
        if ServerStatus() == True:
            name = message.content.split(" ")
            del name[0]
            del name[0]

            MinecraftServerCommand("whitelist add " + " ".join(name), None)
            await message.channel.send(name + " is now whitelisted!") and await message.add_reaction(Sent)

        # If the server isn't running -> pass
        else:
            # Warn the sender
            await message.channel.send("The server is not running... Start the server to send a command!") and await message.add_reaction(Error)

    # -------------------------------------------------------- #
    # ------------------------ mn list ----------------------- #
    # -------------------------------------------------------- #
    # Get the current online players
    elif message.content.lower().startswith(Prefix + " list") :
        # If the server is running
        if ServerStatus() == True:
            onlinePlayers = OnlinePlayers()
            if onlinePlayers == 0 or onlinePlayers == None :
                await message.channel.send("No one is currently online") and await message.add_reaction(Sad)
            elif onlinePlayers == 1 :
                try :
                    server = MinecraftServer.lookup(LocalIP)
                    query = server.query()
                    await message.channel.send("There is " + str(onlinePlayers) + " player online : \n" + "{0}".format(", ".join(query.players.names))) and await message.add_reaction(Gaming)
                
                except :
                    await message.channel.send("ERROR (list is not supported for Minecraft 1.17)") and await message.add_reaction(ERROR)
            else : 
                try :
                    server = MinecraftServer.lookup(LocalIP)
                    query = server.query()
                    await message.channel.send("There are " + str(onlinePlayers) + " players online : \n" + "{0}".format(", ".join(query.players.names))) and await message.add_reaction(Gaming)
                
                except :
                    await message.channel.send("ERROR (list is not supported for Minecraft 1.17)") and await message.add_reaction(ERROR)

        # If the server isn't running
        else:
            # Warn the sender
            await message.channel.send("The server is not running!") and await message.add_reaction(Error)

    # -------------------------------------------------------- #
    # ------------------------ mn say ------------------------ #
    # -------------------------------------------------------- #
    # Broadcast a message
    elif message.content.lower().startswith(Prefix + " say") and message.author.guild_permissions.administrator :
        # If the server is open
        if ServerStatus() == True :
            await message.channel.send("Message sent!") and await message.add_reaction(Sent)
            say = message.content.split(" ")
            del say[0]
            del say[0]

            MinecraftServerCommand("say " + " ".join(say), None)

        else:
            # Warn the operator if the server is closed
            await message.channel.send("The server is not running... Start the server to say something!") and await message.add_reaction(Error)

    # -------------------------------------------------------- #
    # ----------------------- mn report ---------------------- #
    # -------------------------------------------------------- #
    # Report a bug
    elif message.content.lower().startswith(Prefix + " report") :
        # Console and notification info
        bug = message.content.split(" ")
        del bug[0]
        del bug[0]

        msg = "BUG reported : " + " ".join(bug)
        Notification(msg)

        await message.channel.send("Problem reported!") and await message.add_reaction(Nice)

    # -------------------------------------------------------- #
    # ---------------------- mn event ... -------------------- #
    # -------------------------------------------------------- #
    # Create an event 
    elif message.content.lower().startswith(Prefix + " event") and message.author.guild_permissions.administrator :
        msg = message.content.split(" ")
        del msg[0]
        del msg[0]

        EventChannel = client.get_channel(EventChannelId)

        msg = " ".join(msg)
        try :
            if "\\n" in msg :
                msg = msg.split("\\n")
            
                embedVar = discord.Embed(title=msg[1], description="", color=0x2B2B2B)
                for i in range(len(msg)-2):
                    embedVar.add_field(name=msg[i+2].split("- ")[0], value=msg[i+2].split("- ")[1], inline=False)

            await EventChannel.send(msg[0])
            eventMessage = await EventChannel.send(embed=embedVar)
            await eventMessage.add_reaction(Success) and await message.add_reaction(Sent)
        
        except :
            await message.channel.send("**Error** : Your command should look something like this :\n" + Prefix + " event <Heading> \\n <Title> \\n <Name1> - <Value1> \\n <Name2> - <Value2>...") and await message.add_reaction(Error)

    # -------------------------------------------------------- #
    # ------ MinecraftChatLink (discord to minecraft) -------- #
    # -------------------------------------------------------- #
    elif message.channel.id == MinecraftChat :
        msg = 'tellraw @a "§9<' + message.author.name + '> ' + message.content + '\"'
        os.system(f"screen -S {ScreenPrefix}_Minecraft -X stuff '{msg} ^M'")


# -------------------------------------------------------------------------------------------------- #
# -------------------------------------------------------------------------------------------------- #


# -------------------------------------------------------------------------------------------------- #
# ----------------------------------------- Functions ---------------------------------------------- #
# -------------------------------------------------------------------------------------------------- #
# Get information about the bot
def BotInfo():
    BotNameList = ("{0.user}".format(client)).split("#")
    BotName = BotNameList[0]

# Start loopping (activity)
def Loop(): 
    loop = asyncio.get_event_loop()
    loop.call_later(5, LoopStop)
    task = loop.create_task(ServerPresence())

    try :
        loop.run_until_complete(task)
    except :
        pass

# Stop the loop
def LoopStop():
    try :
        task.cancel()
    except :
        pass

# Check the Server's status
def ServerStatus() :
    ServerStatus = str(subprocess.check_output(["screen","-list"]))
    if ScreenPrefix + "_Minecraft" in ServerStatus :
        return True
    else :
        return False

# Check the IP's status
def IPStatus() :
    ServerStatus = str(subprocess.check_output(["screen","-list"]))
    if ScreenPrefix + "_Playit" in ServerStatus :
        return True
    elif StartTunnel == None :
        return True
    else :
        return False

def OnlinePlayers():
    # Return the number of players online
    try :
        server = MinecraftServer.lookup(LocalIP)
        status = server.status()
        try : 
            if "{0}".format(status.players.online).isdigit() :
                return int("{0}".format(status.players.online))
        except :
            return 0
    except :
        pass

# Start the server
def Start(author) :
    # Start minercaft server
    os.system("screen -S " + ScreenPrefix + "_Minecraft -d -m " + StartMinecraftServer)

    # Start tunnel
    if StartTunnel != None :
        os.system("screen -S " + ScreenPrefix + "_Playit -d -m " + StartTunnel)

    # Console and notification info
    msg = author + " started the minecraft server"
    Notification(msg)

# Stop the server
def Stop(author) :
    # Stop command
    os.system("screen -S " + ScreenPrefix + "_Minecraft -X stuff 'stop^M'")

    if StartTunnel != None :
        # Stop tunnel
        os.system("screen -S " + ScreenPrefix + "_Playit -X stuff '^C'")

    # Console and notification info
    msg = author + " stopped the minecraft server"
    Notification(msg)

# Notify important actions
def Notification(msg):
    print(msg)
    try :
        if ChannelName == None :
            resource.push(content=msg)
        else :
            resource.push(content=msg, channel_name=ChannelName)
    except :
        pass

def MinecraftServerCommand(cmd, author):
    os.system("screen -S " + ScreenPrefix + "_Minecraft -X stuff '" + cmd + "^M'")
    if author != None :
    	msg = author + " sent a command to the minecraft server : " + cmd
    	Notification(msg)

def MinecraftTerminalCommand(term_Cmd, author):
    os.system(term_Cmd)
    msg = author + " sent a command to the  server : " + term_Cmd
    Notification(msg)


# Start loopping (activity)
def LoopChat(): 
    loopChat = asyncio.get_event_loop()
    loopChat.call_later(5, LoopChatStop)
    taskChat = loopChat.create_task(MinecraftChatLink())

    try :
        loop.run_until_complete(task)
    except :
        pass

# Stop the loop
def LoopChatStop():
    try :
        taskChat.cancel()
    except :
        pass

def console(q):
    while 1:
        cmd = input('> ')
        q.put(cmd)
        if cmd == 'quit':
            break

# -------------------------------------------------------------------------------------------------- #
# -------------------------------------------------------------------------------------------------- #

# Start the client
client.run(DiscordToken)
