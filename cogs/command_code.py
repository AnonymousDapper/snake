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

    @commands.command(name="debug", brief="eval")
    @checks.is_owner()
    async def debug_statement(self, ctx, *, content:str):
        code = self.clean(content)
        results = await self.bot.run_eval(code, ctx) # only one shard, so only one output
        await ctx.send(results) # only one shard, no comprehension needed

    @commands.command(name="run", brief="exec")
    @checks.is_owner()
    async def run_statement(self, ctx, *, content:str):
        code = self.clean(content)
        results = await self.bot.run_exec(code, ctx) # just as above
        await ctx.send(results)

    @commands.command(name="sql", brief="execute sql")
    @checks.is_owner()
    async def run_sql(self, ctx, *, sql:str):
        sql_command = self.clean(sql)

        if not sql_command.endswith(";"):
            sql_command += ";"

        try:
            results = await self.bot.loop.run_in_executor(None, partial(self.bot.db.engine.execute, sql_command)) # run blocking function in a non-blocking way

        except sqlalchemy.exc.ProgrammingError as e:
            await ctx.send(f"```diff\n- {e.orig.message}\n```\n{e.orig.details.get('hint', 'Unknown fix')}\n\nDouble check your query:\n```sql\n{e.statement}\n{' ' * (int(e.orig.details.get('position', '0')) - 1)}^\n```")
            return

        except Exception as e:
            await ctx.send(f"```diff\n- {type(e).__name__}: {e}") # more f-strings
            return

        if not results.returns_rows:
            result = "Query returned 0 rows"

        else:
            result_list = results.fetchall()
            row_names = results.keys()
            clr = lambda arr: ", ".join(str(item) for item in arr)
            result = f"# Columns: {', '.join(row_names)}\n# {len(result_list)} total rows\n\n{self.newline.join('- ' + clr(arg) for arg in result_list)}" # nasty, horrid messy f-expr
            if len(result) > 1900:
                gist_result = await self.bot.upload_to_gist(result, 'sql.md', title="SQL Results")
                await ctx.send(f"Output too long. View results at {gist_result}")
            else:
                await ctx.send(f"```md\n{result}\n```")

    @commands.command(name="sys", brief="system terminal")
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
            await ctx.send(f"Output too long. View results at {gist_result}") # bypass 2000 char limit with gist
        else:
            await ctx.send(f"```py\n{result}\n```")

def setup(bot):
    bot.add_cog(Debug(bot))