import subprocess, sqlalchemy

from functools import partial
from discord.ext import commands

from .utils import checks

class Debug:
    def __init__(self, bot):
        self.bot = bot
        self.newline = "\n" # f-strings dont allow backslaches, screw that

    def clean(self, code): # Strip codeblock formatting from the message
        if code.startswith("```") and code.endswith("```"):
            return "\n".join(code.split("\n")[1:-1])
        return code.strip("` \n")

    @commands.command(name="globaldebug", aliases=["globdebug", "gdebug"], pass_context=True, brief="eval across shards")
    @checks.is_owner()
    async def global_debug_statement(self, ctx, *, content:str):
        code = self.clean(content)
        results = await self.bot.shared.global_eval(code, ctx) # bot method to run code across shards
        code_result = "\n".join(f"Shard #**{shard_id}**\n{result}\n" for shard_id, result in results.items()) # comprehension inside f-string expression. messy
        await self.bot.say(code_result)

    @commands.command(name="globalrun", aliases=["globrun", "grun"], pass_context=True, brief="exec across shards")
    @checks.is_owner()
    async def global_run_statement(self, ctx, *, content:str):
        code = self.clean(content)
        results = await self.bot.global_exec(code, ctx) # same thing, just different process
        code_result = "\n".join(f"Shard #**{shard_id}**\n{result}\n" for shard_id, result in results.items())
        await self.bot.say(code_result)

    @commands.command(name="debug", pass_context=True, brief="eval")
    @checks.is_owner()
    async def debug_statement(self, ctx, *, content:str):
        code = self.clean(content)
        results = await self.bot.run_eval(code, ctx) # only one shard, so only one output
        await self.bot.say(results) # only one shard, no comprehension needed

    @commands.command(name="run", pass_context=True, brief="exec")
    @checks.is_owner()
    async def run_statement(self, ctx, *, content:str):
        code = self.clean(content)
        results = await self.bot.run_exec(code, ctx) # just as above
        await self.bot.say(results)


    @commands.command(name="psql", pass_context=True, brief="execute sql")
    @checks.is_owner()
    async def run_sql(self, ctx, *, sql:str):
        sql_command = self.clean(sql)

        if not sql_command.endswith(";"):
            print("adding semicolon")
            sql_command += ";"

        try:
            results = await self.bot.loop.run_in_executor(None, partial(self.bot.db.engine.execute, sql_command)) # run blocking function in a non-blocking way

        except sqlalchemy.exc.ProgrammingError:
            await self.bot.send_message(ctx.message.channel, f"Unable to process statement. Double check your query:\n```sql\n{sql_command}\n```")
            return

        except Exception as e:
            await self.bot.say(f"```diff\n- {type(e).__name__}: {e}") # more f-strings
            return

        if not results.returns_rows:
            result = "Query returned 0 rows"

        else:
            result_list = results.fetchall()
            row_names = results.keys()
            clr = lambda arr: ", ".join(repr(item) for item in arr)
            result = f"```py\n[ {', '.join(row_names)} ]\n--> {len(result_list)} rows <--\n{self.newline.join(clr(arg) for arg in result_list)}\n```" # nasty, horrid messy f-expr
            if len(result) > 1900:
                gist_result = await self.bot.upload_to_gist(result, 'sql.py')
                await self.bot.say(f"Output too long. View results at {gist_result}")
            else:
                await self.bot.say(result)

    @commands.command(name="sys", pass_context=True, brief="system terminal")
    @checks.is_owner()
    async def system_terminal(self, ctx, *, command:str):
        result = await self.bot.loop.run_in_executor(None, partial( # blocking function in non-blocking way
            subprocess.run,
            command,
            stdout=subprocess.PIPE,
            shell=True,
            universal_newlines=True
        ))
        result = result.stdout

        if len(result) > 1900:
            gist_result = await self.bot.upload_to_gist(result, 'output.txt')
            await self.bot.say(f"Output too long. View results at {gist_result}") # bypass 2000 char limit with gist
        else:
            await self.bot.say(f"```py\n{result}\n```")

def setup(bot):
    bot.add_cog(Debug(bot))