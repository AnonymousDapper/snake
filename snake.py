""" Discord API Snake bot """

"""
MIT License

Copyright (c) 2016 AnonymousDapper (█▀█ █▄█ █ █ ²) (TickerOfTime)

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

import discord, re, aiohttp, json, io, asyncio, youtube_dl, os, contextlib, sys, time, html
import sqlite3 as sql
from datetime import datetime, timedelta
from urllib.parse import quote
from plotly import plotly as plot ## TODO : https://plot.ly/python/
from plotly import graph_objs
import numpy

# discord: pip install --upgrade https://github.com/Rapptz/discord.py/archive/async.zip
# youtube_dl: pip install --upgrade youtube_dl
# sqlite3 pip install --upgrade sqlite3

#sys.stdout = io.TextIOWrapper(sys.stdout.detach(), encoding = sys.stdout.encoding, errors = "xmlcharrefreplace", line_buffering = True) # Handle printing of Unicode chars.. ugh

""" #						#
	#						#
	#					  	#
		Variables and such
	#						#
	#						#
	#						#
"""

class Text: # ansi color codes for easy access
	black = '\033[30m'
	red = '\033[31m'
	green = '\033[32m'
	yellow = '\033[33m'
	blue = '\033[34m'
	magenta = '\033[35m'
	cyan = '\033[36m'
	white = '\033[37m'
	default = '\033[37m'

class Background:
	black = '\033[40m'
	red = '\033[41m'
	green = '\033[42m'
	yellow = '\033[43m'
	blue = '\033[44m'
	magenta = '\033[45m'
	cyan = '\033[46m'
	white = '\033[47m'
	default = '\033[40m'

class Attributes:
	off = '\033[0m'
	bold = '\033[1m'
	score = '\033[4m'
	blink = '\033[5m'
	reverse = '\033[7m'
	hidden = '\033[8m'

help_docs = '''
```xl
User ** <a/r/l> [User]        => manage admins
Run ** <code>                 => execute code
Leave ** <server>             => leaves the server
Quit **                       => exits snake
Debug ** <expression>         => execute a statement

Clear * <count>               => removes snakes messages
Set * <settingname> <option>  => change settings
Playx * <j/l/m/s/p/r/v> [opt] => voice control
Purge * <User> <count>        => remove someones messages

Video <s/l/d> [name] [id]     => manage stored videos
Play  <url/id/sid> [channel]  => play a video in the channel
Speak <text> [channel]        => speaks the text in channel
Summon                        => bring snake to your voice channel

Help                          => displays this help page
Insult [User]+                => insult people
Invite                        => lets you add snake
Info [chan/role/User]         => print info. "server" works too

Docs <obj>                    => returns discord.py docs for obj
Tag <g/l/d/a/e> <name> <data> => manage tags
Game [gamename]               => makes snake play the game
Xkcd  [comicid]               => get an xkcd comic

Uptime                        => see how long snake has been up
Source                        => get snakes source code
Playing                       => see the song thats playing
List [setting]                => show value of setting(s)

Meme <name> <text> <text>     => make a meme
Chat <chan> <msg> [server]    => chat on different server
Permissions                   => list snakes permissions


User is @Mention or their name

* Admin only
** Owner only
```''' # help page

client_info = '''
```xl
WHOIS Bot

	Name => {0.name}#{0.discriminator}
	  ID => {0.id}
  Avatar => {0.avatar_url}
	Nick => {0.display_name}#{0.discriminator}
 Playing => {7}
 Created => {1}
  Uptime => {2}
Channels => {3}
 Servers => {4}

Running discord.py {5} on Python {6}

Written by AnonymousDapper#7467 [163521874872107009]

```''' # info about snake

user_info = '''
```xl
WHOIS User

   Name => {0.name}#{0.discriminator}
	 ID => {0.id}
 Avatar => {0.avatar_url}
   Nick => {0.display_name}#{0.discriminator}
 Status => {0.status}{5}
	Bot => {1}
Created => {3}
 Joined => {4}
  Roles => {2}
```''' # info about a user

server_info = '''
```xl
WHOIS Server

	Name => {0.name}
	  ID => {0.id}
  Region => {0.region!s}
 Members => {1}
Channels => {2}
   Owner => {0.owner.name}#{0.owner.discriminator}
 Created => {3}
	Icon => {0.icon_url}
   Roles => {4}
```''' # info about server

text_channel_info = '''
```xl
WHOIS Text Channel

   Name => {0.name}
 Server => {0.server.name}
     ID => {0.id}
Created => {1}
  Topic => {0.topic}
```'''

voice_channel_info = '''
```xl
WHOIS Voice Channel

     Name => {0.name}
   Server => {0.server.name}
       ID => {0.id}
  Created => {1}
  Members => {2}/{5}
  Bitrate => {3}kbs
   Online => {4}
```'''

role_info = '''
```xl
WHOIS Role

     Name => {0.name}
       ID => {0.id}
Seperated => {1}
    Color => {2}
  Created => {3}
```'''

ytplayer_info = '''
```xl
Playing "{0.title}" by "{0.uploader}" in {1.name}
```''' # info about yt_player

permission_info = '''
```xl
Snake {22} an Administrator.

	  Create Invites => {0}
		Kick Members => {1}
		 Ban Members => {2}
	 Manage Channels => {3}
	   Manage Server => {4}
	   Read Messages => {5}
	   Send Messages => {6}
   Send TTS Messages => {7}
	 Manage Messages => {8}
		 Embed Links => {9}
		Attach Files => {10}
Read Message History => {11}
	Mention Everyone => {12}
	Connect To Voice => {13}
	  Speak In Voice => {14}
		Mute Members => {15}
	  Deafen Members => {16}
		Move Members => {17}
  Use Voice Activity => {18}
	Change Nicknames => {19}
	Manage Nicknames => {20}
		Manage Roles => {21}
```''' # info about roles

base_docs_url = "http://discordpy.readthedocs.io/en/latest/api.html#" # docs
user_notes, voice_channels = {}, {} # empty stuff

voice_count, private_count, server_count, channel_count = 0,0,0,0

time_format = "%a %B %d, %Y, %H:%M:%S CST" # time format str
pb_bot_id = "b0dafd24ee35a477" # PandoraBots Chomsky
my_id = "163521874872107009" # my userid

xkcd_rand_comic = "http://c.xkcd.com/random/comic/" # random xkcd

utc_offset = timedelta(hours=-5)
opus_loaded = discord.opus.is_loaded()

class Settings: # setting management
	settings_list = {
		"enable_ai": True,
		"notify_on_exit": True,
		"notify_channel": False
	}

	def convert(b):
		if b in [True, False]:
			return "on" if b == True else "off"
		else:
			return b

	@classmethod
	def set(self, key, value):
		self.settings_list[key] = value

	@classmethod
	def get(self, key):
		if key in self.settings_list:
			return self.settings_list[key]

	@classmethod
	def list(self):
		settings = []
		for key, value in self.settings_list.items():
			settings.append("'{}' is {}".format(key, self.convert(value)))
		return settings

class Seconds: # for datetime conversion
	year = 31536000
	month = 2592000
	week = 606461.538462
	day = 86400
	hour = 3600
	minute = 60
	second = 1

with open("memelist.json", 'r') as f:
	meme_list = json.load(f)

with open("facelist.txt", 'r', encoding="utf-8") as f:
	face_list = f.readlines()

temp_db = sql.connect(":memory:")
temp_db_cursor = temp_db.cursor()

log_db = sql.connect("snake.db")
log_db_cursor = log_db.cursor()

temp_db_cursor.execute("CREATE TABLE pb_ids (user_id TEXT, cust_id TEXT)")

log_db_cursor.execute("SELECT * FROM user_tags")

for tag in log_db_cursor.fetchall():
	user_notes[tag[0]] = {"name": tag[0], "owner": tag[2], "content": tag[1]}

temp_db.commit()
client = discord.Client()

## End of variables
""" #						#
	#						#
	#						#
		Helper Functions
	#						#
	#						#
	#						#
"""

# commit to the log database every 30 seconds so i wont forget
async def db_commit():
	log_db.commit()
	asyncio.sleep(30)
	client.loop.create_task(db_commit())

#parse commands into table
def parse_commands(text, quotes="'\"`", whitespace=" 	"):
	args = [""]
	counter = 0
	inside_quotes = False
	current_quote = None
	for char in text:
		if char in quotes:
			if inside_quotes is False:
				inside_quotes = True
				current_quote = char
			elif char is current_quote:
				inside_quotes = False
				current_quote = None
			else:
				args[counter] += char
		elif char in whitespace:
			if inside_quotes is True:
				args[counter] += char
			else:
				args.append("")
				counter += 1
		else:
			args[counter] += char
	return list(filter(lambda t:len(t) > 0, args))

# log messages
async def log_message(message : discord.Message):
	message_data = (
		(message.timestamp + utc_offset).strftime(time_format),
		message.author.name,
		message.content,
		str(message.channel),
		message.id,
		message.server.name if message.channel.is_private == False else "Direct Message",
		message.author.id
	)
	log_db_cursor.execute("INSERT INTO chat_logs VALUES (?,?,?,?,?,?,?)", message_data)

# talk to pandorabots api
async def talk_pandora(user : discord.Member, message):
	temp_db_cursor.execute("SELECT cust_id FROM pb_ids WHERE user_id=?", (user.id,))
	cust_id = temp_db_cursor.fetchone()
	with aiohttp.ClientSession() as session:
		if not cust_id == None:
			async with session.post("http://www.pandorabots.com/pandora/talk-xml", data={"botid": pb_bot_id, "input": message, "custid": cust_id}) as response:
				if response.status == 200:
					pb_response = await response.text()
				pass
		else:
			async with session.post("http://www.pandorabots.com/pandora/talk-xml", data={"botid": pb_bot_id, "input": message}) as response:
				if response.status == 200:
					pb_response = await response.text()
				pass
	response_data = re.search(r'<result status="(?P<status>\d*)"\sbotid="(?P<botid>\w+)"\scustid="(?P<custid>\w+)">\s*<input>[\w ]+</input>\s*<that>(?P<response>.*)</that>', str(pb_response), re.I)
	if cust_id == None:
		temp_db_cursor.execute("INSERT INTO pb_ids VALUES(?,?)", (user.id, response_data.group("custid")))
		temp_db.commit()
	if not response_data == None:
		return response_data.group("response")

# fetch users admin status
def is_admin(user: discord.Member):
	log_db_cursor.execute("SELECT * FROM allowed_users WHERE user_id=?", (user.id, ))
	if log_db_cursor.fetchone() == None:
		return False
	else:
		return True

# get time between two dates
def get_elapsed_time(date_1, date_2):
	delta = abs(date_2 - date_1)
	time = int(delta.total_seconds())
	track = []
	desc = lambda n, h: ('a' if n == 1 else str(int(n))) + ('n' if h == 1 and n == 1 else '') + ''
	mult = lambda n: 's' if n > 1 or n == 0 else ''
	years = (time // Seconds.year)
	track.append("{} year{}".format(desc(years, 0), mult(years)))

	time = time - (years * Seconds.year)
	months = (time // Seconds.month)
	track.append("{} month{}".format(desc(months, 0), mult(months)))

	time = time - (months * Seconds.month)
	weeks = (time // Seconds.week)
	track.append("{} week{}".format(desc(weeks, 0), mult(weeks)))

	time = time - (weeks * Seconds.week)
	days = (time // Seconds.day)
	track.append("{} day{}".format(desc(days, 0), mult(days)))

	time = time - (days * Seconds.day)
	hours = (time // Seconds.hour)
	track.append("{} hour{}".format(desc(hours, 1), mult(hours)))

	time = time - (hours * Seconds.hour)
	minutes = (time // Seconds.minute)
	track.append("{} minute{}".format(desc(minutes, 0), mult(minutes)))

	time = time - (minutes * Seconds.minute)
	track.append("{} second{}".format(desc(time, 0), mult(time)))

	return ", ".join(list(filter(lambda e: not e.startswith("0 "), track)))

# upload a file to discord
async def upload_file(url, file_name, channel : discord.Channel, note=""):
	file_name = "cache/" + file_name
	with aiohttp.ClientSession() as session:
		async with session.get(url) as response:
			if response.status == 200:
				data = await response.read()
				with open(file_name, "wb") as tmp_file:
					tmp_file.write(data)
			pass
	try:
		await client.send_file(channel, file_name, filename=file_name, content=note)
	except Exception as e:
		print("{0.red}{1}: {2}{3.off}".format(Text, type(e).__name__, str(e), Attributes))

# manage saved videos
def manage_saved_videos(action, yt_id="", video_name="", author=None):
	if action is "save":
		log_db_cursor.execute("SELECT * FROM youtube_videos WHERE id=? OR save_name=?", (yt_id, video_name))
		if log_db_cursor.fetchone() == None:
			log_db_cursor.execute("INSERT INTO youtube_videos VALUES (?,?,?)", (video_name, yt_id, author.id))
	elif action is "remove":
		log_db_cursor.execute("SELECT * FROM youtube_videos WHERE save_name=? AND author_id=?", (video_name, author.id))
		if not log_db_cursor.fetchone() == None:
			log_db_cursor.execute("DELETE FROM youtube_videos WHERE save_name=?", (video_name, ))
	elif action is "load":
		log_db_cursor.execute("SELECT * FROM youtube_videos WHERE save_name=?", (video_name, ))
		return log_db_cursor.fetchone()
	elif action is "list":
		log_db_cursor.execute("SELECT * FROM youtube_videos")
		result = []
		for video_data in log_db_cursor.fetchall():
			result.append([video_data[0], video_data[1]])
		return result

# print public channels nicely
def print_channel(channel):
	print("{0.blue} -- {1}{2.name} {3}[{2.id}]{4.off}".format(Text, Text.red if channel.type == discord.ChannelType.voice else Text.cyan, channel, Text.magenta if channel.type == discord.ChannelType.voice else Text.yellow, Attributes))

# print private channels nicely
def print_private_channel(channel):
	print("{0.green}@{2.off}{1.user.name} {0.cyan}[{1.id}]{2.off}".format(Text, channel, Attributes))

# update servers
def update_server_list(servers, do_in_channels):
	for server in servers:
		print("\n{0.green}{1.name} {2.off}[{1.id}] ({0.cyan}{1.owner.name}{2.off}#{0.yellow}{1.owner.discriminator}{2.off})".format(Text, server, Attributes))
		if not do_in_channels == None:
			for channel in server.channels:
				do_in_channels(channel)
	print("\n\n")

# get a user by name and/or nick
def find_user(server, name):
	user = discord.utils.get(server.members, name=name)
	if user == None:
		user = discord.utils.get(server.members, display_name=name)
	return user

# capture results from stdout
@contextlib.contextmanager
def stdoutIO(stdout=None):
	old = sys.stdout
	if stdout == None:
		stdout = io.StringIO()
	sys.stdout = stdout
	yield stdout
	sys.stdout = old

# get full youtube link
def expand_video_url(text):
	url = text
	if text.startswith('$') == True:
		url = manage_saved_videos("load", None, text.lstrip('$'))[1]
	if not url.startswith("http") == True:
		url = "https://www.youtube.com/watch?v=" + url
	return url

# End helper funcs

"""
			 ╔ ╗
		   ╔ ╔ ╗ ╗
		 ╔ ╔ ╔ ╗ ╗ ╗
	   ╔ ┌─┬─┐ ┌─┬─┐ ╗
	  ║──┤ │ ├─┤ │ ├─ ║
	  ╠══│ ├─┼─┼─┤ │══╣                 why?
	  ║──┤ │ ├─┤ │ ├──║               idk
	  ╠══│ ├─┼─┼─┤ │══╣
	 ╔╣_______________╠╗
	 ║║▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄║║
	 ║║/|\|/|\|/|\|/|\║║
	 ║║¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯║║
	'WW'             'WW'
"""

""" #				#
	#				#
	#				#
		Commands
	#				#
	#				#
	#				#
"""

# change admin status
async def manage_admins(ctx, call, command, args):
	user = args[1] if len(args) > 1 else None
	method = args[0] if len(args) > 0 else "None"
	if ctx.author.id == my_id:
		if not isinstance(user, discord.Member) == True: # are we dealing with a string?
			user = find_user(ctx.server, user)
		if method.lower() in ["remove", 'r']:
			if not user == None:
				if is_admin(user) == True:
					log_db_cursor.execute("DELETE FROM allowed_users WHERE user_id=?", (user.id, ))
					await client.send_message(ctx.author, "Removed admin '{}'".format(user.name + "#" + user.discriminator))
		elif method.lower() in ["add", 'a']:
			if not user == None:
				if is_admin(user) == False:
					log_db_cursor.execute("INSERT INTO allowed_users VALUES (?,?)", (user.id, user.name + "#" + user.discriminator))
					await client.send_message(ctx.author, "Added admin '{}'".format(user.name + "#" + user.discriminator))
		elif method.lower() in ['l', "list", "show"]:
			admins = []
			log_db_cursor.execute("SELECT * FROM allowed_users")
			for user in log_db_cursor.fetchall():
				admins.append("{} [{}]".format(user[1], user[0]))
			await client.send_message(ctx.channel, "```xl\n{}\n```".format("\n".join(admins)))

# eval code yey
async def eval_code(ctx, call, command, args):
	code = args[0] if len(args) > 0 else None
	if ctx.author.id == my_id:
		if not code == None:
			try:
				with stdoutIO() as s:
					exec(code)

				result = s.getvalue()
				result = '' if result == None else result
				cutoff = [result[x:x + 1800] for x in range(0, len(result), 1800)]

				if len(cutoff) > 1:
					if len(cutoff) < 3:
						for message in cutoff:
							await client.send_message(ctx.channel, "```py\n{}\n```".format(message))
							time.sleep(.21)
					else:
						await client.send_message(ctx.channel, "```py\n{}\n```".format(cutoff[0]))
						await client.send_message(ctx.channel, "```\n{} pages not sent\n```".format(len(cutoff) - 1))
				else:
					await client.send_message(ctx.channel, "```py\n{}\n```".format(result))
			except Exception as e:
				await client.send_message(ctx.channel, "```py\n{}: {}\n```".format(type(e).__name__, str(e)))

# leave a specific server
async def leave_server(ctx, call, command, args):
	if ctx.author.id == my_id:
		server_name = args[0] if len(args) > 0 else None
		server = discord.utils.get(client.servers, name=server_name)
		if not server == None:
			await client.leave_server(server)
			global channel_count, voice_count, server_count
			for channel in server.channels:
				if channel.type == discord.ChannelType.text:
					channel_count -= 1
				elif channel.type == discord.ChannelType.voice:
					voice_count -= 1
			server_count -= 1
			await client.send_message(ctx.channel, "```xl\nSuccessfully left '{}'\n```".format(server.name))
		else:
			await client.send_message(ctx.channel, "```xl\nCannot find '{}'\n```".format(server_name))

# rip
async def snake_quit(ctx, call, command, args):
	if ctx.author.id == my_id:
		if Settings.get("notify_on_exit") == True:
			await client.send_message(ctx.channel, "rip {}".format(call))
		log_db.commit()
		await client.logout()

# debug one expression
async def debug_code(ctx, call, command, args):
	if ctx.author.id == my_id:
		code = args[0] if len(args) > 0 else None
		if not code == None:
			result = None
			try:
				result = eval(code)
			except Exception as e:
				await client.send_message(ctx.channel, "```py\n{}: {}\n```".format(type(e).__name__, str(e)))
				return

			if asyncio.iscoroutine(result):
				result = await result

			result = str(result)
			cutoff = [result[x:x + 1800] for x in range(0, len(result), 1800)]

			if len(cutoff) > 1:
				if len(cutoff) < 3:
					for message in cutoff:
						await client.send_message(ctx.channel, "```py\n{}\n```".format(message))
						time.sleep(.21)
				else:
					await client.send_message(ctx.channel, "```py\n{}\n```".format(cutoff[0]))
					await client.send_message(ctx.channel, "```\n{} pages not sent\n```".format(len(cutoff) - 1))
			else:
				await client.send_message(ctx.channel, "```py\n{}\n```".format(result))

# clear snakes messages
async def remove_self_messages(ctx, call, command, args):
	count = args[0] if len(args) > 0 else 1
	if (is_admin(ctx.author) == True):
		messages_removed = 0
		count = int(count)
		async for message in client.logs_from(ctx.channel):
			if message.author == client.user:
				if messages_removed < count:
					await client.delete_message(message)
					messages_removed += 1
					time.sleep(.21)

# change a setting value
async def change_setting(ctx, call, command, args):
	if is_admin(ctx.author) == True:
		setting = args[0] if len(args) > 0 else None
		option = args[1] if len(args) > 1 else "None"
		if option.lower() in ["yes", "on", "y"]:
			Settings.set(setting, True)
			await client.send_message(ctx.channel, "Turned '{}' on".format(setting))
		elif option.lower() in ["no", "n", "off"]:
			Settings.set(setting, False)
			await client.send_message(ctx.channel, "Turned '{}' off".format(setting))
		else:
			Settings.set(setting, option)
			await client.send_message(ctx.channel, "Set '{}' to '{}'".format(setting, option))

# player control
async def manage_players(ctx, call, command, args):
	if is_admin(ctx.author) == True:
		method = args[0] if len(args) > 0 else "None"
		channel = discord.utils.get(ctx.server.channels, name=args[1], type=discord.ChannelType.voice) if len(args) > 1 else None
		notify_channel = Settings.get("notify_channel")
		if hasattr(ctx, "server") == True:
			if method.lower() in ['l', "leave", "exit"]:
				voice_client = client.voice_client_in(ctx.server)
				if not voice_client == None:
					await voice_client.disconnect()
					del voice_channels[voice_client]
					if notify_channel == True:
						await client.send_message(ctx.channel, "```xl\nLeft '{}' on '{}'\n```".format(channel.name, ctx.server.name))
			elif method.lower() in ['j', "join"]:
				if not channel == None:
					voice_client = client.voice_client_in(ctx.server)
				if voice_client == None:
					voice_client = await client.join_voice_channel(channel)
					voice_channels[voice_client] = {}
					if notify_channel == True:
						await client.send_message(ctx.channel, "```xl\nJoined '{}' on '{}'\n```".format(channel.name, ctx.server.name))
			elif method.lower() in ['m', "move", "goto"]:
				if not channel == None:
					voice_client = client.voice_client_in(ctx.server)
				if not voice_client == None:
					await voice_client.move_to(channel)
					if notify_channel == True:
						await client.send_message(ctx.channel, "```xl\Moved to '{}' on '{}'\n```".format(channel.name, ctx.server.name))
			else:
				voice_client = client.voice_client_in(ctx.server)
				if not voice_client == None:
					voice_player = voice_channels[voice_client]["player"]
					if not voice_player == None:
						if method.lower() in ['s', "stop"]:
							voice_player.stop()
						elif method.lower() in ['p', "pause"]:
							voice_player.pause()
						elif method.lower() in ['r', "res", "resume"]:
							if voice_player.is_done() == True:
								voice_player.start()
							else:
								voice_player.resume()
						elif method.lower() in ['v', "vol", "volume"]:
							vol = float(args[1] if len(args) > 1 else 100.0) / 100.0
							voice_player.volume = vol

# remove others messages
async def purge_messages(ctx, call, command, args):
	user = args[0] if len(args) > 0 else None
	count = args[1] if len(args) > 1 else None
	if is_admin(ctx.author) == True and (not user == None) and (not count == None):
		if not isinstance(user, discord.Member) == True:
			user = find_user(ctx.server, user)
		messages_removed = 0
		count = int(count)
		try:
			async for message in client.logs_from(ctx.channel):
				if message.author == user:
					if messages_removed < count:
						await client.delete_message(message)
						messages_removed += 1
						time.sleep(.21)
		except Exception as e:
			await client.send_message(ctx.channel, "```py\n{}: {}\n```".format(type(e).__name__, str(e)))

# manage saved videos
async def manage_user_videos(ctx, call, command, args):
	option = args[0] if len(args) > 0 else "None"
	yt_name = args[1] if len(args) > 1 else None
	yt_id = args[2] if len(args) > 2 else None
	if option.lower() in ['s', "save"]:
		if (not yt_id == None) and (not yt_name == None):
			manage_saved_videos("save", yt_id, yt_name, ctx.author)
	elif option.lower() in ["del", "delete", 'd']:
		if not yt_name == None:
			manage_saved_videos("remove", None, yt_name, ctx.author)
	elif option.lower() in ['l', "ls", "list"]:
		result = []
		for video in manage_saved_videos("list"):
			result.append("\"{}\" - \"{}\"".format(video[0], video[1]))
		await client.send_message(ctx.channel, "```xl\n{}\n```".format("\n".join(result)))

# play youtube videos
async def play_youtube_video(ctx, call, command, args):
	if opus_loaded == False:
		await client.send_message(ctx.channel, "```diff\n- Opus audio library is not loaded, cannot play\n```")
		return
	video_url = expand_video_url(args[0] if len(args) > 0 else "None")
	voice_channel = discord.utils.get(ctx.server.channels, name=args[1], type=discord.ChannelType.voice) if len(args) > 1 else None
	voice_client = None
	video_player = None

	if not video_url == "None":
		if voice_channel == None:
			voice_client = client.voice_client_in(ctx.server)
			if voice_client == None:
				return # tell them there is no connection?
		else:
			voice_client = discord.utils.get(client.voice_clients, channel=voice_channel)
			if not voice_client == None:
				if voice_channels[voice_client]["player"].is_done() == True: # IndexError upcoming?
					voice_client.move_to(voice_channel)
				else:
					await client.send_message(ctx.channel, "```diff\n- Cannot play video, something else is playing\n```")
					return
			else:
				voice_client = await client.join_voice_channel(voice_channel)
				voice_channels[voice_client] = {}
		try:
			video_player = await voice_client.create_ytdl_player(video_url) # , after=asyncio.run_coroutine_threadsafe(complete(), client.loop).result()
			voice_channels[voice_client]["player"] = video_player
		except Exception as e:
			await client.send_message(ctx.channel, "```py\nCannot play video\n{}: {}\n```".format(type(e).__name__, str(e)))
			return
		await client.send_message(ctx.channel, ytplayer_info.format(video_player, voice_client.channel))
		video_player.start()

# send dectalk speech
async def play_speech_data(ctx, call, command, args):
	if opus_loaded == False:
		await client.send_message(ctx.channel, "```diff\n- Opus audio library is not loaded, cannot play\n```")
		return
	speech_text = args[0] if len(args) > 0 else None
	voice_channel = discord.utils.get(ctx.server.channels, name=args[1], type=discord.ChannelType.voice) if len(args) > 1 else None

	if not speech_text == None:
		if voice_channel == None:
			voice_client = client.voice_client_in(ctx.server)
			if voice_client == None:
				return # nah, lets keep it quiet. we  have been
		else:
			voice_client = discord.utils.get(client.voice_clients, channel=voice_channel)
			if not voice_client == None:
				if voice_channels[voice_client]["player"].is_done() == True: #more IndexErrors
					voice_client.move_to(voice_channel)
				else:
					await client.send_message(ctx.channel, "```diff\n- Cannot play, something else is playing\n```")
					return
			else:
				voice_client = await client.join_voice_channel(voice_channel)
				voice_channels[voice_client] = {}
		try:
			os.chdir("dectalk")
			os.system("say.exe -w say.wav \"{}\"".format(speech_text.replace("\n", "")))
			sound_player = voice_client.create_ffmpeg_player("say.wav")
			voice_channels[voice_client]["player"] = sound_player
			sound_player.start()
			os.chdir("..")
		except Exception as e:
			await client.send_message(ctx.channel, "```py\n{}: {}\n```".format(type(e).__name__, str(e)))

# follow player into voice channel
async def join_player_voice(ctx, call, command, args):
	if not ctx.author.voice_channel == None:
		if client.voice_client_in(ctx.author.voice_channel) == None:
			voice_client = await client.join_voice_channel(ctx.author.voice_channel)
			voice_channels[voice_client] = {}

# get helpdocs
async def get_help(ctx, call, command, args):
	await client.send_message(ctx.channel, help_docs)

# insults :)
async def get_insult(ctx, call, command, args):
	if len(args) > 0:
		for recipient in args:
			if not isinstance(recipient, discord.Member) == True:
				recipient = find_user(ctx.server, recipient)
			if not recipient == None:
				with aiohttp.ClientSession() as session:
					async with session.get("http://insultgenerator.org/") as response:
						if response.status == 200:
							insult = re.search(r'<div class="wrap">\s*<br><br>(.+)</div>', str(await response.text()), re.I).group(1)
							await client.send_message(recipient, html.unescape(insult))
						pass
	else:
		with aiohttp.ClientSession() as session:
			async with session.get("http://insultgenerator.org/") as response:
				if response.status == 200:
					insult = re.search(r'<div class="wrap">\s*<br><br>(.+)</div>', str(await response.text()), re.I).group(1)
					await client.send_message(ctx.channel, html.unescape(insult))
				pass

# get oath url
async def get_oauth_link(ctx, call, command, args):
	permissions = discord.Permissions(104066057)
	oauth_url = discord.utils.oauth_url("181584771510566922", permissions)
	await client.send_message(ctx.author, "Click the link below to add snake to your server\n{}".format(oauth_url))

#info
async def get_object_info(ctx, call, command, args):
	item = args[0] if len(args) > 0 else None
	if type(item).__name__ == "str":
		user = find_user(ctx.server, item)
		if not user == None:
			item = user
	if not item == None:
		if isinstance(item, discord.Member) == True:
			if not item == ctx.server.me:
				await client.send_message(ctx.channel, user_info.format(
					item,
					"Yes" if item.bot == True else "No?",
					", ".join(map(lambda x:str(x)[1:] if str(x).startswith('@') else str(x), item.roles)),
					"{} ago ({})".format(get_elapsed_time(item.created_at + utc_offset, datetime.utcnow() + utc_offset), (item.created_at + utc_offset).strftime(time_format)),
					"{} ago ({})".format(get_elapsed_time(item.joined_at + utc_offset, datetime.utcnow() + utc_offset), (item.joined_at + utc_offset).strftime(time_format)),
					"" if item.game == None else ", playing {}".format(item.game.name)
				))
			else:
				await client.send_message(ctx.channel, client_info.format(
					client.user,
					"{} ago ({})".format(get_elapsed_time(client.user.created_at + utc_offset, datetime.utcnow() + utc_offset), (client.user.created_at + utc_offset).strftime(time_format)),
					"{} ({})".format(get_elapsed_time(client.start_time, datetime.utcnow() + utc_offset), client.start_time.strftime(time_format)),
					"{} public channels ({} text, {} voice), {} private channels".format(channel_count + voice_count, channel_count, voice_count, private_count),
					"{} servers ({})".format(server_count, "'{}'".format("', '".join(list(map(str, client.servers))))),
					".".join(list(map(str,list(discord.version_info)[:3]))),
					".".join(list(map(str,list(sys.version_info)[:3]))),
					"" if ctx.server.me.game == None else ctx.server.me.game.name
				))

		elif isinstance(item, discord.Role) == True:
			await client.send_message(ctx.channel, role_info.format(
				item,
				"Yes" if item.hoist == True else "No",
				str(item.colour).upper(),
				"{} ago ({})".format(get_elapsed_time(item.created_at + utc_offset, datetime.utcnow() + utc_offset), (item.created_at + utc_offset).strftime(time_format))
			))
		elif isinstance(item, discord.Channel) == True:
			if item.type == discord.ChannelType.text:
				await client.send_message(ctx.channel, text_channel_info.format(
					item,
					"{} ago ({})".format(get_elapsed_time(item.created_at + utc_offset, datetime.utcnow() + utc_offset), (item.created_at + utc_offset).strftime(time_format))
				))
			else:
				await client.send_message(ctx.channel, voice_channel_info.format(
					item,
					"{} ago ({})".format(get_elapsed_time(item.created_at + utc_offset, datetime.utcnow() + utc_offset), (item.created_at + utc_offset).strftime(time_format)),
					len(item.voice_members),
					item.bitrate // 1000,
					", ".join(map(lambda m: m.name, item.voice_members)) if len(item.voice_members) > 0 else "No one",
					item.user_limit if item.user_limit > 0 else '∞'
				))
		else:
			item = str(item)
			voice_channel = discord.utils.get(ctx.server.channels, name=item)
			if item.lower() == "server":
				item = ctx.server
				await client.send_message(ctx.channel, server_info.format(
					item,
					"{} member{}".format(len(item.members), 's' if len(item.members) > 1 or len(item.members) == 0 else ""),
					"{} text channel{}, {} voice channel{}".format(channel_count, 's' if channel_count > 1 or channel_count == 0 else "", voice_count, 's' if voice_count > 1 or voice_count == 0 else ""),
					"{} ago ({})".format(get_elapsed_time(item.created_at + utc_offset, datetime.utcnow() + utc_offset), (item.created_at + utc_offset).strftime(time_format)),
					", ".join(map(lambda x:str(x)[1::] if str(x).startswith("@") else str(x), item.roles))
				))
			elif item.lower() == "client":
				await client.send_message(ctx.channel, client_info.format(
					client.user,
					"{} ago ({})".format(get_elapsed_time(client.user.created_at + utc_offset, datetime.utcnow() + utc_offset), (client.user.created_at + utc_offset).strftime(time_format)),
					"{} ({})".format(get_elapsed_time(client.start_time, datetime.utcnow() + utc_offset), client.start_time.strftime(time_format)),
					"{} public channels ({} text, {} voice), {} private channels".format(channel_count + voice_count, channel_count, voice_count, private_count),
					"{} servers ({})".format(server_count, ", ".join(list(map(str, client.servers)))),
					".".join(list(map(str,list(discord.version_info)[:3]))),
					".".join(list(map(str,list(sys.version_info)[:3]))),
					"" if ctx.server.me.game == None else ctx.server.me.game.name
				))
			else:
				channel = discord.utils.get(ctx.server.channels, name=item, type=discord.ChannelType.voice)
				role = discord.utils.get(ctx.server.roles, name=item)
				if (not channel == None) and (role == None):
					item = channel
					await client.send_message(ctx.channel, voice_channel_info.format(
						item,
						"{} ago ({})".format(get_elapsed_time(item.created_at + utc_offset, datetime.utcnow() + utc_offset), (item.created_at + utc_offset).strftime(time_format)),
						len(item.voice_members),
						item.bitrate // 1000,
						", ".join(map(lambda m: m.name, item.voice_members)) if len(item.voice_members) > 0 else "No one",
						item.user_limit if item.user_limit > 0 else '∞'
					))
				elif (not role == None) and (channel == None):
					item = role
					await client.send_message(ctx.channel, role_info.format(
						item,
						"Yes" if item.hoist == True else "No",
						str(item.colour).upper(),
						"{} ago ({})".format(get_elapsed_time(item.created_at + utc_offset, datetime.utcnow() + utc_offset), (item.created_at + utc_offset).strftime(time_format))
					))
				else:
					await client.send_message(ctx.channel, "Unable to retrieve information, '{}' matches multiple objects.".format(item))

#get docs for soandso
async def get_object_docs(ctx, call, command, args):
	item = args[0] if len(args) > 0 else None
	if not item == None:
		item = str(item).lower()
		await client.send_message(ctx.channel, "{}discord.{}".format(base_docs_url, item.capitalize()))
	else:
		await client.send_message(ctx.channel, base_docs_url)

#manage tags, yay
async def manage_user_tags(ctx, call, command, args):
	method = str(args[0] if len(args) > 0 else None).lower()
	name = args[1] if len(args) > 1 else None
	content = args[2] if len(args) > 2 else None
	if method in ["list", 'l']:
		log_db_cursor.execute("SELECT * FROM user_tags")
		tag_list = []
		for tag in log_db_cursor.fetchall():
			tag_list.append("^'" + tag[0] + "'" if tag[2] == ctx.author.id else "'" + tag[0] + "'")
		await client.send_message(ctx.channel, "**All Saved Tags**:\n```xl\n{}\n```".format(", ".join(tag_list)))
	elif method in ["get", 'g']:
		if not name == None:
			log_db_cursor.execute("SELECT * FROM user_tags WHERE tag_name=?", (name, ))
			tag = log_db_cursor.fetchone()
			if not tag == None:
				await client.send_message(ctx.channel, "**{}** ({}):\n\n{}".format(tag[0], tag[3], tag[1]))
			else:
				await client.send_message(ctx.channel, "Tag `{}` does not exist".format(name))
	elif method in ["add", 'a']:
		if (not name == None) and (not content == None):
			log_db_cursor.execute("SELECT * FROM user_tags WHERE tag_name=?", (name, ))
			if log_db_cursor.fetchone() == None:
				log_db_cursor.execute("INSERT INTO user_tags VALUES (?,?,?,?)", (name, content, ctx.author.id, "{}#{}".format(ctx.author.name, ctx.author.discriminator)))
				log_db.commit()
				await client.send_message(ctx.channel, "Tag `{}` created successfully".format(name))
			else:
				await client.send_message(ctx.channel, "Tag `{}` already exists".format(name))
	elif method in ["edit", 'e']:
		if (not name == None) and (not content == None):
			log_db_cursor.execute("SELECT * FROM user_tags WHERE tag_name=? and tag_owner=?", (name, ctx.author.id))
			if not log_db_cursor.fetchone() == None:
				log_db_cursor.execute("UPDATE user_tags SET tag_name=?,tag_content=?,tag_owner=?,tag_owner_name=? WHERE tag_name=?", (name, content, ctx.author.id, "{}#{}".format(ctx.author.name, ctx.author.discriminator), name))
				log_db.commit()
				await client.send_message(ctx.channel, "Tag `{}` edited successfully".format(name))
			else:
				await client.send_message(ctx.channel, "Tag `{}` does not exist or is not owner by you".format(name))
	elif method in ["del", "delete", 'd']:
		if not name == None:
			log_db_cursor.execute("SELECT * FROM user_tags WHERE tag_name=? and tag_owner=?", (name, ctx.author.id))
			if not log_db_cursor.fetchone() == None:
				log_db_cursor.execute("DELETE FROM user_tags WHERE tag_name=?", (name, ))
				log_db.commit()
				await client.send_message(ctx.channel, "Tag `{}` deleted successfully".format(name))
			else:
				await client.send_message(ctx.channel, "Tag `{}` does not exist or is not owner by you".format(name))

# whats he playing
async def change_snake_game(ctx, call, command, args):
	game_name = args[0] if len(args) > 0 else None
	game = None
	if not game_name == None:
		game = discord.Game(name=game_name, url=game_name, type=1)
	await client.change_status(game=game, idle=False)

# xkcd, yey
async def get_xkcd_comic(ctx, call, command, args):
	xkcd_id = args[0] if len(args) > 0 else None
	await client.send_typing(ctx.channel)
	url, data = '',''
	if xkcd_id == None:
		url = xkcd_rand_comic
	else:
		url = "http://xkcd.com/{}".format(xkcd_id)
	with aiohttp.ClientSession() as session:
		async with session.get(url) as response:
			if response.status == 200:
				data = await response.text()
			pass
	xkcd_match = re.search(r'<div id="ctitle">(?P<title>[\w ]+).*Permanent\slink\sto\sthis\scomic:\s(?P<link>[^<]+).*Image\sURL\s\(for\shotlinking\/embedding\):\s(?P<url>[^ ]+)<div', data, re.S)
	title, url, link = xkcd_match.group("title"), xkcd_match.group("url")[:-1], xkcd_match.group("link")
	await upload_file(url, "xkcd/" + url[28:], ctx.channel, "{} (<{}>)".format(title, link))

# uptime
async def get_uptime(ctx, call, command, args):
	elapsed_time = get_elapsed_time(client.start_time, datetime.utcnow() + utc_offset)
	formatted_time = client.start_time.strftime(time_format)
	await client.send_message(ctx.channel, "```xl\nSnake has been running for {} ({})\n```".format(elapsed_time, formatted_time))

# github :)
async def get_source(ctx, call, command, args):
	await client.send_message(ctx.channel, "https://github.com/TickerOfTime/snake")

# what song is playing
async def get_playing(ctx, call, command, args):
	voice_client = client.voice_client_in(ctx.server)
	if not voice_client == None:
		channel = voice_channels[voice_client]
		if "player" in channel:
			if hasattr(channel["player"], "yt") == True:
				await client.send_message(ctx.channel, ytplayer_info.format(channel["player"], voice_client.channel))
				return
	await client.send_message(ctx.channel, "```xl\nNothing is playing right now\n```")

# list settings
async def list_settings(ctx, call, command, args):
	option = args[0] if len(args) > 0 else None
	setting = Settings.get(option)
	if setting == None:
		await client.send_message(ctx.channel, "```xl\n{}\n```".format("\n".join(Settings.list())))
	else:
		await client.send_message(ctx.channel, "```xl\n'{}' is '{}'\n```".format(option, "on" if setting == True else "off"))

# memes
async def make_meme(ctx, call, command, args):
	meme_name = str(args[0] if len(args) > 0 else None)
	if meme_name.lower() in meme_list:
		text_1 = args[1] if len(args) > 1 else None
		text_2 = args[2] if len(args) > 2 else None
		if (not text_1 == None) and (not text_2 == None):
			url = "http://memegen.link/{}/{}/{}.jpg".format(meme_name.lower(), quote(text_1.replace(" ", "-")), quote(text_2.replace(" ", "-")))
			await upload_file(url, "{}.jpg".format(meme_name.lower()), ctx.channel)
	elif meme_name.lower() in ["list", 'l']:
		result = []
		for K, V in meme_list.items():
			result.append("{} - {}".format(K, V))
			if len(result) > 11:
				await client.send_message(ctx.author, "```xl\n{}\n```".format("\n".join(result)))
				result = []
		await client.send_message(ctx.author, "```xl\n{}\n```".format("\n".join(result)))

# cross server chat
async def cross_server_chat(ctx, call, command, args):
	channel_name = args[0] if len(args) > 0 else None
	message_to_send = args[1] if len(args) > 1 else None
	server_name = args[2] if len(args) > 2 else None
	if (not channel_name == None) and (not message_to_send == None):
		if not server_name == None:
			channel = discord.utils.get(client.get_all_channels(), server__name=server_name, name=channel_name)
		else:
			channel = discord.utils.get(client.get_all_channels(), name=channel_name)
		if channel == None and server_name == None:
			await client.send_message(ctx.channel, "```diff\n- Channel '{}' not found\n```".format(channel_name))
			return
		elif (channel == None) and (not server_name == None):
			await client.send_message(ctx.channel, "```diff\n- Channel '{}' on '{}' not found\n```".format(channel_name, server_name))
			return
		try:
			await client.send_message(channel,"{} - #{}\n**Message from {}#{}:**\n\n{}".format(ctx.server.name,ctx.channel.name,ctx.author.display_name,ctx.author.discriminator,message_to_send))
		except Exception as e:
			await client.send_message(ctx.channel,"```py\n{}: {}\n```".format(type(e).__name__,str(e)))

# get a list of permissions
async def get_permissions(ctx, call, command, args):
	permission_list = ctx.channel.permissions_for(ctx.server.me)
	fmt = lambda x: "yes" if x == True else "no"
	await client.send_message(ctx.channel,permission_info.format(
		fmt(permission_list.create_instant_invite),
		fmt(permission_list.kick_members),
		fmt(permission_list.ban_members),
		fmt(permission_list.manage_channels),
		fmt(permission_list.manage_server),
		fmt(permission_list.read_messages),
		fmt(permission_list.send_messages),
		fmt(permission_list.send_tts_messages),
		fmt(permission_list.manage_messages),
		fmt(permission_list.embed_links),
		fmt(permission_list.attach_files),
		fmt(permission_list.read_message_history),
		fmt(permission_list.mention_everyone),
		fmt(permission_list.connect),
		fmt(permission_list.speak),
		fmt(permission_list.mute_members),
		fmt(permission_list.deafen_members),
		fmt(permission_list.move_members),
		fmt(permission_list.use_voice_activation),
		fmt(permission_list.change_nicknames),
		fmt(permission_list.manage_nicknames),
		fmt(permission_list.manage_roles),
		"is" if permission_list.administrator == True else "is not"
	))

# test
async def test(ctx, call, command, args):
	await client.send_message(ctx.channel, "```py\n{}\n```".format(" ".join(list(map(repr, args)))))

## End commands

"""
```md
[MSG SEND/EDIT][50 / 10 s ]
[MSG SEND/EDIT][ 5 /  5 s  / guild]
[   MSG DELETE][ 5 /  1 s  / guild]
[ROLE EDIT/ADD][10 / 10 s  / guild]
[     NICKNAME][ 1 /  1 s ]
[         NAME][ 2 /  1 hr]
[       STATUS][ 5 /  1 mn]
```
"""

""" #			#
	#			#
	#			#
		Startup
	#			#
	#			#
	#			#
"""

functions = {
	"user": manage_admins,
	"run": eval_code,
	"leave": leave_server,
	"quit": snake_quit,
	"debug": debug_code,
	"clear": remove_self_messages,
	"set": change_setting,
	"playx": manage_players,
	"purge": purge_messages,
	"video": manage_user_videos,
	"play": play_youtube_video,
	"speak": play_speech_data,
	"summon": join_player_voice,
	"help": get_help,
	"insult": get_insult,
	"invite": get_oauth_link,
	"info": get_object_info,
	"docs": get_object_docs,
	"tag": manage_user_tags,
	"game":change_snake_game,
	"xkcd":get_xkcd_comic,
	"uptime": get_uptime,
	"source": get_source,
	"playing": get_playing,
	"list": list_settings,
	"meme": make_meme,
	"chat": cross_server_chat,
	"permissions": get_permissions,


	"test": test
}

@client.event
async def on_ready():
	print("{0.green}Logged in as {0.cyan}{1.user.name}{2.off}#{0.yellow}{1.user.discriminator}{2.off} [{1.user.id}]".format(Text, client, Attributes))
	if hasattr(client, "start_time") == False:
		client.start_time = datetime.utcnow() + utc_offset

	global voice_count, private_count, server_count, channel_count
	voice_count = 0
	private_count = len(list(client.private_channels))
	server_count = len(client.servers)
	channel_count = 0
	for channel in client.get_all_channels():
		if channel.type == discord.ChannelType.text:
			channel_count += 1
		elif channel.type == discord.ChannelType.voice:
			voice_count += 1
	print("{0.cyan}Connected to {1} voice and {2} text channels ({3} total) on {4} servers and {5} private channels{6.off}".format(Text, voice_count, channel_count, voice_count + channel_count, server_count, private_count, Attributes))
	update_server_list(client.servers, print_channel)
	print("\n\n")
	for channel in client.private_channels:
		print_private_channel(channel)

@client.event
async def on_server_join(server):
	print("{0.green}Joined server {0.cyan}{1.name}{0.green}, owned by {0.cyan}{1.owner.name}{2.off}#{0.yellow}{1.owner.discriminator}{2.off}".format(Text, server, Attributes))
	update_server_list([server], print_channel)

@client.event
async def on_server_remove(server):
	print("{0.red}Left server {0.cyan}{1.name}{0.red}, owned by {0.cyan}{1.owner.name}{2.off}#{0.yellow}{1.owner.discriminator}{2.off}".format(Text, server, Attributes))

@client.event
async def on_channel_created(channel):
	if channel.is_private == True:
		print("{0.green}Started a PM with {0.cyan}{1.name}{2.off}#{0.yellow}{1.discriminator}{2.off}".format(Text, channel, Attributes))
		print_private_channel(channel)
	else:
		print("{0.green}Joined channel {0.cyan}{1.name}{0.green} in {0.cyan}{1.server.name}{2.off}".format(Text, channel, Attributes))
		print_channel(channel)
	
@client.event
async def on_channel_delete(channel):
	print("{0.red}Left channel {0.cyan}{1.name}{0.red} in {0.cyan}{1.server.name}{2.off}".format(Text, channel, Attributes))

@client.event
async def on_message(message):
	if message.author == client.user or message.author.bot == True:
		return
	await log_message(message)
	if message.content.lower().startswith("snake"):
		args = parse_commands(message.content)
		for user_mention in message.mentions:
			mention_text = "<@!{}>".format(user_mention.id)
			if mention_text not in args:
				mention_text = "<@{}>".format(user_mention.id)
			args[args.index(mention_text)] = user_mention# parse user mentions
		for channel_mention in message.channel_mentions:
			mention_text = "<#{}>".format(channel_mention.id)
			if mention_text in args:
				args[args.index(mention_text)] = channel_mention# parse channel mentions
		for role_mention in message.role_mentions:
			mention_text = "<@&{}>".format(role_mention.id)
			if mention_text in args:
				args[args.index(mention_text)] = role_mention# parse role mentions

		call = args[0]
		command = args[1] if len(args) > 1 else None
		command_args = [] if len(args) < 3 else args[2:]
		if not command == None:
			if command.lower() in functions:
				await functions[command.lower()](message, call, command, command_args)
			elif Settings.get("enable_ai") == True:
				response = await talk_pandora(message.author, " ".join(args[1:]))
				if not response == None:
					await client.send_message(message.channel, response)

token_file = open("token.txt", 'r')
token = str(token_file.read())
token_file.close()

client.run(token)
temp_db.close()
log_db.close()