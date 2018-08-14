# MIT License
#
# Copyright (c) 2018 AnonymousDapper
#
# Permission is hereby granted
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import inspect
import os
import sqlalchemy
import subprocess

from functools import partial

from discord.ext import commands

from .utils import checks
from .utils.logger import get_logger

logger = get_logger()

class Debug:
    def __init__(self, bot):
        self.bot = bot

        self.NL = "\n" # for embedding in f-strings

    # Strip formatting from codeblocks
    def clean(self, code):
        if code.startswith("```") and code.endswith("```"):
            return "\n".join(code.split("\n")[1:-1])

        return code.strip("` \n")

    # Utility function for length checking and uploading if required
    async def check_length(self, content):
        if len(content) > 2000:
            url = await self.bot.paste_text(self.clean(content))
            return f"\N{WARNING SIGN} Output too long. View result at <{url}>"

        else:
            return content

    # Utility function to eval code
    async def do_eval(self, scope, code):
        try:
            compiled = compile(code, "<eval>", "eval")
            scope["__compiled"] = compiled

            result = eval(compiled, scope)

        except SyntaxError as e:
            return True, f"```py\n{e.text}\n{'^':>{e.offset}}\n{type(e).__name__}: {e}\n```"

        except Exception as e:
            return True, f"```md\n- {type(e).__name__}: {e}\n```"

        else:
            if inspect.isawaitable(result):
                result = await result

            return False, result

    # Utility function to exec code
    async def do_exec(self, scope, code, raw=False):
        with self.bot.stdout_wrapper() as stdout, self.bot.stderr_wrapper() as stderr:
            try:
                compiled = compile(code, "<exec>", "exec")
                scope["__compiled"] = compiled

                exec(compiled, scope)

                raw_result = await scope["__coro"]()

            except SyntaxError as e:
                return True, f"```py\n{e.text}\n{'^':>{e.offset}}\n{type(e).__name__}: {e}\n```"

            except Exception as e:
                return True, f"```md\n- {type(e).__name__}: {e}\n```"

        result_out = str(stdout.getvalue())
        result_err = str(stderr.getvalue())

        result = f"```py\n{result_out}\n{('########## Errors ##########' + self.NL + result_err) if result_err != '' else ''}\n```"

        if not raw:
            return False, result

        else:
            return False, raw_result

    # Utility function to scrape information from a code result
    def get_info(self, result):
        info = []
        header = repr(result).replace("`", "\u200B")

        info.append(("Type", type(result).__name__))
        info.append(("Memory", hex(id(result))))

        # Get module name
        try:
            info.append(("Module", inspect.getmodule(result).__name__))

        except (TypeError, AttributeError) as e:
            logger.warn(f"{type(e).__name__}: {e}")

        # Get source file
        try:
            location = inspect.getfile(result)

        except TypeError as e:
            logger.debug(f"{type(e).__name__}: {e}")

        else:
            cwd = os.getcwd()

            if location.startswith(cwd):
                location = "." + location[len(cwd):]

            info.append(("File", location))

        # Get source lines
        try:
            source_lines, source_offset = inspect.getsourcelines(result)

        except (OSError, TypeError) as e:
            logger.debug(f"{type(e).__name__}: {e}")

        else:
            info.append(("Lines", f"{source_offset}-{source_offset + len(source_lines)}"))

        # Get signature
        try:
            signature = inspect.signature(result)

        except (TypeError, AttributeError, ValueError) as e:
            logger.debug(f"{type(e).__name__}: {e}")

        else:
            info.append(("Signature", str(signature)))

        # Get inheritance
        if inspect.isclass(result):
            obj = result

        else:
            obj = type(result)

            try:
                info.append(("Inheritance", " -> ".join(x.__name__ for x in inspect.getmro(obj))))

            except (TypeError, AttributeError) as e:
                logger.debug(f"{type(e).__name__}: {e}")

        # Get length
        if isinstance(result, (str, tuple, list, bytes)):
            info.append(("Length", len(result)))

        flat_info = "\n".join(f"{x:14.14} :: {y}" for x, y in info)
        return f"```prolog\n{header}\n\n==== Data ====\n\n{flat_info}\n```"

    # Run code in eval mode
    @commands.command(name="debug", brief="eval mode")
    @checks.is_owner()
    async def run_debug(self, ctx, *, code:str):
        source = self.clean(code)

        scope = globals()
        scope.update(dict(
            self=self,
            bot=self.bot,
            message=ctx.message,
            guild=ctx.guild,
            channel=ctx.channel,
            author=ctx.author,
            ctx=ctx,
            __code=source
        ))

        error, result = await self.do_eval(scope, source)

        if not error:
            result = await self.check_length(f"```py\n{result}\n```")

        await ctx.send(result)

    # Run code in exec mode
    @commands.command(name="run", brief="exec mode")
    @checks.is_owner()
    async def run_exec(self, ctx, *, code:str):
        source = "async def __coro():\n  " + "\n  ".join(self.clean(code).split("\n"))

        scope = globals()
        scope.update(dict(
            self=self,
            bot=self.bot,
            message=ctx.message,
            guild=ctx.guild,
            channel=ctx.channel,
            author=ctx.author,
            ctx=ctx,
            __code=source
        ))

        error, result = await self.do_exec(scope, source)

        if not error:
            result = await self.check_length(result)

        await ctx.send(result)

    # Run SQL query
    @commands.command(name="sql", brief="execute sql")
    @checks.is_owner()
    async def run_sql(self, ctx, *, query:str):
        sql = self.clean(query)

        if not sql.endswith(";"):
            sql += ";"

        try:
            results = await self.bot.loop.run_in_executor(None, partial(self.bot.db.engine.execute, sql))


        except sqlalchemy.exc.ProgramingError as e:
            await ctx.send(f"```diff\n- {e.orig.message}\n```\n{e.orig.details.get('hint', 'Unknown fix')}\n\nDouble check your query:\n```sql\n{e.statement}\n{' ' * (int(e.orig.details.get('position', '0')) - 1)}^\n```")
            return

        except Exception as e:
            await ctx.send(f"```diff\n- {type(e).__name__}: {e}\n```")
            return

        if not results.returns_rows:
            await self.bot.post_reaction(ctx.message, success=True)

        else:
            result_list = results.fetchall()

            if len(result_list) == 0:
                await ctx.send("\N{WARNING SIGN} Query returned 0 rows")

            else:
                row_names = results.keys()

                # format a list of items
                clr = lambda arr: ", ".join(str(item) for item in arr)

                # f-string to format total result lsit
                result = f"```md\n# Columns: {', '.join(row_names)}\n# {len(result_list)} total rows\n\n{self.NL.join('- ' + clr(arg) for arg in result_list)}\n```"

                await ctx.send(await self.check_length(result))

    # Run shell commands
    @commands.command(name="sh", brief="system terminal")
    @checks.is_owner()
    async def run_shell(self, ctx, *, command:str):
        command = self.clean(command)

        result = await self.bot.loop.run_in_executor(None,
            partial(
                subprocess.run,
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                shell=True,
                universal_newlines=True
            )
        )

        out_result = result.stdout
        err_result = result.stderr
        result = f"```diff\n+ ----- stdout -----\n{out_result}\n{('- ----- stderr -----' + self.NL + err_result) if err_result != '' else ''}\n```"

        await ctx.send(await self.check_length(result))

    # Expression inspection group
    @commands.group(name="inspect", brief="inspect an expression", invoke_without_command=True)
    @checks.is_owner()
    async def inspect_group(self, ctx, *, expression:str):
        await ctx.invoke(self.inspect_debug, code=expression)

    @inspect_group.command(name="debug", brief="inspect an eval result")
    @checks.is_owner()
    async def inspect_debug(self, ctx, *, code:str):
        source = self.clean(code)

        scope = globals()
        scope.update(dict(
            self=self,
            bot=self.bot,
            message=ctx.message,
            guild=ctx.guild,
            channel=ctx.channel,
            author=ctx.author,
            ctx=ctx,
            __code=source
        ))

        error, result = await self.do_eval(scope, source)

        if error:
            await ctx.send(result)

        else:
            await ctx.send(self.get_info(result))

    @inspect_group.command(name="run", brief="inspect an exec result")
    @checks.is_owner()
    async def inspect_run(self, ctx, *, code:str):
        source = "async def __coro():\n  " + "\n  ".join(self.clean(code).split("\n"))

        scope = globals()
        scope.update(dict(
            self=self,
            bot=self.bot,
            message=ctx.message,
            guild=ctx.guild,
            channel=ctx.channel,
            author=ctx.author,
            ctx=ctx,
            __code=source
        ))

        error, result = await self.do_exec(scope, source, raw=True)

        if error:
            await ctx.send(result)

        else:
            await ctx.send(self.get_info(result))

# Extension setup
def setup(bot):
    bot.add_cog(Debug(bot))