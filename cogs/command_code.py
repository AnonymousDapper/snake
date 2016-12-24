import asyncio, contextlib, io, inspect, sys, functools, subprocess, discord, sqlalchemy
from discord.ext import commands
from .utils import checks

@contextlib.contextmanager
def stdoutIO(stdout=None):
  old = sys.stdout
  if stdout == None:
    stdout = io.StringIO()
  sys.stdout = stdout
  yield stdout
  sys.stdout = old

class Debug:
  def __init__(self, bot):
    self.bot = bot

  def clean(self, code):
    if code.startswith("```") and code.endswith("```"):
      return "\n".join(code.split("\n")[1:-1])

    return code.strip("` \n")

  @commands.command(name='debug', pass_context=True, brief="eval")
  @checks.is_owner()
  async def debug_statement(self, ctx, *, content:str):
    result = None
    code = self.clean(content)
    vals = globals()
    vals.update(dict(
      self=self,
      bot=self.bot,
      message=ctx.message,
      ctx=ctx,
      server=ctx.message.server,
      channel=ctx.message.channel,
      author=ctx.message.author,
      code=code,
      io=io,
      sys=sys,
      commands=commands,
      discord=discord
    ))
    try:
      precompiled = compile(code, "eval.py", "eval")
      vals["compiled"] = precompiled
      result = eval(precompiled, vals)
    except Exception as e:
      await self.bot.say("```diff\n- {}: {}\n```".format(type(e).__name__, e))
      return
    if inspect.isawaitable(result):
      result = await result
    if not result is None:
      result = str(result)
      await self.bot.say("```py\n{}\n```".format(result[:1800] + "..." if len(result) > 1800 else result))

  @commands.command(name='sys', brief="sys terminal")
  @checks.is_owner()
  async def terminal_command(self, *, command:str):
    result = await self.bot.loop.run_in_executor(None, functools.partial(subprocess.run, command, stdout=subprocess.PIPE, shell=True, universal_newlines=True))
    result = result.stdout
    await self.bot.say("```\n{}\n```".format(result[:1800] + "..." if len(result) > 1800 else result))

  @commands.command(name="psql", brief="execute sql", pass_context=True)
  @checks.is_owner()
  async def run_sql(self, ctx, *, sql:str):
    #sql_connection = self.bot.db.engine.connect()
    sql_command = self.clean(sql)
    results = None
    try:
      cmd = functools.partial(self.bot.db.engine.execute, sql_command)
      results = await self.bot.loop.run_in_executor(None, cmd)
      print("passed")

    except sqlalchemy.exc.ProgrammingError:
      await self.bot.send_message(ctx.message.channel, "Unable to process statement. Double check your query:\n```sql\n{}\n```".format(sql_command))
      return

    except Exception as e:
      await self.bot.send_message(ctx.message.channel, "```diff\n- {}: {}\n```".format(type(e).__name__, e))
      return

    if not results.returns_rows:
      #result = "Unable to process statement. Double check your query:\n```sql\n{}\n```".format(sql_command)
      result = "Query returned 0 rows"

    else:
      result_list = results.fetchall()
      clr = lambda arr: ", ".join(repr(item) for item in arr)
      result = ("```py\n--> {} rows <--\n{}\n```".format(len(result_list), "\n".join(clr(arg) for arg in result_list)))[:1950]

    print(result)
    await self.bot.send_message(ctx.message.channel, result)

  @commands.command(name='run', pass_context=True, brief="exec")
  @checks.is_owner()
  async def run_code(self, ctx, *, content:str):
    code = self.clean(content)
    code = "async def coro():\n  " + "\n  ".join(code.split("\n"))
    vals = globals()
    vals.update(dict(
      self=self,
      bot=self.bot,
      message=ctx.message,
      ctx=ctx,
      server=ctx.message.server,
      channel=ctx.message.channel,
      author=ctx.message.author,
      io=io,
      code=code,
      sys=sys,
      commands=commands,
      discord=discord
    ))
    with stdoutIO() as s:
      try:
        precompiled = compile(code, "exec.py", "exec")
        vals["compiled"] = precompiled
        result = exec(precompiled, vals)
        await vals["coro"]()
      except Exception as e:
        await self.bot.say("```diff\n- {}: {}\n```".format(type(e).__name__, e))
        return
    result = str(s.getvalue())
    if not result == "":
      await self.bot.say("```py\n{}\n```".format(result[:1800] + "..." if len(result) > 1800 else result))



def setup(bot):
  bot.add_cog(Debug(bot))