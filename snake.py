#/user/bin/env python3
""" Discord API 'snake'"""

"""
MIT License

Copyright (c) 2016 AnonymousDapper (TickerOfTime)

Permission is hereby granted
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

# discord: pip install -U git+https://github.com/Rapptz/discord.py@master#egg=discord.py[voice]

# Imports
import discord, asyncio, os, logging, sys, traceback, aiohttp, json
from random import choice as rand_choice
from bs4 import BeautifulSoup as b_soup
from discord.ext import commands
from datetime import datetime

from cogs.utils import config, time, checks
from cogs.utils.colors import paint, back, attr

# Library logging
discord_logger = logging.getLogger("discord")
discord_logger.setLevel(logging.ERROR)


class SnakeBot(commands.Bot):
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.config = config.Config("config.json")
		self.credentials = config.Config("credentials.json")
		self.whitelist = config.Config("whitelist.json")
		self.blacklist = config.Config("blacklist.json")
		self.tag_list = config.Config("tags.json")
		self.cust_ids = {}
		self.boot_time = datetime.now()
		self.commands_used = {}
		self.color_emoji = lambda e: "{}{}".format(e, rand_choice(["", "\N{EMOJI MODIFIER FITZPATRICK TYPE-1-2}", "\N{EMOJI MODIFIER FITZPATRICK TYPE-3}", "\N{EMOJI MODIFIER FITZPATRICK TYPE-4}", "\N{EMOJI MODIFIER FITZPATRICK TYPE-5}", "\N{EMOJI MODIFIER FITZPATRICK TYPE-6}"]))

		for filename in os.listdir("cogs"):
			if os.path.isfile("cogs/" + filename) and filename.startswith("command_"):
				name = filename[8:-3]
				cog_name = "cogs.command_" + name
				try:
					self.load_extension(cog_name)
				except Exception as e:
					print("Failed to load {}: [{}]: {}".format(paint(name, "red"), type(e).__name__, e))

		self.log = logging.getLogger()
		self.log.setLevel(logging.INFO)
		self.log.addHandler(
			logging.FileHandler(filename="snake.log", encoding="utf-8", mode='w')
		)

	async def chat(self, user : discord.User, text):
		user_id = user.id
		chat_data = {"botid": self.config.get("pb_bot_id"), "input": text}
		if user_id in self.cust_ids:
			chat_data.update({"custid": self.cust_ids[user_id]})

		async def fetch():
			with aiohttp.ClientSession() as session:
				async with session.post("http://www.pandorabots.com/pandora/talk-xml", data=chat_data) as response:
					if response.status != 200:
						return response.status
					response_text = await response.text()
					chat_soup = b_soup(response_text, "lxml")
					cust_id = chat_soup.find("result")["custid"]
					answer = chat_soup.find("that").text.strip()
					self.cust_ids[user_id] = cust_id
					return answer

		success = False
		while not success:
			chat_result = await fetch()
			if isinstance(chat_result, str):
				success = True
				return chat_result
			else:
				self.log.warning("Could not fetch chat data, retrying. [{}]".format(chat_result))

	async def update_servers(self):
		results = [False, False]

		bots_headers = {
			"Authorization": self.credentials.get("bots_token"),
			"Content-Type": "application/json"
		}

		bots_data = json.dumps({
			"server_count": len(self.servers)
		})

		carbon_data = {
			"servercount": len(self.servers),
			"key": self.credentials.get("carbon_key")
		}

		with aiohttp.ClientSession() as session:
			async with session.post("https://bots.discord.pw/api/bots/{0.user.id}/stats".format(self), headers=bots_headers, data=bots_data) as response:
				if str(response.status)[0] == '2':
					js = await response.json()
					if "error" not in js:
						results[0] = True

			async with session.post("https://www.carbonitex.net/discord/data/botdata.php", data=carbon_data) as response:
				if str(response.status)[0] == '2':
					text = await response.text()
					if text == "1 - Success":
						results[1] = True
		return results

	async def post_log(self, content):
		channel = self.get_channel("234512725554888705")
		if channel is not None:
			try:
				await self.send_message(channel, content)
			except:
				pass

	async def on_command_error(self, error, ctx):
		if isinstance(error, commands.NoPrivateMessage):
			await self.send_message(ctx.message.author, "You cannot use this command in a private message")

		elif isinstance(error, commands.DisabledCommand):
			await self.send_message(ctx.message.author, "This command is disabled")

		elif isinstance(error, commands.CommandOnCooldown):
			await self.send_message(ctx.channel, "{} slow down! Try again in {:.1f} seconds".format(ctx.author.mention, error.retry_after))

		elif isinstance(error, commands.CommandInvokeError):
			original_name = error.original.__class__.__name__
			print("In {}:".format(paint(ctx.command.qualified_name, "red")))
			traceback.print_tb(error.original.__traceback__)
			print("{}: {}".format(paint(original_name, "red"), error.original))

		# Bad or missing argument alerts??
		else:
			print("{}: {}".format(paint(type(error).__name__, "red"), error))

	async def on_command(self, command, ctx):
		if command.name not in self.commands_used:
			self.commands_used[command.name] = 0
		else:
			self.commands_used[command.name] += 1
		message = ctx.message
		destination = None
		if message.channel.is_private:
			destination = "Private Message"
		else:
			destination = "[{0.server.name} #{0.channel.name}]".format(message)
		self.log.info("{1}: {0.author.name}: {0.clean_content}".format(message, destination))

	async def on_message(self, message):
		if not message.channel.is_private:
			if message.author.bot or message.channel.id in self.blacklist.get("channel_ignore") or message.server.id in self.blacklist.get("server_ignore"):
				return

			if (message.content.startswith(self.user.mention) and message.author.id not in self.blacklist.get("chat")) or message.channel.id in self.whitelist.get("chat"):
				chat_text = " ".join(message.clean_content.split()[1:])
				response = await self.chat(message.author, chat_text)
				await self.send_message(message.channel, response)
				return

			if "(╯°□°）╯︵ ┻━┻" in message.clean_content and message.server.id in self.whitelist.get("unflip"):
				await self.send_message(message.channel, "┬─────────────────┬ ノ(:eye:▽:eye:ノ)")


		if message.author.id not in self.blacklist.get("command"):
			await self.process_commands(message)

	async def on_ready(self):
		print("Logged in as {}#{} [{}]".format(paint(self.user.name, "cyan"), paint(self.user.discriminator, "yellow"), paint(self.user.id, "green")))
		self.start_time = datetime.now()
		self.boot_duration = time.get_ping_time(self.boot_time, self.start_time)
		print("Loaded in {}".format(self.boot_duration))

	async def on_server_join(self, server):
		await self.post_log("Joined **{0.name}** [{0.id}] (owned by **{0.owner.display_name}**#{0.owner.discriminator} [{0.owner.id}]) ({1} total servers)".format(server, len(self.servers)))
		await self.update_servers()

	async def on_server_remove(self, server):
		await self.post_log("Left **{0.name}** [{0.id}] (owned by **{0.owner.display_name}**#{0.owner.discriminator} [{0.owner.id}]) ({1} total servers)".format(server, len(self.servers)))
		await self.update_servers()

bot = SnakeBot(command_prefix="snake ", description="\nHsss! Go to discord.gg/qC4ancm for help!\n", help_attrs=dict(hidden=True), command_not_found="Command '{}' does not exist", command_has_no_subcommands="Command '{0.name}'' does not have any subcommands")

@bot.group(invoke_without_command=True, name="cog", brief="manage cogs")
@checks.is_owner()
async def manage_cogs(name : str, action : str):
	cog_name = "cogs.command_" + name
	print(cog_name, bot.extensions.get(cog_name), action)
	action = action.lower()
	if action == "load":
		if bot.extensions.get(cog_name) is not None:
			await bot.say("Cog `{}` is already loaded".format(name))
			return
		try:
			bot.load_extension(cog_name)
		except Exception as e:
			await bot.say("Failed to load `{}`: [{}]: {}".format(name, type(e).__name__, e))
			return
		await bot.say("Loaded `{}`".format(name))

	elif action == "unload":
		if bot.extensions.get(cog_name) is None:
			await bot.say("Cog `{}` is not loaded".format(name))
			return
		try:
			bot.unload_extension(cog_name)
		except Exception as e:
			await bot.say("Failed to unload `{}`: [{}]: {}".format(name, type(e).__name__, e))
			return
		await bot.say("Unloaded `{}`".format(name))

	elif action == "reload":
		if bot.extensions.get(cog_name) is None:
			await bot.say("Cog `{}` is not loaded".format(name))
			return
		try:
			bot.unload_extension(cog_name)
			bot.load_extension(cog_name)
		except Exception as e:
			await bot.say("Failed to reload `{}`: [{}]: {}".format(name, type(e).__name__, e))
			return
		await bot.say("Reloaded `{}`".format(name))



@manage_cogs.command(name="list", brief="list cogs")
async def list_cogs(name : str = None):
	if name is None:
		await bot.say("Currently loaded cogs:\n{}".format(" ".join('`' + cog_name + '`' for cog_name in bot.extensions)) if len(bot.extensions) > 0 else "No cogs loaded")
	else:
		cog_name = "cogs.command_" + name
		await bot.say("`{}` {} loaded".format(cog_name, "is not" if bot.extensions.get(cog_name) is None else "is"))

@bot.command(brief="exit")
@checks.is_owner()
async def quit():
	await bot.logout()

bot.run(bot.credentials.get("token"))

'''
           ╔ ╗
         ╔ ╔ ╗ ╗
       ╔ ╔ ╔ ╗ ╗ ╗
     ╔ ┌─┬─┐ ┌─┬─┐ ╗
    ║──┤ │ ├─┤ │ ├─ ║
    ╠══│ ├─┼─┼─┤ │══╣
    ║──┤ │ ├─┤ │ ├──║
    ╠══│ ├─┼─┼─┤ │══╣
   ╔╣_______________╠╗
   ║║▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄║║
   ║║/|\|/|\|/|\|/|\║║
   ║║¯¯¯¯¯¯¯¯¯¯¯¯¯¯¯║║
  'WW'             'WW'

'''