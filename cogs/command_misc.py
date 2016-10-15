import discord, aiohttp, re
from bs4 import BeautifulSoup as b_s
from urllib.parse import quote_plus
from datetime import datetime
from random import choice
from discord.ext import commands
from .utils import checks, time

suggest_text = '''
Suggestion from **{0.display_name}**#{0.discriminator} [{0.id}]
**{1.server.name}** #**{1.name}**

{2}
'''

class Misc:
  def __init__(self, bot):
    self.bot = bot

  @commands.command(name="retro", brief="make retro text")
  async def make_retro(self, *, content : str):
    texts = [t.strip() for t in content.split('|')]
    if len(texts) != 3:
      await self.bot.say("\N{CROSS MARK} please provide three strings seperated by `|`")
      return

    await self.bot.type()

    data = dict(
      bcg=choice([1, 2, 3, 4]),
      txt=choice([1, 2, 3, 4]),
      text1=texts[0],
      text2=texts[1],
      text3=texts[2]
    )

    with aiohttp.ClientSession() as session:
      async with session.post("http://photofunia.com/effects/retro-wave", data=data) as response:
        if response.status == 200:
          soup = b_s(await response.text(), "lxml")
          download_url = soup.find("div", class_="downloads-container").ul.li.a["href"]
          async with session.get(download_url) as image_response:
            if image_response.status == 200:
              image_data = await image_response.read()
              with BytesIO(image_data) as temp_image:
                await self.bot.upload(temp_image, filename="retro.jpg")

  @commands.command(name="xkcd", brief="get an xkcd comic")
  async def get_xkcd(self, id : str = ''):
    await self.bot.type()
    if id == '':
      url = "http://c.xkcd.com/random/comic/"
    else:
      url = "http://xkcd.com/{}".format(id)
    with aiohttp.ClientSession() as session:
      async with session.get(url) as response:
        if response.status != 200:
          await self.bot.say("Could not fetch comic `{}` (HTTP {})".format(url, response.status))
          return
        page = await response.text()
        soup = b_s(page, "lxml")
        comic = soup.find("div", id="comic").img
        comic_text = comic["title"]
        link_group = re.search(r"Permanent link to this comic: (?P<link>.+)", soup.text).group("link")
        comic_title = comic["alt"]
        comic_image_url = "http:" + comic["src"]
        async with session.get(comic_image_url) as image:
          image_data = await image.read()
          image_name = "cache/{}".format(comic_image_url[28:])
          with open(image_name, "wb") as f:
            f.write(image_data)
          await self.bot.upload(image_name, filename=comic_image_url[28:], content="**{}** (<{}>):\n{}".format(comic_title, link_group, comic_text))

  @commands.command(name="uptime", brief="show uptime")
  async def get_uptime(self):
    uptime = time.get_elapsed_time(self.bot.start_time, datetime.now())
    await self.bot.say("Snake has been running for **{}** ({})".format(uptime, self.bot.start_time.strftime(time.time_format)))

  @commands.command(name="suggest", brief="suggest a feature, or give complaints", pass_context=True, no_pm=True)
  @commands.cooldown(1, 30, commands.BucketType.user)
  async def feedback(self, ctx, *, message : str):
    # TODO: blacklist
    app_info = await self.bot.application_info()
    author = ctx.message.author
    channel = ctx.message.channel
    try:
      await self.bot.send_message(app_info.owner, suggest_text.format(author, channel, message))
    except Exception as e:
      await self.bot.reply("your message could not be delivered. Please report this information to the bot owners:\n`[{}]: {}`".format(type(e).__name__, e))
    else:
      await self.bot.reply("your message was delivered successfully!")

  @commands.command(name="emoji", brief="ask about a topic")
  async def get_emoji(self, *, query : str):
    with aiohttp.ClientSession() as session:
      async with session.get("https://api.getdango.com/api/emoji", params=dict(q=quote_plus(query))) as response:
        if response.status != 200:
          await self.bot.say("Could not find emoji: (HTTP {})".format(response.status))
          return
        emojis = await response.json()
        await self.bot.say(" ".join(x["text"] for x in emojis["results"]))

  @commands.command(name="invite", brief="invite snake to your server")
  async def get_invite(self):
    permissions = discord.Permissions(permissions=238537777)
    oauth_link = discord.utils.oauth_url("181584771510566922", permissions=permissions)
    await self.bot.say("Invite me with this link!\n" + oauth_link)

def setup(bot):
  bot.add_cog(Misc(bot))