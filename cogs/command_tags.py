from discord.ext import commands
from .utils.tag_manager import parser as tag_parser


class TagOverrides(tag_parser.TagFunctions):
  def __init__(self, bot, tag):
    super().__init__()
    self.bot = bot
    self.tag = tag

  def log(self):
    print(self, self.bot, self.tag)


class Tags:
  def __init__(self, bot):
    self.bot = bot

  @commands.group(name="tag", brief="tag manager")
  async def tag_group(self):
    print("tag group")

  @tag_group.command(name="test", brief="run a test parser", pass_context=True)
  async def test_tag(self, ctx, *, text : str):
    try:
       parser = tag_parser.Parser(text, debug=self.bot._DEBUG)
       result = await parser()
    except Exception as e:
      await self.bot.say("```diff\n- [{}]: {}\n```".format(type(e).__name__, e))
      return
    await self.bot.say(str(result))

def setup(bot):
    bot.add_cog(Tags(bot))