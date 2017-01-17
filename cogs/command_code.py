import subprocess, sqlalchemy

from functools import partial
from discord.ext import commands

from .utils import checks

class Debug:
    def __init__(self, bot):
        self.bot = bot
        self.newline = "\n"

    def clean(self, code):
        if code.startswith("```") and code.endswith("```"):
            return "\n".join(code.split("\n")[1:-1])
        return code.strip("` \n")

    @commands.command(name="debug", pass_context=True, brief="eval")
    @checks.is_owner()
    async def debug_statement(self, ctx, *, content:str):
        code = self.clean(content)
        results = await self.shared.global_eval(code, ctx)
        code_result = "\m".join(f"Shard #{shard_id}\n{result}\n" for shard_id, result in results.items())
        await self.bot.say(code_result)

    @commands.command(name="run", pass_context=True, brief="exec")
    @checks.is_owner()
    async def run_statement(self, ctx, *, content:str):
        code = self.clean(content)
        results = await self.shared.global_exec(code, ctx)
        code_result = "\m".join(f"Shard #{shard_id}\n{result}\n" for shard_id, result in results.items())
        await self.bot.say(code_result)

    @commands.command(name="psql", pass_context=True, brief="execute sql")
    @checks.is_owner()
    async def run_sql(self, ctx, *, sql:str):
        sql_command = self.clean(sql)
        try:
            results = await self.bot.loop.run_in_executor(None, partial(self.bot.db.engine.execute, sql_command))

        except sqlalchemy.exc.ProgrammingError:
            await self.bot.say(f"Unable to process statement. Double check your query:\n```sql\m{sql_command}\n```")
            return

        except Exception as e:
            await self.bot.say(f"```diff\n- {type(e).__name__}: {e}")
            return

        if not results.returns_rows:
            result = "Query returned 0 rows"

        else:
            result_list = results.fetchall()
            clr = lambda arr: ", ".join(repr(item) for item in arr)
            result = f"```py{n}{', '.join(row_names)}\n--> {len(result_list)} rows <--\n{self.newline.join(clr(arg) for arg in result_list)}\n```"
            if len(result) > 1900:
                await self.bot.say(f"Output too long. View results at {self.upload_to_gist(result, 'exec.py')}")
            else:
                await self.bot.say(f"```py\n{result}\n```")

    @commands.command(name="sys", pass_context=True, brief="system terminal")
    @checks.is_owner()
    async def system_terminal(self, ctx, *, command:str):
        result = await self.bot.loop.run_in_executor(None, partial(
            subprocess.run,
            command,
            stdout=subprocess.PIPE,
            shell=True,
            universal_newlines=True
        ))
        result = result.stdout

        if len(result) > 1900:
            await self.bot.say(f"Output too long. View results at {self.upload_to_gist(result, 'exec.py')}")
        else:
            await self.bot.say(f"```py\n{result}\n```")

def setup(bot):
    bot.add_cog(Debug(bot))