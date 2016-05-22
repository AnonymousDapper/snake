""" Discord API Snake bot """

"""
MIT License

Copyright (c) 2016 █▀█ █▄█ █ █ ² (AnonymousDapper) (TickerOfTime)

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

import discord, re, requests, random, time, sys, io, asyncio, youtube_dl, os
import sqlite3 as sql
from datetime import datetime, timedelta
from urllib.parse import quote

# discord: pip install --upgrade https://github.com/Rapptz/discord.py/archive/async.zip
# youtube_dl: pip install --upgrade youtube_dl
# sqlite3 pip install --upgrade sqlite3

sys.stdout = io.TextIOWrapper(sys.stdout.detach(), encoding = sys.stdout.encoding, errors = "xmlcharrefreplace", line_buffering = True) # Handle printing of Unicode chars.. ugh

class fg:
	black = '\033[30m'
	red = '\033[31m'
	green = '\033[32m'
	yellow = '\033[33m'
	blue = '\033[34m'
	magenta = '\033[35m'
	cyan = '\033[36m'
	white = '\033[37m'
	default = '\033[37m'

class bg:
	black = '\033[40m'
	red = '\033[41m'
	green = '\033[42m'
	yellow = '\033[43m'
	blue = '\033[44m'
	magenta = '\033[45m'
	cyan = '\033[46m'
	white = '\033[47m'
	default = '\033[40m'

class txt:
	off = '\033[0m'
	bold = '\033[1m'
	score = '\033[4m'
	blink = '\033[5m'
	reverse = '\033[7m'
	hidden = '\033[8m'

# Above is terminal color code classes. Sorry if you're  using default windows cmd

client = discord.Client()
opus_loaded = discord.opus.is_loaded() # screws the entire playx system if its not

class ElapsedTime():
	def __init__(self, elapsed_object):
		self.years = elapsed_object["years"]
		self.months = elapsed_object["months"]
		self.weeks = elapsed_object["weeks"]
		self.days = elapsed_object["days"]
		self.hours = elapsed_object["hours"]
		self.minutes = elapsed_object["minutes"]
		self.seconds = elapsed_object["seconds"]


# Constant variables and reused stuff
help_docs = '''
```xl
User ** <a/r/l> [@Mention]    => adds or removes user as admin
Eval ** <code>                => execute code
Leave ** <server>             => leaves the server
Quit **                       => exits snake

Clear * <count>               => removes snakes messages
Set * <settingname> <option>  => change settings
Playx * <j/l/m/s/p/r/v> [opt] => voice control
Video * <s/l/d> [name] [id]   => manage stored videos

Play  <url/id/sid> [channel]  => play a yt video in the channel
Speak <text> [channel]        => speaks the text in <channel>
Summon                        => bring snake to your voice channel
Help                          => displays this help page

Insult [@Mention]+            => insult people
Invite [invitecode]           => lets you add snake
Whois [@Mention/server]       => gets info. defaults to speaker
Docs <obj>                    => returns discord.py docs for obj

Notes <g/l/d/a> <name> <data> => manage notes
Game [gamename]               => makes snake play the game
Xkcd                          => get a random xkcd comic
Uptime                        => see how long snake has been up

Info                          => view info about snake
Source                        => get snakes source code
Playing                       => see the song thats playing
List [setting]                => show value of setting(s)

Meme <name> <text> <text>     => make a meme
Chat <chan> <msg> [server]    => chat on different server
Permissions                   => list snakes permissions


* Admin only
** Owner only
```'''

client_info = '''
```xl
WHOIS

    Name => {0.name}#{0.discriminator}
      ID => {0.id}
  Avatar => {0.avatar_url}
    Nick => {0.display_name}#{0.discriminator}
 Created => {1}
  Uptime => {2}
Channels => {3}
 Servers => {4}

Running discord.py {5} on Python {6}

Written by █▀█ █▄█ █ █#7467 [163521874872107009]
```'''

user_info = '''
```xl
WHOIS

   Name => {0.name}#{0.discriminator}
     ID => {0.id}
 Avatar => {0.avatar_url}
   Nick => {0.display_name}#{0.discriminator}
 Status => {0.status}
   Game => {5}
  Roles => {2}
    Bot => {1}
Created => {3}
 Joined => {4}
```'''

server_info = '''
```xl
WHOIS

    Name => {0.name}
      ID => {0.id}
  Region => {0.region}
 Members => {1}
Channels => {2}
   Owner => {0.owner.name}#{0.owner.discriminator}
 Created => {3}
    Icon => {0.icon_url}
   Roles => {4}
```'''

ytdl_info_str = '''
```xl
Playing "{0.title}" by "{0.uploader}" in {1.name}
```'''

permission_info_str = '''
```xl
Snake {22} an Administrator.

      Create Invites => {0}
        Kick Members => {1}
         Ban Members => {2}
     Manage Channels => {3}
       Manage Server => {4}
       Read Messages => {5}
       Send Messages => {21}
   Send TTS Messages => {6}
     Manage Messages => {7}
         Embed Links => {8}
        Attach Files => {9}
Read Message History => {10}
    Mention Everyone => {11}
    Connect To Voice => {12}
      Speak In Voice => {13}
        Mute Members => {14}
      Deafen Members => {15}
        Move Members => {16}
  Use Voice Activity => {17}
    Change Nicknames => {18}
    Manage Nicknames => {19}
        Manage Roles => {20}
```'''

challenge_info_str = '''
__**New Challenge!**__
**{0}**:

{1}

- {2}

Allowed languages for this challenge are ({3})
'''

base_docs_url = "http://discordpy.readthedocs.io/en/latest/api.html#"

time_format_str = "%a %B %d, %Y, %H:%M:%S"

xkcd_rand = "http://c.xkcd.com/random/comic/"

# Init database and management stuff
temp_db = sql.connect(":memory:") # creates temp database in ram
temp_dbcur = temp_db.cursor()
log_db = sql.connect("snake.db")
log_dbcur = log_db.cursor()

servers = {}
tags = {} # keep the sql queries down
replies = {} # this'll be fun to manage
reminders = {}
voice_channels = {}
challenge_admins = ["153237408467517441","163521874872107009"]
allowed_language_list = ["Lua 5.3", "Python 3.5"]
meme_list = {
	"tenguy": "10 Guy",
	"afraid": "Afraid to Ask Andy",
	"older": "An Older Code Sir, But It Checks Out",
	"aag": "Ancient Aliens Guy",
	"tried": "At Least You Tried",
	"biw": "Baby Insanity Wolf",
	"blb": "Bad Luck Brian",
	"kermit": "But That's None of My Business",
	"bd": "Butthurt Dweller",
	"ch": "Captain Hindsight",
	"cbg": "Comic Book Guy",
	"wonka": "Condescending Wonka",
	"cb": "Confession Bear",
	"keanu": "Conspiracy Keanu",
	"dsm": "Dating Site Murderer",
	"live": "Do It Live!",
	"ants": "Do You Want Ants?",
	"doge": "Doge",
	"alwaysonbeat": "Drake Always On Beat",
	"ermg": "Ermahgerd",
	"fwp": "First World Problems",
	"fa": "Forever Alone",
	"fbf": "Foul Bachelor Frog",
	"fmr": "Fuck Me, Right?",
	"fry": "Futurama Fry",
	"ggg": "Good Guy Greg",
	"hipster": "Hipster Barista",
	"icanhas": "I Can Has Cheezburger?",
	"crazypills": "I Feel Like I'm Taking Crazy Pills",
	"regret": "I Immediately Regret This Decision!",
	"boat": "I Should Buy a Boat Cat",
	"sohappy": "I Would Be So Happy",
	"captain": "I am the Captain Now",
	"inigo": "Inigo Montoya",
	"iw": "Insanity Wolf",
	"ackbar": "It's A Trap!",
	"happing": "It's Happening",
	"joker": "It's Simple, Kill the Batman",
	"ive": "Jony Ive Redesigns Things",
	"ll": "Laughing Lizard",
	"morpheus": "Matrix Morpheus",
	"badchoice": "Milk Was a Bad Choice",
	"mmm": "Minor Mistake Marvin",
	"jetpack": "Nothing To Do Here",
	"red": "Oh, Is That What We're Going to Do Today?",
	"mordor": "One Does Not Simply Walk into Mordor",
	"oprah": "Oprah You Get a Car",
	"oag": "Overlay Attached Girlfriend",
	"remembers": "Pepperidge Farm Remembers",
	"philosoraptor": "Philosoraptor",
	"jw": "Probably Not a Good Idea",
	"sadfrog": "Sad Frog ",
	"sarcasticbear": "Sarcastic Bear",
	"dwight": "Schrute Facts",
	"sb": "Scumbag Brain",
	"ss": "Scumbag Steve",
	"sf": "Sealed Fate",
	"dodgson": "See? Nobody Cares",
	"sohot": "So Hot Right Now",
	"awesome": "Socially Awesome Penguin",
	"awkward": "Socially Awkward Penguin",
	"fetch": "Stop Trying to Make Fetch Happen",
	"success": "Success Kid",
	"ski": "Super Cool Ski Instructor",
	"officespace": "That Would Be Great",
	"interesting": "The Most Interesting Man in the World",
	"toohigh": "The Rent Is Too Damn High",
	"bs": "This is Bull, Shark",
	"both": "Why Not Both?",
	"winter": "Winter is coming",
	"xy": "X all the Y",
	"buzz": "X, X Everywhere",
	"yodawg": "Xzibit Yo Dawg",
	"yuno": "Y U NO Guy",
	"yallgot": "Y'all Got Any More of Them",
	"bad": "You Should Feel Bad",
	"elf": "You Sit on a Throne of Lies",
	"chosen": "You Were the Chosen One!"
}
face_list = {
  "( ͡° ͜ʖ ͡°)",
  "¯\_(ツ)_/¯",
  "̿̿ ̿̿ ̿̿ ̿'̿'\̵͇̿̿\з= ( ▀ ͜͞ʖ▀) =ε/̵͇̿̿/’̿’̿ ̿ ̿̿ ̿̿ ̿̿",
  "▄︻̷̿┻̿═━一",
  "ʕ•ᴥ•ʔ",
  "( ͡°( ͡° ͜ʖ( ͡° ͜ʖ ͡°)ʖ ͡°) ͡°)",
  "(▀̿Ĺ̯▀̿ ̿)",
  "(ง ͠° ͟ل͜ ͡°)ง",
  "༼ つ ◕_◕ ༽つ",
  "ಠ_ಠ",
  "(づ｡◕‿‿◕｡)づ",
  "[̲̅$̲̅(̲̅5̲̅)̲̅$̲̅]",
  "(ﾉ◕ヮ◕)ﾉ*:･ﾟ✧ ✧ﾟ･: *ヽ(◕ヮ◕ヽ)",
  "┬┴┬┴┤ ͜ʖ ͡°) ├┬┴┬┴",
  "̿'̿'\̵͇̿̿\з=( ͠° ͟ʖ ͡°)=ε/̵͇̿̿/'̿̿ ̿ ̿ ̿ ̿ ̿",
  "(ง'̀-'́)ง",
  "(• ε •)",
  "(͡ ͡° ͜ つ ͡͡°)",
  "(ಥ﹏ಥ)",
  "(ノಠ益ಠ)ノ彡┻━┻",
  "[̲̅$̲̅(̲̅ ͡° ͜ʖ ͡°̲̅)̲̅$̲̅]",
  "﴾͡๏̯͡๏﴿ O'RLY?",
  "(ﾉ◕ヮ◕)ﾉ*:･ﾟ✧",
  "(¬‿¬)",
  "(☞ﾟ∀ﾟ)☞",
  "(◕‿◕✿)",
  "(ᵔᴥᵔ)",
  "(☞ﾟヮﾟ)☞ ☜(ﾟヮﾟ☜)",
  "(╯°□°)╯︵ ʞooqǝɔɐɟ",
  "ლ(ಠ益ಠლ)",
  "(づ￣ ³￣)づ",
  "| (• ◡•)| (❍ᴥ❍ʋ)",
  "♥‿♥",
  "ಠ╭╮ಠ",
  "♪~ ᕕ(ᐛ)ᕗ",
  "/╲/\╭( ͡° ͡° ͜ʖ ͡° ͡°)╮/\╱\\",
  "(;´༎ຶД༎ຶ`)",
  "༼ つ ಥ_ಥ ༽つ",
  "(╯°□°）╯︵ ┻━┻",
  "̿ ̿ ̿'̿'\̵͇̿̿\з=(•_•)=ε/̵͇̿̿/'̿'̿ ̿",
  "( ͡°╭͜ʖ╮͡° )",
  "༼ つ ͡° ͜ʖ ͡° ༽つ",
  "◉_◉",
  "~(˘▾˘~)",
  "ヾ(⌐■_■)ノ♪",
  "( ͡ᵔ ͜ʖ ͡ᵔ )",
  "\ (•◡•) /",
  "(~˘▾˘)~",
  "(._.) ( l: ) ( .-. ) ( :l ) (._.)",
  "༼ ºل͟º ༼ ºل͟º ༼ ºل͟º ༽ ºل͟º ༽ ºل͟º ༽",
  "༼ʘ̚ل͜ʘ̚༽",
  "┬┴┬┴┤(･_├┬┴┬┴",
  "ᕙ(⇀‸↼‶)ᕗ",
  "┻━┻ ︵ヽ(`Д´)ﾉ︵ ┻━┻",
  "⚆ _ ⚆",
  "ᕦ(ò_óˇ)ᕤ",
  "(｡◕‿‿◕｡)",
  "ಥ_ಥ",
  "(•_•) ( •_•)>⌐■-■ (⌐■_■)",
  "⌐╦╦═─",
  "(｡◕‿◕｡)",
  "ヽ༼ຈل͜ຈ༽ﾉ",
  "(☞ຈل͜ຈ)☞",
  "(•ω•)",
  "☜(˚▽˚)☞",
  "（╯°□°）╯︵( .o.)",
  "(ง°ل͜°)ง",
  "˙ ͜ʟ˙",
  "┬──┬ ノ( ゜-゜ノ)",
  "(°ロ°)☝",
  "ಠ⌣ಠ",
  "ლ(´ڡ`ლ)",
  "(っ˘ڡ˘ς)",
  "｡◕‿‿◕｡",
  "╚(ಠ_ಠ)=┐",
  "( ಠ ͜ʖರೃ)",
  "(─‿‿─)",
  "(¬_¬)",
  "(；一_一)",
  "( ⚆ _ ⚆ )",
  "｡◕‿◕｡",
  "(ʘᗩʘ')",
  "ლ,ᔑ•ﺪ͟͠•ᔐ.ლ",
  "ƪ(˘⌣˘)ʃ",
  "Ƹ̵̡Ӝ̵̨̄Ʒ",
  "(ʘ‿ʘ)",
  "¯\(°_o)/¯",
  "☜(⌒▽⌒)☞",
  "ಠ‿↼",
  "ಠ_ಥ",
  "(´・ω・`)",
  "┬─┬ノ( º _ ºノ)",
  "ʘ‿ʘ",
  "(´・ω・)っ由",
  "ಠ~ಠ",
  "(° ͡ ͜ ͡ʖ ͡ °)",
  "(>ლ)",
  "ರ_ರ",
  "ಠoಠ",
  "(✿´‿`)",
  "◔̯◔",
  "(▰˘◡˘▰)",
  "(ღ˘⌣˘ღ)",
  "¬_¬",
  "｡゜(｀Д´)゜｡",
  "ب_ب",
  "◔ ⌣ ◔",
  "(ó ì_í)=óò=(ì_í ò)",
  "°Д°",
  "( ﾟヮﾟ)",
  "┬─┬﻿ ︵ /(.□. ）",
  "☼.☼",
  "≧☉_☉≦",
  ":')",
  "^̮^",
  "٩◔̯◔۶",
  "(>人<)",
  "〆(・∀・＠)",
  "(/) (°,,°) (/)",
  "(~_^)",
  "(･.◤)",
  "^̮^",
  "(^̮^)",
  "=U",
  "^̮^",
  ">_>",
  "^̮^",
  "^̮^",
}
settings = {
	"enable_ai": False,
	"notify_on_exit": True,
	"notify_channel": False
}

pb_bot_id = "b0dafd24ee35a477" # Chomsky
my_id = "163521874872107009" # My userid

utc_offset = timedelta(hours=-5)
seconds_in_year = 31536000
seconds_in_month = 2592000
seconds_in_week = 606461.538462 # date conversion, why'd i reinvent the wheel?
seconds_in_day = 86400
seconds_in_hour = 3600
seconds_in_minute = 60

server_count = 0
channel_count = 0
text_channel_count = 0
voice_channel_count = 0
private_channel_count = 0

temp_dbcur.execute("CREATE TABLE pb_ids (user_id TEXT, cust_id TEXT)")
temp_db.commit()

log_dbcur.execute("SELECT * FROM user_tags")
log_db.commit()
user_tags = log_dbcur.fetchall()
for tag_set in user_tags:
	tags[tag_set[0]] = {"name": tag_set[0], "owner": tag_set[2], "content": tag_set[1]} # load all existing tags into the dict, so we can save on queries

## Helper functions

# split for commands, shlex is picky
def parse(message, quotes="'\"`",whitespace=" 	"):
	tracker = [""]
	point = 0
	in_quotes = None
	for token in message:
		if token in quotes:
			if in_quotes == None:
				in_quotes = token
			elif token == in_quotes:
				in_quotes = None
				tracker.append("")
				point += 1
			else:
				tracker[point] += token
		elif token in whitespace:
			if not in_quotes == None:
				tracker[point] += token
			else:
				tracker.append("")
				point += 1
		else:
			tracker[point] += token
	return list(filter(lambda x:len(x) > 0, tracker))

# log it
async def log_message(message):
	message_time = message.timestamp + utc_offset
	message_data = (message_time.strftime(time_format_str), message.author.name, message.content, message.channel.name if message.channel.is_private == False else "@" + message.channel.user.name, message.id, message.server.name if message.channel.is_private == False else "PM: " + message.channel.user.name, message.author.id)
	log_dbcur.execute("INSERT INTO chat_logs VALUES (?,?,?,?,?,?,?)", message_data)
	log_db.commit()

# Talk to pandorabots AI
def pb_talk(user,message):
	response = None
	temp_dbcur.execute("SELECT cust_id FROM pb_ids WHERE user_id=?", (user.id,))
	temp_db.commit()
	result = temp_dbcur.fetchone()
	if result == None:
		pb_response = requests.post("http://www.pandorabots.com/pandora/talk-xml", {"botid": pb_bot_id, "input": message})
		response_data = re.search(r'<result status="(?P<status>\d*)" botid="(?P<botid>\w+)" custid="(?P<custid>\w+)">\s*<input>[\w ]+</input>\s*<that>(?P<response>.*)</that>', str(pb_response.content), re.I)
		if not response_data == None:
			cust_id, response = response_data.group("custid"), response_data.group("response")
			temp_dbcur.execute("INSERT INTO pb_ids VALUES(?,?)", (user.id, cust_id))
			temp_db.commit()
	else:
		pb_response = requests.post("http://www.pandorabots.com/pandora/talk-xml", {"botid": pb_bot_id, "input": message, "custid": result})
		response_data = re.search(r'<result status="(?P<status>\d*)" botid="(?P<botid>\w+)" custid="(?P<custid>\w+)">\s*<input>[\w ]+</input>\s*<that>(?P<response>.*)</that>', str(pb_response.content), re.I)
		if not response_data == None:
			response = response_data.group("response")
	return response

# is admin?
def user_is_admin(userid):
	log_dbcur.execute("SELECT * FROM allowed_users WHERE user_id=?", (userid,))
	log_db.commit()
	result = log_dbcur.fetchone()
	if not result == None:
		return True
	else:
		return False

# send a message to a chatbot
def get_elapsed_time(date1,date2):
	time_delta = abs(date2 - date1)
	seconds = int(time_delta.total_seconds())
	elapsed = []
	def desc(n,h):
		n = int(n)
		return ("a" if n == 1 else str(n)) + ("n" if h == 1 and n == 1 else "") + ""
	def pl(n):
		return "s" if n > 1 or n == 0 else ""
	years = (seconds // seconds_in_year) # Get years
	elapsed.append("{} year{}".format(desc(years,0), pl(years)))
	seconds = seconds - (years * seconds_in_year)
	months = (seconds // seconds_in_month) # Get months
	elapsed.append("{} month{}".format(desc(months,0), pl(months)))
	seconds = seconds - (months * seconds_in_month)
	weeks = (seconds // seconds_in_week) # Get weeks
	elapsed.append("{} week{}".format(desc(weeks,0), pl(weeks)))
	seconds = seconds - (weeks * seconds_in_week)
	days = (seconds //seconds_in_day) # Get days
	elapsed.append("{} day{}".format(desc(days,0), pl(days)))
	seconds = seconds - (days * seconds_in_day)
	hours = (seconds // seconds_in_hour) # Get hours
	elapsed.append("{} hour{}".format(desc(hours,1), pl(hours)))
	seconds = seconds - (hours * seconds_in_hour)
	minutes = (seconds // seconds_in_minute) # Get minutes
	elapsed.append("{} minute{}".format(desc(minutes,0), pl(minutes)))
	seconds = seconds - (minutes * seconds_in_minute)
	elapsed.append("{} second{}".format(desc(seconds,0), pl(seconds))) # Get seconds
	return list(filter(lambda x:not x.startswith("0 "),elapsed))

# upload an image or other file directly
async def upload_file(url,file_name,channel,content=""):
	tmp = open("cache/" + file_name,"wb")
	data = requests.get(url).content
	tmp.write(data)
	tmp.close()
	try:
		await client.send_file(channel,"cache/" + file_name,filename=file_name,content=content)
	except Exception as e:
		print("{}{}: {}{}".format(fg.red,type(e).__name__,str(e),txt.off))
	tmp.close()

# get dectalk speech data and send it, hacky i guess
def speak(message,server_id):
	os.chdir("dectalk")
	os.system("say.exe -w say.wav \"{}\"".format(message.replace("\n","")))
	try:
		voice_channels[server_id]["ffmpeg_player"] = voice_channels[server_id]["voice_client"].create_ffmpeg_player("say.wav")
		os.chdir("..")
	except Exception as e:
		os.chdir("..")
		return e
	return True

# duh
async def join_voice_channel(channel):
	if channel.is_private == False and channel.type == discord.ChannelType.voice:
		if channel.server.id not in voice_channels:
			voice_channels[channel.server.id] = {"channel":channel, "voice_client":await client.join_voice_channel(channel)}
			return voice_channels[channel.server.id]
		return voice_channels[channel.server.id]
	else:
		return False

#also duh
async def leave_voice_channel(channel):
	if channel.is_private == False and channel.type == discord.ChannelType.voice:
		if channel.server.id in voice_channels:
			if 'yt_player' in voice_channels[channel.server.id]:
				voice_channels[channel.server.id]["yt_player"].stop()
				await voice_channels[channel.server.id]["voice_client"].disconnect()
				del voice_channels[channel.server.id]
				return True
			elif 'ffmpeg_player' in voice_channels[channel.server.id]:
				voice_channels[channel.server.id]["ffmpeg_player"].stop()
				await voice_channels[channel.server.id]["voice_client"].disconnect()
				del voice_channels[channel.server.id]
				return True
			else:
				await voice_channels[channel.server.id]["voice_client"].disconnect()
				del voice_channels[channel.server.id]
				return True
		return True
	return True

# `voice_client.move_to` doesn't work right, so we have to hack this together
async def change_voice_channel(channel):
	if channel.is_private == False and channel.type == discord.ChannelType.voice:
		if channel.server.id in voice_channels:
			channel_from = voice_channels[channel.server.id]
			if await leave_voice_channel(channel_from["channel"]) == True:
				if await join_voice_channel(channel) == True:
					return voice_channels[channel.server.id]
				else:
					return False
			else:
				return False
		return False
	return False

# is something being played or spoken?
def get_currently_playing(server_id):
	if server_id in voice_channels:
		channel = voice_channels[server_id]
		if 'yt_player' in channel:
			return [channel["yt_player"],channel]
		elif 'ffmpeg_player' in channel:
			return [channel["ffmpeg_player"],channel]

# manage saved vids
def manage_videos(action,yt_id="",name=""):
	if action == "save":
		log_dbcur.execute("SELECT * FROM youtube_videos WHERE id=?",(yt_id,))
		if log_dbcur.fetchone() == None:
			log_dbcur.execute("INSERT INTO youtube_videos VALUES (?,?)",(name,yt_id))
			log_db.commit()
	elif action == "remove":
		log_dbcur.execute("SELECT * FROM youtube_videos WHERE id=?",(yt_id,))
		if not log_dbcur.fetchone() == None:
			log_dbcur.execute("DELETE FROM youtube_videos WHERE id=?",(yt_id,))
		log_db.commit()
	elif action == "load":
		log_dbcur.execute("SELECT * FROM youtube_videos WHERE save_name=?",(name,))
		log_db.commit()
		d = log_dbcur.fetchone()
		return d
	elif action == "list":
		log_dbcur.execute("SELECT * FROM youtube_videos")
		result = []
		for tup in log_dbcur.fetchall():
			result.append([tup[0],tup[1]])
		log_db.commit()
		return result

# show list of all connected servers
def update_servers():
	global server_count,channel_count,private_channel_count,text_channel_count,voice_channel_count
	server_count,channel_count,private_channel_count,text_channel_count,voice_channel_count = 0,0,0,0,0
	for server in client.servers:
		server_count += 1
		for channel in server.channels:
			channel_count += 1
	print("{}Connected to {} servers, joining {} channels, {} of which are private{}".format(fg.cyan, len(client.servers), channel_count, len(client.private_channels), txt.off))
	for server in client.servers:
		print("\n{}{} {}[{}] {}({}{}#{}{}){}".format(fg.green, server.name, txt.off, server.id, fg.cyan, server.owner.name, txt.off, fg.yellow,server.owner.discriminator, txt.off))
		servers[server.name] = {"server": server, "channels": {}}
		for channel in server.channels:
			if channel.type == discord.ChannelType.voice:
				voice_channel_count += 1
			else:
				text_channel_count += 1
			print("{} -- {}{} {}[{}]{}".format(fg.blue, fg.red if channel.type == discord.ChannelType.voice else fg.cyan, channel.name, fg.magenta if channel.type == discord.ChannelType.voice else fg.yellow, channel.id, txt.off))
			servers[server.name]["channels"][channel.name] = channel
	print("\n\n")
	servers["private_channels"] = {}
	for channel in client.private_channels:
		private_channel_count += 1
		print("{}@{}{} {}[{}]{}".format(fg.green, txt.off, channel.user.name, fg.cyan, channel.id, txt.off))
		servers["private_channels"][channel.user.name] = channel

## Commands

# rip
async def snake_quit(message,call,cmd,args):
	if message.author.id == my_id:
		if settings["notify_on_exit"] == True:
			await client.send_message(message.channel, "rip {}".format(call))
		await client.logout()

# change a setting value
async def change_settings(message,call,cmd,args):
	if user_is_admin(message.author.id):
		setting = args[0] if len(args) > 0 else None
		option = args[1] if len(args) > 0 else "None"
		if setting in settings:
			if option.lower() == "on":
				settings[setting] = True
				await client.send_message(message.author, "Turned '{}' on".format(setting))
			elif option.lower() == "off":
				settings[setting] = False
				await client.send_message(message.author, "Turned '{}' off".format(setting))
			else:
				await client.send_message(message.author, "Unknown setting or option: '{}'; '{}'".format(setting, option))

# change admin status
async def toggle_user(message,call,cmd,args):
	if message.author.id == my_id:
		user = message.mentions[0] if len(message.mentions) > 0 else None
		option = args[0] if len(args) > 0 else "None"
		
		if not user == None:
			is_admin = user_is_admin(user.id)
			if option.lower() in ['remove','r']:
				if is_admin:
					log_dbcur.execute("DELETE FROM allowed_users WHERE user_id=?", (user.id,))
					await client.send_message(message.author, "Removed admin '{}'".format(user.name + "#" + user.discriminator))
					log_db.commit()
			elif option.lower() == ['a','add']:
				if not is_admin:
					log_dbcur.execute("INSERT INTO allowed_users VALUES (?,?)", (user.id,user.name + "#" + user.discriminator))
					await client.send_message(message.author, "Added admin '{}'".format(user.name + "#" + user.discriminator))
					log_db.commit()

		elif option.lower() in ['l','list','show']:
				result = []
				log_dbcur.execute("SELECT * FROM allowed_users")
				for tup in log_dbcur.fetchall():
					result.append("{} [{}]".format(tup[1],tup[0]))
				log_db.commit()
				await client.send_message(message.channel,"```xl\n{}\n```".format("\n".join(result)))
				return
		else:
			await client.send_message(message.author, "User is not found")

# print helpdocs
async def get_help(message,call,cmd,args):
	await client.send_message(message.channel, help_docs.format(call))			

# oauth link
async def get_oauth_url(message,call,cmd,args):
	await client.send_message(message.author, "Click this link and add me to your server!\nhttps://discordapp.com/oauth2/authorize?&client_id=181584771510566922&scope=bot")

# user (or server) info
async def get_info(message,call,cmd,args):
	arg = args[0] if len(args) > 0 else message.author
	user = message.mentions[0] if len(message.mentions) > 0 else arg
	if str(arg).lower() == "server":
		members = message.server.members
		channels = message.server.channels
		text_channel_count,voice_channel_count = 0,0
		for channel in channels:
			if channel.type == discord.ChannelType.text:
				text_channel_count += 1
			elif channel.type == discord.ChannelType.voice:
				voice_channel_count += 1
		await client.send_message(message.channel, server_info.format(
			message.server,
			"{} member{}".format(len(members), "s" if len(members) > 1 or len(members) == 0 else ""),
			"{} text channel{}, {} voice channel{}".format(text_channel_count, "s" if text_channel_count > 1 or text_channel_count == 0 else "", voice_channel_count, "s" if voice_channel_count > 1 or voice_channel_count == 0 else ""),
			"{} ago ({})".format(", ".join(get_elapsed_time(message.server.created_at + utc_offset,datetime.utcnow() + utc_offset)), (message.server.created_at + utc_offset).strftime(time_format_str)),
			", ".join(map(lambda x:str(x)[1::] if str(x).startswith("@") else str(x), message.server.roles))
		))
	else:
		await client.send_message(message.channel, user_info.format(
			user, 
			"Yes" if user.bot == True else "No?", 
			", ".join(map(lambda x:str(x)[1::] if str(x).startswith("@") else str(x), user.roles)), 
			"{} ago ({})".format(", ".join(get_elapsed_time(user.created_at + utc_offset,datetime.utcnow() + utc_offset)), (user.created_at + utc_offset).strftime(time_format_str)), 
			"{} ago ({})".format(", ".join(get_elapsed_time(user.joined_at + utc_offset,datetime.utcnow() + utc_offset)), (user.joined_at + utc_offset).strftime(time_format_str)),
			"Not playing a game" if user.game == None else user.game.name
		))

# find docs page for discord.py given obj name
async def get_docs_url(message,call,cmd,args):
	if len(args) > 0:
		obj = args[0]
		await client.send_message(message.channel, "{}discord.{}{}".format(base_docs_url, obj[0].upper(), obj[1::]))
	else:
		await client.send_message(message.channel, base_docs_url)

# insults :)
async def get_insult(message,call,cmd,args):
	destinations = message.mentions if len(message.mentions) > 0 else [message.channel]
	for destination in destinations:
		insult = re.search(r'<div class="wrap">\\n\\n<br><br>(.+)</div>', str(requests.get("http://www.insultgenerator.org/").content), re.I).group(1)
		await client.send_message(destination, insult)

# manage notes (tags)
async def edit_tags(message,call,cmd,args): # get/list/edit/remove/create
	method = args[0] if len(args) > 0 else None
	tagname = args[1] if len(args) > 1 else None
	content = args[2] if len(args) > 2 else None
	if not method == None:
		result = "**{}**:\n\n{}\n"
		method = method.lower()
		if method in ['list','l']:
			log_dbcur.execute("SELECT * FROM user_tags")
			temp_res = []
			for tag in log_dbcur.fetchall():
				if tag[2] == message.author.id:
					temp_res.append("^'" + tag[0] + "'")
				else:
					temp_res.append("'" + tag[0] + "'")
			await client.send_message(message.channel, result.format("All saved notes", "```xl\n" + ", ".join(temp_res) + "\n```"))
		elif method in ['get','g']:
			if not tagname == None:
				log_dbcur.execute("SELECT * FROM user_tags WHERE tag_name=?", (tagname,))
				tag = log_dbcur.fetchone()
				if not tag == None:
					await client.send_message(message.channel, result.format(tagname, tag[1]))
		elif method in ['add','a']:
			if (not tagname == None) and (not content == None):
				log_dbcur.execute("SELECT * FROM user_tags WHERE tag_name=?", (tagname,))
				if log_dbcur.fetchone() == None:
					log_dbcur.execute("INSERT INTO user_tags VALUES (?,?,?)", (tagname, content, message.author.id))
				else:
					await client.send_message(message.author,"The note '{}' already exists".format(tagname))
		elif method in ['edit','e']:
			if (not tagname == None) and (not content == None):
				log_dbcur.execute("SELECT * FROM user_tags WHERE tag_name=? AND tag_owner=?", (tagname,message.author.id))
				if not log_dbcur.fetchone() == None:
					log_dbcur.execute("UPDATE user_tags SET tag_name=?,tag_content=?,tag_owner=?", (tagname, content, message.author.id))
				else:
					await client.send_message(message.author,"The note '{}' does not exist or is not owned by you".format(tagname))
		elif method ['del','d']:
			if (not tagname == None):
				log_dbcur.execute("SELECT * FROM user_tags WHERE tag_name=? AND tag_owner=?", (tagname,message.author.id))
				if not log_dbcur.fetchone() == None:
					log_dbcur.execute("DELETE FROM user_tags WHERE tag_name=?", (tagname,))
				else:
					await client.send_message(message.author,"The note '{}' does not exist or is not owned by you".format(tagname))
		log_db.commit()

# whats he playing?
async def change_game(message,call,cmd,args):
	game_name = args[0] if len(args) > 0 else None
	game = None
	if not game_name == None:
		game = discord.Game(name=game_name,url=game_name,type=0)

	await client.change_status(game=game, idle=False)

# needs lots of perms, need to fix
async def remove_snake_messages(message,call,cmd,args):
	count = args[0] if len(args) > 0 else None
	if (user_is_admin(message.author.id) == True) and (not count == None):
		point = 0
	#	messages = []
		count = int(count)
		async for message in client.logs_from(message.channel):
			if message.author == client.user:
				if point < count:
					#if count > 2 and count < 100:
					#	messages.append(message)
					#	print('appending')
					#	point += 1
					#else:
					await client.delete_message(message)
					point += 1
					time.sleep(.75)
		#if len(messages) > 0:
		#	print(messages)
		#	await client.delete_messages(messages)

# random xkcd
async def get_xkcd_comic(message,call,cmd,args):
	xkcd_code = args[0] if len(args) > 0 else None
	await client.send_typing(message.channel)
	data = ""
	if xkcd_code == None:
		data = str(requests.get(xkcd_rand).content)
	else:
		data = str(requests.get("http://xkcd.com/{}".format(xkcd_code)).content)

	xkcd_match = re.search(r'<div id="ctitle">(?P<title>[\w ]+).*Permanent\slink\sto\sthis\scomic:\s(?P<link>[^<]+).*Image\sURL\s\(for\shotlinking\/embedding\):\s(?P<url>[^ ]+)<div',data,re.S)
	title,url,link = xkcd_match.group("title"),xkcd_match.group("url")[:-2],xkcd_match.group("link")
	await upload_file(url,"xkcd" + url[-4:],message.channel,"{} (<{}>)".format(title,link))

# fetch the uptime (nicely formmated, thanks to me reinventing the wheel)
async def get_client_uptime(message,call,cmd,args):
	elapsed_time = ", ".join(get_elapsed_time(client.start_time,datetime.utcnow() + utc_offset))
	strtime = client.start_time.strftime(time_format_str)
	await client.send_message(message.channel,"```xl\nSnake has been running for {} ({})\n```".format(elapsed_time,strtime))

# dangerous, runs anything cash reward
async def eval_code(message,call,cmd,args):
	if message.author.id == my_id:
		code = args[0] if len(args) > 0 else None
		if not code == None:
			code = code.strip("`")
			result = "```py\n{}\n```"
			code_result = None
			try:
				code_result = eval(code)
			except Exception as e:
				await client.send_message(message.channel,result.format(type(e).__name__ + ": " + str(e)))
				return
			if asyncio.iscoroutine(code_result):
				code_result = await code_result
			await client.send_message(message.channel,result.format(code_result))

# info about snake
async def get_client_info(message,call,cmd,args):
	user = client.user
	server_names = list(filter(lambda x:not x == "private_channels", list(servers.keys())))
	await client.send_message(message.channel,client_info.format(
		user,
		"{} ago ({})".format(", ".join(get_elapsed_time(user.created_at + utc_offset,datetime.utcnow() + utc_offset)), (user.created_at + utc_offset).strftime(time_format_str)), 
		", ".join(get_elapsed_time(client.start_time,datetime.utcnow() + utc_offset)),
		"{} public channels ({} text, {} voice), {} private channels".format(channel_count,text_channel_count,voice_channel_count,private_channel_count),
		"{} servers ({})".format(server_count,"'" + "', '".join(server_names) + "'"),
		".".join(list(map(str,list(discord.version_info)[:3]))),
		".".join(list(map(str,list(sys.version_info)[:3])))
	))

# link to github
async def get_source(message,call,cmd,args):
	await client.send_message(message.channel,"https://github.com/TickerOfTime/snake")
	
# youtube, 'nuff said
async def play_ytdl(message,call,cmd,args):
	if True:
		if opus_loaded == False:
			await client.send_message(message.channel, "```py\nOpus has not been loaded, cannot continue\n```")
			return
		else:
			yt_code = str(args[0] if len(args) > 0 else None)
			if yt_code.startswith("$"):
				video_data = manage_videos("load",None,yt_code.lstrip("$"))
				if video_data == None:
					await client.send_message(message.channel,"```xl\nVideo '{}' does not exist\n```".format(yt_code.lstrip("$")))
					return
				else:
					yt_code = video_data[1]
			yt_code = yt_code if yt_code.startswith("http") else "https://www.youtube.com/watch?v=" + yt_code
			channel = discord.utils.get(message.server.channels,name=args[1],type=discord.ChannelType.voice) if len(args) > 1 else None
			voice_channel = None
			if channel == None:
				if message.server.id in voice_channels:
					voice_channel = voice_channels[message.server.id]
				else:
					return
			if not yt_code == None:
				if voice_channel == None:
					voice_channel = await join_voice_channel(channel)
				if channel == None:
					quit_on_complete = str(args[1] if len(args) > 1 else None)
				else:
					quit_on_complete = str(args[2] if len(args) > 2 else None)
				print(quit_on_complete)
				if 'yt_player' in voice_channel:
					if voice_channel["yt_player"].is_done() == False:
						await client.send_message(message.channel,"```xl\nCannot play: \"{}\" is playing\n```".format(voice_channel["yt_player"].title))
						return
				async def complete():
					voice_channel["yt_player"].stop()
					if quit_on_complete.lower() in ['yes','on','y']:
						await leave_voice_channel(voice_channel["channel"])
				try:
					voice_channel["yt_player"] = await voice_channel["voice_client"].create_ytdl_player(yt_code, ytdl_options = {"quiet":True},after=asyncio.run_coroutine_threadsafe(complete(),client.loop)) # ,after=asyncio.run_coroutine_threadsafe(complete(),client.loop)
				except Exception as e:
					await client.send_message(message.channel, "```py\nCannot play video\n{}: {}\n```".format(type(e).__name__, str(e)))
					return
				await client.send_message(message.channel, ytdl_info_str.format(voice_channel["yt_player"],voice_channel["channel"]))
				voice_channel["yt_player"].start()

# playx, mange channels
async def manage_voice_channels(message,call,cmd,args):
	if user_is_admin(message.author.id) == True:
		option = args[0] if len(args) > 0 else None
		channel = discord.utils.get(message.server.channels,name=args[1],type=discord.ChannelType.voice) if len(args) > 1 else None
		if (not option == None):
			if option.lower() in ['l','leave','exit']:
				if message.server.id in voice_channels:
					channel = voice_channels[message.server.id]["channel"]
					if not await leave_voice_channel(channel) == False:
						if settings["notify_channel"] == True:
							await client.send_message(message.channel,"```xl\nLeft '{}' on '{}'\n```".format(channel.name,message.server.name))
			elif option.lower() in ['j','join']:
				if not channel == None:
					if not await join_voice_channel(channel) == False:
						if settings["notify_channel"] == True:
							await client.send_message(message.channel,"```xl\nJoined '{}' on '{}'\n```".format(channel.name,message.server.name))
			elif option.lower() in ['m','move','goto']:
				if not channel == None:
					if not await change_voice_channel(channel) == False:
						if settings["notify_channel"] == True:
							await client.send_message(message.channel,"```xl\nMoved to '{}' on '{}'\n```".format(channel.name,message.server.name))
			elif option.lower() in ['s','stop']:
				player = get_currently_playing(message.server.id)[0]
				if not player == None:
					if player.is_playing() == True:
						player.stop()
			elif option.lower() in ['p','pause']:
				player = get_currently_playing(message.server.id)[0]
				if player.is_playing() == True:
					player.pause()
			elif option.lower() in ['r','resume','res']:
				player = get_currently_playing(message.server.id)[0]
				if player.is_playing() == False:
					player.resume()
			elif option.lower() in ['v','vol','volume']:
				player = get_currently_playing(message.server.id)[0]
				set_vol = float(args[1] if len(args) > 1 else 100.0) / 100.0
				player.volume = set_vol

# whats playing? idk, lets see
async def get_playing(message,call,cmd,args):
	data = get_currently_playing(message.server.id)
	player,channel = data[0],data[1]
	if (not player == None) and (not channel == None):
		if hasattr(player,"yt"):
			await client.send_message(message.channel,ytdl_info_str.format(player,channel["channel"]))
	else:
		await client.send_message(message.channel,'```xl\nNo song is currently playing\n```')

# show all settings
async def list_settings(message,call,cmd,args):
	option = str(args[0] if len(args) > 0 else None)
	if option.lower() in settings:
		await client.send_message(message.channel,"```xl\n'{}' is {}\n```".format(option.lower(),"on" if settings[option.lower()] == True else "off"))
	else:
		results = []
		for setting,value in settings.items():
			results.append("'{}' is {}".format(setting,"on" if value == True else "off"))
		await client.send_message(message.channel,"```xl\n{}\n```".format("\n".join(results)))

# get speech text and play it
async def speak_data(message,call,cmd,args):
	if True:
		if opus_loaded == False:
			await client.send_message(message.channel, "```py\nOpus has not been loaded, cannot continue\n```")
			return
		else:
			text = args[0] if len(args) > 0 else None
			channel = discord.utils.get(message.server.channels,name=args[1],type=discord.ChannelType.voice) if len(args) > 1 else None
			voice_channel = None
			if channel == None:
				if message.server.id in voice_channels:
					voice_channel = voice_channels[message.server.id]
				else:
					return
			if not text == None:
				if voice_channel == None:
					voice_channel = await join_voice_channel(channel)
				if 'yt_player' in voice_channel:
					if voice_channel["yt_player"].is_done() == False:
						await client.send_message(message.channel,"```xl\nCannot speak: \"{}\" is playing\n```".format(voice_channel["yt_player"].title))
						return
				if 'ffmpeg_player' in voice_channel:
					if voice_channel["ffmpeg_player"].is_done() == False:
						await client.send_message(message.channel,"```xl\nCannot speak; already speaking\n```")
						return
				catch_error = speak(text,message.server.id)
				if not catch_error == True:
					await client.send_message(message.channel, "```py\nCannot speak\n{}: {}\n```".format(type(catch_error).__name__, str(catch_error)))
					return
				else:
					voice_channels[message.server.id]["ffmpeg_player"].start()

# dudduduuh
async def make_meme(message,call,cmd,args):
	meme_name = args[0] if len(args) > 0 else "None"
	if meme_name.lower() in meme_list:
		text1 = args[1] if len(args) > 1 else None
		text2 = args[2] if len(args) > 2 else None
		if (not text1 == None) and (not text2 == None):
			await client.send_typing(message.channel)
			url = "http://memegen.link/{}/{}/{}.jpg".format(meme_name.lower(),quote(text1.replace(" ","-")),quote(text2.replace(" ","-")))
			await upload_file(url,"{}.jpg".format(meme_name.lower()),message.channel)
	elif meme_name.lower() in ['l','list']:
		result = []
		for sname,name in meme_list.items():
			result.append("{} - {}".format(sname,name))
			if len(result) > 11:
				await client.send_message(message.author,"```xl\n{}\n```".format("\n".join(result)))
				result = []
		await client.send_message(message.author,"```xl\n{}\n```".format("\n".join(result)))

# manage vids
async def manage_user_videos(message,call,cmd,args):
	option = args[0] if len(args) > 0 else None
	yt_name = args[1] if len(args) > 1 else None
	yt_id = args[2] if len(args) > 2 else None
	if not option == None:
		if option.lower() in ['s','save']:
			if (not yt_id == None) and (not yt_name == None):
				manage_videos("save",yt_id,yt_name)
		elif option.lower() in ['del','delete','d']:
			if not yt_name == None:
				manage_videos("remove",None,yt_name)
		elif option.lower() in ['l','ls','list']:
			video_list = manage_videos("list",None,None)
			result = []
			for vid_data in video_list:
				result.append("\"{data[0]}\" - {data[1]}".format(data=vid_data))
			await client.send_message(message.channel,"```xl\n{}\n```".format("\n".join(result)))

# sending cross server chat based on channel
async def send_cross_server(message,call,cmd,args):
	channel_name = args[0] if len(args) > 0 else None
	message_to_send = args[1] if len(args) > 1 else None
	server_name = args[2] if len(args) > 2 else None
	if (not channel_name == None) and (not message_to_send == None):
		if not server_name == None:
			channel = discord.utils.get(client.get_all_channels(),server__name=server_name,name=channel_name)
		else:
			channel = discord.utils.get(client.get_all_channels(),name=channel_name)
		if channel == None and server_name == None:
			await client.send_message(message.channel,"```xl\nChannel '{}' not found\n```".format(channel_name))
			return
		elif  (channel == None) and (not server_name == None):
			await client.send_message(message.channel,"```xl\nChannel '{}' on server '{}' not found\n```".format(channel_name,server_name))
			return
		try:
			await client.send_message(channel,"`{} - #{}`\n**Message from {}#{}:**\n\n{}".format(message.server.name,message.channel.name,message.author.display_name,message.author.discriminator,message_to_send))
		except Exception as e:
			await client.send_message(message.channel,"```py\n{}: {}\n```".format(type(e).__name__,str(e)))

#leave a server
async def leave_server(message,call,cmd,args):
	if message.author.id == my_id:
		server_name = args[0] if len(args) > 0 else None
		if not server_name == None:
			server = discord.utils.get(client.servers,name=server_name)
			if not server == None:
				await client.leave_server(server)
				await client.send_message(message.channel,"```xl\nSuccessfully left '{}'\n```".format(server_name))
			else:
				await client.send_message(message.channel,"```xl\nCannot find server '{}'\n```".format(server_name))

# get a list of permissions
async def get_permissions(message,call,cmd,args):
	permission_list = message.channel.permissions_for(message.server.me)
	fmt = lambda x: "yes" if x == True else "no"
	await client.send_message(message.channel,permission_info_str.format(
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

# summoned to voice
async def goto_voice_channel(message,call,cmd,args):
	if not message.author.voice_channel == None:
		await join_voice_channel(message.author.voice_channel)

# code contest whee
async def create_code_challenge(message,call,cmd,args):
	if message.author.id in challenge_admins:
		method = args[0] if len(args) > 0 else None
		challenge_name = args[1] if len(args) > 1 else None
		challenge_description = args[2] if len(args) > 2 else None
		channel = discord.utils.get(client.get_all_channels(),id="183687020093243392",name="challenges")

		if (not method == None) and (not challenge_name) == None:
			if method.lower() in ['create','c']:
				if not challenge_description == None:
					log_dbcur.execute("INSERT INTO challenges VALUES (?,?,?,?,?)",(message.author.name,message.author.id,challenge_name,challenge_description,"{} UTC".format(datetime.utcnow().strftime(time_format_str))))
					if not channel == None:
						client.send_message(channel,challenge_info_str.format(challenge_name,challenge_description,"{}#{}".format(message.author.display_name,message.author.discriminator),", ".join(allowed_language_list)))
					log_db.commit()
			elif method.lower() in ['remove','r']:
				if not challenge_name == None:
					log_dbcur.execute("SELECT * FROM challenges WHERE challenge_name=?",(challenge_name,))
					log_db.commit()
					challenge = log_dbcur.fetchone()
					if not challenge == None:
						message = discord.utils.find(lambda m: m.content.startswith("__**New Challenge!**__\n**{}**:\n\n{}".format(challenge[2],challenge[3])),await client.logs_from(channel,datetime.strptime(challenge[4],time_format_str)))
						if not message == None:
							await client.delete_message(message)

functions = {
	"quit": snake_quit,
	"set": change_settings,
	"user": toggle_user,
	"help": get_help,
	"invite": get_oauth_url,
	"whois": get_info,
	"docs": get_docs_url,
	"insult": get_insult,
	"notes": edit_tags,
	"game": change_game,
	"clear": remove_snake_messages,
	"xkcd": get_xkcd_comic,
	"uptime": get_client_uptime,
	"eval": eval_code,
	"info": get_client_info,
	"source": get_source,
	"play": play_ytdl,
	"playx": manage_voice_channels,
	"playing": get_playing,
	"list": list_settings,
	"speak": speak_data,
	"meme": make_meme,
	"video": manage_user_videos,
	"chat": send_cross_server,
	"leave": leave_server,
	"permissions": get_permissions,
	"summon": goto_voice_channel,
	"contest": create_code_challenge,
	#"submit": create_challenge_entry
}

@client.event
async def on_ready():
	if not hasattr(client,"start_time"):
		client.start_time = datetime.utcnow() + utc_offset
	update_servers()

@client.event
async def on_server_update(before,after):
	update_servers()

@client.event
async def on_channel_update(before,after):
	update_servers()
	
	
@client.event
async def on_message(message):
	if message.author == client.user or message.author.bot == True:
		return
	await log_message(message)
	if message.content.lower().startswith(("snake", "snek", "snk")):
		args = parse(message.content)
		call = args[0]
		cmd = args[1] if len(args) > 1 else None
		if not cmd == None:
			if cmd.lower() in functions:
				await functions[cmd.lower()](message,call,cmd,[] if len(args) < 3 else args[2::])
			elif settings["enable_ai"] == True:
				result = pb_talk(message.author," ".join(args[1::]))
				if not result == None:
					await client.send_message(message.channel,result)

client.run("")
temp_db.close()
log_db.close()